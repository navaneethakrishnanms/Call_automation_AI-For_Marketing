"""
Text-to-Speech Service
======================
Sarvam AI Bulbul V3 — sole TTS engine for all languages.
Speaker: priya
"""

import re
import logging
from typing import Optional, Literal
import httpx
import base64

from app.config import settings

logger = logging.getLogger(__name__)

TTSLanguage = Literal["english", "tamil", "tanglish"]


# ============================================================================
# SARVAM AI CONFIGURATION (all languages)
# ============================================================================
SARVAM_VALID_SPEAKERS = ["aditya", "ritu", "ashutosh", "priya", "neha", "rahul", "pooja", "rohan", "simran", "kavya", "amit", "dev"]
SARVAM_MODEL = "bulbul:v3"
SARVAM_SPEAKER = "priya"  # Matches our chatbot persona + natural female voice
SARVAM_LANG_MAP = {
    "tamil": "ta-IN",
    "tanglish": "ta-IN",
}


class TTSService:
    """
    TTS using Sarvam AI Bulbul V3 for all languages.
    """
    
    SARVAM_URL = "https://api.sarvam.ai/text-to-speech"
    
    def __init__(self):
        self.sarvam_key = settings.sarvam_api_key
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info("TTS Service initialized")
        logger.info(f"  All languages → Sarvam Bulbul V3 (speaker: {SARVAM_SPEAKER})")
    
    async def _get_client(self) -> httpx.AsyncClient:
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
        Synthesize speech using Sarvam Bulbul V3 (only engine).
        """
        if not text or not text.strip():
            logger.warning("Empty text for TTS")
            return None
        
        if normalize:
            from app.utils.tts_normalizer import normalize_for_speech
            text = normalize_for_speech(text)
        
        # Preprocess text for natural speech rhythm
        text = self._preprocess_for_speech(text)
        
        # Determine Sarvam language code
        if language == "english":
            lang_code = "en-IN"
        else:
            lang_code = SARVAM_LANG_MAP.get(language, "ta-IN")
        
        # Sarvam Bulbul V3 for all languages
        logger.info(f"TTS: {language} → Sarvam Bulbul V3")
        audio = await self._synthesize_sarvam(text, lang_code)
        if audio:
            return audio
        
        logger.error("TTS failed")
        return None
    

    async def _synthesize_sarvam(self, text: str, lang_code: str) -> Optional[bytes]:
        """
        Synthesize using Sarvam AI Bulbul v3.
        Speaker: kavitha
        Languages: ta-IN (Tamil/Tanglish), en-IN (English fallback)
        """
        if not self.sarvam_key:
            logger.error("Sarvam API key not configured!")
            return None
        
        try:
            client = await self._get_client()
            
            headers = {
                "api-subscription-key": self.sarvam_key,
                "Content-Type": "application/json",
            }
            
            payload = {
                "inputs": [text],
                "target_language_code": lang_code,
                "speaker": SARVAM_SPEAKER,
                "model": SARVAM_MODEL,
                "pace": 1.1,  # Natural phone call speed — slightly fast
                "speech_sample_rate": 24000,  # Better quality
                "enable_preprocessing": True,
                "encoding": "wav",
            }
            
            logger.info(f"Sarvam TTS: lang={lang_code}, speaker={SARVAM_SPEAKER}, text='{text[:60]}...'")
            
            response = await client.post(
                self.SARVAM_URL,
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                audios = result.get("audios", [])
                if audios:
                    audio_bytes = base64.b64decode(audios[0])
                    logger.info(f"Sarvam TTS success: {len(audio_bytes)} bytes, format=wav")
                    return audio_bytes
                logger.warning("Sarvam returned empty audio")
                return None
            else:
                logger.error(f"Sarvam error {response.status_code}: {response.text[:200]}")
                return None
                
        except httpx.TimeoutException:
            logger.error("Sarvam TTS timeout")
            return None
        except Exception as e:
            logger.error(f"Sarvam TTS error: {e}")
            return None
    
    def _preprocess_for_speech(self, text: str) -> str:
        """
        Make text sound more natural when spoken by TTS.
        Adds micro-pauses and breathing points that make speech human-like.
        """
        # Add natural pause after filler words (comma = micro-pause in TTS)
        fillers = ["Oh", "Hmm", "Yeah", "Actually", "So", "Well",
                   "ஆமா", "ஹ்ம்ம்", "அட", "ஓ", "ஹாய்",
                   "Aama", "Ada", "Hey", "Ah"]
        for filler in fillers:
            # Add comma after filler at start of sentence if not already there
            text = re.sub(
                rf'^({re.escape(filler)})([^,!?.])',
                rf'\1, \2', text
            )
        
        # Add micro-pause before questions (makes it sound like thinking)
        text = re.sub(r'(\w) (\?)', r'\1... \2', text, count=1)
        
        # Break very long sentences with natural pauses
        words = text.split()
        if len(words) > 15:
            mid = len(words) // 2
            # Find nearest comma or natural break point near middle
            for i in range(mid - 2, mid + 3):
                if i < len(words) and words[i].endswith((',', '.', '!')):
                    break
            else:
                # Insert a pause comma near the middle
                words.insert(mid, ',')
            text = ' '.join(words)
        
        return text.strip()
    
    async def health_check(self) -> dict:
        return {
            "engine": "sarvam_bulbul_v3",
            "sarvam_configured": bool(self.sarvam_key),
            "sarvam_model": SARVAM_MODEL,
            "sarvam_speaker": SARVAM_SPEAKER,
        }
    
    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


tts_service = TTSService()
