import sys
import os

# Ensure backend package is importable
sys.path.append(os.getcwd())

from backend.database import init_db, SessionLocal
from backend.models import User
from backend.services.auth import get_password_hash

def main():
    print("Initialize DB...")
    init_db()
    print("DB Initialized.")
    
    db = SessionLocal()
    email = "test@example.com"
    password = "password123"
    
    existing = db.query(User).filter(User.email == email).first()
    if not existing:
        print(f"Creating user: {email}")
        user = User(
            email=email,
            hashed_password=get_password_hash(password)
        )
        db.add(user)
        db.commit()
        print(f"User created. Login with {email} / {password}")
    else:
        print(f"User {email} already exists.")
        
    db.close()

if __name__ == "__main__":
    main()
