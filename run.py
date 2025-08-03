from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import requests
import dotenv
import os

dotenv.load_dotenv()

app = FastAPI()

MURF_API_KEY = os.getenv("MURF_API_KEY")
MURF_API_URL = os.getenv("MURF_API_URL")

print(f"MURF_API_KEY: {MURF_API_KEY}")
print(f"MURF_API_URL: {MURF_API_URL}")

app.mount("/static", StaticFiles(directory="static"), name="static")

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
