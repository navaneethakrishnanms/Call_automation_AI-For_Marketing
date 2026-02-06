"""
Voice Chatbot Routes
Browser-based voice chatbot API endpoints - PRIMARY interface.
Handles microphone audio input and returns audio response.
"""

import io
import base64
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.call import Call, CallStatus
from app.models.lead import Lead
from app.models.campaign import Campaign

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice-chatbot"])


class TextChatRequest(BaseModel):
    """Request for text-based chat (testing)."""
    text: str
    session_id: Optional[str] = None
    campaign_id: Optional[int] = None


class VoiceChatResponse(BaseModel):
    """Response from voice chat endpoint."""
    text_response: str
    audio_base64: Optional[str] = None
    audio_format: str = "mp3"
    detected_language: str
    lead_score: Optional[float] = None
    lead_status: Optional[str] = None
    session_id: str


# In-memory session storage (use Redis in production)
_sessions: dict = {}


@router.post("/chat/audio", response_model=VoiceChatResponse)
async def voice_chat_audio(
    audio: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    campaign_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    PRIMARY ENDPOINT: Process voice audio from browser microphone.
    
    Flow:
    1. Receive audio from browser (webm/mp3/wav)
    2. STT: Convert speech to text (Whisper via Groq)
    3. Detect language (EN/TA/Tanglish)
    4. Retrieve relevant FAQs (FAISS)
    5. Generate response (Llama 3.1 8B via Ollama)
    6. TTS: Convert to speech (Sarvam AI)
    7. Return audio + text + lead score
    """
    from app.services.stt_service import stt_service
    from app.services.language_detector import language_detector
    from app.services.faq_retrieval import faq_service
    from app.services.llm_service import llm_service
    from app.services.tts_service import tts_service
    from app.services.lead_qualifier import lead_qualifier
    import uuid
    
    # Generate or retrieve session
    if not session_id:
        session_id = str(uuid.uuid4())
        _sessions[session_id] = {
            "history": [],
            "transcript": [],
            "lead_signals": [],
            "campaign_id": campaign_id
        }
    elif session_id not in _sessions:
        _sessions[session_id] = {
            "history": [],
            "transcript": [],
            "lead_signals": [],
            "campaign_id": campaign_id
        }
    
    session = _sessions[session_id]
    
    try:
        # Step 1: Read audio file
        audio_bytes = await audio.read()
        filename = audio.filename or "audio.webm"
        
        logger.info(f"Received audio: {len(audio_bytes)} bytes, file: {filename}")
        
        # Step 2: Speech-to-Text
        user_text = await stt_service.transcribe_bytes(audio_bytes, filename)
        
        if not user_text:
            logger.warning("STT returned empty result")
            return VoiceChatResponse(
                text_response="I couldn't hear you clearly. Please try again.",
                detected_language="english",
                session_id=session_id
            )
        
        logger.info(f"STT result: {user_text}")
        session["transcript"].append(f"User: {user_text}")
        
        # Step 3: Detect language
        detected_lang = language_detector.detect_language(user_text)
        logger.info(f"Detected language: {detected_lang}")
        
        # Step 4: Get campaign context and FAQs
        campaign_context = None
        faq_context = ""
        
        if campaign_id or session.get("campaign_id"):
            cid = campaign_id or session.get("campaign_id")
            result = await db.execute(
                select(Campaign).where(Campaign.id == cid)
            )
            campaign = result.scalar_one_or_none()
            if campaign:
                campaign_context = f"Campaign: {campaign.name}. {campaign.description or ''}"
                
                # Try FAQ retrieval
                if faq_service.is_campaign_loaded(cid):
                    relevant_faqs = faq_service.retrieve(cid, user_text, top_k=3, threshold=0.5)
                    faq_context = faq_service.format_faq_context(relevant_faqs)
        
        # Step 5: Generate LLM response
        ai_response = await llm_service.generate_response(
            user_message=user_text,
            language=detected_lang,
            context=campaign_context,
            faq_context=faq_context,
            conversation_history=session["history"]
        )
        
        if not ai_response:
            ai_response = "I'm sorry, I couldn't process that. Could you please repeat?"
        
        logger.info(f"LLM response: {ai_response[:100]}...")
        
        # Update session history
        session["history"].append({"role": "user", "content": user_text})
        session["history"].append({"role": "assistant", "content": ai_response})
        session["transcript"].append(f"Agent: {ai_response}")
        
        # Step 6: Lead qualification
        signals = lead_qualifier.extract_signals(user_text)
        session["lead_signals"].extend(signals)
        
        qualification = lead_qualifier.qualify_lead(
            session["transcript"],
            session["lead_signals"]
        )
        
        # Step 7: Text-to-Speech
        audio_response = await tts_service.synthesize(ai_response, detected_lang)
        audio_base64 = None
        
        if audio_response:
            audio_base64 = base64.b64encode(audio_response).decode("utf-8")
        
        return VoiceChatResponse(
            text_response=ai_response,
            audio_base64=audio_base64,
            audio_format="mp3",
            detected_language=detected_lang,
            lead_score=qualification["score"],
            lead_status=qualification["qualification"],
            session_id=session_id
        )
        
    except Exception as e:
        logger.error(f"Voice chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/text", response_model=VoiceChatResponse)
async def voice_chat_text(
    request: TextChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Text-based chat endpoint for testing (no audio).
    Useful for development and debugging.
    """
    from app.services.language_detector import language_detector
    from app.services.faq_retrieval import faq_service
    from app.services.llm_service import llm_service
    from app.services.tts_service import tts_service
    from app.services.lead_qualifier import lead_qualifier
    import uuid
    
    session_id = request.session_id or str(uuid.uuid4())
    
    if session_id not in _sessions:
        _sessions[session_id] = {
            "history": [],
            "transcript": [],
            "lead_signals": [],
            "campaign_id": request.campaign_id
        }
    
    session = _sessions[session_id]
    user_text = request.text
    
    session["transcript"].append(f"User: {user_text}")
    
    # Detect language
    detected_lang = language_detector.detect_language(user_text)
    
    # Get campaign context
    campaign_context = None
    faq_context = ""
    
    if request.campaign_id:
        result = await db.execute(
            select(Campaign).where(Campaign.id == request.campaign_id)
        )
        campaign = result.scalar_one_or_none()
        if campaign:
            campaign_context = f"Campaign: {campaign.name}. {campaign.description or ''}"
            
            if faq_service.is_campaign_loaded(request.campaign_id):
                relevant_faqs = faq_service.retrieve(request.campaign_id, user_text, top_k=3, threshold=0.5)
                faq_context = faq_service.format_faq_context(relevant_faqs)
    
    # Generate response
    ai_response = await llm_service.generate_response(
        user_message=user_text,
        language=detected_lang,
        context=campaign_context,
        faq_context=faq_context,
        conversation_history=session["history"]
    )
    
    if not ai_response:
        ai_response = "I'm sorry, could you please repeat that?"
    
    # Update session
    session["history"].append({"role": "user", "content": user_text})
    session["history"].append({"role": "assistant", "content": ai_response})
    session["transcript"].append(f"Agent: {ai_response}")
    
    # Lead qualification
    signals = lead_qualifier.extract_signals(user_text)
    session["lead_signals"].extend(signals)
    
    qualification = lead_qualifier.qualify_lead(
        session["transcript"],
        session["lead_signals"]
    )
    
    # TTS
    audio_response = await tts_service.synthesize(ai_response, detected_lang)
    audio_base64 = base64.b64encode(audio_response).decode("utf-8") if audio_response else None
    
    return VoiceChatResponse(
        text_response=ai_response,
        audio_base64=audio_base64,
        audio_format="mp3",
        detected_language=detected_lang,
        lead_score=qualification["score"],
        lead_status=qualification["qualification"],
        session_id=session_id
    )


@router.post("/session/{session_id}/end")
async def end_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    End a voice chat session and save lead data.
    """
    from app.services.lead_qualifier import lead_qualifier
    
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _sessions[session_id]
    
    # Final lead qualification
    qualification = lead_qualifier.qualify_lead(
        session["transcript"],
        session["lead_signals"]
    )
    
    # Save lead to database
    lead = Lead(
        campaign_id=session.get("campaign_id") or 0,
        phone_number="voice-chat",
        name=f"Voice Lead {session_id[:8]}",
        qualification=qualification["qualification"],
        score=qualification["score"],
        transcript="\n".join(session["transcript"]),
        notes=f"Signals: {len(session['lead_signals'])} positive/negative"
    )
    db.add(lead)
    await db.commit()
    
    # Clean up session
    del _sessions[session_id]
    
    return {
        "status": "ended",
        "session_id": session_id,
        "lead_qualification": qualification["qualification"],
        "lead_score": qualification["score"],
        "transcript_length": len(session["transcript"])
    }


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get current session state."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _sessions[session_id]
    from app.services.lead_qualifier import lead_qualifier
    
    qualification = lead_qualifier.qualify_lead(
        session["transcript"],
        session["lead_signals"]
    )
    
    return {
        "session_id": session_id,
        "message_count": len(session["history"]) // 2,
        "transcript": session["transcript"],
        "lead_score": qualification["score"],
        "lead_status": qualification["qualification"]
    }


@router.get("/health")
async def voice_health_check():
    """Check all voice services health."""
    from app.services.stt_service import stt_service
    from app.services.llm_service import llm_service
    from app.services.tts_service import tts_service
    
    return {
        "status": "healthy",
        "services": {
            "stt": await stt_service.health_check(),
            "llm": await llm_service.health_check(),
            "tts": await tts_service.health_check()
        }
    }
