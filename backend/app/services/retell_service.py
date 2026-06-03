"""
Retell AI Service
Handles outbound call creation via the Retell AI REST API.
"""

import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

RETELL_API_URL = "https://api.retellai.com/v2/create-phone-call"


async def create_retell_call(to_number: str, agent_id: str = None) -> dict:
    """
    Create an outbound phone call using Retell AI.
    
    Args:
        to_number: The destination phone number (E.164 format, e.g. +917904480971)
        agent_id: Optional Retell agent ID. Falls back to RETELL_AGENT_ID from .env if not provided.
        
    Returns:
        dict with call_id, agent_id, and status from Retell API
    """
    # Ensure E.164 format, default to +91 (India) if no + is provided
    if to_number and not to_number.startswith('+'):
        # Just strip non-digits to be safe and prepend +91 if we assume it's a raw number
        clean_num = ''.join(filter(str.isdigit, to_number))
        to_number = f"+91{clean_num}"

    if not settings.retell_api_key:
        return {"status": "error", "message": "RETELL_API_KEY not configured in .env"}
    
    # Use provided agent_id, or fall back to .env
    resolved_agent_id = agent_id or settings.retell_agent_id
    if not resolved_agent_id:
        return {"status": "error", "message": "No agent_id provided and RETELL_AGENT_ID not configured in .env"}

    headers = {
        "Authorization": f"Bearer {settings.retell_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "from_number": settings.retell_phone_number,
        "to_number": to_number,
        "agent_id": resolved_agent_id,
    }

    logger.info(f"Creating Retell call: {settings.retell_phone_number} → {to_number}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(RETELL_API_URL, json=payload, headers=headers)

        if response.status_code in (200, 201):
            data = response.json()
            logger.info(f"Retell call created successfully: {data}")
            return {
                "status": "success",
                "call_id": data.get("call_id"),
                "agent_id": data.get("agent_id"),
                "call_status": data.get("call_status"),
                "message": "Call initiated successfully via Retell AI!",
            }
        else:
            error_detail = response.text
            logger.error(f"Retell API error ({response.status_code}): {error_detail}")
            return {
                "status": "error",
                "message": f"Retell API error ({response.status_code}): {error_detail}",
            }
    except httpx.TimeoutException:
        logger.error("Retell API request timed out")
        return {"status": "error", "message": "Retell API request timed out"}
    except Exception as e:
        logger.error(f"Retell call failed: {e}")
        return {"status": "error", "message": str(e)}

async def get_retell_call(call_id: str) -> dict:
    """
    Get call details and transcript from Retell AI.
    """
    if not settings.retell_api_key:
        return {"status": "error", "message": "RETELL_API_KEY not configured"}

    headers = {
        "Authorization": f"Bearer {settings.retell_api_key}",
    }
    
    url = f"https://api.retellai.com/v2/get-call/{call_id}"
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers)
            
        if response.status_code == 200:
            return {"status": "success", "data": response.json()}
        else:
            return {"status": "error", "message": f"Retell API error: {response.text}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
