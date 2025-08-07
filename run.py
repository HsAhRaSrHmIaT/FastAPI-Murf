from fastapi import FastAPI, Request, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import requests
import dotenv
import os
import time
import assemblyai as aai

dotenv.load_dotenv()

app = FastAPI()

MURF_API_KEY = os.getenv("MURF_API_KEY")
MURF_API_URL = os.getenv("MURF_API_URL")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

aai.settings.api_key = ASSEMBLYAI_API_KEY

# print(f"MURF_API_KEY: {MURF_API_KEY}")
# print(f"MURF_API_URL: {MURF_API_URL}")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

templates = Jinja2Templates(directory="templates")


class SpeechRequest(BaseModel):
    text: str
    voice_id: str = "en-IN-arohi"
    language: str = "en-IN"

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/generate-speech")
def generate_speech(speech_request: SpeechRequest):
    payload = {
        "text": speech_request.text,
        "voice_id": speech_request.voice_id,
        "language": speech_request.language
    }

    headers = {
        "api-key": MURF_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.post(MURF_API_URL, headers=headers, json=payload)

    if response.status_code == 200:
        return {"audio_url": response.json().get("audioFile")}
    else:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    

@app.post("/upload")
def upload_file(file: UploadFile = File(...)):
    try:
        main_content_type = file.content_type.split(";")[0] if file.content_type else ""

        allowed_types = [
            "audio/wav",
            "audio/mpeg",
            "audio/mp3",
            "audio/webm", 
            "audio/ogg",
            "audio/webm;codecs=opus",
            "audio/ogg;codecs=opus"
        ]

        # print(f"Uploaded file content type: {file.content_type}")
        # print(f"Uploaded file filename: {file.filename}")

        if main_content_type not in allowed_types:
            # print(f"Rejected content type: {main_content_type}")
            raise HTTPException(status_code=400, detail="Invalid file type")


        if "webm" in main_content_type:
            file_extension = ".webm"
        elif "ogg" in main_content_type:
            file_extension = ".ogg"
        elif "wav" in main_content_type:
            file_extension = ".wav"
        elif "mp3" in main_content_type:
            file_extension = ".mp3"
        else:
            file_extension = os.path.splitext(file.filename)[1] or ".webm"

        timestamp = int(time.time())
        filename = f"recording_{timestamp}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        with open(file_path, "wb") as f:
            f.write(file.file.read())

        file_size = os.path.getsize(file_path)

        return {
            "filename": filename,
            "content_type": file.content_type,
            "size": file_size,
            "message": "Audio file uploaded successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/transcribe-file")
def transcribe_file(file: UploadFile = File(...)):
    """
    Endpoint to transcribe audio files using AssemblyAI.
    Accepts audio files and returns transcription text.
    """
    try:
        # Validate file type
        allowed_types = [
            "audio/wav", "audio/mpeg", "audio/mp3", 
            "audio/webm", "audio/ogg", "audio/mp4",
            "audio/webm;codecs=opus", "audio/ogg;codecs=opus"
        ]
        
        main_content_type = file.content_type.split(";")[0] if file.content_type else ""
        if main_content_type not in ["audio/wav", "audio/mpeg", "audio/mp3", "audio/webm", "audio/ogg", "audio/mp4"]:
            raise HTTPException(status_code=400, detail=f"Invalid file type: {file.content_type}")
        
        # Read the audio file content
        audio_data = file.file.read()
        
        # Create a transcriber instance
        transcriber = aai.Transcriber()
        
        # Transcribe the audio data directly (no need to save to disk)
        transcript = transcriber.transcribe(audio_data)
        
        if transcript.status == aai.TranscriptStatus.error:
            raise HTTPException(status_code=500, detail=f"Transcription failed: {transcript.error}")
        
        return {
            "transcription": transcript.text,
            "confidence": round(transcript.confidence * 100, 2) if hasattr(transcript, 'confidence') else None,
            "audio_duration": round(transcript.audio_duration, 2) if hasattr(transcript, 'audio_duration') else None,
            "filename": file.filename,
            "message": "Transcription completed successfully"
        }
        
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
