import os
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class OpenRouterClientFactory:
    """
    Singleton factory for the OpenRouter client.
    Ensures a single instance of the client is used throughout the application.
    """
    _instance: Optional[OpenAI] = None

    @classmethod
    def get_client(cls) -> OpenAI:
        """
        Returns the OpenRouter client instance, initializing it if necessary.
        """
        if cls._instance is None:
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                # Fallback to GEMINI_API_KEY if OPENROUTER_API_KEY is not set
                api_key = os.getenv("GEMINI_API_KEY")
                if not api_key:
                    raise ValueError("OPENROUTER_API_KEY environment variable is not set")
            
            base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
            
            cls._instance = OpenAI(
                api_key=api_key,
                base_url=base_url
            )
            
        return cls._instance

    @classmethod
    def check_connectivity(cls) -> bool:
        """
        Simple connectivity check to verify the API key and access to the model.
        """
        try:
            client = cls.get_client()
            model = os.getenv("GEMINI_MODEL", "google/gemini-2.0-flash-001")
            # Try a very simple prompt to check connectivity
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5
            )
            return response.choices[0].message.content is not None
        except Exception as e:
            print(f"OpenRouter connectivity check failed: {e}")
            return False

def get_gemini_client() -> OpenAI:
    """
    Convenience function to get the client.
    Renamed conceptually, but kept name for compatibility.
    """
    return OpenRouterClientFactory.get_client()
