"""
Test Routes
Direct API endpoints for testing AI services without database.
"""

import logging
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/test", tags=["test"])


class TextInput(BaseModel):
    text: str
    language: Optional[str] = None


class ConversationInput(BaseModel):
    text: str
    campaign_context: Optional[str] = "General marketing campaign"


@router.get("/")
async def test_status():
    """Test endpoint status."""
    return {"status": "ok", "message": "Test endpoints are working!"}


@router.post("/detect-language")
async def test_language_detection(input: TextInput):
    """Test language detection."""
    from app.services.language_detector import language_detector
    
    detected = language_detector.detect_language(input.text)
    confidence = language_detector.get_confidence(input.text)
    
    return {
        "input": input.text,
        "detected_language": detected,
        "confidence": confidence
    }


@router.post("/llm")
async def test_llm(input: ConversationInput):
    """Test LLM response generation."""
    from app.services.llm_service import llm_service
    from app.services.language_detector import language_detector
    
    detected_lang = language_detector.detect_language(input.text)
    
    response = await llm_service.generate_response(
        user_message=input.text,
        language=detected_lang,
        context=input.campaign_context,
        faq_context="",
        conversation_history=[]
    )
    
    return {
        "input": input.text,
        "detected_language": detected_lang,
        "response": response
    }


@router.post("/tts")
async def test_tts(input: TextInput):
    """Test TTS synthesis - returns audio info (not actual audio for simplicity)."""
    from app.services.tts_service import tts_service
    from app.services.language_detector import language_detector
    
    lang = input.language or language_detector.detect_language(input.text)
    
    audio_bytes = await tts_service.synthesize(input.text, lang)
    
    if audio_bytes:
        return {
            "input": input.text,
            "language": lang,
            "audio_size_bytes": len(audio_bytes),
            "status": "success"
        }
    else:
        return {
            "input": input.text,
            "language": lang,
            "status": "failed",
            "message": "TTS synthesis failed - check API keys"
        }


@router.post("/conversation")
async def test_conversation(input: ConversationInput):
    """Test full conversation flow: Language Detection → LLM → Response."""
    from app.services.call_orchestrator import call_orchestrator
    
    response = await call_orchestrator.process_text_input(
        call_id=0,  # Dummy call ID for testing
        user_text=input.text,
        campaign_context=input.campaign_context
    )
    
    return {
        "input": input.text,
        "response": response,
        "campaign_context": input.campaign_context
    }


@router.get("/health-services")
async def test_health_services():
    """Check health of all AI services."""
    from app.services.stt_service import stt_service
    from app.services.llm_service import llm_service
    from app.services.tts_service import tts_service
    
    return {
        "stt": await stt_service.health_check(),
        "llm": await llm_service.health_check(),
        "tts": await tts_service.health_check()
    }


class TestCallInput(BaseModel):
    phone_number: str
    message: Optional[str] = "Hello! This is a test call from Marketing AI."


@router.post("/call")
async def test_twilio_call(input: TestCallInput):
    """Test Twilio call - makes an actual phone call WITHOUT needing database."""
    from app.config import settings
    from twilio.rest import Client
    
    logger.info(f"Attempting test call to {input.phone_number}")
    
    # Check Twilio credentials
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        return {
            "status": "error",
            "message": "Twilio credentials not configured. Check TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env"
        }
    
    if not settings.twilio_phone_number:
        return {
            "status": "error", 
            "message": "TWILIO_PHONE_NUMBER not configured in .env"
        }
    
    try:
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        
        # For TRIAL accounts: TwiML that keeps call alive with demo message
        # This handles the trial restriction properly
        twiml_content = f'''
        <Response>
            <Say voice="alice">{input.message}</Say>
            <Say voice="alice">This is a demo of our AI marketing system.</Say>
            <Pause length="2"/>
            <Say voice="alice">Due to Twilio trial restrictions, the call will end shortly.</Say>
            <Pause length="3"/>
            <Say voice="alice">Thank you for testing. Goodbye!</Say>
        </Response>
        '''
        
        call = client.calls.create(
            twiml=twiml_content,
            to=input.phone_number,
            from_=settings.twilio_phone_number
        )
        
        logger.info(f"Call initiated successfully! SID: {call.sid}")
        
        return {
            "status": "success",
            "call_sid": call.sid,
            "to": input.phone_number,
            "from": settings.twilio_phone_number,
            "message": "Call initiated! You should receive a call shortly."
        }
    except Exception as e:
        logger.error(f"Twilio call failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


# Simple voice webhook for inbound calls (works without database)
from fastapi.responses import Response as FastAPIResponse

@router.post("/voice/inbound")
async def simple_inbound_call():
    """
    Simple inbound voice handler for Twilio Trial accounts.
    Works WITHOUT database - just returns TwiML.
    """
    logger.info("Inbound call received (simple handler)")
    
    twiml = """
    <Response>
        <Say voice="alice">
            Hello! Welcome to Marketing AI. 
            This is a demo of our AI-powered call automation system.
        </Say>
        <Pause length="2"/>
        <Say voice="alice">
            Due to Twilio trial restrictions, this demo call will end shortly.
            Thank you for your interest in our services.
        </Say>
        <Pause length="5"/>
        <Say voice="alice">
            Goodbye!
        </Say>
    </Response>
    """
    
    return FastAPIResponse(content=twiml, media_type="application/xml")


# Simple Twilio voice endpoint for testing (exactly as requested)
@router.post("/twilio/voice")
async def twilio_voice():
    """Simple test voice endpoint - keeps call alive for 10 seconds."""
    twiml = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">
        Hello! Your system is working.
        I will talk to you for ten seconds.
    </Say>
    <Pause length="10"/>
</Response>
'''
    return FastAPIResponse(content=twiml, media_type="application/xml")


class TestCallInput(BaseModel):
    phone_number: str
    message: Optional[str] = "Hello! This is a test call from Marketing AI."


@router.post("/call")
async def test_twilio_call(input: TestCallInput):
    """Test Twilio call - makes an actual phone call WITHOUT needing database."""
    from app.config import settings
    from twilio.rest import Client
    
    logger.info(f"Attempting test call to {input.phone_number}")
    
    # Check Twilio credentials
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        return {
            "status": "error",
            "message": "Twilio credentials not configured. Check TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env"
        }
    
    if not settings.twilio_phone_number:
        return {
            "status": "error", 
            "message": "TWILIO_PHONE_NUMBER not configured in .env"
        }
    
    try:
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        
        # Make outbound call with TwiML that reads a message
        call = client.calls.create(
            twiml=f'<Response><Say voice="alice">{input.message}</Say></Response>',
            to=input.phone_number,
            from_=settings.twilio_phone_number
        )
        
        logger.info(f"Call initiated successfully! SID: {call.sid}")
        
        return {
            "status": "success",
            "call_sid": call.sid,
            "to": input.phone_number,
            "from": settings.twilio_phone_number,
            "message": "Call initiated! You should receive a call shortly."
        }
    except Exception as e:
        logger.error(f"Twilio call failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

