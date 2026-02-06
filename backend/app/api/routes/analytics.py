"""
Analytics Routes
API endpoints for marketing analytics and reporting.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api.deps import get_db
from app.models.call import Call
from app.models.lead import Lead
from app.models.campaign import Campaign

router = APIRouter(prefix="/analytics", tags=["analytics"])


class OverviewStats(BaseModel):
    """Dashboard overview statistics."""
    total_campaigns: int
    active_campaigns: int
    total_calls: int
    total_leads: int
    hot_leads: int
    warm_leads: int
    cold_leads: int
    avg_call_duration: float
    conversion_rate: float


class CallMetric(BaseModel):
    """Call metrics for a time period."""
    date: str
    total_calls: int
    completed_calls: int
    avg_duration: float


class LanguageBreakdown(BaseModel):
    """Language distribution in calls."""
    language: str
    count: int
    percentage: float


class LeadTrend(BaseModel):
    """Lead trend over time."""
    date: str
    hot: int
    warm: int
    cold: int


@router.get("/overview", response_model=OverviewStats)
async def get_overview_stats(
    campaign_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard overview statistics."""
    # Campaign counts
    total_campaigns = (await db.execute(
        select(func.count()).select_from(Campaign)
    )).scalar() or 0
    
    active_campaigns = (await db.execute(
        select(func.count()).select_from(Campaign).where(Campaign.is_active == True)
    )).scalar() or 0
    
    # Call counts
    call_query = select(func.count()).select_from(Call)
    if campaign_id:
        call_query = call_query.where(Call.campaign_id == campaign_id)
    total_calls = (await db.execute(call_query)).scalar() or 0
    
    # Average call duration
    duration_query = select(func.avg(Call.duration_seconds)).select_from(Call)
    if campaign_id:
        duration_query = duration_query.where(Call.campaign_id == campaign_id)
    avg_duration = (await db.execute(duration_query)).scalar() or 0
    
    # Lead counts
    lead_base = select(Lead)
    if campaign_id:
        lead_base = lead_base.where(Lead.campaign_id == campaign_id)
    
    total_leads = (await db.execute(
        select(func.count()).select_from(Lead).where(
            Lead.campaign_id == campaign_id if campaign_id else True
        )
    )).scalar() or 0
    
    hot_leads = (await db.execute(
        select(func.count()).select_from(Lead).where(
            and_(
                Lead.qualification == "hot",
                Lead.campaign_id == campaign_id if campaign_id else True
            )
        )
    )).scalar() or 0
    
    warm_leads = (await db.execute(
        select(func.count()).select_from(Lead).where(
            and_(
                Lead.qualification == "warm",
                Lead.campaign_id == campaign_id if campaign_id else True
            )
        )
    )).scalar() or 0
    
    cold_leads = (await db.execute(
        select(func.count()).select_from(Lead).where(
            and_(
                Lead.qualification == "cold",
                Lead.campaign_id == campaign_id if campaign_id else True
            )
        )
    )).scalar() or 0
    
    # Conversion rate (hot leads / total calls)
    conversion_rate = (hot_leads / total_calls * 100) if total_calls > 0 else 0
    
    return OverviewStats(
        total_campaigns=total_campaigns,
        active_campaigns=active_campaigns,
        total_calls=total_calls,
        total_leads=total_leads,
        hot_leads=hot_leads,
        warm_leads=warm_leads,
        cold_leads=cold_leads,
        avg_call_duration=float(avg_duration),
        conversion_rate=round(conversion_rate, 2)
    )


@router.get("/calls", response_model=List[CallMetric])
async def get_call_metrics(
    days: int = Query(default=7, ge=1, le=90),
    campaign_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get call metrics over time."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    metrics = []
    
    for i in range(days):
        day_start = start_date + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        
        # Query for this day
        query = select(Call).where(
            and_(
                Call.started_at >= day_start,
                Call.started_at < day_end
            )
        )
        if campaign_id:
            query = query.where(Call.campaign_id == campaign_id)
        
        result = await db.execute(query)
        calls = result.scalars().all()
        
        total = len(calls)
        completed = len([c for c in calls if c.status == "completed"])
        durations = [c.duration_seconds for c in calls if c.duration_seconds > 0]
        avg_dur = sum(durations) / len(durations) if durations else 0
        
        metrics.append(CallMetric(
            date=day_start.strftime("%Y-%m-%d"),
            total_calls=total,
            completed_calls=completed,
            avg_duration=round(avg_dur, 1)
        ))
    
    return metrics


@router.get("/languages", response_model=List[LanguageBreakdown])
async def get_language_breakdown(
    campaign_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get language distribution in calls."""
    query = select(
        Call.language_detected,
        func.count(Call.id)
    ).group_by(Call.language_detected)
    
    if campaign_id:
        query = query.where(Call.campaign_id == campaign_id)
    
    result = await db.execute(query)
    counts = result.fetchall()
    
    total = sum(c[1] for c in counts) or 1
    
    breakdown = []
    for lang, count in counts:
        if lang:
            breakdown.append(LanguageBreakdown(
                language=lang,
                count=count,
                percentage=round(count / total * 100, 1)
            ))
    
    # Default if no data
    if not breakdown:
        breakdown = [
            LanguageBreakdown(language="english", count=0, percentage=0),
            LanguageBreakdown(language="tamil", count=0, percentage=0),
            LanguageBreakdown(language="tanglish", count=0, percentage=0),
        ]
    
    return breakdown


@router.get("/leads", response_model=List[LeadTrend])
async def get_lead_trends(
    days: int = Query(default=7, ge=1, le=90),
    campaign_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get lead qualification trends over time."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    trends = []
    
    for i in range(days):
        day_start = start_date + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        
        base_filter = and_(
            Lead.created_at >= day_start,
            Lead.created_at < day_end
        )
        if campaign_id:
            base_filter = and_(base_filter, Lead.campaign_id == campaign_id)
        
        hot = (await db.execute(
            select(func.count()).select_from(Lead).where(
                and_(base_filter, Lead.qualification == "hot")
            )
        )).scalar() or 0
        
        warm = (await db.execute(
            select(func.count()).select_from(Lead).where(
                and_(base_filter, Lead.qualification == "warm")
            )
        )).scalar() or 0
        
        cold = (await db.execute(
            select(func.count()).select_from(Lead).where(
                and_(base_filter, Lead.qualification == "cold")
            )
        )).scalar() or 0
        
        trends.append(LeadTrend(
            date=day_start.strftime("%Y-%m-%d"),
            hot=hot,
            warm=warm,
            cold=cold
        ))
    
    return trends
