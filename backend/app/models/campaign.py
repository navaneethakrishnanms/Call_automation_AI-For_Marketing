"""
Campaign Model
Represents marketing campaigns with their FAQs and settings.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Campaign(Base):
    """Marketing campaign with associated FAQs."""
    
    __tablename__ = "campaigns"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # FAQ data stored as JSON array
    faqs: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=list)
    
    # Campaign settings
    greeting_message: Mapped[Optional[str]] = mapped_column(
        Text, 
        default="Hello! Thank you for your interest. How can I help you today?"
    )
    farewell_message: Mapped[Optional[str]] = mapped_column(
        Text,
        default="Thank you for calling! Have a wonderful day!"
    )
    
    # Auto-build pipeline fields
    website_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    target_audience: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    goal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    languages: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=list)
    competitors: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=list)
    
    # Build status tracking
    build_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="idle")
    build_progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    build_log: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=list)
    
    # Auto-generated content
    extracted_knowledge: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    voice_scripts: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    competitor_intel: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Crawl tracking
    pages_crawled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_crawled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
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
    
    # Relationships
    calls = relationship("Call", back_populates="campaign", lazy="selectin")
    leads = relationship("Lead", back_populates="campaign", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<Campaign(id={self.id}, name='{self.name}')>"
