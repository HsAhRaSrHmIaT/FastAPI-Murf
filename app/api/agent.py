"""Agent chat API endpoints"""
from fastapi import APIRouter, HTTPException, File, UploadFile
from typing import Optional
from app.models.schemas import (
    AgentChatResponse, ChatHistory, SessionClearResponse,
    ServiceErrors, SpeechRequest
)
from app.services.stt_service import stt_service
from app.services.llm_service import llm_service
from app.services.tts_service import tts_service
from app.services.session_service import session_service
from app.services.health_service import health_service
from app.core.config import settings
# from app.core.logging import get_logger

# logger = get_logger(__name__)
router = APIRouter(prefix="/agent", tags=["agent"])


def validate_audio_file(file: UploadFile) -> None:
    """Validate uploaded audio file"""
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    main_content_type = file.content_type.split(";")[0] if file.content_type else ""
    
    if main_content_type not in settings.allowed_audio_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type: {file.content_type}. Allowed types: {settings.allowed_audio_types}"
        )


@router.post("/chat/{session_id}", response_model=AgentChatResponse)
async def agent_chat(
    session_id: str,
    file: Optional[UploadFile] = File(None),
):
    """
    Process voice input and generate AI response with TTS
    
    Args:
        session_id: Unique session identifier
        file: Audio file upload
        
    Returns:
        AgentChatResponse with transcription, AI response, and audio URL
    """
    # logger.info(f"Agent chat request for session: {session_id}")
    
    try:
        # Validate file upload
        validate_audio_file(file)
        
        # Initialize response data
        user_message = ""
        assistant_message = ""
        audio_url = None
        errors = ServiceErrors()
        
        # Step 1: Transcribe audio (STT)
        try:
            audio_data = await file.read()
            # logger.info(f"Processing audio file: {len(audio_data)} bytes")
            
            transcription_result = await stt_service.transcribe_audio(audio_data)
            user_message = transcription_result.text
            
            # logger.info(f"Transcription successful: '{user_message[:100]}...'")
            
        except Exception as e:
            errors.transcription_error = str(e)
            # logger.error(f"Transcription failed: {str(e)}")
            user_message = "I'm having trouble understanding the audio."
        
        # Add user message to session
        session_service.add_message(session_id, "user", user_message)
        
        # Step 2: Generate AI response (LLM)
        try:
            chat_history = session_service.get_messages_for_llm(session_id)
            assistant_message = await llm_service.generate_chat_response(chat_history)
            
            # logger.info(f"LLM response generated: '{assistant_message[:100]}...'")
            
        except Exception as e:
            errors.llm_error = str(e)
            # logger.error(f"LLM generation failed: {str(e)}")
            
            # Generate fallback response
            assistant_message = health_service.generate_fallback_response(
                transcription_error=errors.transcription_error,
                llm_error=str(e)
            )
        
        # Add assistant message to session
        session_service.add_message(session_id, "assistant", assistant_message)
        
        # Step 3: Generate speech (TTS)
        try:
            speech_request = SpeechRequest(text=assistant_message)
            speech_response = await tts_service.generate_speech(speech_request)
            audio_url = speech_response.audio_url
            
            # logger.info(f"TTS successful: {audio_url}")
            
        except Exception as e:
            errors.tts_error = str(e)
            # logger.error(f"TTS generation failed: {str(e)}")
            audio_url = None
        
        # Get current chat history length
        chat_history = session_service.get_chat_history(session_id)
        
        response = AgentChatResponse(
            session_id=session_id,
            user_message=user_message,
            assistant_response=assistant_message,
            audio_url=audio_url,
            chat_history_length=len(chat_history.messages),
            input_type="audio",
            errors=errors
        )
        
        # logger.info(f"Agent chat completed for session {session_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        # logger.error(f"Critical error in agent chat: {str(e)}")
        
        # Return error response
        return AgentChatResponse(
            session_id=session_id,
            user_message="Error processing audio",
            assistant_response="I'm experiencing technical difficulties right now. Please try again later.",
            audio_url=None,
            chat_history_length=0,
            input_type="audio",
            errors=ServiceErrors(critical_error=str(e))
        )


@router.get("/chat/{session_id}/history", response_model=ChatHistory)
async def get_chat_history(session_id: str):
    """Get chat history for a session"""
    # logger.info(f"Chat history requested for session: {session_id}")
    return session_service.get_chat_history(session_id)


@router.delete("/chat/{session_id}", response_model=SessionClearResponse)
async def clear_chat_history(session_id: str):
    """Clear chat history for a session"""
    # logger.info(f"Clearing chat history for session: {session_id}")
    
    session_cleared = session_service.clear_session(session_id)
    
    if session_cleared:
        message = f"Chat history cleared for session {session_id}"
    else:
        message = f"No chat history found for session {session_id}"
    
    return SessionClearResponse(
        message=message,
        session_id=session_id
    )
