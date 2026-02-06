"""
Call Schemas
Pydantic models for call API validation and serialization.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.call import CallStatus


class CallBase(BaseModel):
    """Base call schema."""
    phone_number: str = Field(..., min_length=10, max_length=20)
    campaign_id: int


class CallCreate(CallBase):
    """Schema for initiating a call."""
    pass


class CallUpdate(BaseModel):
    """Schema for updating call data."""
    status: Optional[str] = None
    transcript: Optional[str] = None
    language_detected: Optional[str] = None
    lead_score: Optional[float] = Field(None, ge=0, le=1)
    lead_qualification: Optional[str] = None
    duration_seconds: Optional[int] = None
    recording_url: Optional[str] = None
    ended_at: Optional[datetime] = None


class CallResponse(BaseModel):
    """Schema for call response."""
    id: int
    campaign_id: int
    phone_number: str
    twilio_call_sid: Optional[str] = None
    duration_seconds: int
    transcript: Optional[str] = None
    language_detected: Optional[str] = None
    lead_score: Optional[float] = None
    lead_qualification: Optional[str] = None
    status: str
    recording_url: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CallListResponse(BaseModel):
    """Schema for paginated call list."""
    items: List[CallResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CallInitiateRequest(BaseModel):
    """Request schema for initiating an outbound call."""
    campaign_id: int
    phone_number: str = Field(..., min_length=10, max_length=20)


class CallInitiateResponse(BaseModel):
    """Response schema for call initiation."""
    call_id: int
    twilio_call_sid: Optional[str] = None
    status: str
    message: str
