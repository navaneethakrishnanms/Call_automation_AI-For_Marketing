"""
Text-to-Speech Service
Integrates with ElevenLabs (English) and Sarvam AI (Tamil) for speech synthesis.
"""

import logging
from typing import Optional, Literal
import httpx
import base64

from app.config import settings

logger = logging.getLogger(__name__)

TTSLanguage = Literal["english", "tamil", "tanglish"]


class TTSService:
    """Text-to-Speech service with multi-language support."""
    
    ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech"
    SARVAM_URL = "https://api.sarvam.ai/text-to-speech"
    
    def __init__(self):
        """Initialize the TTS service."""
        self.elevenlabs_key = settings.elevenlabs_api_key
        self.elevenlabs_voice = settings.elevenlabs_voice_id
        self.sarvam_key = settings.sarvam_api_key
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client
    
    async def synthesize(
        self,
        text: str,
        language: TTSLanguage = "english",
        normalize: bool = True
    ) -> Optional[bytes]:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to convert to speech
            language: Target language
            normalize: Whether to normalize text for natural speech
            
        Returns:
            Audio bytes (MP3) or None if failed
        """
        # Apply TTS normalization to prevent robotic pronunciation
        if normalize:
            from app.utils.tts_normalizer import normalize_for_speech
            text = normalize_for_speech(text)
            logger.debug(f"Normalized text for TTS: {text}")
        
        if language == "tamil":
            return await self._synthesize_tamil(text)
        else:
            # Use ElevenLabs for English and Tanglish
            return await self._synthesize_english(text)
    
    async def _synthesize_english(self, text: str) -> Optional[bytes]:
        """Synthesize English speech using ElevenLabs."""
        if not self.elevenlabs_key:
            logger.error("ElevenLabs API key not configured")
            return None
        
        try:
            client = await self._get_client()
            
            url = f"{self.ELEVENLABS_URL}/{self.elevenlabs_voice}"
            
            headers = {
                "xi-api-key": self.elevenlabs_key,
                "Content-Type": "application/json",
            }
            
            payload = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.5,
                    "use_speaker_boost": True
                }
            }
            
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                logger.info(f"ElevenLabs TTS successful: {len(text)} chars")
                return response.content
            else:
                logger.error(f"ElevenLabs API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"ElevenLabs TTS failed: {str(e)}")
            return None
    
    async def _synthesize_tamil(self, text: str) -> Optional[bytes]:
        """Synthesize Tamil speech using Sarvam AI."""
        if not self.sarvam_key:
            logger.error("Sarvam AI API key not configured")
            return None
        
        try:
            client = await self._get_client()
            
            headers = {
                "api-subscription-key": self.sarvam_key,
                "Content-Type": "application/json",
            }
            
            payload = {
                "inputs": [text],
                "target_language_code": "ta-IN",
                "speaker": "meera",  # Female Tamil voice
                "pitch": 0,
                "pace": 1.0,
                "loudness": 1.0,
                "speech_sample_rate": 22050,
                "enable_preprocessing": True,
                "model": "bulbul:v1"
            }
            
            response = await client.post(
                self.SARVAM_URL,
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                # Sarvam returns base64 encoded audio
                audios = result.get("audios", [])
                if audios:
                    audio_base64 = audios[0]
                    audio_bytes = base64.b64decode(audio_base64)
                    logger.info(f"Sarvam TTS successful: {len(text)} chars")
                    return audio_bytes
                return None
            else:
                logger.error(f"Sarvam API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Sarvam TTS failed: {str(e)}")
            return None
    
    async def health_check(self) -> dict:
        """Check if TTS services are configured."""
        return {
            "elevenlabs": bool(self.elevenlabs_key),
            "sarvam": bool(self.sarvam_key)
        }
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Singleton instance
tts_service = TTSService()
