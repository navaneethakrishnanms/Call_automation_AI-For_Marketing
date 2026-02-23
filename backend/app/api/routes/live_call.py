"""
Live Call WebSocket Routes
Real-time bidirectional audio streaming for phone-call-like experience.
Uses WebSocket for continuous mic → STT → LLM → TTS → speaker pipeline.
"""

import io
import json
import base64
import uuid
import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.call import Call, CallStatus
from app.models.lead import Lead
from app.models.campaign import Campaign
from app.utils.prompts import _detect_tone

logger = logging.getLogger(__name__)

router = APIRouter(tags=["live-call"])

# In-memory session storage for live calls
_live_sessions: dict = {}


class LiveCallSession:
    """Manages state for a single live call."""

    def __init__(self, session_id: str, campaign_id: int, campaign_name: str):
        self.session_id = session_id
        self.campaign_id = campaign_id
        self.campaign_name = campaign_name
        self.history: list = []
        self.transcript: list = []
        self.lead_signals: list = []
        self.detected_language: Optional[str] = None
        self.audio_buffer: bytearray = bytearray()
        self.turn_count: int = 0

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "turn_count": self.turn_count,
            "detected_language": self.detected_language,
        }


async def _process_audio_turn(
    session: LiveCallSession,
    audio_bytes: bytes,
    campaign: object,
    db: AsyncSession,
) -> dict:
    """
    Run the full STT → LLM → TTS pipeline on an audio chunk.
    Returns dict with text_response, audio_base64, pipeline_info, etc.
    """
    from app.services.stt_service import stt_service
    from app.services.language_detector import language_detector
    from app.services.faq_retrieval import faq_service
    from app.services.llm_service import llm_service
    from app.services.tts_service import tts_service
    from app.services.lead_qualifier import lead_qualifier

    # Step 1: STT
    previous_lang = session.detected_language
    user_text = await stt_service.transcribe_bytes(
        audio_bytes, "live_call.webm", language_hint=previous_lang
    )

    if not user_text or len(user_text.strip()) < 2:
        return {"type": "silence", "text": ""}

    logger.info(f"[LiveCall] STT: {user_text}")
    session.transcript.append(f"User: {user_text}")

    # Step 2: Language detection
    detected_lang = language_detector.detect_language(user_text)
    session.detected_language = detected_lang

    # Step 3: Campaign context + FAQs
    campaign_context = f"Campaign: {campaign.name}. {campaign.description or ''}"
    faq_context = ""

    if not faq_service.is_campaign_loaded(session.campaign_id) and campaign.faqs:
        logger.info(f"Auto-loading FAQs for campaign {session.campaign_id}")
        faq_service.load_faqs(session.campaign_id, campaign.faqs)

    # Smart retrieval with tiered confidence
    faq_result = faq_service.smart_retrieve(session.campaign_id, user_text)

    # Step 4: Direct answer or LLM response
    if faq_result["source"] == "faq_direct" and faq_result["direct_answer"]:
        # HIGH confidence (≥ 0.85): skip LLM entirely
        ai_response = faq_result["direct_answer"].strip()
        if not ai_response.endswith("."):
            ai_response += "."
        logger.info(f"[LiveCall] Direct FAQ answer (similarity={faq_result['top_similarity']:.3f})")
    else:
        faq_context = faq_result["faq_context"][:1200]  # Limit context size for fast inference
        ai_response = await llm_service.generate_response(
            user_message=user_text,
            language=detected_lang,
            context=campaign_context,
            faq_context=faq_context,
            conversation_history=session.history,
        )

    if not ai_response:
        ai_response = "Hmm, didn't get that. One more time?"

    logger.info(f"[LiveCall] Response ({faq_result['source']}): {ai_response[:80]}...")

    # Update session
    session.history.append({"role": "user", "content": user_text})
    session.history.append({"role": "assistant", "content": ai_response})
    session.transcript.append(f"Agent: {ai_response}")
    session.turn_count += 1

    # Step 5: Lead qualification
    signals = lead_qualifier.extract_signals(user_text)
    session.lead_signals.extend(signals)
    qualification = lead_qualifier.qualify_lead(
        session.transcript, session.lead_signals
    )

    # Step 6: TTS
    audio_response = await tts_service.synthesize(ai_response, detected_lang)
    audio_base64 = None
    if audio_response:
        audio_base64 = base64.b64encode(audio_response).decode("utf-8")

    return {
        "type": "response",
        "user_text": user_text,
        "ai_text": ai_response,
        "audio_base64": audio_base64,
        "detected_language": detected_lang,
        "lead_score": qualification["score"],
        "lead_status": qualification["qualification"],
        "pipeline_info": {
            "stt_engine": "dual-engine" if not previous_lang else "sarvam+whisper",
            "detected_language": detected_lang,
            "llm_model": "ollama/llama3.1:8b",
            "tts_engine": "sarvam-priya",
            "tts_status": "success" if audio_response else "failed",
            "faq_source": faq_result["source"],
            "faq_confidence": faq_result["confidence_tier"],
            "faq_top_similarity": faq_result["top_similarity"],
            "faq_match_count": faq_result["match_count"],
            "campaign_name": campaign.name,
            "tone": _detect_tone(campaign_context),
            "turn_count": session.turn_count,
        },
    }


async def _save_lead(session: LiveCallSession, db: AsyncSession):
    """Save the lead from a completed live call session."""
    from app.services.lead_qualifier import lead_qualifier

    qualification = lead_qualifier.qualify_lead(
        session.transcript, session.lead_signals
    )

    lead = Lead(
        campaign_id=session.campaign_id,
        phone="live-call",
        name=f"Live Call Lead {session.session_id[:8]}",
        qualification=qualification["qualification"],
        interest_level=int(qualification["score"] * 10),
        call_summary="\n".join(session.transcript),
        notes=f"Live call — {session.turn_count} turns, signals: {len(session.lead_signals)}",
    )
    db.add(lead)
    await db.commit()
    logger.info(
        f"[LiveCall] Saved lead: {qualification['qualification']} ({qualification['score']})"
    )
    return qualification


@router.websocket("/ws/live-call")
async def live_call_ws(
    websocket: WebSocket,
    campaign_id: int = Query(...),
):
    """
    WebSocket endpoint for real-time voice calls.

    Protocol:
    - Client sends binary frames = audio chunks (webm/pcm)
    - Client sends text frames = JSON control messages:
        {"type": "mute"}
        {"type": "unmute"}
        {"type": "hangup"}
        {"type": "audio_end"}  → signals end of a speech segment
    - Server sends text frames = JSON responses with transcripts, audio, lead info
    """
    from app.database import async_session_maker

    await websocket.accept()
    logger.info(f"[LiveCall] WebSocket connected, campaign_id={campaign_id}")

    # Validate campaign
    async with async_session_maker() as db:
        result = await db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()

        if not campaign:
            await websocket.send_json({
                "type": "error",
                "message": f"Campaign {campaign_id} not found",
            })
            await websocket.close()
            return

        # Create session
        session_id = str(uuid.uuid4())
        session = LiveCallSession(session_id, campaign_id, campaign.name)
        _live_sessions[session_id] = session

        # Send session info to client
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "campaign_name": campaign.name,
        })

        # Send greeting using campaign greeting_message
        greeting = campaign.greeting_message
        if not greeting:
            greeting = f"Hello! We are from {campaign.name}. Thank you for your interest. How can I help you today?"

        # Generate TTS for greeting
        from app.services.tts_service import tts_service

        greeting_audio = await tts_service.synthesize(greeting, "english")
        greeting_audio_b64 = None
        if greeting_audio:
            greeting_audio_b64 = base64.b64encode(greeting_audio).decode("utf-8")

        session.history.append({"role": "assistant", "content": greeting})
        session.transcript.append(f"Agent: {greeting}")

        await websocket.send_json({
            "type": "greeting",
            "ai_text": greeting,
            "audio_base64": greeting_audio_b64,
        })

    # Main receive loop
    try:
        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            # Binary frame = audio data
            if "bytes" in message and message["bytes"]:
                session.audio_buffer.extend(message["bytes"])

                # Don't process tiny fragments — wait for enough audio
                # The client sends "audio_end" when user stops speaking
                continue

            # Text frame = JSON control message
            if "text" in message and message["text"]:
                try:
                    data = json.loads(message["text"])
                except json.JSONDecodeError:
                    continue

                msg_type = data.get("type", "")

                if msg_type == "audio_end":
                    # User stopped speaking — process accumulated audio
                    if len(session.audio_buffer) < 1000:
                        session.audio_buffer.clear()
                        continue  # too small, skip

                    audio_bytes = bytes(session.audio_buffer)
                    session.audio_buffer.clear()

                    # Tell client we're processing
                    await websocket.send_json({"type": "processing"})

                    # Process through STT → LLM → TTS pipeline
                    async with async_session_maker() as db:
                        result = await db.execute(
                            select(Campaign).where(Campaign.id == campaign_id)
                        )
                        campaign = result.scalar_one_or_none()
                        if campaign:
                            response = await _process_audio_turn(
                                session, audio_bytes, campaign, db
                            )
                            await websocket.send_json(response)

                elif msg_type == "hangup":
                    logger.info(f"[LiveCall] Hangup: {session_id}")

                    # Save lead
                    async with async_session_maker() as db:
                        qualification = await _save_lead(session, db)

                    await websocket.send_json({
                        "type": "call_ended",
                        "session_id": session_id,
                        "turn_count": session.turn_count,
                        "lead_score": qualification["score"],
                        "lead_status": qualification["qualification"],
                        "transcript": session.transcript,
                    })

                    # Clean up
                    if session_id in _live_sessions:
                        del _live_sessions[session_id]

                    await websocket.close()
                    return

    except WebSocketDisconnect:
        logger.info(f"[LiveCall] Client disconnected: {session_id}")
        # Save lead on disconnect too
        try:
            async with async_session_maker() as db:
                await _save_lead(session, db)
        except Exception as e:
            logger.error(f"[LiveCall] Error saving lead on disconnect: {e}")
    except Exception as e:
        logger.error(f"[LiveCall] WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
    finally:
        if session_id in _live_sessions:
            del _live_sessions[session_id]
        logger.info(f"[LiveCall] Session cleaned up: {session_id}")
