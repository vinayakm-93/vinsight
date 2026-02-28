from sqlalchemy.orm import Session
from database import SessionLocal
from models import GuardianAlert
import logging

logger = logging.getLogger(__name__)

def get_guardian_status(ticker: str) -> str:
    """
    Fetches the latest active GuardianAlert for the given ticker to see if the
    thesis has been broken by external events. (Phase 3: Agent Collaboration)
    
    Returns "BROKEN" if a severe alert exists, otherwise returns "INTACT".
    """
    db: Session = SessionLocal()
    try:
        # We query for any unread, active BROKEN alert globally for this ticker
        # This provides the ReasoningScorer with objective context that a thesis
        # has been fundamentally compromised somewhere in the system.
        broken_alert = db.query(GuardianAlert).filter(
            GuardianAlert.symbol == ticker,
            GuardianAlert.thesis_status == 'BROKEN',
            GuardianAlert.is_read == False
        ).order_by(GuardianAlert.created_at.desc()).first()
        
        if broken_alert:
            logger.info(f"GuardianClient: Detected BROKEN thesis for {ticker}.")
            return "BROKEN"
            
        return "INTACT"
    except Exception as e:
        logger.error(f"GuardianClient Error fetching status for {ticker}: {e}")
        return "INTACT" # Fail safe
    finally:
        db.close()
