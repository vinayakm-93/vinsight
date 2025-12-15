import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

BASE_URL = "http://localhost:8000/api"

def debug_create_alert():
    print("--- DEBUG ALERT CREATION ---")
    
    # 1. Login
    print("1. Logging in as 'test_alert_user@example.com'...")
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", json={"email": "test_alert_user@example.com", "password": "password123"})
        if resp.status_code != 200:
            print(f"LOGIN FAILED: {resp.status_code} {resp.text}")
            return
        
        token = resp.cookies.get("access_token") 
        # Or maybe it returned JSON? In route it sets cookie but returns {"status": "success"}
        # But `AlertModal` uses localStorage token? 
        # Ah, looking at `AlertModal.tsx`: headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
        # My backend login endpoint:
        # return {"status": "success", "user": ...} AND sets cookie.
        # Wait, if `AlertModal` relies on `localStorage.getItem('token')`, does the /login endpoint return it?
        # In `auth.py`: `return {"status": "success", "user": ...}`. It does NOT return the token in the body anymore!
        # If the frontend expects a token in the body to save to localStorage, THAT IS THE BUG.
        
        # Let's check `frontend/src/context/AuthContext.tsx` or how login works in Frontend. 
        # If I can't check that, I'll assume the frontend MIGHT be broken if I changed auth recently. 
        # But I didn't change auth recently.
        
        # For this script, I'll access the cookie.
        jar = resp.cookies

    except Exception as e:
        print(f"Login Exception: {e}")
        return

    # 2. Create Alert
    print("2. Creating Alert...")
    payload = {
        "symbol": "DEBUG",
        "target_price": 100.0,
        "condition": "above"
    }
    
    try:
        # Note: The backend `get_current_user` usually looks for cookie OR header.
        # Let's try sending cookie.
        resp = requests.post(f"{BASE_URL}/alerts/", json=payload, cookies=jar)
        
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")
        
        if resp.status_code == 500:
             print("SERVER ERROR DETECTED. Check terminal logs.")
             
    except Exception as e:
        print(f"Request Failed: {e}")

if __name__ == "__main__":
    debug_create_alert()
