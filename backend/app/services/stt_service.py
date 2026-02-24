"""
Speech-to-Text Service
======================
PARALLEL DUAL-ENGINE (Sarvam PRIMARY):
  - Run BOTH Sarvam AND Whisper (Groq) on EVERY turn
  - Sarvam ASR v3 = PRIMARY (best for Tamil + Indian English)
  - Whisper = SECONDARY/FALLBACK (used when Sarvam transliterates English)
  - Smart pick: detect transliteration, prefer correct result
"""

import io
import re
import logging
import asyncio
from typing import Optional, BinaryIO, Tuple
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Audio debounce settings
MIN_AUDIO_BYTES = 1000  # Lowered — webm compresses heavily

# Tamil script Unicode range
TAMIL_SCRIPT_RE = re.compile(r'[\u0B80-\u0BFF]')

# Common English words that Sarvam transliterates into Tamil script
# If the text is MOSTLY these kinds of transliterations, it's misrecognized English
TRANSLITERATION_MARKERS = re.compile(
    r'(தி|இஸ்|யுவர்|மை|வாட்|ஹவ்|கேன்|வில்|நாட்|ஆர்|யூ|ஹலோ|நோ|யெஸ்|'
    r'பட்|ஃபார்|இட்|வித்|ஃப்ரம்|ஆஃப்|அண்ட்|ஆர்|'
    r'கால|காலேஜ்|ஸ்கூல்|பேங்க்|ஹாஸ்பிடல்|'
    r'ப்ளீஸ்|தேங்க்|சார்|சர்|மேம்|ஓகே|'
    r'ஒன்|டூ|த்ரீ|ஃபோர்|ஃபைவ்|சிக்ஸ்|செவன்|எயிட்|நைன்|டென்|'
    r'சிஎஸ்|ஐடி|எம்பிஏ|எம்சிஏ|ஏஐ)',
    re.UNICODE
)


def _is_transliterated_english(text: str) -> bool:
    """
    Detect if Tamil-script text is just transliterated English.
    e.g., "சம் ஒன் சிஎஸ் யுவர் காலேஜ் இஸ் ஃபர்ஸ்ட்" = transliterated English
    vs    "நான் இந்த கல்லூரியில் படிக்க விரும்புகிறேன்" = real Tamil
    """
    if not text or not TAMIL_SCRIPT_RE.search(text):
        return False
    
    words = text.split()
    if len(words) < 2:
        return False
    
    # Count how many words match transliteration patterns
    transliterated_count = 0
    for word in words:
        if TRANSLITERATION_MARKERS.search(word):
            transliterated_count += 1
    
    ratio = transliterated_count / len(words)
    
    # If >40% of words look like transliterated English, it's probably English
    if ratio > 0.4:
        logger.info(f"Transliteration detected: {ratio:.0%} of words are transliterated English")
        return True
    
    return False


class STTService:
    """
    PARALLEL dual-engine STT — Sarvam PRIMARY, Whisper SECONDARY:
      - Every turn: run BOTH Sarvam + Whisper
      - Prefer Sarvam unless it transliterates English
    """
    
    WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
    WHISPER_MODEL = "whisper-large-v3-turbo"
    SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
    TIMEOUT = 30.0
    
    def __init__(self):
        self.groq_key = settings.groq_api_key
        self.sarvam_key = settings.sarvam_api_key
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info("STT Service initialized (Sarvam PRIMARY, Whisper SECONDARY)")
        logger.info(f"  Engine 1 (PRIMARY): Sarvam ASR v3")
        logger.info(f"  Engine 2 (FALLBACK): Whisper V3 Turbo via Groq")
        logger.info(f"  Strategy: Run both parallel, prefer Sarvam unless transliteration detected")
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.TIMEOUT)
        return self._client
    
    def _should_skip(self, audio_bytes: bytes) -> Tuple[bool, str]:
        if len(audio_bytes) < MIN_AUDIO_BYTES:
            return True, f"too_short ({len(audio_bytes)} bytes)"
        # NOTE: Skip silence detection for compressed formats (webm/opus).
        # Compressed bytes have uniform entropy regardless of audio content,
        # making raw-byte variance checks meaningless.
        return False, ""
    
    async def transcribe_bytes(
        self,
        audio_bytes: bytes,
        filename: str = "audio.webm",
        language_hint: Optional[str] = None
    ) -> Optional[str]:
        """
        ALWAYS run both engines in parallel and pick the best result.
        language_hint is used for fine-tuning the decision, NOT for routing.
        """
        skip, reason = self._should_skip(audio_bytes)
        if skip:
            logger.info(f"STT skipped: {reason}")
            return None
        
        # ALWAYS run both engines in parallel, prefer Sarvam
        logger.info("🎯 STT: Running Sarvam (PRIMARY) + Whisper (SECONDARY) in parallel")
        return await self._transcribe_parallel(audio_bytes, filename, language_hint)
    
    async def _transcribe_parallel(
        self,
        audio_bytes: bytes,
        filename: str,
        language_hint: Optional[str] = None
    ) -> Optional[str]:
        """
        Run both engines in parallel. Sarvam is PRIMARY, Whisper is SECONDARY.
        """
        try:
            whisper_task = asyncio.create_task(
                self._transcribe_whisper(audio_bytes, filename)
            )
            sarvam_task = asyncio.create_task(
                self._transcribe_sarvam(audio_bytes, language_hint or "auto")
            )
            
            whisper_result, sarvam_result = await asyncio.gather(
                whisper_task, sarvam_task, return_exceptions=True
            )
            
            # Extract results
            whisper_text = None
            whisper_confidence = 0.0
            if isinstance(whisper_result, tuple):
                whisper_text, whisper_confidence = whisper_result
            
            sarvam_text = None
            if isinstance(sarvam_result, str):
                sarvam_text = sarvam_result
            
            logger.info(
                f"Parallel results — "
                f"Sarvam (PRIMARY): '{(sarvam_text or '')[:60]}', "
                f"Whisper (SECONDARY): '{(whisper_text or '')[:60]}' (conf={whisper_confidence:.2f})"
            )
            
            # === SARVAM-FIRST DECISION LOGIC ===
            
            # Case 1: Sarvam returned transliterated English → fall back to Whisper
            if sarvam_text and _is_transliterated_english(sarvam_text):
                if whisper_text:
                    logger.info("→ Sarvam transliterated English! Falling back to Whisper.")
                    return whisper_text
            
            # Case 2: Sarvam has valid result → use it (PRIMARY)
            if sarvam_text:
                logger.info("→ Using Sarvam (PRIMARY engine)")
                return sarvam_text
            
            # Case 3: Sarvam failed, use Whisper as fallback
            if whisper_text:
                logger.info("→ Sarvam failed, using Whisper (FALLBACK)")
                return whisper_text
            
            # Case 4: Both failed
            logger.warning("Both STT engines failed")
            return None
            
        except Exception as e:
            logger.error(f"Parallel transcription error: {e}")
            # Emergency fallback: try Sarvam alone first, then Whisper
            sarvam_result = await self._transcribe_sarvam(audio_bytes, language_hint)
            if sarvam_result:
                return sarvam_result
            result, _ = await self._transcribe_whisper(audio_bytes, filename)
            return result
    
    async def _transcribe_whisper(
        self,
        audio_bytes: bytes,
        filename: str
    ) -> Tuple[Optional[str], float]:
        """Transcribe using Groq Whisper V3 Turbo."""
        if not self.groq_key:
            return None, 0.0
        
        for attempt in range(2):
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
                    
                    if not text or text.lower() in ["", "you", "thank you", "thanks"]:
                        return None, 0.0
                    
                    segments = result.get("segments", [])
                    if segments:
                        avg_confidence = sum(s.get("avg_logprob", -1) for s in segments) / len(segments)
                        confidence = min(1.0, max(0.0, 1 + avg_confidence))
                    else:
                        confidence = 0.8
                    
                    detected_lang = result.get("language", "")
                    logger.info(f"Whisper: '{text[:80]}' (conf={confidence:.2f}, lang={detected_lang})")
                    return text, confidence
                else:
                    logger.error(f"Whisper error {response.status_code}: {response.text[:200]}")
                    
            except httpx.TimeoutException:
                logger.error("Whisper timeout")
            except Exception as e:
                logger.error(f"Whisper error: {e}")
            
            if attempt == 0:
                logger.warning("Whisper retry...")
        
        return None, 0.0
    
    async def _transcribe_sarvam(
        self, 
        audio_bytes: bytes,
        language_hint: Optional[str] = None
    ) -> Optional[str]:
        """Transcribe using Sarvam ASR v3."""
        if not self.sarvam_key:
            return None
        
        try:
            client = await self._get_client()
            
            lang_code_map = {
                "tamil": "ta-IN",
                "tanglish": "ta-IN",
                "english": "en-IN",
                "auto": "unknown",
            }
            lang_code = lang_code_map.get(language_hint, "unknown")
            
            # Send with correct content type — browser records webm/opus
            files = {"file": ("audio.webm", io.BytesIO(audio_bytes), "audio/webm")}
            data = {
                "language_code": lang_code,
                "model": "saaras:v3",
            }
            
            response = await client.post(
                self.SARVAM_STT_URL,
                files=files,
                data=data,
                headers={"api-subscription-key": self.sarvam_key}
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result.get("transcript", "").strip()
                language_detected = result.get("language_code", "unknown")
                
                if text:
                    logger.info(f"Sarvam ASR: '{text[:80]}' (lang={language_detected})")
                    return text
                else:
                    logger.warning("Sarvam returned empty transcript")
            else:
                logger.error(f"Sarvam STT error {response.status_code}: {response.text[:200]}")
                
        except httpx.TimeoutException:
            logger.error("Sarvam STT timeout")
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
            "routing": "parallel_sarvam_primary",
            "primary": "sarvam_asr_v3",
            "secondary": "whisper_v3_turbo",
            "strategy": "always_parallel + sarvam_preferred + transliteration_detection",
            "groq_configured": bool(self.groq_key),
            "sarvam_configured": bool(self.sarvam_key),
        }
    
    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


stt_service = STTService()
