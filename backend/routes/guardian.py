from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from database import get_db
from models import User, GuardianThesis, GuardianAlert, InvestmentThesis
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
    
    active_symbols = [t.symbol for t in theses if t.is_active]
    
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
            "thesis": t.thesis or "",
            "is_active": bool(t.is_active),
            "status": status,
            "last_checked_at": str(t.last_checked_at) if t.last_checked_at else None,
            "check_count": t.check_count or 0,
            "auto_generated": bool(t.auto_generated)
        })
    return results

@router.post("/enable")
async def enable_guardian(req: ThesisCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Enable Guardian for a stock. Auto-generates thesis if new."""
    
    # 1. Check Limit
    active_theses = db.query(GuardianThesis).filter(
        GuardianThesis.user_id == current_user.id,
        GuardianThesis.is_active == True
    ).all()
    active_count = len(active_theses)
    active_symbols = [t.symbol for t in active_theses]
    
    # Default limit fallback if column missing (migration safety)
    limit = getattr(current_user, 'guardian_limit', 10)
    
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
        guardian_summary = f"Monitoring {req.symbol}"
        if existing:
            existing.is_active = True
        else:
            # Auto-generate full deep-dive thesis
            thesis_data = guardian_agent.generate_investment_thesis(req.symbol)
            guardian_summary = thesis_data.get('one_liner', guardian_summary)
            
            new_guardian_thesis = GuardianThesis(
                user_id=current_user.id,
                symbol=req.symbol,
                thesis=guardian_summary,
                is_active=True,
                auto_generated=True
            )
            db.add(new_guardian_thesis)
            existing = new_guardian_thesis
            
        # Phase 5 Bidirectional Sync: Also check if it exists in the new Thesis Library
        inv_thesis = db.query(InvestmentThesis).filter(
            InvestmentThesis.user_id == current_user.id,
            InvestmentThesis.symbol == req.symbol.upper()
        ).first()

        if not inv_thesis:
            # Only generate if we didn't already
            if not locals().get('thesis_data'):
                thesis_data = guardian_agent.generate_investment_thesis(req.symbol)
                guardian_summary = thesis_data.get('one_liner', guardian_summary)
                existing.thesis = guardian_summary
                
            import json
            new_investment_thesis = InvestmentThesis(
                user_id=current_user.id,
                symbol=req.symbol.upper(),
                stance=thesis_data.get('stance', 'NEUTRAL'),
                one_liner=guardian_summary,
                key_drivers=json.dumps(thesis_data.get('key_drivers', [])),
                primary_risk=thesis_data.get('primary_risk', 'Market volatility'),
                confidence_score=thesis_data.get('confidence_score', 5.0),
                content=thesis_data.get('content', f"# Auto-generated thesis for {req.symbol.upper()}"),
                sources=json.dumps([]),
                agent_log="Generated via Guardian Agent Sync"
            )
            db.add(new_investment_thesis)
            
        db.commit()
        return {"message": f"Guardian enabled for {req.symbol}", "thesis": guardian_summary}

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
    
    # Phase 5 Bidirectional Sync: We NO LONGER delete from library here.
    # Disabling monitoring should NOT destroy the research.
    # The user can delete from Library explicitly if they want it gone.
        
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
            "is_read": bool(a.is_read)
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

@router.post("/scan/{symbol}", status_code=status.HTTP_202_ACCEPTED)
async def manual_scan_symbol(
    symbol: str, 
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Trigger a manual scan for a specific stock as an async background task."""
    from datetime import datetime, timedelta
    
    thesis = db.query(GuardianThesis).filter(
        GuardianThesis.user_id == current_user.id,
        GuardianThesis.symbol == symbol.upper()
    ).first()
    
    if not thesis or not thesis.is_active:
        raise HTTPException(400, "Thesis Agent is not active for this stock.")
        
    # Check rate limit (1 per day)
    if thesis.last_manual_scan_at:
        time_since_last = datetime.utcnow() - thesis.last_manual_scan_at
        if time_since_last < timedelta(days=1):
            next_allowed = thesis.last_manual_scan_at + timedelta(days=1)
            time_left = next_allowed - datetime.utcnow()
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            raise HTTPException(429, f"Manual scan limit reached. Cannot scan {symbol} again for {hours}h {minutes}m.")
            
    # Import and run the actual logic
    from jobs.guardian_job import process_thesis
    from database import SessionLocal
    import asyncio
    
    # Unique ID for linking frontend polling to the ephemeral log cache
    scan_id = f"{current_user.id}_{symbol.upper()}"
    
    # Initialize the log cache
    guardian_agent.active_scan_logs[scan_id] = [{"timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), "stage": "INIT", "content": f"Initializing background scan for {symbol.upper()}..."}]
    
    # Sync wrapper to run inside the BackgroundTasks threadpool
    def run_background_scan(thesis_id: int):
        # We must create a new isolated DB session for the background thread
        bg_db = SessionLocal()
        try:
            # Re-fetch the thesis object securely within the new session
            bg_thesis = bg_db.query(GuardianThesis).filter(GuardianThesis.id == thesis_id).first()
            if not bg_thesis:
                logger.error(f"Background thesis ID {thesis_id} not found.")
                return
                
            logger.info(f"Background executing process_thesis for {scan_id}")
            # process_thesis is async, so we use asyncio.run inside the sync wrapper!
            asyncio.run(process_thesis(bg_db, bg_thesis, scan_id=scan_id))
            
            # Update last scan time
            bg_thesis.last_manual_scan_at = datetime.utcnow()
            bg_db.commit()
            
            # Append completion marker
            guardian_agent.active_scan_logs[scan_id].append({
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "stage": "COMPLETE", 
                "content": "Scan completed."
            })
            
        except Exception as e:
            logger.error(f"Background Manual scan failed for {scan_id}: {e}")
            guardian_agent.active_scan_logs[scan_id].append({
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "stage": "ERROR", 
                "content": f"Scan failed: {str(e)}"
            })
        finally:
            bg_db.close()

    # Dispatch to background
    thesis_id = thesis.id
    background_tasks.add_task(run_background_scan, thesis_id)
    
    return {
        "message": f"Scan started in the background for {symbol}",
        "scan_id": scan_id
    }

@router.get("/scan/{symbol}/status")
async def get_scan_status(symbol: str, current_user: User = Depends(get_current_user)):
    """
    Poll the ephemeral in-memory log for the current background scan of {symbol}.
    Once the scan is complete, the log is returned AND cleared from memory.
    Design: Ephemeral — the trace lives only in RAM and is destroyed after this final fetch.
    Only GuardianAlerts are persisted to the DB.
    """
    scan_id = f"{current_user.id}_{symbol.upper()}"
    
    log_entries = guardian_agent.active_scan_logs.get(scan_id)
    
    if log_entries is None:
        # No scan is in progress or log was already cleared
        return {"status": "NOT_FOUND", "log": [], "scan_id": scan_id}
    
    # Check if the scan has completed or errored
    is_finished = any(e["stage"] in ("COMPLETE", "ERROR") for e in log_entries)
    
    if is_finished:
        # Ephemeral cleanup: return the full trace then evict from memory
        final_log = list(log_entries)
        del guardian_agent.active_scan_logs[scan_id]
        logger.info(f"Ephemeral scan log for {scan_id} delivered and cleared.")
        return {"status": "COMPLETED", "log": final_log, "scan_id": scan_id}
    
    # Scan still running — return current trace snapshot (do NOT delete yet)
    return {"status": "RUNNING", "log": list(log_entries), "scan_id": scan_id}
