"""
Campaign Schemas
Pydantic models for campaign API validation and serialization.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class FAQItem(BaseModel):
    """Individual FAQ item."""
    question: str = Field(..., min_length=1, max_length=500)
    answer: str = Field(..., min_length=1, max_length=2000)
    keywords: Optional[List[str]] = Field(default_factory=list)


class CampaignBase(BaseModel):
    """Base campaign schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    greeting_message: Optional[str] = "Hello! Thank you for your interest. How can I help you today?"
    farewell_message: Optional[str] = "Thank you for calling! Have a wonderful day!"


class CampaignCreate(CampaignBase):
    """Schema for creating a campaign."""
    faqs: Optional[List[FAQItem]] = Field(default_factory=list)


class CampaignUpdate(BaseModel):
    """Schema for updating a campaign."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    greeting_message: Optional[str] = None
    farewell_message: Optional[str] = None
    is_active: Optional[bool] = None
    faqs: Optional[List[FAQItem]] = None


class CampaignResponse(CampaignBase):
    """Schema for campaign response."""
    id: int
    faqs: List[FAQItem] = Field(default_factory=list)
    is_active: bool
    created_at: datetime
    updated_at: datetime
    total_calls: int = 0
    total_leads: int = 0
    
    class Config:
        from_attributes = True


class CampaignListResponse(BaseModel):
    """Schema for paginated campaign list."""
    items: List[CampaignResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
