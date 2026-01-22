from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import logging

from database import get_db
from models import Alert, User
from services import auth
from services import finance
from services import alert_checker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

@router.post("/check")
async def trigger_check(db: Session = Depends(get_db), user: User = Depends(auth.get_current_user)):
    """Manually trigger alert check (authenticated users only)"""
    await alert_checker.check_alerts(db)
    return {"status": "checked"}

class AlertCreate(BaseModel):
    symbol: str
    target_price: float
    condition: str # "above" or "below"

class AlertOut(BaseModel):
    id: int
    symbol: str
    target_price: float
    condition: str
    is_triggered: bool
    created_at: datetime
    current_price: Optional[float] = None

    class Config:
        from_attributes = True

@router.get("/", response_model=List[AlertOut])
def get_alerts(db: Session = Depends(get_db), user: User = Depends(auth.get_current_user)):
    alerts = db.query(Alert).filter(Alert.user_id == user.id).all()
    results = []
    # Optionally fetch current prices to show progress?
    # For speed, maybe just return alert config. Or fetch current price for each.
    for alert in alerts:
        # Check current price logic could go here or in a separate "status" call
        try:
            info = finance.get_stock_info(alert.symbol)
            # Use fast info or fallback
            price = info.get('currentPrice') or info.get('regularMarketPrice')
        except:
            price = None
            
        results.append(AlertOut(
            id=alert.id,
            symbol=alert.symbol,
            target_price=alert.target_price,
            condition=alert.condition,
            is_triggered=alert.is_triggered,
            created_at=alert.created_at,
            current_price=price
        ))
    return results

@router.post("/", response_model=AlertOut)
def create_alert(alert: AlertCreate, db: Session = Depends(get_db), user: User = Depends(auth.get_current_user)):
    logger.info(f"Creating alert for user {user.id}: {alert.symbol} {alert.condition} {alert.target_price}")
    try:
        # 1. Lazy Reset Monthly Limit
        now = datetime.utcnow()
        # Default last_alert_reset if None (migration safe)
        if not user.last_alert_reset:
            user.last_alert_reset = now
        
        if user.last_alert_reset.month != now.month or user.last_alert_reset.year != now.year:
            logger.info(f"Resetting alert count for user {user.id}")
            user.alerts_triggered_this_month = 0
            user.last_alert_reset = now
            db.commit() # Save reset state

        # 2. Limit Checks
        # 2a. Check Monthly Trigger Limit (prevent creating new alerts if limit reached)
        if user.alerts_triggered_this_month >= user.alert_limit:
            raise HTTPException(
                status_code=400, 
                detail=f"Monthly alert limit reached ({user.alerts_triggered_this_month}/{user.alert_limit}). Alerts will reset next month."
            )
        
        # 2b. Check Active Alerts Count
        active_count = db.query(Alert).filter(Alert.user_id == user.id).count()
        if active_count >= 50:
             raise HTTPException(status_code=400, detail="Maximum 50 active alerts allowed.")
             
        # 3. Validate Symbol
        try:
            info = finance.get_stock_info(alert.symbol)
            if not info:
                 print(f"Warning: Info not found for {alert.symbol}, but proceeding.")
        except Exception as e:
            logger.warning(f"Validation warning for {alert.symbol}: {e}")

        db_alert = Alert(
            user_id=user.id,
            symbol=alert.symbol.upper(),
            target_price=alert.target_price,
            condition=alert.condition,
            is_triggered=False
        )
        db.add(db_alert)
        db.commit()
        db.refresh(db_alert)
        
        logger.info(f"Created alert {db_alert.id} for user {user.id}")
        
        return AlertOut(
            id=db_alert.id,
            symbol=db_alert.symbol,
            target_price=db_alert.target_price,
            condition=db_alert.condition,
            is_triggered=db_alert.is_triggered,
            created_at=db_alert.created_at,
            current_price=None 
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception(f"Error creating alert")
        raise HTTPException(status_code=500, detail="Failed to create alert. Please try again.")

@router.delete("/{alert_id}")
def delete_alert(alert_id: int, db: Session = Depends(get_db), user: User = Depends(auth.get_current_user)):
    alert = db.query(Alert).filter(Alert.id == alert_id, Alert.user_id == user.id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    db.delete(alert)
    db.commit()
    return {"status": "success"}
