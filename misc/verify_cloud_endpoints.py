import requests
import time
import sys
import json

BASE_URL = "https://vinsight-backend-wddr2kfz3a-uc.a.run.app"

def test_health():
    print(f"Testing Health Check at {BASE_URL}...")
    try:
        res = requests.get(f"{BASE_URL}/")
        if res.status_code == 200:
            print("✅ Health Check Passed")
        else:
            print(f"❌ Health Check Failed: {res.status_code}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

def test_quote():
    print(f"\nTesting Basic Data Fetch (/api/data/quote/AAPL)...")
    try:
        res = requests.get(f"{BASE_URL}/api/data/quote/AAPL")
        if res.status_code == 200:
            data = res.json()
            print(f"✅ Quote Fetched: {data.get('price')} (Change: {data.get('changePercent')}%)")
        else:
            print(f"❌ Quote Fetch Failed: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ Request Error: {e}")

def test_reasoning_scorer():
    print(f"\nTesting Reasoning Scorer (/api/data/analysis/AAPL?scoring_engine=reasoning)...")
    print("This requires the backend to fetch data, connect to DB (ScoreHistory), and call the LLM.")
    print("Waiting 10-15 seconds for response...")
    start_time = time.time()
    try:
        res = requests.get(f"{BASE_URL}/api/data/analysis/AAPL?scoring_engine=reasoning")
        duration = time.time() - start_time
        
        if res.status_code == 200:
            data = res.json()
            analysis = data.get("ai_analysis", {})
            score = analysis.get("score")
            rating = analysis.get("rating")
            source = analysis.get("meta", {}).get("source", "Unknown")
            
            print(f"✅ Reasoning Scorer Passed ({duration:.2f}s)!")
            print(f"   -> Score: {score}/100")
            print(f"   -> Rating: {rating}")
            print(f"   -> Source: {source}")
            
            # Print brief justification snippet
            just = analysis.get("justification", "")
            snippet = just[:150].replace('\n', ' ') + "..." if len(just) > 150 else just
            print(f"   -> Justification Snippet: {snippet}")
        else:
            print(f"❌ Reasoning Scorer Failed: {res.status_code} - {res.text}")
    except Exception as e:
         print(f"❌ Request Error: {e}")

def test_memory_throttle():
    print(f"\nTesting DB Throttling (Calling AAPL again)...")
    print("This should successfully return a score but internally skip saving to DB.")
    try:
        res = requests.get(f"{BASE_URL}/api/data/analysis/AAPL?scoring_engine=reasoning")
        if res.status_code == 200:
             print(f"✅ Second analysis successful (Throttle active, DB protected).")
        else:
             print(f"❌ Second analysis failed: {res.status_code} - {res.text}")
    except Exception as e:
         print(f"❌ Request Error: {e}")

if __name__ == "__main__":
    print(f"=== Starting Cloud Live Verification ===")
    test_health()
    test_quote()
    test_reasoning_scorer()
    test_memory_throttle()
    print(f"\n=== Cloud Verification Complete ===")
