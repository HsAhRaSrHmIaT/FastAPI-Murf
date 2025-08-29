"""Configuration settings and environment variables"""
import os
import json
from typing import Optional
from pydantic_settings import BaseSettings


USER_KEYS_FILE = "user_keys.json"

def load_user_keys() -> dict:
    """Load user keys from JSON file"""
    if os.path.exists(USER_KEYS_FILE):
        try:
            with open(USER_KEYS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading user keys: {e}")
            return {}
    return {}

def save_user_keys(user_keys: dict):
    """Save user keys to JSON file"""
    try:
        with open(USER_KEYS_FILE, "w") as f:
            json.dump(user_keys, f, indent=2)
    except Exception as e:
        print(f"Error saving user keys: {e}")

def get_api_key_from_sources(env_var: str, json_key: str) -> Optional[str]:
    """Get API key from environment variable first, then from user_keys.json"""
    # Try environment variable first
    env_value = os.getenv(env_var)
    if env_value:
        return env_value

    # Try user keys JSON as fallback
    user_keys = load_user_keys()
    return user_keys.get(json_key)

class Settings(BaseSettings):
    """Application settings loaded from environment variables and user keys"""

    # API Keys with fallback to user_keys.json
    assemblyai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    murf_api_key: Optional[str] = None
    ws_murf_api_url: Optional[str] = None

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra environment variables

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Load API keys with fallback mechanism
        self.assemblyai_api_key = get_api_key_from_sources(
            "ASSEMBLYAI_API_KEY", "assemblyai_api_key"
        )
        self.google_api_key = get_api_key_from_sources(
            "GOOGLE_API_KEY", "google_api_key"
        )
        self.murf_api_key = get_api_key_from_sources(
            "MURF_API_KEY", "murf_api_key"
        )
        self.ws_murf_api_url = get_api_key_from_sources(
            "WS_MURF_API_URL", "ws_murf_api_url"
        )

# Global settings instance
settings = Settings()

def get_api_key(key_name: str) -> Optional[str]:
    """Get the API key for a specific service"""
    return getattr(settings, key_name, None)

# Utility functions for managing user keys
def update_user_key(key_name: str, key_value: str):
    """Update a specific user key in the JSON file"""
    user_keys = load_user_keys()
    user_keys[key_name] = key_value
    save_user_keys(user_keys)
    # Reload settings to pick up the new key
    global settings
    settings = Settings()

def get_all_user_keys() -> dict:
    """Get all user keys from JSON file"""
    return load_user_keys()

def list_available_keys():
    """List which keys are available from which sources"""
    user_keys = load_user_keys()
    return {
        "assemblyai_api_key": {
            "env_available": bool(os.getenv("ASSEMBLYAI_API_KEY")),
            "user_available": "assemblyai_api_key" in user_keys,
            "current_value": bool(settings.assemblyai_api_key)
        },
        "google_api_key": {
            "env_available": bool(os.getenv("GOOGLE_API_KEY")),
            "user_available": "google_api_key" in user_keys,
            "current_value": bool(settings.google_api_key)
        },
        "murf_api_key": {
            "env_available": bool(os.getenv("MURF_API_KEY")),
            "user_available": "murf_api_key" in user_keys,
            "current_value": bool(settings.murf_api_key)
        },
        "ws_murf_api_url": {
            "env_available": bool(os.getenv("WS_MURF_API_URL")),
            "user_available": "ws_murf_api_url" in user_keys,
            "current_value": bool(settings.ws_murf_api_url)
        }
    }
