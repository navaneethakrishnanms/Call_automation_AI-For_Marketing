"""
Call Orchestrator
Manages the end-to-end call flow: STT → Language Detection → FAQ → LLM → TTS.
"""

import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime

from app.services.language_detector import language_detector, LanguageType
from app.services.stt_service import stt_service
from app.services.llm_service import llm_service
from app.services.faq_retrieval import faq_service
from app.services.tts_service import tts_service
from app.services.lead_qualifier import lead_qualifier

logger = logging.getLogger(__name__)


@dataclass
class ConversationState:
    """State for an ongoing conversation."""
    call_id: int
    campaign_id: int
    phone_number: str
    language: LanguageType = "english"
    history: List[Dict[str, str]] = field(default_factory=list)
    transcript: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    lead_signals: List[str] = field(default_factory=list)


class CallOrchestrator:
    """Orchestrates the AI-powered call flow."""
    
    def __init__(self):
        """Initialize the call orchestrator."""
        self._active_calls: Dict[int, ConversationState] = {}
    
    def start_call(
        self,
        call_id: int,
        campaign_id: int,
        phone_number: str,
        faqs: Optional[List[Dict]] = None
    ) -> ConversationState:
        """
        Initialize a new call session.
        
        Args:
            call_id: Database call ID
            campaign_id: Campaign ID
            phone_number: Caller's phone number
            faqs: Campaign FAQs to load
            
        Returns:
            New conversation state
        """
        # Load FAQs if provided
        if faqs and not faq_service.is_campaign_loaded(campaign_id):
            faq_service.load_faqs(campaign_id, faqs)
        
        state = ConversationState(
            call_id=call_id,
            campaign_id=campaign_id,
            phone_number=phone_number
        )
        
        self._active_calls[call_id] = state
        logger.info(f"Started call session: {call_id}")
        return state
    
    async def process_audio_input(
        self,
        call_id: int,
        audio_bytes: bytes,
        campaign_context: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Process audio input and generate audio response.
        
        Full pipeline: STT → Language Detection → FAQ Retrieval → LLM → TTS
        
        Args:
            call_id: Active call ID
            audio_bytes: Raw audio from caller
            campaign_context: Additional context about the campaign
            
        Returns:
            Response audio bytes or None if failed
        """
        state = self._active_calls.get(call_id)
        if not state:
            logger.error(f"No active call found: {call_id}")
            return None
        
        try:
            # Step 1: Speech-to-Text
            user_text = await stt_service.transcribe_bytes(audio_bytes)
            if not user_text:
                logger.warning(f"STT failed for call {call_id}")
                return await self._generate_retry_audio(state.language)
            
            # Add to transcript
            state.transcript.append(f"User: {user_text}")
            
            # Step 2: Detect language
            detected_lang = language_detector.detect_language(user_text)
            state.language = detected_lang
            
            # Process text input and get response
            response_text = await self._process_text_input(
                state,
                user_text,
                campaign_context
            )
            
            if not response_text:
                return await self._generate_retry_audio(state.language)
            
            # Step 5: Text-to-Speech
            audio_response = await tts_service.synthesize(
                response_text,
                state.language
            )
            
            return audio_response
            
        except Exception as e:
            logger.error(f"Call processing failed: {str(e)}")
            return await self._generate_retry_audio(state.language)
    
    async def process_text_input(
        self,
        call_id: int,
        user_text: str,
        campaign_context: Optional[str] = None
    ) -> Optional[str]:
        """
        Process text input (for testing without audio).
        
        Args:
            call_id: Active call ID
            user_text: User's text message
            campaign_context: Additional context
            
        Returns:
            Response text or None if failed
        """
        state = self._active_calls.get(call_id)
        if not state:
            # Create temporary state for testing
            state = ConversationState(
                call_id=call_id,
                campaign_id=0,
                phone_number=""
            )
            self._active_calls[call_id] = state
        
        # Detect language
        state.language = language_detector.detect_language(user_text)
        state.transcript.append(f"User: {user_text}")
        
        return await self._process_text_input(state, user_text, campaign_context)
    
    async def _process_text_input(
        self,
        state: ConversationState,
        user_text: str,
        campaign_context: Optional[str] = None
    ) -> Optional[str]:
        """Internal text processing logic."""
        
        # Step 3: Retrieve relevant FAQs
        faq_context = ""
        if faq_service.is_campaign_loaded(state.campaign_id):
            relevant_faqs = faq_service.retrieve(
                state.campaign_id,
                user_text,
                top_k=3,
                threshold=0.5
            )
            faq_context = faq_service.format_faq_context(relevant_faqs)
        
        # Step 4: Generate response with LLM
        response_text = await llm_service.generate_response(
            user_message=user_text,
            language=state.language,
            context=campaign_context,
            faq_context=faq_context,
            conversation_history=state.history
        )
        
        if response_text:
            # Update conversation history
            state.history.append({"role": "user", "content": user_text})
            state.history.append({"role": "assistant", "content": response_text})
            state.transcript.append(f"Agent: {response_text}")
            
            # Track lead signals
            signals = lead_qualifier.extract_signals(user_text)
            state.lead_signals.extend(signals)
        
        return response_text
    
    async def _generate_retry_audio(self, language: LanguageType) -> Optional[bytes]:
        """Generate a retry prompt audio."""
        retry_messages = {
            "english": "I didn't quite catch that. Could you please repeat?",
            "tamil": "மன்னிக்கவும், மீண்டும் சொல்லுங்கள்?",
            "tanglish": "Sorry, konjam puriyala. Please repeat pannunga?"
        }
        message = retry_messages.get(language, retry_messages["english"])
        return await tts_service.synthesize(message, language)
    
    def end_call(self, call_id: int) -> Optional[Dict[str, Any]]:
        """
        End a call session and return summary.
        
        Args:
            call_id: Call ID to end
            
        Returns:
            Call summary with transcript and lead qualification
        """
        state = self._active_calls.pop(call_id, None)
        if not state:
            return None
        
        # Qualify the lead
        qualification = lead_qualifier.qualify_lead(
            state.transcript,
            state.lead_signals
        )
        
        summary = {
            "call_id": call_id,
            "duration_seconds": (datetime.utcnow() - state.started_at).total_seconds(),
            "language_detected": state.language,
            "transcript": "\n".join(state.transcript),
            "lead_qualification": qualification["qualification"],
            "lead_score": qualification["score"],
            "lead_signals": state.lead_signals
        }
        
        logger.info(f"Call {call_id} ended: {qualification['qualification']} lead")
        return summary
    
    def get_active_calls(self) -> List[int]:
        """Get list of active call IDs."""
        return list(self._active_calls.keys())


# Singleton instance
call_orchestrator = CallOrchestrator()
