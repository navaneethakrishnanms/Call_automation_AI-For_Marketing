"""
Lead Model
Represents qualified leads from call interactions.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class LeadQualification(str, enum.Enum):
    """Lead qualification levels."""
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


class Lead(Base):
    """Qualified lead from call interactions."""
    
    __tablename__ = "leads"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Foreign key to campaign
    campaign_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("campaigns.id"),
        nullable=False
    )
    
    # Contact information
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Qualification
    qualification: Mapped[str] = mapped_column(
        String(20),
        default=LeadQualification.COLD.value
    )
    
    # Interest indicators
    interest_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-10
    expressed_interests: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Notes and context
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    call_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Follow-up
    requires_callback: Mapped[bool] = mapped_column(default=False)
    callback_scheduled: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationship
    campaign = relationship("Campaign", back_populates="leads")
    
    def __repr__(self) -> str:
        return f"<Lead(id={self.id}, phone='{self.phone}', qualification='{self.qualification}')>"
