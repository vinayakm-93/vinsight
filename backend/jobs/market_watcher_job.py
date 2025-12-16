import asyncio
import sys
import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

# Add parent directory to path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from database import SessionLocal
from services import alert_checker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("market_watcher_job")

def is_market_open():
    """Checks if US Stock Market is open (9:30 AM - 4:00 PM ET, Mon-Fri)."""
    # Use generic weekday checks for simplicity; could use holidays lib later
    try:
        et_tz = ZoneInfo("America/New_York")
        now = datetime.now(et_tz)
    except Exception:
        # Fallback if zoneinfo resource missing (though standard in 3.9+)
        now = datetime.now()
        logger.warning("Could not load America/New_York timezone, using local time.")

    # 1. Check Weekend
    if now.weekday() >= 5: # 5=Sat, 6=Sun
        return False
        
    # 2. Check Time (09:30 - 16:00)
    # We allow a small buffer just in case
    start_hour, start_minute = 9, 30
    end_hour, end_minute = 16, 0 
    
    current_minutes = now.hour * 60 + now.minute
    start_minutes = start_hour * 60 + start_minute
    end_minutes = end_hour * 60 + end_minute
    
    return start_minutes <= current_minutes <= end_minutes

async def run_job():
    logger.info("Starting Market Watcher Job...")

    if not is_market_open():
        logger.info("Market is CLOSED. Skipping checks.")
        return
    
    db = SessionLocal()
    try:
        # Check alerts (prices, sentiment, etc.)
        await alert_checker.check_alerts(db)
        logger.info("Market Watcher Job Completed Successfully.")
    except Exception as e:
        logger.error(f"Error in Market Watcher Job: {e}")
        # We generally don't want to crash the job container on logic error to avoid rapid retries if configured
        # But for Cloud Run Jobs, exit 1 allows retry policies.
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_job())
