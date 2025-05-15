from prompt import *

# --- Configuration ---
EDGE_USER_DATA_DIR = r"C:\\Users\\USERNAME\\AppData\\Local\\Microsoft\\Edge\\User Data"
EDGE_PROFILE_DIRECTORY = "Default"
MSEDGEDRIVER_PATH = r"C:\Users\USERNAME\Desktop\chromedriver\msedgedriver.exe"

CLASSES_TO_HIDE = [
    "hud_root__ByG3Q",
    "styles_root__EvsEF",
    "duels-guess-map_container__k6LUq",
    "duels-panorama_controls___OEib",
    "guess-map_guessMap__IP8n_",
    "chat_root__j9pUs"
]

SCREENSHOT_DIR = "screenshots"

SYSTEM_PROMPT = """
You are an expert geolocator participating in a geolocation challenge. Your task is to analyze the provided image and determine its geographic location by providing detailed reasoning and coordinates.

Your analysis should include the following:

1.  **Detailed Clue Identification & Analysis:**
    * Identify and describe several distinct visual clues from the image (e.g., architecture, signage, language, text, vehicle types, license plates, road markings, utility poles, vegetation, terrain, soil color, sun direction, etc.).
    * For each significant clue, explain its geographical relevance. Why does this clue suggest a particular country, region, or type of environment?

2.  **Step-by-Step Deduction Process:**
    * Outline your thought process for deducing the likely country or major region. Explain how you synthesize the information from the various clues.
    * If there are conflicting clues or ambiguities, discuss how you addressed them.

3.  **Latitude and Longitude Estimation Rationale:**
    * Based on your country/region deduction, explain how you arrived at your estimated latitude and longitude. Consider factors like the specific area within the country suggested by the clues, apparent climate, and landscape features.

Take your time to reason through the evidence. Provide a comprehensive and well-explained analysis.

Your final answer MUST include these three lines somewhere in your response:

lat: [latitude as a decimal number]
lng: [longitude as a decimal number]
"""

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
LLM = Gemini2_5Pro(GEMINI_API_KEY)