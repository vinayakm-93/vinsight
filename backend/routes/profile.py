import logging
from datetime import datetime, date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import User, UserGoal, ProfileEvent, Portfolio
from services import auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])

# --- Telemetry ---

def log_profile_event(db: Session, user_id: int, event: str, field: str = None, value: str = None):
    """Log a minimal telemetry event for profile interactions."""
    try:
        db.add(ProfileEvent(user_id=user_id, event=event, field=field, value=str(value)[:200] if value else None))
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to log profile event: {e}")


# --- Schemas ---

class ProfileUpdate(BaseModel):
    monthly_budget: Optional[float] = None
    risk_appetite: Optional[str] = None
    default_horizon: Optional[str] = None
    investment_experience: Optional[str] = None

class ProfileOut(BaseModel):
    monthly_budget: Optional[float]
    risk_appetite: Optional[str]
    default_horizon: Optional[str]
    investment_experience: Optional[str]
    profile_completed_at: Optional[datetime]

    class Config:
        from_attributes = True

class GoalCreate(BaseModel):
    name: str
    target_amount: Optional[float] = None
    target_date: Optional[date] = None
    priority: Optional[str] = None  # high, medium, low
    notes: Optional[str] = None
    portfolio_id: Optional[int] = None

class GoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[float] = None
    target_date: Optional[date] = None
    priority: Optional[str] = None
    notes: Optional[str] = None
    portfolio_id: Optional[int] = None

class GoalOut(BaseModel):
    id: int
    name: str
    target_amount: Optional[float]
    target_date: Optional[date]
    priority: Optional[str]
    notes: Optional[str]
    portfolio_id: Optional[int]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

class FullProfileOut(BaseModel):
    profile: ProfileOut
    goals: List[GoalOut]


# --- Profile Endpoints ---

VALID_RISK = {"conservative", "moderate", "aggressive"}
VALID_HORIZON = {"< 1 year", "1-3 years", "3-5 years", "5-10 years", "10+ years"}
VALID_EXPERIENCE = {"beginner", "intermediate", "advanced"}
VALID_PRIORITY = {"high", "medium", "low"}


@router.get("", response_model=FullProfileOut)
async def get_profile(
    db: Session = Depends(get_db),
    user: User = Depends(auth.get_current_user)
):
    """Get the full user profile including goals."""
    log_profile_event(db, user.id, "profile_opened")
    goals = db.query(UserGoal).filter(UserGoal.user_id == user.id).order_by(UserGoal.created_at).all()
    return FullProfileOut(
        profile=ProfileOut(
            monthly_budget=user.monthly_budget,
            risk_appetite=user.risk_appetite,
            default_horizon=user.default_horizon,
            investment_experience=user.investment_experience,
            profile_completed_at=user.profile_completed_at,
        ),
        goals=[GoalOut.model_validate(g) for g in goals],
    )


@router.put("", response_model=ProfileOut)
async def update_profile(
    body: ProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(auth.get_current_user)
):
    """Update user profile fields (partial updates)."""
    if body.monthly_budget is not None:
        user.monthly_budget = body.monthly_budget
        log_profile_event(db, user.id, "field_saved", "monthly_budget", str(body.monthly_budget))

    if body.risk_appetite is not None:
        if body.risk_appetite.lower() not in VALID_RISK:
            raise HTTPException(status_code=400, detail=f"risk_appetite must be one of: {', '.join(VALID_RISK)}")
        user.risk_appetite = body.risk_appetite.lower()
        log_profile_event(db, user.id, "field_saved", "risk_appetite", user.risk_appetite)

    if body.default_horizon is not None:
        if body.default_horizon not in VALID_HORIZON:
            raise HTTPException(status_code=400, detail=f"default_horizon must be one of: {', '.join(VALID_HORIZON)}")
        user.default_horizon = body.default_horizon
        log_profile_event(db, user.id, "field_saved", "default_horizon", user.default_horizon)

    if body.investment_experience is not None:
        if body.investment_experience.lower() not in VALID_EXPERIENCE:
            raise HTTPException(status_code=400, detail=f"investment_experience must be one of: {', '.join(VALID_EXPERIENCE)}")
        user.investment_experience = body.investment_experience.lower()
        log_profile_event(db, user.id, "field_saved", "investment_experience", user.investment_experience)

    # Check if profile is now complete (all 4 core fields set)
    if (user.monthly_budget is not None and user.risk_appetite and
            user.default_horizon and user.investment_experience and
            not user.profile_completed_at):
        user.profile_completed_at = datetime.utcnow()
        log_profile_event(db, user.id, "profile_completed")

    db.commit()
    db.refresh(user)
    return ProfileOut(
        monthly_budget=user.monthly_budget,
        risk_appetite=user.risk_appetite,
        default_horizon=user.default_horizon,
        investment_experience=user.investment_experience,
        profile_completed_at=user.profile_completed_at,
    )


# --- Goal Endpoints ---

@router.get("/goals", response_model=List[GoalOut])
async def list_goals(
    db: Session = Depends(get_db),
    user: User = Depends(auth.get_current_user)
):
    goals = db.query(UserGoal).filter(UserGoal.user_id == user.id).order_by(UserGoal.created_at).all()
    return [GoalOut.model_validate(g) for g in goals]


@router.post("/goals", response_model=GoalOut, status_code=201)
async def create_goal(
    body: GoalCreate,
    db: Session = Depends(get_db),
    user: User = Depends(auth.get_current_user)
):
    if body.priority and body.priority.lower() not in VALID_PRIORITY:
        raise HTTPException(status_code=400, detail=f"priority must be one of: {', '.join(VALID_PRIORITY)}")
    if body.portfolio_id:
        portfolio = db.query(Portfolio).filter(Portfolio.id == body.portfolio_id, Portfolio.user_id == user.id).first()
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")

    goal = UserGoal(
        user_id=user.id,
        name=body.name[:100],
        target_amount=body.target_amount,
        target_date=body.target_date,
        priority=body.priority.lower() if body.priority else None,
        notes=body.notes[:500] if body.notes else None,
        portfolio_id=body.portfolio_id,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    log_profile_event(db, user.id, "goal_created", goal.name, str(body.target_amount) if body.target_amount else None)
    return GoalOut.model_validate(goal)


@router.put("/goals/{goal_id}", response_model=GoalOut)
async def update_goal(
    goal_id: int,
    body: GoalUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(auth.get_current_user)
):
    goal = db.query(UserGoal).filter(UserGoal.id == goal_id, UserGoal.user_id == user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    if body.name is not None:
        goal.name = body.name[:100]
    if body.target_amount is not None:
        goal.target_amount = body.target_amount
    if body.target_date is not None:
        goal.target_date = body.target_date
    if body.priority is not None:
        if body.priority.lower() not in VALID_PRIORITY:
            raise HTTPException(status_code=400, detail=f"priority must be one of: {', '.join(VALID_PRIORITY)}")
        goal.priority = body.priority.lower()
    if body.notes is not None:
        goal.notes = body.notes[:500]
    if body.portfolio_id is not None:
        if body.portfolio_id == 0:
            goal.portfolio_id = None  # Unlink
        else:
            portfolio = db.query(Portfolio).filter(Portfolio.id == body.portfolio_id, Portfolio.user_id == user.id).first()
            if not portfolio:
                raise HTTPException(status_code=404, detail="Portfolio not found")
            goal.portfolio_id = body.portfolio_id

    goal.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(goal)
    log_profile_event(db, user.id, "goal_updated", goal.name)
    return GoalOut.model_validate(goal)


@router.delete("/goals/{goal_id}")
async def delete_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(auth.get_current_user)
):
    goal = db.query(UserGoal).filter(UserGoal.id == goal_id, UserGoal.user_id == user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    goal_name = goal.name
    db.delete(goal)
    db.commit()
    log_profile_event(db, user.id, "goal_deleted", goal_name)
    return {"status": "deleted", "goal_id": goal_id}
