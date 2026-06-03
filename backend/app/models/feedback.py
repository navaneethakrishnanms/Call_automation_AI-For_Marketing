from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.database import Base

class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String, index=True, nullable=True)
    message = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)  # Optional 1-5 rating
    created_at = Column(DateTime, default=datetime.utcnow)
