from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models import Feedback, User
from services import auth

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

class FeedbackCreate(BaseModel):
    message: str
    rating: Optional[int] = None

@router.post("/")
def create_feedback(feedback: FeedbackCreate, db: Session = Depends(get_db), user: Optional[User] = Depends(auth.get_current_user_optional)):
    db_feedback = Feedback(
        message=feedback.message,
        rating=feedback.rating,
        user_id=user.id if user else None
    )
    db.add(db_feedback)
    db.commit()
    return {"status": "success", "message": "Feedback received"}
