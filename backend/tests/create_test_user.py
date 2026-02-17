import logging
import sys
import os
from sqlalchemy.orm import Session
from passlib.context import CryptContext

# Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_user")

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import User

from services.auth import get_password_hash

def seed_test_user():
    db = SessionLocal()
    email = "guardian_test@example.com"
    password = "password123"
    
    try:
        # Check if exists
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            logger.info(f"User {email} already exists. Skipping creation.")
            return

        logger.info(f"Creating user {email}...")
        hashed_pw = get_password_hash(password)
        new_user = User(
            email=email,
            hashed_password=hashed_pw,
            investing_goals="Growth",
            guardian_limit=10
        )
        db.add(new_user)
        db.commit()
        logger.info(f"User {email} created successfully.")
        
    except Exception as e:
        logger.error(f"Failed to seed user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_test_user()
