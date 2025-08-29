"""Pydantic models for request/response validation"""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class TranscriptionResponse(BaseModel):
    """Response model for speech-to-text transcription"""
    text: str = Field(..., description="Transcribed text")
    confidence: Optional[float] = Field(None, description="Transcription confidence score")
    duration: Optional[float] = Field(None, description="Audio duration in seconds")


class HealthStatus(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Overall health status (healthy/degraded/down)")
    missing_api_keys: List[str] = Field(default_factory=list, description="List of missing API keys")
    timestamp: float = Field(..., description="Health check timestamp")


class ErrorTestResponse(BaseModel):
    """Response for error testing endpoint"""
    stt_test: str = Field(..., description="STT service status")
    llm_test: str = Field(..., description="LLM service status (not used)")
    tts_test: str = Field(..., description="TTS service status (not used)")
    overall_status: str = Field(..., description="Overall system status")
    fallback_message: str = Field(..., description="Generated fallback message")
