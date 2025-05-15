import base64
from abc import ABC, abstractmethod
import requests
import os
from ratelimit import limits, sleep_and_retry

def get_image_media_type(image_path: str) -> str:
    """Determine the media type based on file extension."""
    ext = os.path.splitext(image_path)[1].lower()
    if ext == '.png':
        return "image/png"
    elif ext in ['.jpg', '.jpeg']:
        return "image/jpeg"
    else:
        return "image/jpeg" # Default fallback

class BaseMultimodalModel(ABC):
    """Abstract base class for multimodal models."""
    api_key_name: str = None
    model_identifier: str = None
    name: str = None
    rate_limit: int = 5
    rate_limit_period: int = 60
    max_tokens: int = 32000
    temperature: float = 0.4

    def __init__(self, api_key: str):
        if not self.name:
            self.name = self.__class__.__name__
        if not self.api_key_name:
            raise NotImplementedError(f"api_key_name must be set in {self.name} or its parent provider class")
        if not self.model_identifier:
             raise NotImplementedError(f"model_identifier must be set in {self.name}")
        self.api_key = api_key

    def _encode_image(self, image_path: str) -> tuple[str, str]:
        media_type = get_image_media_type(image_path)
        with open(image_path, "rb") as img_file:
            img_data = base64.b64encode(img_file.read()).decode("utf-8")
        return img_data, media_type

    @abstractmethod
    def _build_headers(self) -> dict: pass

    @abstractmethod
    def _build_payload(self, prompt: str, img_data: str, media_type: str) -> dict: pass

    @abstractmethod
    def _get_endpoint(self) -> str: pass

    @abstractmethod
    def _extract_response_text(self, response: requests.Response) -> str: pass

    def query(self, image_path: str, prompt: str, timestamp: str) -> str:
        def api():
            img_data, media_type = self._encode_image(image_path)
            headers = self._build_headers()
            payload = self._build_payload(prompt, img_data, media_type)
            endpoint = self._get_endpoint()
            try:
                response = requests.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                os.makedirs(f"json/", exist_ok=True)
                with open(f"json/{timestamp}.json", "w", encoding="utf-8") as f:
                    f.write(response.text)
                return self._extract_response_text(response)
            except requests.exceptions.RequestException as e:
                status_code = e.response.status_code if e.response is not None else "N/A"
                error_text = e.response.text if e.response is not None else str(e)
                print(f"API error ({status_code}) for {self.name}: {error_text[:100]}...")
                raise Exception(f"{self.name} API error ({status_code})") from e
            except Exception as e:
                print(f"Unexpected error in {self.name} core logic: {str(e)}")
                raise

        call = sleep_and_retry(
            limits(calls=self.rate_limit, period=self.rate_limit_period)(api)
        )

        return call()
    
class GoogleClient(BaseMultimodalModel):
    api_key_name = "GEMINI_API_KEY"
    base_url = "https://generativelanguage.googleapis.com"
    api_version_path: str = "v1" # e.g., "beta/" for experimental versions
    tools: str = None

    def _get_endpoint(self) -> str:
        action = "generateContent"
        version_path = getattr(self, 'api_version_path', '')
        return f"{self.base_url}/{version_path}/models/{self.model_identifier}:{action}?key={self.api_key}"

    def _build_headers(self) -> dict:
        return {"Content-Type": "application/json"}

    def _build_payload(self, prompt: str, img_data: str, media_type: str) -> dict:
        payload = {
            "contents": [{"parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": media_type, "data": img_data}}
            ]}],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens
            }
        }

        if self.tools:
            payload["tools"] = self.tools

        return payload

    def _extract_response_text(self, response: requests.Response) -> str:
        response_json = response.json()
        try:
            parts = response_json['candidates'][0]['content']['parts']
            return ''.join(part.get('text', '') for part in parts)
        except (KeyError, IndexError, TypeError) as e:
            raise ValueError(f"Could not extract text from Google response: {response_json}") from e
        

class Gemini2Flash(GoogleClient):
    name = "Gemini 2.0 Flash"
    model_identifier = "gemini-2.0-flash"
    rate_limit = 10

class Gemini2_5Pro(GoogleClient):
    name = "Gemini 2.5 Pro"
    model_identifier = "gemini-2.5-pro-preview-05-06"
    rate_limit = 8
    api_version_path = "v1beta"

class Gemini2_5Flash(GoogleClient):
    name = "Gemini 2.5 Flash Preview"
    model_identifier = "gemini-2.5-flash-preview-04-17"
    rate_limit = 2
    api_version_path = "v1beta"