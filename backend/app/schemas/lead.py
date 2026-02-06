"""
Lead Schemas
Pydantic models for lead API validation and serialization.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr

from app.models.lead import LeadQualification


class LeadBase(BaseModel):
    """Base lead schema."""
    phone: str = Field(..., min_length=10, max_length=20)
    campaign_id: int


class LeadCreate(LeadBase):
    """Schema for creating a lead."""
    name: Optional[str] = None
    email: Optional[str] = None
    qualification: str = LeadQualification.COLD.value
    notes: Optional[str] = None


class LeadUpdate(BaseModel):
    """Schema for updating a lead."""
    name: Optional[str] = None
    email: Optional[str] = None
    qualification: Optional[str] = None
    interest_level: Optional[int] = Field(None, ge=1, le=10)
    expressed_interests: Optional[str] = None
    notes: Optional[str] = None
    call_summary: Optional[str] = None
    requires_callback: Optional[bool] = None
    callback_scheduled: Optional[datetime] = None


class LeadResponse(BaseModel):
    """Schema for lead response."""
    id: int
    campaign_id: int
    name: Optional[str] = None
    phone: str
    email: Optional[str] = None
    qualification: str
    interest_level: Optional[int] = None
    expressed_interests: Optional[str] = None
    notes: Optional[str] = None
    call_summary: Optional[str] = None
    requires_callback: bool
    callback_scheduled: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    """Schema for paginated lead list."""
    items: List[LeadResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class LeadQualificationStats(BaseModel):
    """Statistics for lead qualifications."""
    hot: int = 0
    warm: int = 0
    cold: int = 0
    total: int = 0
