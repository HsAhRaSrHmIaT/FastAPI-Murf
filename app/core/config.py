"""Configuration settings and environment variables"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Keys
    google_api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")
    murf_api_key: Optional[str] = os.getenv("MURF_API_KEY") 
    murf_api_url: Optional[str] = os.getenv("MURF_API_URL")
    assemblyai_api_key: Optional[str] = os.getenv("ASSEMBLYAI_API_KEY")
    
    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # File Settings
    upload_dir: str = "uploads"
    max_file_size: int = 25 * 1024 * 1024  # 25MB
    allowed_audio_types: list = [
        "audio/wav", "audio/mpeg", "audio/mp3", 
        "audio/webm", "audio/ogg", "audio/mp4"
    ]
    
    # AI Model Settings
    default_llm_model: str = "gemini-1.5-flash"
    default_voice_id: str = "en-IN-arohi"
    default_language: str = "en-IN"
    max_prompt_length: int = 10000
    max_response_tokens: int = 1000
    
    class Config:
        env_file = ".env"


settings = Settings()
