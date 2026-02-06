"""
Speech-to-Text Service
Groq Whisper Large v3 Turbo with:
- 30s timeout
- Single retry on failure
- Audio debounce (skip <500ms, silence detection)
"""

import io
import logging
from typing import Optional, BinaryIO
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Audio debounce settings
MIN_AUDIO_DURATION_MS = 500
MIN_AUDIO_BYTES = 3000  # ~500ms of webm audio


class STTService:
    """Speech-to-Text using Groq Whisper with debounce and retry."""
    
    WHISPER_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
    MODEL = "whisper-large-v3-turbo"
    TIMEOUT = 30.0
    
    def __init__(self):
        self.api_key = settings.groq_api_key
        self._client: Optional[httpx.AsyncClient] = None
        logger.info(f"STT Service: Groq Whisper, timeout={self.TIMEOUT}s")
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.TIMEOUT,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        return self._client
    
    def _should_skip_audio(self, audio_bytes: bytes) -> tuple[bool, str]:
        """
        Check if audio should be skipped (debounce).
        Returns (should_skip, reason).
        """
        if len(audio_bytes) < MIN_AUDIO_BYTES:
            return True, f"too_short ({len(audio_bytes)} bytes < {MIN_AUDIO_BYTES})"
        
        if self._is_silence(audio_bytes):
            return True, "silence_detected"
        
        return False, ""
    
    def _is_silence(self, audio_bytes: bytes) -> bool:
        """
        Quick silence detection based on byte variance.
        If audio bytes have very low variance, likely silence.
        """
        if len(audio_bytes) < 1000:
            return True
        
        sample = audio_bytes[100:1100]
        if not sample:
            return True
        
        avg = sum(sample) / len(sample)
        variance = sum((b - avg) ** 2 for b in sample) / len(sample)
        
        return variance < 50
    
    async def transcribe_bytes(
        self,
        audio_bytes: bytes,
        filename: str = "audio.webm",
        language: Optional[str] = None
    ) -> Optional[str]:
        """
        Transcribe audio bytes with debounce and single retry.
        """
        should_skip, reason = self._should_skip_audio(audio_bytes)
        if should_skip:
            logger.info(f"STT skipped: {reason}")
            return None
        
        audio_file = io.BytesIO(audio_bytes)
        result = await self._transcribe_with_retry(audio_file, filename, language)
        return result
    
    async def _transcribe_with_retry(
        self,
        audio_file: BinaryIO,
        filename: str,
        language: Optional[str]
    ) -> Optional[str]:
        """
        Transcribe with single retry on failure.
        """
        for attempt in range(2):
            result = await self._do_transcribe(audio_file, filename, language)
            if result is not None:
                return result
            
            if attempt == 0:
                logger.warning("STT failed, retrying once...")
                audio_file.seek(0)
        
        logger.error("STT failed after retry")
        return None
    
    async def _do_transcribe(
        self,
        audio_file: BinaryIO,
        filename: str,
        language: Optional[str]
    ) -> Optional[str]:
        """
        Single transcription attempt.
        """
        if not self.api_key:
            logger.error("Groq API key not configured")
            return None
        
        try:
            client = await self._get_client()
            
            ext = filename.split(".")[-1].lower()
            content_types = {
                "m4a": "audio/m4a",
                "mp3": "audio/mpeg",
                "wav": "audio/wav",
                "webm": "audio/webm",
                "ogg": "audio/ogg",
                "flac": "audio/flac"
            }
            content_type = content_types.get(ext, "audio/webm")
            
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
                text = result.get("text", "").strip()
                
                if not text or text.lower() in ["", "you", "thank you", "thanks"]:
                    logger.debug(f"STT empty/noise: '{text}'")
                    return None
                
                logger.info(f"STT success: '{text[:50]}...' ({len(text)} chars)")
                return text
            else:
                logger.error(f"Groq error {response.status_code}: {response.text[:100]}")
                return None
                
        except httpx.TimeoutException:
            logger.error("STT timeout")
            return None
        except Exception as e:
            logger.error(f"STT error: {e}")
            return None
    
    async def transcribe(
        self,
        audio_file: BinaryIO,
        filename: str = "audio.m4a",
        language: Optional[str] = None
    ) -> Optional[str]:
        """Legacy method for file-based transcription."""
        audio_bytes = audio_file.read()
        audio_file.seek(0)
        return await self.transcribe_bytes(audio_bytes, filename, language)
    
    async def health_check(self) -> bool:
        return bool(self.api_key)
    
    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


stt_service = STTService()
