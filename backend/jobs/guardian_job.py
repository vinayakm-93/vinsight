import logging
import asyncio
import os
import json
import time
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
        
        for i, thesis in enumerate(theses):
            await process_thesis(db, thesis)
            # Rate Limiter: 5-second cooldown between theses to avoid hammering LLM/web APIs
            if i < len(theses) - 1:
                logger.info("⏳ Rate limiter: waiting 5 seconds before next thesis...")
                time.sleep(5)
            
    except Exception as e:
        logger.error(f"Guardian job failed: {e}")
    finally:
        db.close()
        logger.info("Guardian Scan Completed.")

async def process_thesis(db: Session, thesis: GuardianThesis, scan_id: str = None):
    symbol = thesis.symbol
    logger.info(f"Checking {symbol} (User ID: {thesis.user_id})...")
    
    try:
        # Stage 1: Event Detection (Fast Filter)
        # For MANUAL scans (scan_id set), bypass the fast filter entirely so the
        # full 3-turn agent always runs regardless of market conditions.
        if scan_id:
            logger.info(f"⚡ Manual scan for {symbol} — bypassing detect_events fast filter.")
            detection = {'triggered': True, 'events': ['Manual scan requested by user'], 'current_price': None}
            # Try to get current price for record update even in bypass mode
            try:
                info = guardian.detect_events(symbol, last_known_price=None)
                if info.get('current_price'):
                    detection['current_price'] = info['current_price']
            except Exception:
                pass
        else:
            detection = guardian.detect_events(symbol, last_known_price=thesis.last_price)
        
        if not detection['triggered']:
            logger.info(f"✅ No significant events for {symbol}. Keeping thesis INTACT.")
            # Update check stats
            thesis.last_checked_at = datetime.utcnow()
            thesis.check_count += 1
            if detection.get('current_price'):
                thesis.last_price = detection['current_price']
            db.commit()
            # Signal the frontend polling loop that this scan finished cleanly
            if scan_id and scan_id in guardian_agent.active_scan_logs:
                guardian_agent.active_scan_logs[scan_id].append({
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    "stage": "COMPLETE",
                    "content": f"No significant market events detected for {symbol}. Thesis remains INTACT. No deep-dive required."
                })
            return

        # Events Detected!
        events = detection['events']
        logger.info(f"⚠️ Events detected for {symbol}: {events}")
        
        # Stage 2: Gather Evidence
        evidence = guardian.gather_evidence(symbol)
        
        # Stage 3: Agent Evaluation
        risk_eval = guardian_agent.evaluate_risk_agentic(symbol, thesis.thesis, events, evidence, scan_id=scan_id)
        
        status = risk_eval.get('thesis_status', 'AT_RISK')
        confidence = risk_eval.get('confidence', 0.0)
        
        logger.info(f"Agent Verdict for {symbol}: {status} (Conf: {confidence})")

        # Stage 4: Act (Save Alert & Notify)
        if status in ['AT_RISK', 'BROKEN'] or (status == 'INTACT' and confidence < 0.7):
            # Create Alert
            # Full reasoning goes to email, capped version goes to DB
            full_reasoning = risk_eval.get('reasoning_full') or risk_eval.get('reasoning', '')
            capped_reasoning = risk_eval.get('reasoning', '')[:100]
            
            alert = GuardianAlert(
                user_id=thesis.user_id,
                symbol=symbol,
                thesis_status=status,
                confidence=confidence,
                reasoning=capped_reasoning,
                recommended_action=risk_eval.get('recommended_action'),
                key_evidence=json.dumps(risk_eval.get('key_evidence', [])),
                events_detected=json.dumps(events),
                research_history=json.dumps(risk_eval.get('research_history', [])),
                thinking_log=json.dumps(risk_eval.get('agent_thinking_log', [])),
                email_sent=False
            )
            db.add(alert)
            db.commit() # Commit to get ID
            
            # Send Email (Skip for manual scans)
            user = db.query(User).filter(User.id == thesis.user_id).first()
            if user and user.email:
                if scan_id:
                    logger.info(f"Skipping email alert for manual scan {scan_id} (symbol: {symbol})")
                else:
                    try:
                        # Pass full reasoning to email (not the DB-capped version)
                        alert.reasoning = full_reasoning  # Temporarily set full for email template
                        await mail.send_guardian_alert_email(user.email, alert)
                        alert.reasoning = capped_reasoning  # Reset to capped for DB
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
