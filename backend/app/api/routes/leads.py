"""
Lead Routes
API endpoints for lead management.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.lead import Lead, LeadQualification
from app.schemas.lead import (
    LeadCreate,
    LeadUpdate,
    LeadResponse,
    LeadListResponse,
    LeadQualificationStats,
)

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=LeadListResponse)
async def list_leads(
    page: int = 1,
    page_size: int = 20,
    campaign_id: Optional[int] = None,
    qualification: Optional[str] = None,
    requires_callback: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all leads with filters and pagination."""
    query = select(Lead)
    count_query = select(func.count()).select_from(Lead)
    
    # Apply filters
    if campaign_id:
        query = query.where(Lead.campaign_id == campaign_id)
        count_query = count_query.where(Lead.campaign_id == campaign_id)
    
    if qualification:
        query = query.where(Lead.qualification == qualification)
        count_query = count_query.where(Lead.qualification == qualification)
    
    if requires_callback is not None:
        query = query.where(Lead.requires_callback == requires_callback)
        count_query = count_query.where(Lead.requires_callback == requires_callback)
    
    # Get total
    total = (await db.execute(count_query)).scalar() or 0
    
    # Paginate and order
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Lead.created_at.desc())
    
    result = await db.execute(query)
    leads = result.scalars().all()
    
    return LeadListResponse(
        items=[LeadResponse.model_validate(lead) for lead in leads],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/stats", response_model=LeadQualificationStats)
async def get_lead_stats(
    campaign_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get lead qualification statistics."""
    base_query = select(Lead.qualification, func.count(Lead.id))
    
    if campaign_id:
        base_query = base_query.where(Lead.campaign_id == campaign_id)
    
    base_query = base_query.group_by(Lead.qualification)
    
    result = await db.execute(base_query)
    counts = {row[0]: row[1] for row in result.fetchall()}
    
    return LeadQualificationStats(
        hot=counts.get("hot", 0),
        warm=counts.get("warm", 0),
        cold=counts.get("cold", 0),
        total=sum(counts.values())
    )


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    lead_data: LeadCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new lead manually."""
    lead = Lead(
        campaign_id=lead_data.campaign_id,
        phone=lead_data.phone,
        name=lead_data.name,
        email=lead_data.email,
        qualification=lead_data.qualification,
        notes=lead_data.notes,
    )
    
    db.add(lead)
    await db.flush()
    await db.refresh(lead)
    
    return LeadResponse.model_validate(lead)


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a lead by ID."""
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found"
        )
    
    return LeadResponse.model_validate(lead)


@router.put("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: int,
    lead_data: LeadUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a lead."""
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found"
        )
    
    # Update fields
    update_data = lead_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)
    
    await db.flush()
    await db.refresh(lead)
    
    return LeadResponse.model_validate(lead)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a lead."""
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found"
        )
    
    await db.delete(lead)
