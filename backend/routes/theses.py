from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import json

from database import get_db
from models import User, UserGoal, InvestmentThesis, GuardianThesis
from services import auth, guardian_agent

router = APIRouter(prefix="/api/theses", tags=["theses"])

class ThesisOut(BaseModel):
    id: int
    symbol: str
    stance: Optional[str]
    one_liner: Optional[str]
    key_drivers: Optional[str]
    primary_risk: Optional[str]
    confidence_score: Optional[float]
    content: Optional[str]
    sources: Optional[str]
    agent_log: Optional[str]
    is_edited: bool
    is_monitoring: bool = False
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ThesisUpdate(BaseModel):
    stance: Optional[str]
    content: Optional[str]
    one_liner: Optional[str]

class QuotaOut(BaseModel):
    thesis_limit: int
    theses_generated_this_month: int

class GenerateRequest(BaseModel):
    symbol: str

@router.get("", response_model=List[ThesisOut])
def get_theses(
    stance: Optional[str] = None,
    symbol: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(auth.get_current_user)
):
    query = db.query(InvestmentThesis).filter(InvestmentThesis.user_id == user.id)
    if stance:
        query = query.filter(InvestmentThesis.stance == stance)
    if symbol:
        query = query.filter(InvestmentThesis.symbol == symbol.upper())
    theses = query.order_by(InvestmentThesis.created_at.desc()).all()
    
    # 2. Get active monitoring symbols (The source of truth for "monitored")
    guardian_theses = db.query(GuardianThesis).filter(
        GuardianThesis.user_id == user.id,
        GuardianThesis.is_active == True
    ).all()
    guardian_map = {gt.symbol.upper(): gt for gt in guardian_theses}
    active_symbols = set(guardian_map.keys())
    
    # 3. Handle Sync (Identify orphans: Monitored in Agent but missing from Hub)
    # Check against ALL theses for this user, regardless of current stance filter
    all_existing = db.query(InvestmentThesis.symbol).filter(InvestmentThesis.user_id == user.id).all()
    all_existing_symbols = {s[0].upper() for s in all_existing}
    orphans = active_symbols - all_existing_symbols
    
    if orphans: # Auto-repair regardless of what is driving the current view constraint to ensure data consistency
        for sym in orphans:
            gt = guardian_map[sym]
            new_it = InvestmentThesis(
                user_id=user.id,
                symbol=sym.upper(),
                stance='NEUTRAL',
                one_liner=gt.thesis or f"Monitoring {sym.upper()}",
                content=f"# Auto-generated research for {sym.upper()}\n\nCurrently being monitored by Thesis Agent.",
                key_drivers=json.dumps([]),
                primary_risk="Market volatility",
                confidence_score=5.0,
                sources=json.dumps([]),
                agent_log="Auto-synced from Guardian monitoring state"
            )
            db.add(new_it)
        db.commit()
        # Re-fetch to include orphans in the correct order matching the original request
        theses = query.order_by(InvestmentThesis.created_at.desc()).all()
    
    # Enrich with monitoring status
    for t in theses:
        t.is_monitoring = t.symbol.upper() in active_symbols
        
    return theses

@router.get("/quota", response_model=QuotaOut)
def get_quota(user: User = Depends(auth.get_current_user)):
    return {
        "thesis_limit": user.thesis_limit or 10,
        "theses_generated_this_month": user.theses_generated_this_month or 0
    }

@router.get("/{symbol}", response_model=ThesisOut)
def get_thesis_by_symbol(
    symbol: str, 
    db: Session = Depends(get_db),
    user: User = Depends(auth.get_current_user)
):
    thesis = db.query(InvestmentThesis).filter(
        InvestmentThesis.user_id == user.id,
        InvestmentThesis.symbol == symbol.upper()
    ).order_by(InvestmentThesis.created_at.desc()).first()
    
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
        
    guardian = db.query(GuardianThesis).filter(
        GuardianThesis.user_id == user.id,
        GuardianThesis.symbol == symbol.upper(),
        GuardianThesis.is_active == True
    ).first()
    thesis.is_monitoring = guardian is not None
    
    return thesis

@router.delete("/{thesis_id}")
def delete_thesis(
    thesis_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(auth.get_current_user)
):
    thesis = db.query(InvestmentThesis).filter(
        InvestmentThesis.id == thesis_id,
        InvestmentThesis.user_id == user.id
    ).first()
    
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    # Phase 5 Bidirectional Sync: Also disable Guardian monitoring
    guardian = db.query(GuardianThesis).filter(
        GuardianThesis.user_id == user.id,
        GuardianThesis.symbol == thesis.symbol.upper()
    ).first()
    if guardian:
        guardian.is_active = False
    
    db.delete(thesis)
    db.commit()
    return {"status": "deleted"}

@router.put("/{thesis_id}", response_model=ThesisOut)
def update_thesis(
    thesis_id: int,
    update_data: ThesisUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(auth.get_current_user)
):
    thesis = db.query(InvestmentThesis).filter(
        InvestmentThesis.id == thesis_id,
        InvestmentThesis.user_id == user.id
    ).first()
    
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
        
    if update_data.stance is not None:
        thesis.stance = update_data.stance
    if update_data.content is not None:
        thesis.content = update_data.content
    if update_data.one_liner is not None:
        thesis.one_liner = update_data.one_liner
        
    thesis.is_edited = True
    db.commit()
    db.refresh(thesis)
    return thesis

@router.post("/generate", response_model=ThesisOut)
def generate_thesis(
    req: GenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(auth.get_current_user)
):
    return _perform_generation(req.symbol, db, user)

@router.post("/generate/{symbol}", response_model=ThesisOut)
def generate_thesis_by_path(
    symbol: str,
    db: Session = Depends(get_db),
    user: User = Depends(auth.get_current_user)
):
    return _perform_generation(symbol, db, user)

def _perform_generation(symbol: str, db: Session, user: User):
    # 1. Check quotas
    limit = user.thesis_limit or 10
    generated = user.theses_generated_this_month or 0
    
    if generated >= limit:
        raise HTTPException(status_code=403, detail="Thesis generation limit reached for this month.")
        
    # Extract user profile
    goals = db.query(UserGoal).filter(UserGoal.user_id == user.id).all()
    goal_list = []
    for g in goals:
        goal_list.append({
            "name": g.name,
            "target_amount": g.target_amount,
            "target_date": g.target_date.isoformat() if g.target_date else "N/A",
            "priority": g.priority
        })
    user_profile = {
        "risk_appetite": user.risk_appetite,
        "monthly_budget": user.monthly_budget,
        "investment_experience": user.investment_experience,
        "goals": goal_list
    }
        
    # Connect to explicit agent layer
    thesis_data = guardian_agent.generate_investment_thesis(symbol, user_profile)
    
    new_thesis = InvestmentThesis(
        user_id=user.id,
        symbol=symbol.upper(),
        stance=thesis_data.get('stance', 'NEUTRAL'),
        one_liner=thesis_data.get('one_liner', f"Preliminary analysis for {symbol.upper()}"),
        key_drivers=json.dumps(thesis_data.get('key_drivers', [])),
        primary_risk=thesis_data.get('primary_risk', 'Market volatility'),
        confidence_score=thesis_data.get('confidence_score', 5.0),
        content=thesis_data.get('content', f"# Auto-generated thesis for {symbol.upper()}\\n\\nGathering data..."),
        sources=json.dumps([]),
        agent_log="Generated via Guardian Agent Sync"
    )
    db.add(new_thesis)
    
    # Phase 5 Bidirectional Sync: Also enable Guardian monitoring
    guardian = db.query(GuardianThesis).filter(
        GuardianThesis.user_id == user.id,
        GuardianThesis.symbol == symbol.upper()
    ).first()
    
    guardian_summary = thesis_data.get('one_liner', f"Monitoring {symbol.upper()}")
    if guardian:
        guardian.is_active = True
        guardian.thesis = guardian_summary
    else:
        new_guardian = GuardianThesis(
            user_id=user.id,
            symbol=symbol.upper(),
            thesis=guardian_summary,
            is_active=True,
            auto_generated=True
        )
        db.add(new_guardian)

    user.theses_generated_this_month = generated + 1
    
    db.commit()
    db.refresh(new_thesis)
    return new_thesis
