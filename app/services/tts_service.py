import asyncio
import websockets
import json

from app.core.config import settings


API_KEY = settings.murf_api_key
WS_URL = settings.ws_murf_api_url
STATIC_CONTEXT_ID = "fastapi-demo-context-001"

print("WS_URL:", WS_URL)
print("API_KEY:", API_KEY)

async def tts_service(text: str) -> str:
    """
    Send text to Murf TTS via WebSocket and print base64 audio.
    Returns the last base64 audio chunk.
    """
    async with websockets.connect(
        f"{WS_URL}?api-key={API_KEY}&sample_rate=44100&channel_type=MONO&format=WAV"
    ) as ws:
        # Send voice config with static context_id
        voice_config_msg = {
            "voice_config": {
                "voiceId": "en-US-amara",
                "style": "Conversational",
                "rate": 0,
                "pitch": 0,
                "variation": 1
            },
            "context_id": STATIC_CONTEXT_ID
        }
        await ws.send(json.dumps(voice_config_msg))

        # Send text
        text_msg = {
            "text": text,
            "end": True,
            "context_id": STATIC_CONTEXT_ID
        }
        await ws.send(json.dumps(text_msg))

        last_audio_b64 = ""
        while True:
            response = await ws.recv()
            data = json.loads(response)
            if "audio" in data:
                audio_b64 = data["audio"]
                print(f"[MURF AUDIO BASE64]: {audio_b64}")
                last_audio_b64 = audio_b64
            if data.get("final"):
                break
        return last_audio_b64

# Example usage for testing
if __name__ == "__main__":
    asyncio.run(tts_service("With a single WebSocket connection, you can stream text input and receive synthesized audio continuously, without the overhead of repeated HTTP requests."))