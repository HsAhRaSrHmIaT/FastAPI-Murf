"""Pydantic models for request/response validation"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum


class VoiceID(str, Enum):
    """Supported voice IDs for TTS"""
    EN_IN_AROHI = "en-IN-arohi"
    EN_US_JOHN = "en-US-john"
    EN_US_MARY = "en-US-mary"


class Language(str, Enum):
    """Supported languages for TTS"""
    EN_IN = "en-IN"
    EN_US = "en-US"


class SpeechRequest(BaseModel):
    """Request model for text-to-speech generation"""
    text: str = Field(..., min_length=1, max_length=5000, description="Text to convert to speech")
    voice_id: VoiceID = Field(default=VoiceID.EN_IN_AROHI, description="Voice ID for TTS")
    language: Language = Field(default=Language.EN_IN, description="Language for TTS")


class SpeechResponse(BaseModel):
    """Response model for text-to-speech generation"""
    audio_url: str = Field(..., description="URL of generated audio file")


class TranscriptionResponse(BaseModel):
    """Response model for speech-to-text transcription"""
    text: str = Field(..., description="Transcribed text")
    confidence: Optional[float] = Field(None, description="Transcription confidence score")
    duration: Optional[float] = Field(None, description="Audio duration in seconds")


class LLMRequest(BaseModel):
    """Request model for LLM query"""
    prompt: str = Field(..., min_length=1, max_length=10000, description="Prompt for LLM")
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0, description="Temperature for generation")
    max_tokens: Optional[int] = Field(default=1000, ge=1, le=4000, description="Maximum tokens to generate")


class LLMResponse(BaseModel):
    """Response model for LLM query"""
    prompt: str = Field(..., description="Original prompt")
    response: str = Field(..., description="LLM generated response")
    input_type: str = Field(..., description="Type of input (text/audio)")
    transcription: Optional[str] = Field(None, description="Transcribed text if input was audio")


class ChatMessage(BaseModel):
    """Individual chat message"""
    role: str = Field(..., description="Role of the message sender (user/assistant)")
    content: str = Field(..., description="Content of the message")
    timestamp: Optional[float] = Field(None, description="Timestamp of the message")


class ServiceErrors(BaseModel):
    """Error details from various services"""
    transcription_error: Optional[str] = Field(None, description="STT service error")
    llm_error: Optional[str] = Field(None, description="LLM service error")
    tts_error: Optional[str] = Field(None, description="TTS service error")
    critical_error: Optional[str] = Field(None, description="Critical system error")


class AgentChatResponse(BaseModel):
    """Response model for agent chat endpoint"""
    session_id: str = Field(..., description="Chat session ID")
    user_message: str = Field(..., description="User's transcribed message")
    assistant_response: str = Field(..., description="Assistant's response")
    audio_url: Optional[str] = Field(None, description="URL of assistant's audio response")
    chat_history_length: int = Field(..., description="Number of messages in chat history")
    input_type: str = Field(default="audio", description="Type of input")
    errors: ServiceErrors = Field(default_factory=ServiceErrors, description="Any errors that occurred")


class ChatHistory(BaseModel):
    """Chat history for a session"""
    session_id: str = Field(..., description="Chat session ID")
    messages: List[ChatMessage] = Field(default_factory=list, description="List of chat messages")


class HealthStatus(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Overall health status (healthy/degraded/down)")
    missing_api_keys: List[str] = Field(default_factory=list, description="List of missing API keys")
    timestamp: float = Field(..., description="Health check timestamp")


class ErrorTestResponse(BaseModel):
    """Response for error testing endpoint"""
    stt_test: str = Field(..., description="STT service status")
    llm_test: str = Field(..., description="LLM service status")
    tts_test: str = Field(..., description="TTS service status")
    overall_status: str = Field(..., description="Overall system status")
    fallback_message: str = Field(..., description="Generated fallback message")


class SessionClearResponse(BaseModel):
    """Response for session clear endpoint"""
    message: str = Field(..., description="Confirmation message")
    session_id: str = Field(..., description="Cleared session ID")
