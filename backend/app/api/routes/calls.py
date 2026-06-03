"""
Call Routes
API endpoints for call management and initiation.
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.call import Call, CallStatus
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.schemas.call import (
    CallResponse,
    CallListResponse,
    CallInitiateRequest,
    CallInitiateResponse,
    CallUpdate,
)
from app.services.call_orchestrator import call_orchestrator

router = APIRouter(prefix="/calls", tags=["calls"])


@router.get("", response_model=CallListResponse)
async def list_calls(
    page: int = 1,
    page_size: int = 20,
    campaign_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    language: Optional[str] = None,
    qualification: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all calls with filters and pagination."""
    query = select(Call)
    count_query = select(func.count()).select_from(Call)
    
    # Apply filters
    if campaign_id:
        query = query.where(Call.campaign_id == campaign_id)
        count_query = count_query.where(Call.campaign_id == campaign_id)
    
    if status_filter:
        query = query.where(Call.status == status_filter)
        count_query = count_query.where(Call.status == status_filter)
    
    if language:
        query = query.where(Call.language_detected == language)
        count_query = count_query.where(Call.language_detected == language)
    
    if qualification:
        query = query.where(Call.lead_qualification == qualification)
        count_query = count_query.where(Call.lead_qualification == qualification)
    
    # Get total
    total = (await db.execute(count_query)).scalar() or 0
    
    # Paginate and order
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Call.started_at.desc())
    
    result = await db.execute(query)
    calls = result.scalars().all()
    
    # Auto-sync 'initiated' calls with Retell API to get duration/transcript without webhooks
    from app.services.retell_service import get_retell_call
    synced = False
    for call in calls:
        if call.status == CallStatus.INITIATED.value and call.twilio_call_sid:
            retell_res = await get_retell_call(call.twilio_call_sid)
            if retell_res.get("status") == "success":
                data = retell_res["data"]
                r_status = data.get("call_status")
                
                if r_status in ["ended", "error"]:
                    duration_ms = data.get("duration_ms", 0)
                    call.duration_seconds = duration_ms // 1000
                    
                    call.recording_url = data.get("recording_url")
                    
                    # Extract cost
                    call_cost_data = data.get("call_cost", {})
                    if call_cost_data and isinstance(call_cost_data, dict):
                        combined = call_cost_data.get("combined_cost")
                        if combined is not None:
                            call.cost = combined / 100.0

                    call_analysis = data.get("call_analysis", {})
                    if call_analysis and isinstance(call_analysis, dict):
                        call.call_summary = call_analysis.get("call_summary")
                    
                    # Format transcript history
                    transcript_obj = data.get("transcript_object", [])
                    if transcript_obj:
                        formatted_transcript = ""
                        for msg in transcript_obj:
                            role = "AI" if msg.get("role") == "agent" else "Customer"
                            formatted_transcript += f"{role}: {msg.get('content')}\n\n"
                        call.transcript = formatted_transcript.strip()
                    
                    # Detect language from transcript
                    from app.utils.language_detector import detect_language
                    if call.transcript:
                        call.language_detected = detect_language(call.transcript)
                    else:
                        call.language_detected = "English"
                    
                    # Set simplified status
                    reason = data.get("disconnection_reason", "")
                    if reason in ["dial_failure", "voicemail_reached", "machine_detected", "dial_busy", "call_timeout"]:
                        call.status = "not_answered"
                    else:
                        call.status = "completed"
                        
                    # Fix campaign mapping based on agent_id
                    agent_id = data.get("agent_id")
                    if agent_id:
                        camp_res = await db.execute(select(Campaign).where(Campaign.agent_id == agent_id))
                        matched_camp = camp_res.scalar_one_or_none()
                        if matched_camp and call.campaign_id != matched_camp.id:
                            call.campaign_id = matched_camp.id
                        
                    # Set ended_at
                    end_ts = data.get("end_timestamp")
                    if end_ts:
                        call.ended_at = datetime.fromtimestamp(end_ts / 1000)
                    else:
                        call.ended_at = datetime.utcnow()
                    
                    synced = True
    
    if synced:
        await db.commit()
    
    
    # Convert any lingering 'initiated' statuses to 'not_answered'
    for call in calls:
        if call.status == "initiated":
            call.status = "not_answered"
    return CallListResponse(
        items=[CallResponse.model_validate(call) for call in calls],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/{call_id}", response_model=CallResponse)
async def get_call(
    call_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a call by ID with full details."""
    result = await db.execute(
        select(Call).where(Call.id == call_id)
    )
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    # Auto-sync individual call if it's still initiated or missing data
    if call.twilio_call_sid and (
        call.status == CallStatus.INITIATED.value 
        or not call.recording_url 
        or not call.call_summary
    ):
        from app.services.retell_service import get_retell_call
        retell_res = await get_retell_call(call.twilio_call_sid)
        if retell_res.get("status") == "success":
            data = retell_res["data"]
            r_status = data.get("call_status")
            
            if r_status in ["ended", "error"]:
                duration_ms = data.get("duration_ms", 0)
                call.duration_seconds = duration_ms // 1000
                
                call.recording_url = data.get("recording_url")
                
                # Extract cost
                call_cost_data = data.get("call_cost", {})
                if call_cost_data and isinstance(call_cost_data, dict):
                    combined = call_cost_data.get("combined_cost")
                    if combined is not None:
                        call.cost = combined / 100.0

                call_analysis = data.get("call_analysis", {})
                if call_analysis and isinstance(call_analysis, dict):
                    call.call_summary = call_analysis.get("call_summary")
                
                transcript_obj = data.get("transcript_object", [])
                if transcript_obj:
                    formatted_transcript = ""
                    for msg in transcript_obj:
                        role = "AI" if msg.get("role") == "agent" else "Customer"
                        formatted_transcript += f"{role}: {msg.get('content')}\n\n"
                    call.transcript = formatted_transcript.strip()
                
                reason = data.get("disconnection_reason", "")
                if reason in ["dial_failure", "voicemail_reached", "machine_detected", "dial_busy", "call_timeout"]:
                    call.status = "not_answered"
                else:
                    call.status = "completed"
                    
                # Fix campaign mapping based on agent_id
                agent_id = data.get("agent_id")
                if agent_id:
                    camp_res = await db.execute(select(Campaign).where(Campaign.agent_id == agent_id))
                    matched_camp = camp_res.scalar_one_or_none()
                    if matched_camp and call.campaign_id != matched_camp.id:
                        call.campaign_id = matched_camp.id
                    
                # Set ended_at
                end_ts = data.get("end_timestamp")
                if end_ts:
                    call.ended_at = datetime.fromtimestamp(end_ts / 1000)
                else:
                    call.ended_at = datetime.utcnow()
                
                await db.commit()
    
    return CallResponse.model_validate(call)


@router.post("/initiate", response_model=CallInitiateResponse)
async def initiate_call(
    request: CallInitiateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Initiate an outbound call to a phone number."""
    # Verify campaign exists
    campaign_result = await db.execute(
        select(Campaign).where(Campaign.id == request.campaign_id)
    )
    campaign = campaign_result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    if not campaign.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign is not active"
        )
    
    # Create call record
    call = Call(
        campaign_id=request.campaign_id,
        phone_number=request.phone_number,
        status=CallStatus.INITIATED.value
    )
    
    db.add(call)
    await db.flush()
    await db.refresh(call)
    
    # Initialize call orchestrator
    call_orchestrator.start_call(
        call_id=call.id,
        campaign_id=campaign.id,
        phone_number=request.phone_number,
        faqs=campaign.faqs
    )
    
    # TODO: Integrate with Twilio to actually make the call
    # For now, return success with the call ID
    
    return CallInitiateResponse(
        call_id=call.id,
        twilio_call_sid=None,  # Would be set by Twilio integration
        status=call.status,
        message="Call initiated successfully"
    )


@router.put("/{call_id}", response_model=CallResponse)
async def update_call(
    call_id: int,
    call_data: CallUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update call data (typically from webhook)."""
    result = await db.execute(
        select(Call).where(Call.id == call_id)
    )
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    # Update fields
    update_data = call_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(call, field, value)
    
    await db.flush()
    await db.refresh(call)
    
    return CallResponse.model_validate(call)


@router.post("/{call_id}/end")
async def end_call(
    call_id: int,
    db: AsyncSession = Depends(get_db)
):
    """End a call and get summary."""
    result = await db.execute(
        select(Call).where(Call.id == call_id)
    )
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    # End call in orchestrator
    summary = call_orchestrator.end_call(call_id)
    
    if summary:
        # Update call record
        call.status = CallStatus.COMPLETED.value
        call.ended_at = datetime.utcnow()
        call.duration_seconds = int(summary.get("duration_seconds", 0))
        call.transcript = summary.get("transcript")
        call.language_detected = summary.get("language_detected")
        call.lead_score = summary.get("lead_score")
        call.lead_qualification = summary.get("lead_qualification")
        
        await db.flush()
        
        # Create or update lead
        if call.lead_qualification in ["hot", "warm"]:
            lead = Lead(
                campaign_id=call.campaign_id,
                phone=call.phone_number,
                qualification=call.lead_qualification,
                interest_level=int(call.lead_score * 10) if call.lead_score else None,
                call_summary=call.transcript[:500] if call.transcript else None
            )
            db.add(lead)
            await db.flush()
    else:
        call.status = CallStatus.COMPLETED.value
        call.ended_at = datetime.utcnow()
        await db.flush()
    
    return {
        "status": "success",
        "call_id": call_id,
        "summary": summary
    }


@router.post("/{call_id}/process-text")
async def process_text_input(
    call_id: int,
    text: str,
    db: AsyncSession = Depends(get_db)
):
    """Process text input for a call (for testing without audio)."""
    # Verify call exists
    result = await db.execute(
        select(Call).where(Call.id == call_id)
    )
    call = result.scalar_one_or_none()
    
    campaign_context = None
    if call:
        campaign_result = await db.execute(
            select(Campaign).where(Campaign.id == call.campaign_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        if campaign:
            campaign_context = f"Campaign: {campaign.name}. {campaign.description or ''}"
    
    # Process through orchestrator
    response = await call_orchestrator.process_text_input(
        call_id=call_id,
        user_text=text,
        campaign_context=campaign_context
    )
    
    return {
        "user_input": text,
        "response": response,
        "call_id": call_id
    }


class RetellCallRequest(BaseModel):
    """Request schema for initiating a Retell AI call."""
    phone_number: str
    agent_id: Optional[str] = None
    campaign_id: Optional[int] = None


@router.post("/retell-call")
async def retell_call(request: RetellCallRequest, db: AsyncSession = Depends(get_db)):
    """Initiate an outbound call using Retell AI and log it in the database."""
    from app.services.retell_service import create_retell_call
    from app.models.call import Call, CallStatus

    # Resolve agent_id: explicit > campaign > .env fallback
    agent_id = request.agent_id
    campaign_id_to_store = request.campaign_id
    
    if not agent_id and request.campaign_id:
        campaign_result = await db.execute(
            select(Campaign).where(Campaign.id == request.campaign_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        if campaign and campaign.agent_id:
            agent_id = campaign.agent_id

    # Fallback to first campaign if none provided to satisfy DB constraints
    if not campaign_id_to_store:
        first_camp_result = await db.execute(select(Campaign).limit(1))
        first_camp = first_camp_result.scalar_one_or_none()
        if first_camp:
            campaign_id_to_store = first_camp.id

    result = await create_retell_call(to_number=request.phone_number, agent_id=agent_id)
    
    if result.get("status") == "success" and campaign_id_to_store:
        # Save the call to database so it appears in the Calls page
        call = Call(
            campaign_id=campaign_id_to_store,
            phone_number=request.phone_number,
            status=CallStatus.INITIATED.value,
            twilio_call_sid=result.get("call_id") # We can store retell call_id here
        )
        db.add(call)
        await db.flush()
        result["internal_call_id"] = call.id
        
    return result
