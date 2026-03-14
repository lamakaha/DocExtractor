import os
from typing import Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class GeminiClientFactory:
    """
    Singleton factory for the Gemini client.
    Ensures a single instance of the client is used throughout the application.
    """
    _instance: Optional[genai.Client] = None

    @classmethod
    def get_client(cls) -> genai.Client:
        """
        Returns the Gemini client instance, initializing it if necessary.
        """
        if cls._instance is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable is not set")
            
            cls._instance = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(api_version='v1')
            )
            
        return cls._instance

    @classmethod
    def check_connectivity(cls) -> bool:
        """
        Simple connectivity check to verify the API key and access to the model.
        """
        try:
            client = cls.get_client()
            # Try a very simple prompt to check connectivity
            response = client.models.generate_content(
                model="gemini-2.0-flash", # Use flash for a quick, cheap check
                contents="ping"
            )
            return response.text is not None
        except Exception as e:
            print(f"Gemini connectivity check failed: {e}")
            return False

def get_gemini_client() -> genai.Client:
    """
    Convenience function to get the Gemini client.
    """
    return GeminiClientFactory.get_client()
