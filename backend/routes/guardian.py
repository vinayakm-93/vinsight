from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from database import get_db
from models import User, GuardianThesis, GuardianAlert
from services import guardian_agent
from services.auth import get_current_user
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("guardian_routes")

router = APIRouter(prefix="/api/guardian", tags=["guardian"])

# --- Pydantic Models ---

class ThesisCreate(BaseModel):
    symbol: str

class ThesisUpdate(BaseModel):
    thesis: str

class ThesisResponse(BaseModel):
    symbol: str
    thesis: str
    is_active: bool
    status: str # INTACT / AT_RISK / BROKEN
    last_checked_at: Optional[str]
    check_count: int
    auto_generated: bool

class AlertResponse(BaseModel):
    id: int
    symbol: str
    thesis_status: str
    confidence: Optional[float]
    reasoning: Optional[str]
    created_at: str
    is_read: bool

# --- Endpoints ---

@router.get("/theses", response_model=List[ThesisResponse])
async def get_theses(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all active Guardian theses for the user."""
    theses = db.query(GuardianThesis).filter(GuardianThesis.user_id == current_user.id).all()
    
    results = []
    for t in theses:
        # Get latest status from alerts if available, or compute simple one
        latest_alert = db.query(GuardianAlert).filter(
            GuardianAlert.user_id == current_user.id,
            GuardianAlert.symbol == t.symbol
        ).order_by(GuardianAlert.created_at.desc()).first()
        
        status = latest_alert.thesis_status if latest_alert else "INTACT"
        
        results.append({
            "symbol": t.symbol,
            "thesis": t.thesis,
            "is_active": t.is_active,
            "status": status,
            "last_checked_at": str(t.last_checked_at) if t.last_checked_at else None,
            "check_count": t.check_count,
            "auto_generated": t.auto_generated
        })
    return results

@router.post("/enable")
async def enable_guardian(req: ThesisCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Enable Guardian for a stock. Auto-generates thesis if new."""
    
    # 1. Check Limit
    active_count = db.query(GuardianThesis).filter(
        GuardianThesis.user_id == current_user.id,
        GuardianThesis.is_active == True
    ).count()
    
    # Default limit fallback if column missing (migration safety)
    limit = getattr(current_user, 'guardian_limit', 10)
    
    logger.info(f"ENABLE CHECK: User={current_user.email}, Symbol={req.symbol}, Active={active_count}, Limit={limit}")

    # Check if already enabled (doesn't count towards limit)
    existing = db.query(GuardianThesis).filter(
        GuardianThesis.user_id == current_user.id,
        GuardianThesis.symbol == req.symbol
    ).first()
    
    if not existing and active_count >= limit:
         raise HTTPException(
            status_code=400,
            detail=f"Guardian limit reached ({limit} stocks). Disable one to add another."
        )
    elif existing and not existing.is_active and active_count >= limit:
         raise HTTPException(
            status_code=400,
            detail=f"Guardian limit reached ({limit} stocks). Disable one to add another."
        )

    try:
        if existing:
            # Reactivate
            existing.is_active = True
            # Optional: Regenerate if it was auto-generated and old? No, keep history.
            db.commit()
            return {"message": f"Guardian re-enabled for {req.symbol}"}
        
        # New Thesis
        # Auto-generate thesis
        generated_thesis = guardian_agent.generate_thesis_detected(req.symbol)
        
        new_thesis = GuardianThesis(
            user_id=current_user.id,
            symbol=req.symbol,
            thesis=generated_thesis,
            is_active=True,
            auto_generated=True
        )
        db.add(new_thesis)
        db.commit()
        return {"message": f"Guardian enabled for {req.symbol}", "thesis": generated_thesis}

    except Exception as e:
        logger.error(f"Error enabling guardian for {req.symbol}: {e}")
        raise HTTPException(500, "Failed to enable Guardian")

@router.post("/disable/{symbol}")
async def disable_guardian(symbol: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Disable Guardian for a stock."""
    thesis = db.query(GuardianThesis).filter(
        GuardianThesis.user_id == current_user.id,
        GuardianThesis.symbol == symbol
    ).first()
    
    if not thesis:
        raise HTTPException(404, "Thesis not found")
    
    thesis.is_active = False
    db.commit()
    return {"message": f"Guardian disabled for {symbol}"}

@router.put("/theses/{symbol}")
async def update_thesis(symbol: str, req: ThesisUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update manual thesis text."""
    thesis = db.query(GuardianThesis).filter(
        GuardianThesis.user_id == current_user.id,
        GuardianThesis.symbol == symbol
    ).first()
    
    if not thesis:
        raise HTTPException(404, "Thesis not found")
    
    thesis.thesis = req.thesis
    thesis.auto_generated = False # User edited it
    db.commit()
    return {"message": "Thesis updated"}

@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(symbol: Optional[str] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get alert history."""
    query = db.query(GuardianAlert).filter(GuardianAlert.user_id == current_user.id)
    
    if symbol:
        query = query.filter(GuardianAlert.symbol == symbol)
        
    alerts = query.order_by(GuardianAlert.created_at.desc()).limit(50).all()
    
    results = []
    for a in alerts:
        results.append({
            "id": a.id,
            "symbol": a.symbol,
            "thesis_status": a.thesis_status,
            "confidence": a.confidence,
            "reasoning": a.reasoning,
            "created_at": str(a.created_at),
            "is_read": a.is_read
        })
    return results

@router.post("/scan")
async def manual_scan(current_user: User = Depends(get_current_user)):
    """Trigger manual scan (Dev only)."""
    # Import here to avoid circular ref if job imports router (unlikely)
    from jobs.guardian_job import run_guardian_scan
    # Run in background ideally, but for dev sync is fine
    try:
        run_guardian_scan()
        return {"message": "Scan triggered"}
    except Exception as e:
        raise HTTPException(500, str(e))
