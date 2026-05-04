from sqlalchemy.orm import Session
from database import SessionLocal
from models import GuardianAlert
import logging

logger = logging.getLogger(__name__)

def get_guardian_status(ticker: str) -> str:
    """
    Fetches the latest active GuardianAlert for the given ticker to see if the
    thesis has been affected by external events. (Phase 3: Agent Collaboration)
    
    Returns:
        "BROKEN"  — thesis is fundamentally compromised → conviction capped at 40
        "AT_RISK" — thesis has active concerns → conviction penalty -10
        "INTACT"  — no active alerts
    """
    db: Session = SessionLocal()
    try:
        # Check for BROKEN thesis first (most severe)
        broken_alert = db.query(GuardianAlert).filter(
            GuardianAlert.symbol == ticker,
            GuardianAlert.thesis_status == 'BROKEN',
            GuardianAlert.is_read == False
        ).order_by(GuardianAlert.created_at.desc()).first()
        
        if broken_alert:
            logger.info(f"GuardianClient: Detected BROKEN thesis for {ticker}.")
            return "BROKEN"
        
        # Check for AT_RISK thesis (moderate concern)
        at_risk_alert = db.query(GuardianAlert).filter(
            GuardianAlert.symbol == ticker,
            GuardianAlert.thesis_status == 'AT_RISK',
            GuardianAlert.is_read == False
        ).order_by(GuardianAlert.created_at.desc()).first()
        
        if at_risk_alert:
            logger.info(f"GuardianClient: Detected AT_RISK thesis for {ticker}.")
            return "AT_RISK"
            
        return "INTACT"
    except Exception as e:
        logger.error(f"GuardianClient Error fetching status for {ticker}: {e}")
        return "INTACT"  # Fail safe
    finally:
        db.close()

