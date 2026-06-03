from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.database import get_db
from app.models.feedback import Feedback
from app.schemas.feedback import FeedbackCreate, FeedbackResponse

router = APIRouter(prefix="/feedback", tags=["feedback"])

@router.post("/", response_model=FeedbackResponse)
async def create_feedback(feedback: FeedbackCreate, db: AsyncSession = Depends(get_db)):
    """Submit new user feedback."""
    db_feedback = Feedback(
        user_name=feedback.user_name,
        message=feedback.message,
        rating=feedback.rating
    )
    db.add(db_feedback)
    await db.commit()
    await db.refresh(db_feedback)
    return db_feedback

@router.get("/", response_model=List[FeedbackResponse])
async def get_feedback(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Get all feedback (for admin viewing)."""
    result = await db.execute(select(Feedback).order_by(Feedback.created_at.desc()).offset(skip).limit(limit))
    feedbacks = result.scalars().all()
    return feedbacks
