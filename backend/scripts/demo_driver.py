import os
import asyncio
import sys
import json
import logging
from unittest.mock import patch
from datetime import datetime

# demo_driver is in backend/scripts/
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)

# Add both to path for maximum compatibility with existing scripts
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Standard imports
# Note: we use 'from models' because database.py does, and we want to share the same module object
from database import SessionLocal, engine
from models import User, GuardianThesis, GuardianAlert, Base
from jobs import guardian_job

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("demo_driver")

DEFAULT_EMAIL = "vinayakmalhotra11111@gmail.com"

async def reset_demo_state(email=DEFAULT_EMAIL):
    """Resets the database for a clean demo."""
    print(f"\n[DEMO] Resetting state for {email}...")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            # Clear old alerts for this user
            db.query(GuardianAlert).filter(GuardianAlert.user_id == user.id).delete()
            # Ensure MSFT thesis exists
            msft_thesis = db.query(GuardianThesis).filter(
                GuardianThesis.user_id == user.id, 
                GuardianThesis.symbol == "MSFT"
            ).first()
            
            if not msft_thesis:
                msft_thesis = GuardianThesis(
                    user_id=user.id,
                    symbol="MSFT",
                    thesis="Microsoft is lead in AI via Azure and Copilot. Enterprise lock-in is the moat.",
                    is_active=True
                )
                db.add(msft_thesis)
            else:
                msft_thesis.is_active = True
                msft_thesis.last_checked_at = None
                msft_thesis.last_price = 420.0 # Set a dummy price
                
            db.commit()
            print("✅ Demo state reset. Ready for Scenario.")
        else:
            print(f"❌ User {email} not found. Please sign in to the app first.")
    finally:
        db.close()

def mock_crisis_events(symbol, last_known_price=None):
    """Scenario: Microsoft facing regulatory and growth headwinds."""
    print(f"\n[DEMO] [MOCK] 🚨 CRISIS DETECTED FOR {symbol}!")
    return {
        "triggered": True,
        "events": [
            "BREAKING: FTC opens wide-ranging antitrust investigation into Microsoft's AI partnership with OpenAI.",
            "Azure growth decelerated to 28% YoY, missing analyst consensus of 32%.",
            "Major security vulnerability discovered in Windows 11 affecting enterprise customers."
        ],
        "current_price": 385.50
    }

async def trigger_scenario(email=DEFAULT_EMAIL, symbol="MSFT"):
    """Triggers the agentic loop for a specific symbol."""
    print(f"\n[DEMO] Triggering AI Guardian Loop for {symbol}...")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"❌ User {email} not found.")
            return

        thesis = db.query(GuardianThesis).filter(
            GuardianThesis.user_id == user.id, 
            GuardianThesis.symbol == symbol
        ).first()
        
        if not thesis:
            print(f"❌ No thesis found for {symbol}. Run reset first.")
            return

        # Double check the 'guardian' attribute on the imported job module
        print(f"[DEMO] Patching guardian.detect_events for the thesis run...")
        
        # We patch 'services.guardian.detect_events' as that's what's typically in sys.modules
        # But to be safe, we patch it where guardian_job sees it.
        with patch.object(guardian_job.guardian, 'detect_events', side_effect=mock_crisis_events):
            await guardian_job.process_thesis(db, thesis)
            
        print(f"\n✅ Scenario Complete. Check your email ({email}) and the Dashboard!")
    except Exception as e:
        print(f"❌ Demo Trigger Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="VinSight Demo Driver")
    parser.add_argument("action", choices=["reset", "trigger"], help="Action to perform")
    parser.add_argument("--email", default=DEFAULT_EMAIL, help="User email")
    
    args = parser.parse_args()
    
    if args.action == "reset":
        asyncio.run(reset_demo_state(args.email))
    else:
        asyncio.run(trigger_scenario(args.email))
