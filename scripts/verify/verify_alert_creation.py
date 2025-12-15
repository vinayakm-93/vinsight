import sys
import os

# Add the current directory to sys.path so we can import backend modules
sys.path.append(os.getcwd())

from backend.database import SessionLocal
from backend.models import Alert, User
from backend.services import auth

def verify_db_storage():
    db = SessionLocal()
    try:
        # 1. Get or Create a Test User
        user = db.query(User).filter(User.email == "test_alert_user@example.com").first()
        if not user:
            print("Creating test user...")
            user = User(
                email="test_alert_user@example.com",
                hashed_password=auth.get_password_hash("password123"),
                investing_goals="Testing"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        print(f"Using user: {user.email} (ID: {user.id})")

        # 2. Clear existing alerts for this user
        db.query(Alert).filter(Alert.user_id == user.id).delete()
        db.commit()

        # 3. Create 'above' alert
        alert_above = Alert(
            user_id=user.id,
            symbol="API_TEST_ABOVE",
            target_price=100.0,
            condition="above"
        )
        db.add(alert_above)
        
        # 4. Create 'below' alert
        alert_below = Alert(
            user_id=user.id,
            symbol="API_TEST_BELOW",
            target_price=50.0,
            condition="below"
        )
        db.add(alert_below)
        
        db.commit()
        
        # 5. Verify Retrieval
        saved_above = db.query(Alert).filter(Alert.symbol == "API_TEST_ABOVE", Alert.user_id == user.id).first()
        saved_below = db.query(Alert).filter(Alert.symbol == "API_TEST_BELOW", Alert.user_id == user.id).first()
        
        if not saved_above:
            print("FAILED: API_TEST_ABOVE not found in DB")
            exit(1)
        
        if not saved_below:
             print("FAILED: API_TEST_BELOW not found in DB")
             exit(1)
             
        print(f"Verified ABOVE alert: {saved_above.symbol}, Condition: {saved_above.condition}")
        print(f"Verified BELOW alert: {saved_below.symbol}, Condition: {saved_below.condition}")
        
        assert saved_above.condition == "above"
        assert saved_below.condition == "below"
        
        print("SUCCESS: Both conditions correctly recorded in DB.")

    except Exception as e:
        print(f"Verification Failed: {e}")
        exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    verify_db_storage()
