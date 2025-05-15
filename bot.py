from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
import time
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import os
import datetime

from parser import parse_response
from config import *

from dotenv import load_dotenv
load_dotenv()

GEOGUESSR_URL = "https://www.geoguessr.com"

# Singleplayer
INITIAL_PLAY_BUTTON_XPATH = "/html/body/div/div[2]/div[3]/div[1]/main/div/div/div/div[2]/div[2]/div/div[6]/div/div/div/button"
NMPZ_BUTTON_XPATH = "/html/body/div/div[2]/div[3]/div[1]/main/div/div/div/div[2]/div[2]/div/div[3]/button[3]"
START_GAME_AFTER_NMPZ_BUTTON_XPATH = "/html/body/div/div[2]/div[3]/div[1]/main/div/div/div/div[2]/div[2]/div/div[6]/div/div/div/button"
GAME_RUNNING_INDICATOR_SELECTOR = ".slanted-wrapper_root__XmLse"

# Panorama
PANO_CONTAINER_ID = "panorama-container"
PANO_LOADING_SELECTOR = ".fullscreen-spinner_root__gtDP1"

# Duel specific selectors
DUEL_ACTIVE_INDICATOR_SELECTOR = ".duels_root__A75Oi"
DUEL_ENDED_INDICATOR_SELECTOR = ".game-finished_container__HOD2O"
DUELS_GUESS_BUTTON_SELECTOR = ".guess-map_guessButton__iZNh5 button.button_button__aR6_e"

VIEW_RESULTS_BUTTON_SELECTOR = ".round-result_actions__45WOU button.button_button__aR6_e"
NEW_GAME_BUTTON_SELECTOR = ".standard-final-result_primaryButton__hJeQb button.button_button__aR6_e"

HP_CLASS_NAME = "health-bar_livesLabel__qONTf"

def get_duel_hp(driver: WebDriver) -> tuple[int | None, int | None]:
    """
    Reads the HP of the player and the opponent from the duel health bars.
    The first health bar found with the class is assumed to be the player's,
    and the second is the opponent's. Waits for text to be present in labels.

    Args:
        driver: The Selenium WebDriver instance.

    Returns:
        A tuple (my_hp, opponent_hp). Values can be None if HP cannot be read.
    """
    my_hp = None
    opponent_hp = None
    
    raw_my_hp_text = ""
    raw_opponent_hp_text = ""

    try:
        def hp_labels_are_ready(d):
            elements = d.find_elements(By.CLASS_NAME, HP_CLASS_NAME)
            if len(elements) >= 2:
                text1 = (elements[0].get_attribute('textContent') or "").strip()
                if not text1:
                    text1 = (elements[0].text or "").strip()

                text2 = (elements[1].get_attribute('textContent') or "").strip()
                if not text2:
                    text2 = (elements[1].text or "").strip()
                
                return (text1 and any(char.isdigit() for char in text1)) and \
                       (text2 and any(char.isdigit() for char in text2))
            return False

        WebDriverWait(driver, 10, 0.5).until(hp_labels_are_ready) # Wait up to 10 seconds

        hp_elements = driver.find_elements(By.CLASS_NAME, HP_CLASS_NAME)

        if len(hp_elements) >= 2:
            raw_my_hp_text = (hp_elements[0].get_attribute('textContent') or "").strip()
            if not raw_my_hp_text:
                raw_my_hp_text = (hp_elements[0].text or "").strip()

            raw_opponent_hp_text = (hp_elements[1].get_attribute('textContent') or "").strip()
            if not raw_opponent_hp_text:
                raw_opponent_hp_text = (hp_elements[1].text or "").strip()

            if raw_my_hp_text and any(char.isdigit() for char in raw_my_hp_text):
                my_hp = int("".join(filter(str.isdigit, raw_my_hp_text)))
            else:
                print(f"Player HP text is empty or invalid: '{raw_my_hp_text}'")


            if raw_opponent_hp_text and any(char.isdigit() for char in raw_opponent_hp_text):
                opponent_hp = int("".join(filter(str.isdigit, raw_opponent_hp_text)))
            else:
                print(f"Opponent HP text is empty or invalid: '{raw_opponent_hp_text}'")
        else:
            print(f"Could not find two HP elements with class '{HP_CLASS_NAME}' after robust wait. Found {len(hp_elements)}.")

    except TimeoutException:
        print(f"Timeout waiting for HP labels with class '{HP_CLASS_NAME}' to have valid text content.")
    except Exception as e:
        print(f"An error occurred while reading HP: {e}")
        import traceback
        traceback.print_exc()

    return my_hp, opponent_hp

def hide_elements_by_class_name(driver: webdriver.Remote, class_names_to_hide: list):
    """
    Hides elements on the page that match the given CSS class names.

    Args:
        driver: The Selenium WebDriver instance.
        class_names_to_hide: A list of CSS class names of the elements to hide.
    """
    for class_name in class_names_to_hide:
        try:
            # Find all elements with the given class name
            elements = driver.find_elements(By.CLASS_NAME, class_name)
            if elements:
                for element_to_hide in elements:
                    try:
                        driver.execute_script("arguments[0].style.display = 'none';", element_to_hide)
                        # print(f"Hid element with class: {class_name}")
                    except Exception as e:
                        pass
                        # print(f"Could not hide an element with class {class_name} (already hidden or stale?): {e}")
                # if not elements: # Double check if list was actually empty after potential exceptions
                    # print(f"No elements found with class name: {class_name}")
            else:
                pass
                # print(f"No elements found with class name: {class_name}")
        except NoSuchElementException:
            print(f"No elements found with class name: {class_name} (NoSuchElementException)")
        except Exception as e:
            print(f"An error occurred while trying to hide elements with class {class_name}: {e}")

def wait_for_page_load(driver: WebDriver, timeout: int = 30):
    """Waits for the page to be fully loaded."""
    WebDriverWait(driver, timeout).until(
        lambda drv: drv.execute_script('return document.readyState') == 'complete'
    )
    time.sleep(0.5)

def capture_screenshot(driver: WebDriver):
    """Captures a screenshot of the current browser window and saves it with a timestamp."""
    
    if not os.path.exists(SCREENSHOT_DIR):
        os.makedirs(SCREENSHOT_DIR)
        print(f"Created directory: {SCREENSHOT_DIR}")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"round_{timestamp}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    try:
        driver.save_screenshot(filepath)
        print(f"Screenshot saved to: {filepath}")
        return filepath
    except Exception as e:
        print(f"Error saving screenshot: {e}")
        return None

def play_singleplayer_game(driver: WebDriver, wait_timeout: int = 20):
    try:
        print("Attempting to select NMPZ mode...")
        nmpz_button = WebDriverWait(driver, wait_timeout).until(
            EC.presence_of_element_located((By.XPATH, NMPZ_BUTTON_XPATH))
        )
        nmpz_button.click()

        print("Attempting to start the game after selecting NMPZ...")
        start_game_button = WebDriverWait(driver, wait_timeout).until(
            EC.presence_of_element_located((By.XPATH, START_GAME_AFTER_NMPZ_BUTTON_XPATH))
        )
        start_game_button.click()

        print("Waiting for game interface to load...")
        WebDriverWait(driver, wait_timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, GAME_RUNNING_INDICATOR_SELECTOR))
        )
        print("Game interface loaded. Game is now running.")

        while True:
            try:
                # Ensure the game is still running
                game_indicator = driver.find_element(By.CSS_SELECTOR, GAME_RUNNING_INDICATOR_SELECTOR)

                #TODO
                next_results = driver.find_elements(By.CSS_SELECTOR, VIEW_RESULTS_BUTTON_SELECTOR)
                if next_results:
                    print("Next results button found. Clicking...")
                    next_results[0].click()
                    print("Waiting for new game button to load...")

                    WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, NEW_GAME_BUTTON_SELECTOR))
                    )

                    new_game_button = driver.find_elements(By.CSS_SELECTOR, NEW_GAME_BUTTON_SELECTOR)
                    if new_game_button:
                        print("New game button found. Clicking...")
                        new_game_button[0].click()
                        time.sleep(0.5)
                        continue

                print("\n--- New Round Started ---")

                try:
                    print("Waiting for panorama canvas to load...")
                    WebDriverWait(driver, wait_timeout).until(
                        EC.all_of(
                            EC.presence_of_element_located((By.ID, PANO_CONTAINER_ID)),
                            EC.invisibility_of_element_located((By.CSS_SELECTOR, PANO_LOADING_SELECTOR))
                        )
                    )
                    time.sleep(0.25)
                    print("Panorama canvas loaded.")
                except TimeoutException:
                    print("Timeout waiting for panorama canvas. Screenshot might be taken before fully loaded.")
                except Exception as e:
                    print(f"Error waiting for panorama canvas: {e}. Proceeding with screenshot anyway.")

                screenshot = capture_screenshot(driver)

                # --- Make guess ---
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                response = None
                guess = None
                llm_max_retries = 1 # Allows for 1 retry, so up to 2 attempts total
                llm_retry_delay_seconds = 3

                for attempt in range(llm_max_retries + 1):
                    try:
                        print(f"Attempting to get guess from LLM. Attempt {attempt + 1}/{llm_max_retries + 1}.")
                        response = LLM.query(screenshot, SYSTEM_PROMPT, timestamp)
                        # If LLM.query is successful, try to parse
                        try:
                            guess = parse_response(response)
                            print(f"LLM guess obtained and parsed: {guess}")
                            break # Successfully got and parsed guess, exit retry loop
                        except Exception as e_parse:
                            print(f"Error parsing LLM response: {e_parse}")
                            print(f"LLM Raw Response was: {response}")
                            # If parsing fails, we might not want to retry the LLM query itself
                            # unless the parsing error is related to an incomplete/failed LLM response.
                            # For now, if parsing fails, we break and proceed with guess as None.
                            break # Exit retry loop, as LLM query itself didn't throw an exception
                    except Exception as e_llm:
                        error_message = str(e_llm)
                        is_503_error = "503" in error_message # Assuming 503 is in the error string

                        if is_503_error and attempt < llm_max_retries:
                            print(f"LLM query failed with a 503-like error: {error_message}. Retrying in {llm_retry_delay_seconds}s...")
                            time.sleep(llm_retry_delay_seconds)
                        else:
                            print(f"LLM query failed after {attempt + 1} attempt(s) or with a non-retryable error: {e_llm}")
                            # Store the raw response if available from the exception, or keep it None
                            if hasattr(e_llm, 'response') and e_llm.response is not None:
                                response_content = e_llm.response.text if hasattr(e_llm.response, 'text') else str(e_llm.response)
                                print(f"LLM Raw Error Response: {response_content}")
                            break # Exit retry loop

                if guess: # Proceed only if guess was successfully obtained and parsed
                    game_response = send_guess_api_request(driver, guess.lat, guess.lng)
                    print("API Response:", game_response)
                else:
                    print("Could not obtain a valid guess from the LLM after retries. Skipping guess submission for this round.")

                time.sleep(0.5)

                print("Refreshing page after guess...")
                driver.refresh()
                wait_for_page_load(driver)

            except NoSuchElementException:
                break

    except TimeoutException:
        print("A timeout occurred in play_singleplayer_game.")

def play_duel(driver: WebDriver, wait_timeout: int = 20):
    """Manages the gameplay loop for a Geoguessr duel."""
    print("Attempting to play a duel...")

    try:
        while True:
            print("\n--- Checking Duel Status & Fetching Details ---")
            try:
                # if driver.find_elements(By.CSS_SELECTOR, DUEL_ENDED_INDICATOR_SELECTOR):
                #     print("Duel ended indicator found. Exiting duel loop.")
                #     break
                hide_elements_by_class_name(driver, CLASSES_TO_HIDE)

                WebDriverWait(driver, 5, 0.1).until( 
                    EC.presence_of_element_located((By.CSS_SELECTOR, DUEL_ACTIVE_INDICATOR_SELECTOR))
                )
                print("Duel page is active.")

                WebDriverWait(driver, 5, 0.1).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, DUELS_GUESS_BUTTON_SELECTOR))
                )

                duel_details = get_duel_details(driver)
                if not duel_details or 'currentRoundNumber' not in duel_details:
                    print("Failed to fetch duel details or currentRoundNumber. Retrying after delay...")
                    time.sleep(5)
                    continue
                
                current_round_number_from_server = duel_details['currentRoundNumber']
                player_id = duel_details.get('playerId')
                print(f"Fetched duel details: Current Round from Server = {current_round_number_from_server}, Player ID = {player_id}")

                # --- Game Round Logic --- 
                try:
                    print("Waiting for panorama canvas to load...")
                    WebDriverWait(driver, wait_timeout, 0.1).until(
                        EC.all_of(
                            EC.presence_of_element_located((By.ID, PANO_CONTAINER_ID)),
                            EC.invisibility_of_element_located((By.CSS_SELECTOR, PANO_LOADING_SELECTOR))
                        )
                    )
                    print("Panorama canvas loaded.")
                except TimeoutException:
                    print("Timeout waiting for panorama canvas. Screenshot might be taken before fully loaded or round not ready.")
                    time.sleep(5)
                    continue 
                except Exception as e:
                    print(f"Error waiting for panorama canvas: {e}. Proceeding with screenshot anyway.")
                
                hide_elements_by_class_name(driver, CLASSES_TO_HIDE)
                
                screenshot_path = capture_screenshot(driver)
                if not screenshot_path:
                    print("Failed to capture screenshot. Skipping this turn.")
                    time.sleep(5) 
                    continue

                # --- Make guess ---
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                response = None
                guess = None
                llm_max_retries = 2 
                llm_retry_delay_seconds = 2

                for attempt in range(llm_max_retries + 1):
                    try:
                        # print(f"Attempting to get guess from LLM. Attempt {attempt + 1}/{llm_max_retries + 1}.")
                        response = LLM.query(screenshot_path, SYSTEM_PROMPT, timestamp)
                        try:
                            guess = parse_response(response)
                            print(f"LLM guess obtained and parsed: {guess}")
                            break 
                        except Exception as e_parse:
                            print(f"Error parsing LLM response: {e_parse}")
                            print(f"LLM Raw Response was: {response}")
                            if attempt >= llm_max_retries:
                                print("Max parsing retries reached.")
                    except Exception as e_llm:
                        error_message = str(e_llm)
                        is_retryable_error = "503" in error_message 
                        
                        if is_retryable_error and attempt < llm_max_retries:
                            print(f"LLM query failed with a retryable error: {error_message}. Retrying in {llm_retry_delay_seconds}s...")
                            time.sleep(llm_retry_delay_seconds)
                        else:
                            print(f"LLM query failed after {attempt + 1} attempt(s) or with a non-retryable error: {e_llm}")
                            if hasattr(e_llm, 'response') and e_llm.response is not None:
                                response_content = e_llm.response.text if hasattr(e_llm.response, 'text') else str(e_llm.response)
                                print(f"LLM Raw Error Response: {response_content}")
                            break 
                
                if guess:
                    print(f"Submitting guess for round {current_round_number_from_server}: Lat: {guess.lat}, Lng: {guess.lng}")
                    current_time_iso = datetime.datetime.utcnow().isoformat(timespec='milliseconds') + "Z"
                    game_response = send_duel_guess_api_request(driver, guess.lat, guess.lng, current_round_number_from_server, current_time_iso)
                    print("Guess submission response:", game_response)
                    
                    if game_response: 
                        print(f"Guess for round {current_round_number_from_server} submitted successfully.")
                    else:
                        print(f"Failed to submit guess for round {current_round_number_from_server}. Will re-fetch state.")
                        time.sleep(3)

                    print("Waiting for next state or duel end...")
                    # time.sleep(3)
                else:
                    print("Could not obtain a valid guess from the LLM after retries. Skipping guess for this round.")
                    time.sleep(5)

                my_hp, opponent_hp = get_duel_hp(driver)
                if my_hp is not None and opponent_hp is not None:
                    print(f"Current HP - My: {my_hp}, Opponent: {opponent_hp}")
                else:
                    print("Could not retrieve current HP for this iteration.")

            except TimeoutException:
                print("Timeout checking duel status or waiting for active duel. Retrying...")
                continue
            except NoSuchElementException:
                print("A required element for duel progression was not found. Duel might have ended abruptly or page changed.")
                if driver.find_elements(By.CSS_SELECTOR, DUEL_ENDED_INDICATOR_SELECTOR): 
                     print("Duel ended indicator found after NoSuchElementException. Exiting.")
                     break
                print("Assuming duel ended or critical error. Exiting duel loop.")
                break 
            except Exception as e:
                print(f"An unexpected error occurred in the duel loop: {e}")
                import traceback
                traceback.print_exc()
                print("Attempting to continue duel if possible, otherwise exiting...")
                time.sleep(10)
                break 

        print("Exited duel game loop.")

    except Exception as e:
        print(f"A critical error occurred in play_duel setup or outer loop: {e}")
        import traceback
        traceback.print_exc()

def get_duel_details(driver: WebDriver):
    """Fetches current duel state from the Geoguessr API."""
    try:
        current_url = driver.current_url
        url_parts = current_url.split('/')
        token = None
        if 'duels' in url_parts:
            duels_index = url_parts.index('duels')
            if len(url_parts) > duels_index + 1:
                token = url_parts[duels_index + 1]
        
        if not token:
            print("Could not find duel game token in the URL for get_duel_details.")
            return None

        api_url = f"https://game-server.geoguessr.com/api/duels/{token}"

        js_script = """            
            const url = arguments[0];
            let csrfToken = null;
            try {
                csrfToken = document.cookie.split('; ').find(row => row.startsWith('_csrf='))?.split('=')[1];
            } catch (e) {
                console.warn('[get_duel_details] Could not parse CSRF token from cookies:', e);
            }
            if (!csrfToken) {
                console.warn('[get_duel_details] CSRF token not found. API call might fail if CSRF is required.');
            }
            const headers = {
                'Accept': 'application/json' // Typically good for GET requests expecting JSON
            };
            if (csrfToken) {
                headers['x-csrf-token'] = csrfToken;
            }

            return fetch(url, {
                method: 'GET',
                headers: headers,
                credentials: 'include' 
            })
            .then(response => {
                if (!response.ok) {
                    console.error('[get_duel_details] API request failed:', response.status, response.statusText);
                    return response.text().then(text => {
                        console.error('[get_duel_details] Error body:', text);
                        throw new Error('[get_duel_details] API request failed: ' + response.status + ", " + response.statusText + ", Body: " + text);
                    });
                }
                return response.json();
            })
            .catch(error => {
                console.error('[get_duel_details] API fetch error:', error);
                return { error: error.message || error.toString() }; 
            });
        """
        # print(f"Executing JS to get duel details for token: {token}")
        response = driver.execute_script(js_script, api_url)
        # print("[get_duel_details] JS script executed.")
        
        if response and isinstance(response, dict) and 'error' in response:
            print(f"Error from get_duel_details API: {response['error']}")
            return None 
        return response

    except Exception as e:
        print(f"An error occurred in get_duel_details: {e}")
        import traceback
        traceback.print_exc()
        return None

def send_duel_guess_api_request(driver: WebDriver, lat: float, lng: float, round_number: int, current_time_iso: str):
    """Sends a guess to the Geoguessr duel API."""
    try:
        current_url = driver.current_url
        url_parts = current_url.split('/')
        token = None
        if 'duels' in url_parts:
            duels_index = url_parts.index('duels')
            if len(url_parts) > duels_index + 1:
                token = url_parts[duels_index + 1]
        
        if not token:
            print("Could not find duel game token in the URL.")
            return None

        api_url = f"https://game-server.geoguessr.com/api/duels/{token}/guess"

        payload = {
            "lat": lat,
            "lng": lng,
            "roundNumber": round_number,
            "time": current_time_iso
        }

        js_script = """            
            const url = arguments[0];
            const payload = arguments[1];
            let csrfToken = null;
            try {
                csrfToken = document.cookie.split('; ').find(row => row.startsWith('_csrf='))?.split('=')[1];
            } catch (e) {
                console.warn('[send_duel_guess] Could not parse CSRF token from cookies:', e);
            }

            // It's good practice to warn if CSRF is missing, as POSTs often require it.
            if (!csrfToken) {
                console.warn('[send_duel_guess] CSRF token not found or accessible in document.cookie. API call might fail if CSRF is required for this endpoint.');
            }

            const headers = {
                'Content-Type': 'application/json'
            };
            if (csrfToken) {
                headers['x-csrf-token'] = csrfToken;
            }

            return fetch(url, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(payload),
                credentials: 'include' 
            })
            .then(response => {
                if (!response.ok) {
                    console.error('[send_duel_guess] API duel guess request failed:', response.status, response.statusText);
                    return response.text().then(text => {
                        console.error('[send_duel_guess] Error body:', text);
                        throw new Error('[send_duel_guess] API duel guess request failed: ' + response.status + ", " + response.statusText + ", Body: " + text);
                    });
                }
                console.log('[send_duel_guess] API duel guess request successful. Returning JSON.');
                return response.json();
            })
            .catch(error => {
                console.error('[send_duel_guess] API duel guess fetch error:', error);
                return { error: error.message || error.toString() }; 
            });
        """

        # print(f"Executing JS to send API duel guess for token: {token}, round: {round_number}")
        # print(f"Payload: {payload}")
        response = driver.execute_script(js_script, api_url, payload)
        # print("JS script for duel guess executed.")
        
        if response and isinstance(response, dict) and 'error' in response:
            print(f"Error from API duel guess: {response['error']}")
            return None 
        return response

    except Exception as e:
        print(f"An error occurred in send_duel_guess_api_request: {e}")
        import traceback
        traceback.print_exc()
        return None

def send_guess_api_request(driver: WebDriver, lat: float, lng: float):
    try:
        current_url = driver.current_url
        url_parts = current_url.split('/')
        if 'game' in url_parts:
            game_token = url_parts[-1]
            game_token = game_token.split('?')[0]
        else:
            print("Could not find game token in the URL.")
            return

        js_script = """
            const token = arguments[0];
            const lat = arguments[1];
            const lng = arguments[2];

            const payload = {
                token: token,
                lat: lat,
                lng: lng,
                timedOut: false,
                stepsCount: 0
            };

            return fetch('/api/v3/games/' + token, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            })
            .then(response => {
                if (!response.ok) {
                    console.error('API guess request failed:', response.status, response.statusText);
                    return response.text().then(text => {
                        console.error('Error body:', text);
                        throw new Error('API guess request failed: ' + response.status + ", " + response.statusText + ", Body: " + text);
                    });
                }
                console.log('API guess request successful. Returning JSON.');
                return response.json();
            })
            .catch(error => {
                console.error('API guess fetch error:', error);
                throw error;
            });
        """

        print(f"Executing JS to send API guess request for token: {game_token}")
        response = driver.execute_script(js_script, game_token, lat, lng)
        print("JS script executed.")
        return response

    except Exception as e:
        print(f"An error occurred in send_guess_api_request: {e}")

def main():
    edge_options = EdgeOptions()
    edge_options.add_argument(f"--user-data-dir={EDGE_USER_DATA_DIR}")
    edge_options.add_argument(f"--profile-directory={EDGE_PROFILE_DIRECTORY}")
    edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    edge_options.add_experimental_option('useAutomationExtension', False)
    edge_options.add_argument('--disable-blink-features=AutomationControlled')
    edge_options.add_argument("--start-maximized")

    driver = None
    try:
        service = EdgeService(executable_path=MSEDGEDRIVER_PATH)
        driver = webdriver.Edge(service=service, options=edge_options)

        driver.maximize_window()
        driver.get(GEOGUESSR_URL)

        wait_for_page_load(driver)

        # ACTION
        play_duel(driver)

    except TimeoutException:
        print("A timeout occurred in the main script flow.")
    except Exception as e:
        print(f"An error occurred in main: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()