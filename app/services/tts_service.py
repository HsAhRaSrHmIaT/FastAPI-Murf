import asyncio
import websockets
import json
import base64
from app.core.config import settings

API_KEY = settings.murf_api_key
WS_URL = settings.ws_murf_api_url
STATIC_CONTEXT_ID = "fastapi-demo-context-001"

print("WS_URL:", WS_URL)
print("API_KEY:", API_KEY)

async def tts_service(text: str) -> str:
    """
    Send text to Murf TTS via WebSocket and return base64 audio.
    Returns the complete base64 audio data ready for browser playback.
    """
    try:
        # Preprocess text: replace URLs with 'link to <domain>'
        import re
        def url_replacer(match):
            url = match.group(0)
            # Remove markdown formatting if present
            url_clean = url.strip('`').strip()
            # Extract domain
            domain = re.sub(r'^https?://', '', url_clean).split('/')[0]
            if domain:
                return f'link to {domain}'
            return 'link'

        # Replace URLs in the text (http/https, bare or markdown/backtick-wrapped)
        url_pattern = r'`?(https?://[^\s`]+)`?'
        processed_text = re.sub(url_pattern, url_replacer, text)

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
            print(f'Sending voice config: {voice_config_msg}')
            await ws.send(json.dumps(voice_config_msg))

            # Send processed text
            text_msg = {
                "text": processed_text,
                "end": True,
                "context_id": STATIC_CONTEXT_ID
            }
            print(f'Sending text: {text_msg}')
            await ws.send(json.dumps(text_msg))

            # Collect all audio chunks
            audio_chunks = []
            first_chunk = True
            
            while True:
                response = await ws.recv()
                data = json.loads(response)
                # print(f'Received data: {data}')
                
                if "audio" in data:
                    audio_b64 = data["audio"]
                    
                    # Decode base64 to bytes for processing
                    audio_bytes = base64.b64decode(audio_b64)
                    
                    # Skip WAV header only for the first chunk
                    if first_chunk and len(audio_bytes) > 44:
                        # Keep the WAV header for the first chunk since we need it for browser playback
                        # The browser's Web Audio API can handle WAV files with headers
                        audio_chunks.append(audio_bytes)
                        first_chunk = False
                    else:
                        # For subsequent chunks, append the raw audio data
                        audio_chunks.append(audio_bytes)
                    
                    print(f"[MURF AUDIO CHUNK]: Received {len(audio_bytes)} bytes")
                    
                if data.get("final"):
                    break

            # Combine all audio chunks
            if audio_chunks:
                # For browser playback, we need to reconstruct a proper WAV file
                combined_audio = b''.join(audio_chunks)
                combined_b64 = base64.b64encode(combined_audio).decode('utf-8')
                
                print(f"[MURF AUDIO BASE64 COMPLETE]: {combined_b64[:100]}... (total length: {len(combined_b64)})")
                return combined_b64
            else:
                print("[MURF AUDIO]: No audio data received")
                return ""
                
    except Exception as e:
        print(f"[MURF TTS ERROR]: {e}")
        return ""

# Example usage for testing
if __name__ == "__main__":
    # Test both versions
    test_text = "With a single WebSocket connection, you can stream text input and receive synthesized audio continuously, without the overhead of repeated HTTP requests."
    
    print("Testing standard version:")
    result1 = asyncio.run(tts_service(test_text))  