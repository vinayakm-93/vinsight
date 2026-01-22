import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from sqlalchemy.orm import Session
from backend.database import SessionLocal, get_db
from backend.models import User, Watchlist
from backend.services import auth

def test():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "vinayak.malhotra20@gmail.com").first()
        if not user:
            print("User not found")
            return
        
        print(f"Found user: {user.email} (id: {user.id})")
        
        watchlists = db.query(Watchlist).filter(Watchlist.user_id == user.id).all()
        print(f"Found {len(watchlists)} watchlists in DB")
        for w in watchlists:
            print(f" - ID: {w.id}, Name: {w.name}, Position: {w.position}")
            
    finally:
        db.close()

if __name__ == "__main__":
    test()
