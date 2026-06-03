from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class FeedbackCreate(BaseModel):
    user_name: Optional[str] = None
    message: str = Field(..., min_length=1)
    rating: Optional[int] = Field(None, ge=1, le=5)

class FeedbackResponse(BaseModel):
    id: int
    user_name: Optional[str] = None
    message: str
    rating: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
