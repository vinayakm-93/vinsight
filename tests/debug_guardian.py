import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from models import User, GuardianThesis
from database import SQLALCHEMY_DATABASE_URL
from services import guardian_agent

def debug_guardian():
    url = SQLALCHEMY_DATABASE_URL
    engine = create_engine(url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        users = db.query(User).all()
        print(f"Found {len(users)} users.")
        
        for user in users:
            print(f"\nUser: {user.email} (ID: {user.id})")
            print(f" - Guardian Limit: {user.guardian_limit}")
            
            active_count = db.query(GuardianThesis).filter(
                GuardianThesis.user_id == user.id,
                GuardianThesis.is_active == True
            ).count()
            
            total_count = db.query(GuardianThesis).filter(GuardianThesis.user_id == user.id).count()
            
            print(f" - Active: {active_count}, Total: {total_count}")
            
            if user.guardian_limit and active_count >= user.guardian_limit:
                 print("   ⚠️ LIMIT REACHED")
            else:
                 print("   ✅ Under Limit")

    finally:
        db.close()

    print("\n--- Testing Thesis Generation ---")
    try:
        thesis = guardian_agent.generate_thesis_detected("AAPL")
        print(f"✅ Generated Thesis for AAPL: {thesis}")
    except Exception as e:
        print(f"❌ Failed to generate thesis: {e}")

from services.auth import get_password_hash, verify_password

def create_api_user():
    url = SQLALCHEMY_DATABASE_URL
    engine = create_engine(url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    email = "limit_repro_user@example.com"
    password = "password123"
    
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"Creating user {email}...")
            hashed = get_password_hash(password)
            user = User(email=email, hashed_password=hashed, guardian_limit=10)
            db.add(user)
            db.commit()
            print("✅ User created.")
        else:
            print(f"User {email} already exists.")
            # Verify password
            if verify_password(password, user.hashed_password):
                 print("✅ Password verified correctly in DB.")
            else:
                 print("❌ Password mismatch in DB! Updating...")
                 user.hashed_password = get_password_hash(password)
                 db.commit()
                 print("✅ Password updated.")
            
            # Ensure limit is 10
            if user.guardian_limit != 10:
                user.guardian_limit = 10
                db.commit()
                print("✅ Reset limit to 10.")

    finally:
        db.close()

if __name__ == "__main__":
    create_api_user()
    debug_guardian()
