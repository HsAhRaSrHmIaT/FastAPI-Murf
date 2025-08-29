"""Configuration settings and environment variables"""
import os
import json
from typing import Optional
from pydantic_settings import BaseSettings


USER_KEYS_FILE = "user_keys.json"

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Keys
    assemblyai_api_key: Optional[str] = os.getenv("ASSEMBLYAI_API_KEY")
    google_api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")
    murf_api_key: Optional[str] = os.getenv("MURF_API_KEY")
    ws_murf_api_url: Optional[str] = os.getenv("WS_MURF_API_URL")

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    user_keys: dict = {}
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra environment variables

def load_user_keys():
    if os.path.exists(USER_KEYS_FILE):
        try:
            with open(USER_KEYS_FILE, "r") as f:
                settings.user_keys = json.load(f)
        except Exception as e:
            print(f"Error loading user keys: {e}")
            settings.user_keys = {}

def save_user_keys():
    with open(USER_KEYS_FILE, "w") as f:
        json.dump(settings.user_keys, f)

def get_setting(key: str) -> Optional[str]:
    return settings.user_keys.get(key) or getattr(settings, key, None)

settings = Settings()
load_user_keys()
