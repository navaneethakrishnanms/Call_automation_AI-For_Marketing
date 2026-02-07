"""
Speech-to-Text Service
======================
MODEL SELECTION RULES:
  PRIMARY: Whisper Large v3 Turbo (Groq)
  FALLBACK: Sarvam AI STT (for Tamil/low confidence)

Features:
  - 30s timeout
  - Single retry on failure
  - Audio debounce (<500ms skip)
  - Sarvam fallback for low confidence transcriptions
"""

import io
import logging
from typing import Optional, BinaryIO, Tuple
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Audio debounce settings
MIN_AUDIO_BYTES = 3000  # ~500ms


class STTService:
    """
    STT with fallback:
      PRIMARY: Whisper Large v3 Turbo (Groq)
      FALLBACK: Sarvam AI STT (for Tamil/low confidence)
    """
    
    # Groq Whisper
    WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
    WHISPER_MODEL = "whisper-large-v3-turbo"
    
    # Sarvam STT
    SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
    
    TIMEOUT = 30.0
    LOW_CONFIDENCE_THRESHOLD = 0.6
    
    def __init__(self):
        self.groq_key = settings.groq_api_key
        self.sarvam_key = settings.sarvam_api_key
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info("STT Service initialized")
        logger.info(f"  Primary: Whisper Large v3 Turbo (Groq)")
        logger.info(f"  Fallback: Sarvam AI STT")
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.TIMEOUT)
        return self._client
    
    def _should_skip(self, audio_bytes: bytes) -> Tuple[bool, str]:
        """Check if audio should be skipped (debounce)."""
        if len(audio_bytes) < MIN_AUDIO_BYTES:
            return True, f"too_short ({len(audio_bytes)} bytes)"
        if self._is_silence(audio_bytes):
            return True, "silence"
        return False, ""
    
    def _is_silence(self, audio_bytes: bytes) -> bool:
        """Quick silence detection."""
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
        language_hint: Optional[str] = None
    ) -> Optional[str]:
        """
        Transcribe audio with Whisper (primary) and Sarvam (fallback).
        """
        skip, reason = self._should_skip(audio_bytes)
        if skip:
            logger.info(f"STT skipped: {reason}")
            return None
        
        # Try Whisper first (primary)
        result, confidence = await self._transcribe_whisper(audio_bytes, filename)
        
        if result:
            # Check if we need Sarvam fallback (low confidence + likely Tamil)
            if confidence < self.LOW_CONFIDENCE_THRESHOLD and language_hint in ("tamil", "tanglish"):
                logger.info(f"Whisper low confidence ({confidence:.2f}), trying Sarvam fallback")
                sarvam_result = await self._transcribe_sarvam(audio_bytes)
                if sarvam_result:
                    return sarvam_result
            return result
        
        # Whisper failed completely, try Sarvam as fallback
        logger.warning("Whisper failed, trying Sarvam STT fallback")
        return await self._transcribe_sarvam(audio_bytes)
    
    async def _transcribe_whisper(
        self,
        audio_bytes: bytes,
        filename: str
    ) -> Tuple[Optional[str], float]:
        """
        Transcribe using Groq Whisper.
        Returns (text, confidence).
        """
        if not self.groq_key:
            logger.error("Groq API key not configured")
            return None, 0.0
        
        for attempt in range(2):  # Single retry
            try:
                client = await self._get_client()
                
                ext = filename.split(".")[-1].lower()
                content_types = {
                    "m4a": "audio/m4a", "mp3": "audio/mpeg",
                    "wav": "audio/wav", "webm": "audio/webm",
                    "ogg": "audio/ogg", "flac": "audio/flac"
                }
                content_type = content_types.get(ext, "audio/webm")
                
                audio_file = io.BytesIO(audio_bytes)
                files = {"file": (filename, audio_file, content_type)}
                data = {
                    "model": self.WHISPER_MODEL,
                    "temperature": "0",
                    "response_format": "verbose_json"
                }
                
                response = await client.post(
                    self.WHISPER_URL,
                    files=files,
                    data=data,
                    headers={"Authorization": f"Bearer {self.groq_key}"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    text = result.get("text", "").strip()
                    
                    # Filter noise
                    if not text or text.lower() in ["", "you", "thank you", "thanks"]:
                        return None, 0.0
                    
                    # Extract confidence from segments if available
                    segments = result.get("segments", [])
                    if segments:
                        avg_confidence = sum(s.get("avg_logprob", -1) for s in segments) / len(segments)
                        confidence = min(1.0, max(0.0, 1 + avg_confidence))
                    else:
                        confidence = 0.8  # Default confidence
                    
                    logger.info(f"Whisper: '{text[:50]}...' (conf={confidence:.2f})")
                    return text, confidence
                else:
                    logger.error(f"Whisper error {response.status_code}")
                    
            except httpx.TimeoutException:
                logger.error("Whisper timeout")
            except Exception as e:
                logger.error(f"Whisper error: {e}")
            
            if attempt == 0:
                logger.warning("Whisper retry...")
        
        return None, 0.0
    
    async def _transcribe_sarvam(self, audio_bytes: bytes) -> Optional[str]:
        """
        Transcribe using Sarvam AI STT (fallback for Tamil/Indian languages).
        """
        if not self.sarvam_key:
            logger.warning("Sarvam API key not configured for STT fallback")
            return None
        
        try:
            client = await self._get_client()
            
            # Sarvam STT uses multipart form data
            files = {"file": ("audio.wav", io.BytesIO(audio_bytes), "audio/wav")}
            data = {"language_code": "ta-IN"}  # Tamil
            
            response = await client.post(
                self.SARVAM_STT_URL,
                files=files,
                data=data,
                headers={"api-subscription-key": self.sarvam_key}
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result.get("transcript", "").strip()
                if text:
                    logger.info(f"Sarvam STT: '{text[:50]}...'")
                    return text
            else:
                logger.error(f"Sarvam STT error {response.status_code}: {response.text[:100]}")
                
        except Exception as e:
            logger.error(f"Sarvam STT error: {e}")
        
        return None
    
    async def transcribe(
        self,
        audio_file: BinaryIO,
        filename: str = "audio.m4a",
        language: Optional[str] = None
    ) -> Optional[str]:
        """Legacy method."""
        audio_bytes = audio_file.read()
        audio_file.seek(0)
        return await self.transcribe_bytes(audio_bytes, filename, language)
    
    async def health_check(self) -> dict:
        return {
            "primary": "whisper_large_v3_turbo",
            "fallback": "sarvam_stt",
            "groq_configured": bool(self.groq_key),
            "sarvam_configured": bool(self.sarvam_key),
        }
    
    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


stt_service = STTService()
