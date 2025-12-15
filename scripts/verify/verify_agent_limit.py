import sys
import os
import asyncio
from datetime import datetime

# Add the current directory to sys.path
sys.path.append(os.getcwd())

from backend.database import SessionLocal
from backend.models import Alert, User
from backend.services import alert_checker

async def verify_agent_logic():
    db = SessionLocal()
    try:
        # 1. Setup User with Low Limit
        user = db.query(User).filter(User.email == "limit_test@example.com").first()
        if not user:
            from backend.services import auth
            user = User(
                email="limit_test@example.com",
                hashed_password=auth.get_password_hash("pass"),
                alert_limit=1,
                alerts_triggered_this_month=0
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            user.alert_limit = 1
            user.alerts_triggered_this_month = 0
            db.commit()
            
        print(f"Test User: {user.email} Limit: {user.alert_limit} Used: {user.alerts_triggered_this_month}")

        # 2. Create 2 Alerts that SHOULD trigger (e.g. Price > 0)
        # Clear old
        db.query(Alert).filter(Alert.user_id == user.id).delete()
        
        a1 = Alert(user_id=user.id, symbol="AAPL", target_price=0.01, condition="above", is_triggered=False)
        a2 = Alert(user_id=user.id, symbol="TSLA", target_price=0.01, condition="above", is_triggered=False)
        db.add_all([a1, a2])
        db.commit()
        
        print("Created 2 alerts with target > 0.01 (Should trigger)")

        # 3. Run Checker
        # We manually invoke the checker function (imitating the scheduler)
        # Note: We need MOCK_MODE for email to avoid spam or error if creds invalid
        os.environ["MAIL_USERNAME"] = "MOCK" # Force mock
        
        await alert_checker.check_alerts(db)
        
        # 4. Operations Check
        db.refresh(user)
        a1 = db.query(Alert).filter(Alert.symbol=="AAPL", Alert.user_id==user.id).first()
        a2 = db.query(Alert).filter(Alert.symbol=="TSLA", Alert.user_id==user.id).first()
        
        print(f"Results:")
        print(f"User Usage: {user.alerts_triggered_this_month}/{user.alert_limit}")
        print(f"Alert 1 (AAPL) Triggered? {a1.is_triggered}")
        print(f"Alert 2 (TSLA) Triggered? {a2.is_triggered}")
        
        # Logic: Usage should be 1. One alert triggered, one skipped/remaining active.
        if user.alerts_triggered_this_month == 1:
            print("SUCCESS: Usage incremented correctly.")
        else:
            print("FAILED: Usage count mismatch.")

        if (a1.is_triggered and not a2.is_triggered) or (a2.is_triggered and not a1.is_triggered):
             print("SUCCESS: Limit enforced. Only 1 alert triggered.")
        else:
             print("FAILED: Both triggered or None triggered despite 1 limit.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(verify_agent_logic())
