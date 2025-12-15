import requests
import sys

BASE_URL = "http://localhost:8000"

def log(msg, status="INFO"):
    print(f"[{status}] {msg}")

def test_health():
    try:
        r = requests.get(f"{BASE_URL}/")
        if r.status_code == 200:
            log("Backend Health Check Passed", "SUCCESS")
        else:
            log(f"Backend Health Check Failed: {r.status_code}", "ERROR")
    except Exception as e:
        log(f"Backend Connection Failed: {e}", "CRITICAL")
        sys.exit(1)

def seed_data():
    log("Seeding Data...", "INFO")
    
    # create watchlist
    wl_name = "Tech Giants"
    try:
        # Check if exists
        r = requests.get(f"{BASE_URL}/api/watchlist/")
        current = r.json()
        target_id = None
        for w in current:
            if w['name'] == wl_name:
                target_id = w['id']
                log(f"Watchlist '{wl_name}' already exists (ID: {target_id})", "INFO")
                break
        
        if not target_id:
            r = requests.post(f"{BASE_URL}/api/watchlist/", json={"name": wl_name})
            if r.status_code == 200:
                target_id = r.json()['id']
                log(f"Created Watchlist '{wl_name}'", "SUCCESS")
            else:
                log(f"Failed to create watchlist: {r.text}", "ERROR")
                return

        # Add stocks
        for ticker in ["AAPL", "GOOGL", "MSFT", "NVDA"]:
            r = requests.post(f"{BASE_URL}/api/watchlist/{target_id}/add", json={"symbol": ticker})
            if r.status_code == 200:
                log(f"Added {ticker} to watchlist", "SUCCESS")
            else:
                log(f"Failed to add {ticker}: {r.text}", "ERROR")

    except Exception as e:
        log(f"Seeding failed: {e}", "ERROR")

def test_services():
    log("Testing External Services...", "INFO")
    ticker = "AAPL"
    
    # Finance Data
    r = requests.get(f"{BASE_URL}/api/data/stock/{ticker}")
    if r.status_code == 200 and 'symbol' in r.json():
         log(f"Finance API (yfinance) working for {ticker}", "SUCCESS")
    else:
         log(f"Finance API failed: {r.text}", "ERROR")

    # Analysis
    r = requests.get(f"{BASE_URL}/api/data/analysis/{ticker}")
    if r.status_code == 200:
        data = r.json()
        if "indicators" in data and "risk" in data and "sentiment" in data:
            log(f"Technical Analysis (ta) working. RSI: {data['indicators'][-1].get('RSI', 'N/A')}", "SUCCESS")
            log(f"Risk Metrics working. Sharpe: {data['risk'].get('sharpe_ratio', 'N/A')}", "SUCCESS")
            log(f"Sentiment Analysis working. Score: {data['sentiment'].get('score', 'N/A')} ({data['sentiment'].get('label', 'N/A')})", "SUCCESS")
        else:
            log("Analysis API response structure invalid", "ERROR")
    else:
         log(f"Analysis API failed: {r.status_code}", "ERROR")

    # Simulation
    r = requests.get(f"{BASE_URL}/api/data/simulation/{ticker}")
    if r.status_code == 200:
        data = r.json()
        if 'p50' in data:
            log("Monte Carlo Simulation working", "SUCCESS")
        else:
            log("Simulation response malformed", "ERROR")
    else:
        log(f"Simulation API failed: {r.status_code}", "ERROR")

    # Search
    log("Testing Search...", "INFO")
    r = requests.get(f"{BASE_URL}/api/data/search?q=ora")
    if r.status_code == 200:
        results = r.json()
        if len(results) > 0 and any("ORCL" in x['symbol'] for x in results):
             log("Search API working (Found ORCL for 'ora')", "SUCCESS")
        else:
             log(f"Search API returned no valid results: {results}", "WARNING")
    else:
        log(f"Search API failed: {r.status_code}", "ERROR")

if __name__ == "__main__":
    test_health()
    seed_data()
    test_services()
