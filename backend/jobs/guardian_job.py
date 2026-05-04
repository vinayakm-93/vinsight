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
    logger.info("Starting Portfolio Guardian Scan with Async Batching...")
    # 1. Fetch Active Theses IDs
    db = SessionLocal()
    try:
        theses = db.query(GuardianThesis).filter(GuardianThesis.is_active == True).all()
        logger.info(f"Found {len(theses)} active theses to monitor.")
        
        # We only pass IDs to threads so each thread can open its own DB session (Thread-safe)
        thesis_tasks = [{"id": t.id, "scan_id": None} for t in theses]
    finally:
        db.close()
        
    if not thesis_tasks:
        logger.info("Guardian Scan Completed. No active theses.")
        return

    # 2. Async Filter Batching
    # We use ThreadPoolExecutor because detect_events blocks on yfinance/network calls
    from concurrent.futures import ThreadPoolExecutor
    loop = asyncio.get_event_loop()
    
    # Process 5 concurrent requests at a time to stay under Yahoo/Finnhub rate limits
    with ThreadPoolExecutor(max_workers=5) as pool:
        tasks = [
            loop.run_in_executor(pool, process_thesis_sync, task["id"], task["scan_id"]) 
            for task in thesis_tasks
        ]
        # Wait for all to finish
        await asyncio.gather(*tasks, return_exceptions=True)
        
    logger.info("Guardian Scan Completed.")


def process_thesis_sync(thesis_id: int, scan_id: str = None):
    """
    Synchronous wrapper for processing a single thesis in an isolated thread.
    Opens and closes a fresh DB session avoiding SQLite locked errors.
    """
    # Create thread-local session
    db = SessionLocal()
    import hashlib
    
    try:
        thesis = db.query(GuardianThesis).get(thesis_id)
        if not thesis:
            return
            
        symbol = thesis.symbol
        logger.info(f"Checking {symbol} (User ID: {thesis.user_id})...")
        
        # Stage 1: Event Detection (Fast Filter)
        if scan_id:
            logger.info(f"⚡ Manual scan for {symbol} — bypassing detect_events fast filter.")
            detection = {'triggered': True, 'events': ['Manual scan requested by user'], 'event_keys': ['manual_scan'], 'current_price': None}
            try:
                info = guardian.detect_events(symbol, last_known_price=None)
                if info.get('current_price'):
                    detection['current_price'] = info['current_price']
            except Exception:
                pass
        else:
            detection = guardian.detect_events(symbol, last_known_price=thesis.last_price)
        
        # If no events triggered, update heartbeat and bail
        if not detection.get('triggered', False):
            logger.info(f"✅ No significant events for {symbol}. Keeping thesis INTACT.")
            thesis.last_checked_at = datetime.utcnow()
            thesis.check_count += 1
            if detection.get('current_price'):
                thesis.last_price = detection['current_price']
            db.commit()
            
            if scan_id and scan_id in guardian_agent.active_scan_logs:
                guardian_agent.active_scan_logs[scan_id].append({
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    "stage": "COMPLETE",
                    "content": f"No significant market events detected for {symbol}. Thesis remains INTACT."
                })
            return

        # --- STATEFULNESS EVENT DEDUPLICATION ---
        events = detection.get('events', [])
        event_keys = detection.get('event_keys', [])
        
        # Create deterministic signature of current event categories
        if event_keys:
            event_keys.sort()
        current_state_signature = hashlib.md5(json.dumps(event_keys).encode()).hexdigest()
        
        if not scan_id and thesis.last_trigger_state == current_state_signature and event_keys:
            logger.info(f"✅ Deduplication: Events for {symbol} ({event_keys}) identical to last run. Suppressing redundant LLM evaluation.")
            thesis.last_checked_at = datetime.utcnow()
            thesis.check_count += 1
            if detection.get('current_price'):
                thesis.last_price = detection['current_price']
            db.commit()
            return
            
        logger.info(f"⚠️ NEW Events detected for {symbol}: {events}")
        
        # Stage 2: Gather Evidence
        evidence = guardian.gather_evidence(symbol)
        
        # Stage 3: Agent Evaluation
        try:
            risk_eval = guardian_agent.evaluate_risk_agentic(symbol, thesis.thesis, events, evidence, scan_id=scan_id)
        except Exception as e:
            # RATE LIMIT SAFETY NET
            if "429" in str(e) or "quota" in str(e).lower():
                logger.warning(f"🚨 LLM Rate Limit Hit for {symbol}. Moving to delayed retry, skipped alert.")
                return
            logger.error(f"Error during agentic evaluation for {symbol}: {e}")
            risk_eval = {"thesis_status": "AT_RISK", "confidence": 0.0, "reasoning": f"AI evaluation failed: {e}", "recommended_action": "HOLD"}
        
        status = risk_eval.get('thesis_status', 'AT_RISK')
        confidence = risk_eval.get('confidence', 0.0)
        
        logger.info(f"Agent Verdict for {symbol}: {status} (Conf: {confidence})")

        # Stage 4: Act (Save Alert & Notify)
        if status in ['AT_RISK', 'BROKEN'] or (status == 'INTACT' and confidence < 0.7):
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
                        # Required to send email via sync blocking thread (create a mini event loop if mail is async)
                        import asyncio as sync_asyncio
                        
                        async def send_mail():
                            alert.reasoning = full_reasoning
                            await mail.send_guardian_alert_email(user.email, alert)
                            alert.reasoning = capped_reasoning
                            alert.email_sent = True
                            
                        sync_asyncio.run(send_mail())
                        db.commit()
                        logger.info(f"Generated alert {alert.id} for user {user.email}")
                    except Exception as e:
                        logger.error(f"Failed to send email: {e}")
            
        # Success - update trigger state to prevent duplicate reporting tomorrow
        thesis.last_trigger_state = current_state_signature
        thesis.last_checked_at = datetime.utcnow()
        thesis.check_count += 1
        if detection.get('current_price'):
            thesis.last_price = detection['current_price']
        db.commit()

    except Exception as e:
        logger.error(f"Error processing {symbol} (ID: {thesis_id}): {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_guardian_scan())
