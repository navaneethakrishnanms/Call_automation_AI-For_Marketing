"""
Campaign Routes
API endpoints for campaign management.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.campaign import Campaign
from app.models.call import Call
from app.models.lead import Lead
from app.schemas.campaign import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CampaignListResponse,
    FAQItem,
)
from app.services.faq_retrieval import faq_service

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    page: int = 1,
    page_size: int = 10,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all campaigns with pagination."""
    # Build query
    query = select(Campaign)
    if is_active is not None:
        query = query.where(Campaign.is_active == is_active)
    
    # Get total count
    count_query = select(func.count()).select_from(Campaign)
    if is_active is not None:
        count_query = count_query.where(Campaign.is_active == is_active)
    total = (await db.execute(count_query)).scalar() or 0
    
    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Campaign.created_at.desc())
    
    result = await db.execute(query)
    campaigns = result.scalars().all()
    
    # Build response with counts
    items = []
    for campaign in campaigns:
        # Get call count
        call_count = (await db.execute(
            select(func.count()).select_from(Call).where(Call.campaign_id == campaign.id)
        )).scalar() or 0
        
        # Get lead count
        lead_count = (await db.execute(
            select(func.count()).select_from(Lead).where(Lead.campaign_id == campaign.id)
        )).scalar() or 0
        
        item = CampaignResponse(
            id=campaign.id,
            name=campaign.name,
            description=campaign.description,
            greeting_message=campaign.greeting_message,
            farewell_message=campaign.farewell_message,
            faqs=[FAQItem(**faq) for faq in (campaign.faqs or [])],
            is_active=campaign.is_active,
            created_at=campaign.created_at,
            updated_at=campaign.updated_at,
            total_calls=call_count,
            total_leads=lead_count,
        )
        items.append(item)
    
    return CampaignListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_data: CampaignCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new campaign."""
    campaign = Campaign(
        name=campaign_data.name,
        description=campaign_data.description,
        greeting_message=campaign_data.greeting_message,
        farewell_message=campaign_data.farewell_message,
        faqs=[faq.model_dump() for faq in campaign_data.faqs] if campaign_data.faqs else [],
    )
    
    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)
    
    # Load FAQs into retrieval service
    if campaign.faqs:
        faq_service.load_faqs(campaign.id, campaign.faqs)
    
    return CampaignResponse(
        id=campaign.id,
        name=campaign.name,
        description=campaign.description,
        greeting_message=campaign.greeting_message,
        farewell_message=campaign.farewell_message,
        faqs=[FAQItem(**faq) for faq in (campaign.faqs or [])],
        is_active=campaign.is_active,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        total_calls=0,
        total_leads=0,
    )


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a campaign by ID."""
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    # Get counts
    call_count = (await db.execute(
        select(func.count()).select_from(Call).where(Call.campaign_id == campaign_id)
    )).scalar() or 0
    
    lead_count = (await db.execute(
        select(func.count()).select_from(Lead).where(Lead.campaign_id == campaign_id)
    )).scalar() or 0
    
    return CampaignResponse(
        id=campaign.id,
        name=campaign.name,
        description=campaign.description,
        greeting_message=campaign.greeting_message,
        farewell_message=campaign.farewell_message,
        faqs=[FAQItem(**faq) for faq in (campaign.faqs or [])],
        is_active=campaign.is_active,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        total_calls=call_count,
        total_leads=lead_count,
    )


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int,
    campaign_data: CampaignUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a campaign."""
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    # Update fields
    update_data = campaign_data.model_dump(exclude_unset=True)
    
    if "faqs" in update_data and update_data["faqs"] is not None:
        update_data["faqs"] = [faq.model_dump() for faq in campaign_data.faqs]
        # Reload FAQs in retrieval service
        faq_service.load_faqs(campaign_id, update_data["faqs"])
    
    for field, value in update_data.items():
        setattr(campaign, field, value)
    
    await db.flush()
    await db.refresh(campaign)
    
    # Get counts
    call_count = (await db.execute(
        select(func.count()).select_from(Call).where(Call.campaign_id == campaign_id)
    )).scalar() or 0
    
    lead_count = (await db.execute(
        select(func.count()).select_from(Lead).where(Lead.campaign_id == campaign_id)
    )).scalar() or 0
    
    return CampaignResponse(
        id=campaign.id,
        name=campaign.name,
        description=campaign.description,
        greeting_message=campaign.greeting_message,
        farewell_message=campaign.farewell_message,
        faqs=[FAQItem(**faq) for faq in (campaign.faqs or [])],
        is_active=campaign.is_active,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        total_calls=call_count,
        total_leads=lead_count,
    )


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a campaign."""
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    # Remove from FAQ service
    faq_service.remove_campaign(campaign_id)
    
    await db.delete(campaign)


@router.post("/{campaign_id}/faqs", response_model=CampaignResponse)
async def upload_faqs(
    campaign_id: int,
    faqs: List[FAQItem],
    db: AsyncSession = Depends(get_db)
):
    """Upload FAQs to a campaign."""
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    # Update FAQs
    campaign.faqs = [faq.model_dump() for faq in faqs]
    
    # Reload in retrieval service
    faq_service.load_faqs(campaign_id, campaign.faqs)
    
    await db.flush()
    await db.refresh(campaign)
    
    # Get counts
    call_count = (await db.execute(
        select(func.count()).select_from(Call).where(Call.campaign_id == campaign_id)
    )).scalar() or 0
    
    lead_count = (await db.execute(
        select(func.count()).select_from(Lead).where(Lead.campaign_id == campaign_id)
    )).scalar() or 0
    
    return CampaignResponse(
        id=campaign.id,
        name=campaign.name,
        description=campaign.description,
        greeting_message=campaign.greeting_message,
        farewell_message=campaign.farewell_message,
        faqs=[FAQItem(**faq) for faq in (campaign.faqs or [])],
        is_active=campaign.is_active,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        total_calls=call_count,
        total_leads=lead_count,
    )
