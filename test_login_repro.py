import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from fastapi.testclient import TestClient
from main import app
from database import get_db, SessionLocal
from models import User

client = TestClient(app)

def test_login():
    db = SessionLocal()
    user = db.query(User).first()
    if not user:
        print("No users in database.")
        return
        
    print(f"Testing login for {user.email}")
    
    response = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "password123"} 
    )
    print("STATUS CODE:", response.status_code)
    print("RESPONSE JSON:", response.json())
    print("SET-COOKIE HEADERS:", response.headers.get("set-cookie"))
    
if __name__ == "__main__":
    test_login()
