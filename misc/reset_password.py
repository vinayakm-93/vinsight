import sys
import os

# Ensure backend package is importable
sys.path.append(os.getcwd())

from backend.database import SessionLocal
from backend.models import User
from backend.services.auth import get_password_hash

def reset_password(email, new_password):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            print(f"Resetting password for: {email}")
            user.hashed_password = get_password_hash(new_password)
            db.commit()
            print("Password reset successful.")
        else:
            print(f"User {email} not found.")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python reset_password.py <email> <new_password>")
    else:
        reset_password(sys.argv[1], sys.argv[2])
