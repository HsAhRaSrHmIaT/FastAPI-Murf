"""Configuration settings and environment variables"""
import os
from typing import Optional
from pydantic_settings import BaseSettings

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
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra environment variables


settings = Settings()
