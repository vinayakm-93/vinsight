import logging
import asyncio
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from database import SessionLocal
from models import GuardianThesis, GuardianAlert, User
from services import guardian, guardian_agent, mail
from datetime import datetime

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("guardian_job")

# --- Configuration ---
BATCH_SIZE = 10  # Process 10 stocks concurrently? Or strictly serial for MVP to avoid rate limits?
# Serial is safer for LLM rate limits initially.

async def run_guardian_scan():
    """
    Main entry point for the Cloud Scheduler job.
    """
    logger.info("Starting Portfolio Guardian Scan...")
    db = SessionLocal()
    
    try:
        # 1. Fetch Active Theses
        theses = db.query(GuardianThesis).filter(GuardianThesis.is_active == True).all()
        logger.info(f"Found {len(theses)} active theses to monitor.")
        
        for thesis in theses:
            await process_thesis(db, thesis)
            
    except Exception as e:
        logger.error(f"Guardian job failed: {e}")
    finally:
        db.close()
        logger.info("Guardian Scan Completed.")

async def process_thesis(db: Session, thesis: GuardianThesis):
    symbol = thesis.symbol
    logger.info(f"Checking {symbol} (User ID: {thesis.user_id})...")
    
    try:
        # Stage 1: Event Detection (Fast Filter)
        # Note: detect_events is synchronous heavily CPU bound or I/O? 
        # Ideally should be async if I/O bound, but for now we run it sync.
        detection = guardian.detect_events(symbol, last_known_price=thesis.last_price)
        
        if not detection['triggered']:
            logger.info(f"✅ No significant events for {symbol}. Keeping thesis INTACT.")
            # Update check stats
            thesis.last_checked_at = datetime.utcnow()
            thesis.check_count += 1
            if detection.get('current_price'):
                thesis.last_price = detection['current_price']
            db.commit()
            return

        # Events Detected!
        events = detection['events']
        logger.info(f"⚠️ Events detected for {symbol}: {events}")
        
        # Stage 2: Gather Evidence
        evidence = guardian.gather_evidence(symbol)
        
        # Stage 3: Agent Evaluation
        risk_eval = await guardian_agent.evaluate_risk(symbol, thesis.thesis, events, evidence)
        
        status = risk_eval.get('thesis_status', 'AT_RISK')
        confidence = risk_eval.get('confidence', 0.0)
        
        logger.info(f"Agent Verdict for {symbol}: {status} (Conf: {confidence})")

        # Stage 4: Act (Save Alert & Notify)
        if status in ['AT_RISK', 'BROKEN'] or (status == 'INTACT' and confidence < 0.7):
            # Create Alert
            alert = GuardianAlert(
                user_id=thesis.user_id,
                symbol=symbol,
                thesis_status=status,
                confidence=confidence,
                reasoning=risk_eval.get('reasoning'),
                recommended_action=risk_eval.get('recommended_action'),
                key_evidence=str(risk_eval.get('key_evidence')), # Store as string for now or JSON
                events_detected=str(events),
                email_sent=False
            )
            db.add(alert)
            db.commit() # Commit to get ID
            
            # Send Email
            user = db.query(User).filter(User.id == thesis.user_id).first()
            if user and user.email:
                # We'll implement send_guardian_alert_email in mail.py next
                try:
                    await mail.send_guardian_alert_email(user.email, alert)
                    alert.email_sent = True
                    db.commit()
                    logger.info(f"Generated alert {alert.id} for user {user.email}")
                except Exception as e:
                    logger.error(f"Failed to send email: {e}")
            
        # Update Thesis State
        thesis.last_checked_at = datetime.utcnow()
        thesis.check_count += 1
        if detection.get('current_price'):
            thesis.last_price = detection['current_price']
        db.commit()

    except Exception as e:
        logger.error(f"Error processing {symbol}: {e}")
        db.rollback()

if __name__ == "__main__":
    asyncio.run(run_guardian_scan())
