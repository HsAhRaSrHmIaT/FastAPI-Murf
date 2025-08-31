"""Text-to-Speech service using Murf AI with WebSocket streaming"""

import asyncio
import websockets
import json
import base64
import re
from typing import Optional
from app.core.config import settings
# from app.core.logging import get_logger

# logger = get_logger(__name__)

class TTSService:
    """Text-to-Speech service using Murf AI WebSocket API"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.ws_url = "wss://api.murf.ai/v1/speech/stream-input"  # Hardcoded WebSocket URL
        self.context_id = "fastapi-demo-context-001"
        if not self.api_key:
            self._available = False
        else:
            self._available = True

    def is_available(self) -> bool:
        """Check if TTS service is available"""
        return bool(self.api_key)

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text by replacing URLs with readable format"""
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
        return re.sub(url_pattern, url_replacer, text)

    async def generate_speech(self, text: str) -> str:
        """
        Generate speech from text using Murf TTS via WebSocket.
        Returns the complete base64 audio data ready for browser playback.
        """
        if not self.is_available():
            print(f"[DEBUG] TTS service not available, api_key: {bool(self.api_key)}")
            return ""

        try:
            print(f"[DEBUG] Starting TTS generation for text: {text[:50]}...")
            # Preprocess text
            processed_text = self._preprocess_text(text)
            print(f"[DEBUG] Processed text: {processed_text[:50]}...")

            async with websockets.connect(
                f"{self.ws_url}?api-key={self.api_key}&sample_rate=44100&channel_type=MONO&format=WAV"
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
                    "context_id": self.context_id
                }
                # logger.debug(f'Sending voice config: {voice_config_msg}')
                await ws.send(json.dumps(voice_config_msg))

                # Send processed text
                text_msg = {
                    "text": processed_text,
                    "end": True,
                    "context_id": self.context_id
                }
                # logger.debug(f'Sending text: {text_msg}')
                await ws.send(json.dumps(text_msg))

                # Collect all audio chunks
                audio_chunks = []
                first_chunk = True

                while True:
                    response = await ws.recv()
                    data = json.loads(response)

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

                        # logger.debug(f"Received audio chunk: {len(audio_bytes)} bytes")

                    if data.get("final"):
                        break

                # Combine all audio chunks
                if audio_chunks:
                    # For browser playback, we need to reconstruct a proper WAV file
                    combined_audio = b''.join(audio_chunks)
                    combined_b64 = base64.b64encode(combined_audio).decode('utf-8')

                    print(f"[DEBUG] TTS generation completed, audio length: {len(combined_b64)}")
                    return combined_b64
                else:
                    print(f"[DEBUG] TTS returned empty audio")
                    return ""

        except Exception as e:
            print(f"[DEBUG] TTS service error: {e}")
            return ""


# Legacy function for backward compatibility
async def tts_service(text: str) -> str:
    """
    Legacy function - use TTSService class instead.
    Send text to Murf TTS via WebSocket and return base64 audio.
    """
    service = TTSService()
    return await service.generate_speech(text)


# Global TTS service instance - removed since we now use per-user API keys
# tts_service = TTSService()  