"""
Webhook Routes
Twilio webhook handlers for call events.
"""

import logging
from fastapi import APIRouter, Request, HTTPException, Depends, Form
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.twiml.voice_response import VoiceResponse, Gather

from app.api.deps import get_db
from app.models.call import Call, CallStatus
from app.models.campaign import Campaign
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/twilio", tags=["webhooks"])


@router.post("/voice")
async def handle_incoming_call(
    request: Request,
    CallSid: str = Form(default=""),
    From: str = Form(default=""),
    To: str = Form(default=""),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle incoming Twilio voice calls.
    Returns TwiML for greeting and gathering input.
    """
    logger.info(f"Incoming call: {CallSid} from {From}")
    
    # Find active campaign (use first active for incoming calls)
    result = await db.execute(
        select(Campaign).where(Campaign.is_active == True).limit(1)
    )
    campaign = result.scalar_one_or_none()
    
    # Create call record
    call = Call(
        campaign_id=campaign.id if campaign else 0,
        phone_number=From,
        twilio_call_sid=CallSid,
        status=CallStatus.IN_PROGRESS.value
    )
    db.add(call)
    await db.flush()
    await db.refresh(call)
    
    # Build TwiML response
    response = VoiceResponse()
    
    greeting = "Hello! Thank you for calling. How can I help you today?"
    if campaign and campaign.greeting_message:
        greeting = campaign.greeting_message
    
    # Gather speech input
    gather = Gather(
        input="speech",
        action=f"/api/webhooks/twilio/process/{call.id}",
        method="POST",
        speech_timeout="auto",
        language="en-IN",  # Indian English, supports Tamil accent
    )
    gather.say(greeting, voice="Polly.Aditi")
    
    response.append(gather)
    
    # If no input, prompt again
    response.redirect("/api/webhooks/twilio/no-input")
    
    return Response(
        content=str(response),
        media_type="application/xml"
    )


@router.post("/process/{call_id}")
async def process_speech_input(
    call_id: int,
    request: Request,
    SpeechResult: str = Form(default=""),
    Confidence: float = Form(default=0.0),
    db: AsyncSession = Depends(get_db)
):
    """
    Process speech input from Twilio and generate response.
    Uses AI pipeline for response generation.
    """
    logger.info(f"Speech input for call {call_id}: {SpeechResult} (confidence: {Confidence})")
    
    # Get call
    result = await db.execute(
        select(Call).where(Call.id == call_id)
    )
    call = result.scalar_one_or_none()
    
    if not call:
        logger.error(f"Call not found: {call_id}")
        response = VoiceResponse()
        response.say("Sorry, there was an error processing your request.", voice="Polly.Aditi")
        response.hangup()
        return Response(content=str(response), media_type="application/xml")
    
    # Import here to avoid circular imports
    from app.services.call_orchestrator import call_orchestrator
    from app.services.language_detector import language_detector
    
    # Get campaign context
    campaign_result = await db.execute(
        select(Campaign).where(Campaign.id == call.campaign_id)
    )
    campaign = campaign_result.scalar_one_or_none()
    campaign_context = f"Campaign: {campaign.name}. {campaign.description or ''}" if campaign else None
    
    # Process through AI pipeline
    ai_response = await call_orchestrator.process_text_input(
        call_id=call_id,
        user_text=SpeechResult,
        campaign_context=campaign_context
    )
    
    # Detect language for TTS voice selection
    detected_lang = language_detector.detect_language(SpeechResult)
    voice = "Polly.Aditi" if detected_lang in ["tamil", "tanglish"] else "Polly.Joanna"
    
    # Build response
    response = VoiceResponse()
    
    if ai_response:
        # Continue conversation
        gather = Gather(
            input="speech",
            action=f"/api/webhooks/twilio/process/{call_id}",
            method="POST",
            speech_timeout="auto",
            language="en-IN",
        )
        gather.say(ai_response, voice=voice)
        response.append(gather)
        response.redirect(f"/api/webhooks/twilio/process/{call_id}")
    else:
        # Error fallback
        response.say("I'm having trouble understanding. Let me connect you to someone who can help.", voice=voice)
        response.hangup()
    
    return Response(content=str(response), media_type="application/xml")


@router.post("/status")
async def handle_call_status(
    request: Request,
    CallSid: str = Form(default=""),
    CallStatus: str = Form(default=""),
    CallDuration: str = Form(default="0"),
    db: AsyncSession = Depends(get_db)
):
    """Handle Twilio call status updates."""
    logger.info(f"Call status update: {CallSid} -> {CallStatus}")
    
    # Find call by SID
    result = await db.execute(
        select(Call).where(Call.twilio_call_sid == CallSid)
    )
    call = result.scalar_one_or_none()
    
    if call:
        call.status = CallStatus.lower()
        call.duration_seconds = int(CallDuration)
        await db.flush()
        
        # End call in orchestrator if completed
        if CallStatus.lower() in ["completed", "failed", "no-answer", "busy"]:
            from app.services.call_orchestrator import call_orchestrator
            call_orchestrator.end_call(call.id)
    
    return {"status": "received"}


@router.post("/recording")
async def handle_recording(
    request: Request,
    CallSid: str = Form(default=""),
    RecordingUrl: str = Form(default=""),
    RecordingDuration: str = Form(default="0"),
    db: AsyncSession = Depends(get_db)
):
    """Handle Twilio recording callbacks."""
    logger.info(f"Recording received for {CallSid}: {RecordingUrl}")
    
    # Find call by SID
    result = await db.execute(
        select(Call).where(Call.twilio_call_sid == CallSid)
    )
    call = result.scalar_one_or_none()
    
    if call:
        call.recording_url = RecordingUrl
        await db.flush()
    
    return {"status": "received"}


@router.post("/no-input")
async def handle_no_input():
    """Handle no speech input - prompt again."""
    response = VoiceResponse()
    response.say("I didn't hear anything. Please speak after the beep, or press any key to end the call.", voice="Polly.Aditi")
    
    gather = Gather(
        input="speech dtmf",
        action="/api/webhooks/twilio/voice",
        method="POST",
        speech_timeout="auto",
    )
    response.append(gather)
    
    response.say("Goodbye! Thank you for calling.", voice="Polly.Aditi")
    response.hangup()
    
    return Response(content=str(response), media_type="application/xml")
