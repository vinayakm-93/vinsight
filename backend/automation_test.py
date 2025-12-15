import requests
import sys

BASE_URL = "http://127.0.0.1:8000"
TEST_EMAIL = "demo_user@finance.app"
TEST_PASS = "DemoPass123!"

STOCKS = {
    "Energy Giants": ["XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO", "OXY", "HES"],
    "Tech Titans": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "AVGO", "ORCL", "ADBE", "CRM"],
    "Pharma Leaders": ["LLY", "JNJ", "MRK", "ABBV", "PFE", "AMGN", "BMY", "GILD", "VRTX", "REGN"],
    "Chips & Semi": ["NVDA", "TSM", "AVGO", "AMD", "QCOM", "TXN", "INTC", "MU", "AMAT", "LRCX"]
}

def log(msg, type="INFO"):
    print(f"[{type}] {msg}")

def test_negative_cases():
    log("Running Negative Tests...")
    
    # 1. Verification Request Bad Email
    res = requests.post(f"{BASE_URL}/api/auth/request-verify", json={"email": "not-an-email"})
    if res.status_code == 422:
        log("PASS: Invalid email rejected")
    else:
        log(f"FAIL: Invalid email accepted: {res.status_code}", "ERROR")

    # 2. Verify Code Bad Code - First need to request a code for a dummy
    requests.post(f"{BASE_URL}/api/auth/request-verify", json={"email": "bad@test.com"})
    res = requests.post(f"{BASE_URL}/api/auth/verify-code", json={"email": "bad@test.com", "code": "000000"})
    if res.status_code == 400:
        log("PASS: Invalid code rejected")
    else:
        log(f"FAIL: Invalid code accepted: {res.status_code}", "ERROR")

def run_flow():
    session = requests.Session()
    
    # 1. Cleanup (Try login to get ID and delete, or just rely on backend failing? 
    # Since we don't have a delete-user endpoint easily accessible, we'll use a unique email or just restart DB if needed. 
    # But wait, user said "clean entries".
    # I'll just try to login, if success, I can't delete easily via API.
    # For this script, I'll rely on the previous DB reset manually if it fails, OR I can add a random suffix. 
    # But user wants a specific username/pass. 
    # I will assume the DB is clean from my previous deletion COMMAND or I will fail if exists.
    
    log(f"Starting Registration for {TEST_EMAIL}")
    
    # 2. Request Verify
    res = requests.post(f"{BASE_URL}/api/auth/request-verify", json={"email": TEST_EMAIL})
    if res.status_code == 400 and "registered" in res.text:
        log("User already exists. Skipping registration.")
        # Proceed to login
    elif res.status_code == 200:
        log("Verification code requested.")
        
        # 3. Get Code (Debug)
        res = requests.get(f"{BASE_URL}/api/auth/debug-code/{TEST_EMAIL}")
        if res.status_code != 200:
            log("FAIL: Could not get debug code", "CRITICAL")
            sys.exit(1)
        
        code = res.json()['code']
        log(f"Got Debug Code: {code}")
        
        # 4. Verify Code
        res = requests.post(f"{BASE_URL}/api/auth/verify-code", json={"email": TEST_EMAIL, "code": code})
        if res.status_code != 200:
            log(f"FAIL: Code verification failed: {res.text}", "CRITICAL")
            sys.exit(1)
        log("PASS: Email Verified")
        
        # 5. Register
        res = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_EMAIL,
            "password": TEST_PASS,
            "investing_goals": "Long-term Growth",
            "feature_requests": "Automated Testing",
            "verification_code": code
        })
        if res.status_code != 200:
            log(f"FAIL: Registration Failed: {res.text}", "CRITICAL")
            sys.exit(1)
        log("PASS: User Registered")
    else:
        log(f"FAIL: Request verify failed: {res.text}", "CRITICAL")
        sys.exit(1)

    # 6. Login
    res = requests.post(f"{BASE_URL}/api/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASS})
    if res.status_code != 200:
        log(f"FAIL: Login Failed: {res.text}", "CRITICAL")
        sys.exit(1)
    
    log("PASS: Login Successful")
    # Cookie is in session/response set-cookie, but we need to extract for requests if not using session object correctly ? 
    # Requests Session handles cookies automatically!
    # But wait, the API expects cookie or header?
    # Backend: token = request.cookies.get("access_token")
    # requests.Session() should handle it.
    
    cookies = res.cookies
    
    # 7. Seed Watchlists
    for name, tickers in STOCKS.items():
        # Join tickers
        ticker_str = ",".join(tickers)
        log(f"Creating Watchlist: {name} with {len(tickers)} stocks...")
        
        # Check if exists first to avoid duplicate error
        # Actually create endpoint might fail if unique name.
        # We'll just try to create.
        
        create_res = requests.post(
            f"{BASE_URL}/api/watchlists/", 
            json={"name": name, "stocks": ticker_str},
            cookies=cookies # Explicitly passing just in case
        )
        
        if create_res.status_code == 200:
            log(f"PASS: Created {name}")
        elif create_res.status_code == 400 and "already exists" in create_res.text:
             log(f"INFO: Watchlist {name} already exists")
        else:
            log(f"FAIL: Create {name} failed: {create_res.text}", "ERROR")

    log("="*30)
    log("TEST & SEEDING COMPLETE")
    log(f"Username: {TEST_EMAIL}")
    log(f"Password: {TEST_PASS}")
    log("="*30)

if __name__ == "__main__":
    try:
        test_negative_cases()
        run_flow()
    except Exception as e:
        log(f"CRITICAL EXCEPTION: {e}", "CRITICAL")
