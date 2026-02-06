"""
Speech-to-Text Service
Integrates with Groq Whisper Large v3 Turbo API for audio transcription.
"""

import logging
from typing import Optional, BinaryIO
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class STTService:
    """Speech-to-Text service using Groq Whisper Large v3 Turbo API."""
    
    WHISPER_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
    MODEL = "whisper-large-v3-turbo"
    
    def __init__(self):
        """Initialize the STT service."""
        self.api_key = settings.groq_api_key
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=60.0,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        return self._client
    
    async def transcribe(
        self,
        audio_file: BinaryIO,
        filename: str = "audio.m4a",
        language: Optional[str] = None
    ) -> Optional[str]:
        """
        Transcribe audio to text using Groq Whisper API.
        
        Args:
            audio_file: Audio file binary data
            filename: Name of the audio file
            language: Optional language hint (e.g., "en", "ta")
            
        Returns:
            Transcribed text or None if failed
        """
        if not self.api_key:
            logger.error("Groq API key not configured")
            return None
        
        try:
            client = await self._get_client()
            
            # Determine content type based on filename
            ext = filename.split(".")[-1].lower()
            content_types = {
                "m4a": "audio/m4a",
                "mp3": "audio/mpeg",
                "wav": "audio/wav",
                "webm": "audio/webm",
                "ogg": "audio/ogg",
                "flac": "audio/flac"
            }
            content_type = content_types.get(ext, "audio/m4a")
            
            # Prepare multipart form data
            files = {"file": (filename, audio_file, content_type)}
            data = {
                "model": self.MODEL,
                "temperature": "0",
                "response_format": "verbose_json"
            }
            
            if language:
                data["language"] = language
            
            response = await client.post(
                self.WHISPER_API_URL,
                files=files,
                data=data
            )
            
            if response.status_code == 200:
                result = response.json()
                transcription = result.get("text", "").strip()
                logger.info(f"Transcription successful: {len(transcription)} chars")
                logger.debug(f"Detected language: {result.get('language', 'unknown')}")
                return transcription
            else:
                logger.error(f"Groq Whisper API error: {response.status_code} - {response.text}")
                return None
                
        except httpx.TimeoutException:
            logger.error("Groq Whisper API timeout")
            return None
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            return None
    
    async def transcribe_bytes(
        self,
        audio_bytes: bytes,
        filename: str = "audio.m4a",
        language: Optional[str] = None
    ) -> Optional[str]:
        """
        Transcribe audio bytes to text.
        
        Args:
            audio_bytes: Raw audio bytes
            filename: Name for the audio file
            language: Optional language hint
            
        Returns:
            Transcribed text or None if failed
        """
        import io
        audio_file = io.BytesIO(audio_bytes)
        return await self.transcribe(audio_file, filename, language)
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def health_check(self) -> bool:
        """Check if the STT service is configured and accessible."""
        return bool(self.api_key)


# Singleton instance
stt_service = STTService()
