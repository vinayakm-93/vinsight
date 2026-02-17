import requests
import json
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("verify_api")

BASE_URL = "http://localhost:8000"

def verify_api():
    # 1. Register/Login User
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    email = "guardian_test@example.com"
    password = "password123"
    
    logger.info(f"--- 1. Authenticating as {email} ---")
    
    # Register
    try:
        reg_resp = session.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": password,
            "investing_goals": "Growth"
        })
        if reg_resp.status_code == 200:
            logger.info("Registered new user.")
        elif reg_resp.status_code == 400 and "already exists" in reg_resp.text:
            logger.info("User already exists.")
        else:
            logger.error(f"Registration failed (Proceeding to login check...): {reg_resp.text}")
            # return # Proceed to login anyway, as user might be seeded manually
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return

    # Login
    auth_resp = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": email,
        "password": password
    })
    
    if auth_resp.status_code != 200:
        logger.error(f"Login failed: {auth_resp.text}")
        return
        
    # token = auth_resp.json()["access_token"]
    # headers = {"Authorization": f"Bearer {token}"}
    logger.info("Login successful. Session cookies acquired.")

    # 2. Enable Guardian for NVDA
    symbol = "NVDA"
    logger.info(f"--- 2. Enabling Guardian for {symbol} ---")
    
    enable_resp = session.post(f"{BASE_URL}/api/guardian/enable", json={"symbol": symbol})
    
    if enable_resp.status_code == 200:
        data = enable_resp.json()
        logger.info(f"✅ Success! Thesis: {data.get('thesis', 'N/A')}")
    else:
        logger.error(f"❌ Failed to enable: {enable_resp.text}")
        # Validate if it failed due to limit or other reason logic
        
    # 3. List Theses
    logger.info("--- 3. Listing Theses ---")
    list_resp = session.get(f"{BASE_URL}/api/guardian/theses")
    
    if list_resp.status_code == 200:
        theses = list_resp.json()
        logger.info(f"Found {len(theses)} theses.")
        found = False
        for t in theses:
            if t['symbol'] == symbol:
                found = True
                logger.info(f"✅ Found {symbol}: Active={t['is_active']}, AutoGen={t['auto_generated']}")
        if not found:
            logger.error(f"❌ {symbol} not found in list!")
    else:
        logger.error(f"Failed to list: {list_resp.text}")

    # 4. Disable Guardian
    logger.info(f"--- 4. Disabling Guardian for {symbol} ---")
    disable_resp = session.post(f"{BASE_URL}/api/guardian/disable/{symbol}")
    
    if disable_resp.status_code == 200:
        logger.info(f"✅ Disabled {symbol}.")
    else:
        logger.error(f"❌ Failed to disable: {disable_resp.text}")

    # 5. Verify Disabled Status
    list_resp_2 = session.get(f"{BASE_URL}/api/guardian/theses")
    for t in list_resp_2.json():
        if t['symbol'] == symbol:
            if not t['is_active']:
                logger.info(f"✅ Verified {symbol} is inactive.")
            else:
                logger.error(f"❌ {symbol} is still active!")

if __name__ == "__main__":
    verify_api()
