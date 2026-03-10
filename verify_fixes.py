import requests
import sys

BASE_URL = "http://localhost:8000"

def test_analysis(ticker="AAPL"):
    print(f"Testing Analysis for {ticker}...")
    try:
        url = f"{BASE_URL}/api/data/analysis/{ticker}?scoring_engine=formula"
        resp = requests.get(url, timeout=30)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("SUCCESS: Analysis endpoint returned 200 OK")
            # print(resp.json())
        else:
            print(f"FAILURE: Analysis endpoint returned {resp.status_code}")
            print(resp.text)
    except Exception as e:
        print(f"ERROR: {e}")

def test_generate_thesis(ticker="TSLA"):
    print(f"\nTesting Thesis Generation for {ticker}...")
    # This requires auth, so we might not be able to test easily without a token
    # But we can at least check if the route exists (401 is better than 404 or 500)
    try:
        url = f"{BASE_URL}/api/theses/generate/{ticker}"
        resp = requests.post(url, timeout=30)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 401:
            print("SUCCESS: Route exists and requires authentication (as expected)")
        elif resp.status_code == 200:
            print("SUCCESS: Thesis generated (if auth was bypassed or not needed)")
        else:
            print(f"FAILED: Returned {resp.status_code}")
            print(resp.text)
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_analysis()
    test_generate_thesis()
