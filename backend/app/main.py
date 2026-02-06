"""
Marketing AI Backend
FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import campaigns, calls, leads, analytics, webhooks, test

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Marketing AI Backend...")
    
    # Try to initialize database (optional for testing)
    try:
        from app.database import init_db, close_db
        await init_db()
        logger.info("Database initialized")
        db_enabled = True
    except Exception as e:
        logger.warning(f"Database skipped (optional for testing): {e}")
        db_enabled = False
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    
    if db_enabled:
        try:
            from app.database import close_db
            await close_db()
        except Exception:
            pass
    
    # Close service clients
    from app.services.stt_service import stt_service
    from app.services.llm_service import llm_service
    from app.services.tts_service import tts_service
    
    await stt_service.close()
    await llm_service.close()
    await tts_service.close()
    
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Marketing AI Call Automation",
    description="AI-powered call automation platform for marketing with multilingual support",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(test.router, prefix="/api")  # Test routes first
app.include_router(campaigns.router, prefix="/api")
app.include_router(calls.router, prefix="/api")
app.include_router(leads.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "status": "healthy",
        "service": "Marketing AI Call Automation",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check endpoint."""
    from app.services.stt_service import stt_service
    from app.services.llm_service import llm_service
    from app.services.tts_service import tts_service
    
    return {
        "status": "healthy",
        "services": {
            "stt": await stt_service.health_check(),
            "llm": await llm_service.health_check(),
            "tts": await tts_service.health_check(),
        },
        "database": "connected"
    }


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "name": "Marketing AI API",
        "version": "1.0.0",
        "endpoints": {
            "campaigns": "/api/campaigns",
            "calls": "/api/calls",
            "leads": "/api/leads",
            "analytics": "/api/analytics",
            "webhooks": "/api/webhooks/twilio"
        },
        "docs": "/docs"
    }


# ============================================================================
# TWILIO VOICE WEBHOOKS - No DTMF, Speech Input Only
# ============================================================================
# These endpoints handle Twilio voice calls without requiring key presses.
# Works with Twilio trial accounts.

@app.post("/twilio/voice")
async def twilio_voice():
    """
    Main voice webhook - called when a call comes in.
    Uses TTS normalizer and SSML for natural pronunciation.
    """
    from app.utils.tts_normalizer import normalize_for_speech
    
    # Campaign name - this would come from database in production
    # For now using a test name that demonstrates the normalization
    campaign_name = "Marketing AI"
    
    # Normalize the greeting text for natural pronunciation
    greeting = f"Hello! Welcome to {campaign_name}. I'm your AI assistant. How can I help you today?"
    greeting = normalize_for_speech(greeting)
    
    # Use SSML with prosody to slow down proper nouns for clearer pronunciation
    # The <prosody rate="slow"> helps TTS engines pronounce names naturally
    twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">
        <prosody rate="95%">{greeting}</prosody>
    </Say>
    <Gather input="speech" 
            action="/twilio/process" 
            method="POST" 
            speechTimeout="auto"
            language="en-US">
        <Say voice="Polly.Joanna">Please go ahead and speak.</Say>
    </Gather>
    <Say voice="Polly.Joanna">I didn't hear anything. Let me try again.</Say>
    <Redirect>/twilio/voice</Redirect>
</Response>
'''
    return Response(content=twiml, media_type="application/xml")


@app.post("/twilio/process")
async def twilio_process(request):
    """
    Process speech input from the caller.
    This is called after <Gather> captures speech.
    Uses LLM for response generation and TTS normalizer for natural speech.
    """
    import logging
    from app.utils.tts_normalizer import normalize_for_speech
    
    logger = logging.getLogger(__name__)
    
    # Get form data from Twilio
    form_data = await request.form()
    speech_result = form_data.get("SpeechResult", "")
    confidence = form_data.get("Confidence", "0")
    
    logger.info(f"Speech received: '{speech_result}' (confidence: {confidence})")
    
    # Generate AI response
    if speech_result:
        try:
            # Try to use LLM for intelligent response
            from app.services.call_orchestrator import call_orchestrator
            ai_response = await call_orchestrator.process_text_input(
                call_id=0,
                user_text=speech_result,
                campaign_context="Marketing AI Assistant"
            )
            if not ai_response:
                ai_response = f"I heard you say: {speech_result}. How can I help you with that?"
        except Exception as e:
            logger.error(f"LLM error: {e}")
            ai_response = f"I heard you say: {speech_result}. How can I help you with that?"
    else:
        ai_response = "I couldn't understand that. Could you please repeat?"
    
    # Normalize response for natural TTS pronunciation
    ai_response = normalize_for_speech(ai_response)
    
    # Continue the conversation with SSML for natural pronunciation
    twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">
        <prosody rate="95%">{ai_response}</prosody>
    </Say>
    <Gather input="speech" 
            action="/twilio/process" 
            method="POST" 
            speechTimeout="auto"
            language="en-US">
    </Gather>
    <Say voice="Polly.Joanna">Thank you for calling. Goodbye!</Say>
</Response>
'''
    return Response(content=twiml, media_type="application/xml")


@app.post("/twilio/status")
async def twilio_status(request):
    """Handle call status callbacks (optional, for logging)."""
    return {"status": "received"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
