"""Legacy endpoints for backward compatibility"""
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from typing import Optional
from app.models.schemas import SpeechRequest, SpeechResponse, LLMResponse
from app.services.stt_service import stt_service
from app.services.llm_service import llm_service
from app.services.tts_service import tts_service
from app.core.config import settings
# from app.core.logging import get_logger

# logger = get_logger(__name__)
router = APIRouter(tags=["legacy"])


@router.post("/generate-speech", response_model=SpeechResponse)
async def generate_speech(speech_request: SpeechRequest):
    """
    Generate speech from text (legacy endpoint)
    
    Args:
        speech_request: SpeechRequest with text and voice settings
        
    Returns:
        SpeechResponse with audio URL
    """
    # logger.info(f"Legacy speech generation requested for: '{speech_request.text[:50]}...'")
    
    try:
        return await tts_service.generate_speech(speech_request)
    except Exception as e:
        # logger.error(f"Legacy speech generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Legacy file upload endpoint for audio transcription
    
    Args:
        file: Audio file upload
        
    Returns:
        Transcription result with metadata
    """
    # logger.info(f"Legacy file upload: {file.filename}")
    
    try:
        # Validate file type
        main_content_type = file.content_type.split(";")[0] if file.content_type else ""
        
        if main_content_type not in settings.allowed_audio_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type: {file.content_type}"
            )
        
        # Read and transcribe audio
        audio_data = await file.read()
        transcription_result = await stt_service.transcribe_audio(audio_data)
        
        return {
            "filename": file.filename,
            "transcription": transcription_result.text,
            "confidence": transcription_result.confidence,
            "duration": transcription_result.duration,
            "file_size": len(audio_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # logger.error(f"Legacy upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/llm/query", response_model=LLMResponse)
async def llm_query(
    prompt: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """
    Legacy LLM query endpoint with optional audio input
    
    Args:
        prompt: Text prompt for LLM
        file: Optional audio file for transcription
        
    Returns:
        LLMResponse with generated text
    """
    # logger.info("Legacy LLM query requested")
    
    try:
        final_prompt = ""
        transcription = None
        
        # Handle audio input
        if file:
            main_content_type = file.content_type.split(";")[0] if file.content_type else ""
            
            if main_content_type not in settings.allowed_audio_types:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid file type: {file.content_type}"
                )
            
            # Transcribe audio
            audio_data = await file.read()
            transcription_result = await stt_service.transcribe_audio(audio_data)
            final_prompt = transcription_result.text
            transcription = transcription_result.text
            
        elif prompt:
            final_prompt = prompt
        else:
            raise HTTPException(
                status_code=400, 
                detail="Either prompt or audio file must be provided"
            )
        
        if not final_prompt or final_prompt.strip() == "":
            raise HTTPException(status_code=400, detail="No valid input detected")
        
        # Generate LLM response
        response_text = await llm_service.generate_response(final_prompt)
        
        return LLMResponse(
            prompt=final_prompt,
            response=response_text,
            input_type="audio" if file else "text",
            transcription=transcription
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # logger.error(f"Legacy LLM query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
