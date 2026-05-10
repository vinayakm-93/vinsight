
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from database import SessionLocal
from models import User, Watchlist
from services import auth

def create_test_user():
    db = SessionLocal()
    try:
        email = "test@example.com"
        password = "password123"
        
        # Check if user exists
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"User {email} already exists.")
            return

        # Create user
        hashed_pw = auth.get_password_hash(password)
        new_user = User(
            email=email,
            hashed_password=hashed_pw
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Create default watchlist
        wl = Watchlist(
            name="My First List",
            user_id=new_user.id,
            stocks="AAPL,NVDA,GOOGL,MSFT,TSLA"
        )
        db.add(wl)
        db.commit()
        print(f"Created test user: {email} / {password}")
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user()
