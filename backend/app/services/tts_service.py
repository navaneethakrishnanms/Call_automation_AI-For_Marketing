"""
Text-to-Speech Service
ROUTING: Sarvam AI (bulbul:v3) for ALL languages
- Tamil → Sarvam (ta-IN)
- Tanglish → Sarvam (ta-IN)  
- English → Sarvam (en-IN)

REMOVED: ElevenLabs (401 errors), XTTS (not integrated yet)
"""

import logging
from typing import Optional, Literal
import httpx
import base64

from app.config import settings

logger = logging.getLogger(__name__)

TTSLanguage = Literal["english", "tamil", "tanglish"]


# ============================================================================
# SARVAM AI CONFIGURATION - STRICT VALIDATION
# ============================================================================

# Valid Sarvam speakers (as of 2024)
SARVAM_VALID_SPEAKERS = [
    "kavitha",    # Female Tamil (DEFAULT)
    "meera",      # Female
    "arvind",     # Male
    "priya",      # Female
]

# Valid Sarvam models
SARVAM_VALID_MODELS = [
    "bulbul:v3",  # Latest (REQUIRED)
    "bulbul:v2",
    "bulbul:v1",
]

# Sarvam language codes
SARVAM_LANG_MAP = {
    "english": "en-IN",
    "tamil": "ta-IN",
    "tanglish": "ta-IN",
}

# Default configuration
DEFAULT_SARVAM_SPEAKER = "kavitha"
DEFAULT_SARVAM_MODEL = "bulbul:v3"


class TTSService:
    """
    Text-to-Speech service using Sarvam AI for ALL languages.
    Model: bulbul:v3
    Speaker: kavitha (default)
    
    ElevenLabs: DISABLED (removed)
    XTTS: NOT INTEGRATED (future)
    """
    
    SARVAM_URL = "https://api.sarvam.ai/text-to-speech"
    
    def __init__(self):
        """Initialize TTS service."""
        self.sarvam_key = settings.sarvam_api_key
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info(f"TTS Service initialized")
        logger.info(f"  Provider: Sarvam AI (all languages)")
        logger.info(f"  Model: {DEFAULT_SARVAM_MODEL}")
        logger.info(f"  Speaker: {DEFAULT_SARVAM_SPEAKER}")
        logger.info(f"  API key: {'configured' if self.sarvam_key else 'MISSING!'}")
    
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
        Synthesize speech using Sarvam AI.
        
        Args:
            text: Text to convert to speech
            language: Target language (english/tamil/tanglish)
            normalize: Whether to normalize text
            
        Returns:
            Audio bytes (WAV) or None
        """
        if not text or not text.strip():
            logger.warning("Empty text provided to TTS")
            return None
        
        # Apply normalization
        if normalize:
            from app.utils.tts_normalizer import normalize_for_speech
            text = normalize_for_speech(text)
            logger.debug(f"Normalized: {text[:80]}...")
        
        # Use Sarvam for all languages
        return await self._synthesize_sarvam(text, language)
    
    async def _synthesize_sarvam(
        self,
        text: str,
        language: TTSLanguage
    ) -> Optional[bytes]:
        """
        Synthesize using Sarvam AI bulbul:v3.
        STRICT validation of model and speaker.
        """
        if not self.sarvam_key:
            logger.error("Sarvam API key not configured!")
            return None
        
        # STRICT VALIDATION
        speaker = DEFAULT_SARVAM_SPEAKER
        model = DEFAULT_SARVAM_MODEL
        
        if speaker not in SARVAM_VALID_SPEAKERS:
            logger.error(f"Invalid speaker '{speaker}', using 'kavitha'")
            speaker = "kavitha"
        
        if model not in SARVAM_VALID_MODELS:
            logger.error(f"Invalid model '{model}', using 'bulbul:v3'")
            model = "bulbul:v3"
        
        lang_code = SARVAM_LANG_MAP.get(language, "en-IN")
        
        try:
            client = await self._get_client()
            
            headers = {
                "api-subscription-key": self.sarvam_key,
                "Content-Type": "application/json",
            }
            
            payload = {
                "inputs": [text],
                "target_language_code": lang_code,
                "speaker": speaker,
                "model": model,
                "pace": 1.0,
                "speech_sample_rate": 22050,
                "enable_preprocessing": True,
            }
            
            logger.info(f"Sarvam TTS: lang={lang_code}, model={model}, speaker={speaker}")
            logger.debug(f"Payload: {payload}")
            
            response = await client.post(
                self.SARVAM_URL,
                json=payload,
                headers=headers
            )
            
            logger.info(f"Sarvam response: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                audios = result.get("audios", [])
                
                if audios:
                    audio_base64 = audios[0]
                    audio_bytes = base64.b64decode(audio_base64)
                    logger.info(f"Sarvam TTS success: {len(audio_bytes)} bytes")
                    return audio_bytes
                else:
                    logger.warning(f"Sarvam returned empty audio: {result}")
                    return None
            else:
                logger.error(f"Sarvam error {response.status_code}: {response.text}")
                return None
                
        except httpx.TimeoutException:
            logger.error("Sarvam TTS timeout")
            return None
        except Exception as e:
            logger.error(f"Sarvam TTS failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    async def health_check(self) -> dict:
        """Check TTS service health."""
        return {
            "provider": "sarvam",
            "sarvam_configured": bool(self.sarvam_key),
            "model": DEFAULT_SARVAM_MODEL,
            "speaker": DEFAULT_SARVAM_SPEAKER,
            "elevenlabs": "REMOVED",
            "xtts": "NOT_INTEGRATED",
        }
    
    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Singleton
tts_service = TTSService()
