import os
import asyncio
import sys
import json
import logging
from unittest.mock import patch
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine
from models import User, GuardianThesis, GuardianAlert, Base
from jobs.guardian_job import process_thesis
from services import guardian

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_msft_email")

# Test Configuration
TEST_EMAIL = "vinayakmalhotra11111@gmail.com"
TEST_SYMBOL = "MSFT"
TEST_THESIS = "Microsoft is the primary winner in the AI infrastructure and software layer through Azure and Copilot. Key risk is antitrust regulation and cloud margin compression."

async def setup_test_data(db):
    """Ensure a test user and an active MSFT thesis exist."""
    print(f"\n> Setting up test data for {TEST_EMAIL}...")
    
    # 1. Ensure User exists
    user = db.query(User).filter(User.email == TEST_EMAIL).first()
    if not user:
        print(f"Creating new test user: {TEST_EMAIL}")
        # Note: In a real app we'd need a hashed password, but for DB testing this is enough
        user = User(email=TEST_EMAIL, hashed_password="mock_password")
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # 2. Ensure MSFT Thesis exists
    thesis = db.query(GuardianThesis).filter(
        GuardianThesis.user_id == user.id, 
        GuardianThesis.symbol == TEST_SYMBOL
    ).first()
    
    if not thesis:
        print(f"Creating new MSFT thesis for user {user.id}")
        thesis = GuardianThesis(
            user_id=user.id,
            symbol=TEST_SYMBOL,
            thesis=TEST_THESIS,
            is_active=True
        )
        db.add(thesis)
        db.commit()
    else:
        print(f"Using existing MSFT thesis (ID: {thesis.id})")
        thesis.is_active = True
        thesis.thesis = TEST_THESIS
        db.commit()
    
    return user, thesis

def mock_detect_events(symbol, last_known_price=None):
    """Force a trigger for Microsoft."""
    print(f"\n> [MOCK] Forcing a trigger event for {symbol}...")
    return {
        "triggered": True,
        "events": [
            "Microsoft reported a surprise 12% revenue miss in Azure growth.",
            "Reports of a major security breach in Azure Government cloud.",
            "EU regulators announced an intensified antitrust probe into Copilot bundling."
        ],
        "current_price": 405.20
    }

async def run_test():
    """Main test execution."""
    print("\n--- MSFT Local Email Test Execution ---")
    
    # Ensure tables exist (especially if running on a fresh SQLite/Postgres)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        user, thesis = await setup_test_data(db)
        
        # Patch the event detection to force a trigger
        with patch('services.guardian.detect_events', side_effect=mock_detect_events):
            print(f"> Starting Agentic Loop for {TEST_SYMBOL}...")
            await process_thesis(db, thesis)
            
        print("\n> Verification Status:")
        # Check if an alert was actually created
        latest_alert = db.query(GuardianAlert).filter(
            GuardianAlert.user_id == user.id, 
            GuardianAlert.symbol == TEST_SYMBOL
        ).order_by(GuardianAlert.created_at.desc()).first()
        
        if latest_alert:
            print(f"✅ Alert Created! ID: {latest_alert.id}")
            print(f"✅ Status: {latest_alert.thesis_status}")
            print(f"✅ Email Sent: {latest_alert.email_sent}")
            print(f"✅ Reasoning Snippet: {latest_alert.reasoning[:50]}...")
        else:
            print("❌ No alert found in database.")
            
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    # We must be in the backend directory for imports to work as expected if we don't set PYTHONPATH
    asyncio.run(run_test())
