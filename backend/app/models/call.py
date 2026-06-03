"""
Call Model
Represents individual call logs with transcripts and analytics.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Integer, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class CallStatus(str, enum.Enum):
    """Call status enumeration."""
    INITIATED = "initiated"
    COMPLETED = "completed"
    NOT_ANSWERED = "not_answered"


class Call(Base):
    """Individual call log with conversation data."""
    
    __tablename__ = "calls"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Foreign key to campaign
    campaign_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("campaigns.id"),
        nullable=False
    )
    
    # Call details
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    twilio_call_sid: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Call metrics
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    
    # Conversation data
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language_detected: Mapped[Optional[str]] = mapped_column(
        String(20), 
        default="english"
    )
    
    # Customer intent (e.g., placement, hostel, just exploring)
    intent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Lead qualification (kept for backward compat)
    lead_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lead_qualification: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True
    )
    
    # Cost
    cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default=CallStatus.INITIATED.value
    )
    
    # Recording URL (if available)
    recording_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Call summary
    call_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationship
    campaign = relationship("Campaign", back_populates="calls")
    
    def __repr__(self) -> str:
        return f"<Call(id={self.id}, phone='{self.phone_number}', status='{self.status}')>"
