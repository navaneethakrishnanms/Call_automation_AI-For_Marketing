"""
Call Routes
API endpoints for call management and initiation.
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
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
