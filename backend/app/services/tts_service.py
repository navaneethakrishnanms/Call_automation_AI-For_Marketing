"""
Text-to-Speech Service
======================
MODEL SELECTION RULES:
  - English → XTTS v2 (local, "Daisy Studious" voice)
  - Tamil/Tanglish → Sarvam AI Bulbul v3 (meera voice — conversational)

NEVER use XTTS for Tamil.
NEVER use Sarvam for English (unless XTTS fails).
"""

import re

import os
import logging
import tempfile
import subprocess
from typing import Optional, Literal
import httpx
import base64

from app.config import settings

logger = logging.getLogger(__name__)

TTSLanguage = Literal["english", "tamil", "tanglish"]


# ============================================================================
# XTTS v2 CONFIGURATION (English only)
# ============================================================================
XTTS_SPEAKER = "Daisy Studious"
XTTS_LANGUAGE = "en"


# ============================================================================
# SARVAM AI CONFIGURATION (Tamil/Tanglish only)
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
    TTS with strict language routing:
      - English → XTTS v2 (local)
      - Tamil/Tanglish → Sarvam AI
    """
    
    SARVAM_URL = "https://api.sarvam.ai/text-to-speech"
    
    def __init__(self):
        self.sarvam_key = settings.sarvam_api_key
        self._client: Optional[httpx.AsyncClient] = None
        self._xtts_available: Optional[bool] = None
        
        logger.info("TTS Service initialized")
        logger.info(f"  English → XTTS v2 (speaker: {XTTS_SPEAKER})")
        logger.info(f"  Tamil/Tanglish → Sarvam Bulbul v3 (speaker: {SARVAM_SPEAKER})")
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client
    
    def _check_xtts(self) -> bool:
        """Check if XTTS v2 is available in torch_gpu conda env."""
        if self._xtts_available is not None:
            return self._xtts_available
        
        try:
            # Check in torch_gpu conda environment
            result = subprocess.run(
                ["conda", "run", "-n", "torch_gpu", "tts", "--version"],
                capture_output=True,
                timeout=10
            )
            self._xtts_available = result.returncode == 0
            logger.info(f"XTTS v2 available (torch_gpu env): {self._xtts_available}")
        except Exception as e:
            self._xtts_available = False
            logger.warning(f"XTTS v2 not available: {e}")
        
        return self._xtts_available
    async def synthesize(
        self,
        text: str,
        language: TTSLanguage = "english",
        normalize: bool = True
    ) -> Optional[bytes]:
        """
        Synthesize speech with Sarvam as primary.
        
        ROUTING (Sarvam-first):
          - All languages → Sarvam AI (primary)
          - English → XTTS v2 (fallback if Sarvam fails)
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
        
        # PRIMARY: Try Sarvam first (fast and reliable)
        logger.info(f"TTS routing: {language} → Sarvam AI (primary)")
        audio = await self._synthesize_sarvam(text, lang_code)
        if audio:
            return audio
        
        # FALLBACK: Try XTTS for English only
        if language == "english":
            logger.warning("Sarvam failed, trying XTTS v2 as fallback")
            audio = await self._synthesize_xtts(text)
            if audio:
                return audio
        
        logger.error("All TTS methods failed")
        return None
    
    async def _synthesize_xtts(self, text: str) -> Optional[bytes]:
        """
        Synthesize using local XTTS v2.
        Speaker: Daisy Studious
        Language: English only
        
        NOTE: XTTS is installed in the 'torch_gpu' conda environment,
        so we must activate it before running the tts command.
        """
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                output_path = f.name
            
            # XTTS v2 is installed in torch_gpu conda env
            # Use conda run to execute in that environment
            cmd = [
                "conda", "run", "-n", "torch_gpu", "--no-capture-output",
                "tts",
                "--model_name", "tts_models/multilingual/multi-dataset/xtts_v2",
                "--text", text,
                "--speaker_idx", XTTS_SPEAKER,
                "--language_idx", XTTS_LANGUAGE,
                "--out_path", output_path
            ]
            
            logger.debug(f"XTTS command: {' '.join(cmd)}")
            
            # Run with longer timeout since XTTS can take 15-20 seconds
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                timeout=90,
                shell=False
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                with open(output_path, "rb") as f:
                    audio_bytes = f.read()
                os.unlink(output_path)
                logger.info(f"XTTS v2 success: {len(audio_bytes)} bytes")
                return audio_bytes
            else:
                stderr = result.stderr.decode() if result.stderr else ""
                logger.error(f"XTTS error (code {result.returncode}): {stderr[:300]}")
                if os.path.exists(output_path):
                    os.unlink(output_path)
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("XTTS timeout (90s)")
            return None
        except Exception as e:
            logger.error(f"XTTS error: {e}")
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
            "routing": {
                "english": "xtts_v2",
                "tamil": "sarvam",
                "tanglish": "sarvam"
            },
            "xtts_available": self._check_xtts(),
            "xtts_speaker": XTTS_SPEAKER,
            "sarvam_configured": bool(self.sarvam_key),
            "sarvam_model": SARVAM_MODEL,
            "sarvam_speaker": SARVAM_SPEAKER,
        }
    
    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


tts_service = TTSService()
