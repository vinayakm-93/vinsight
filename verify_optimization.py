
import time
import requests
import sys
import os

# Add the parent directory to sys.path to import backend modules directly if needed
# But better to test via API if the server is running.
# The user metadata says uvicorn is running on localhost:8000

BASE_URL = "http://localhost:8000"

def test_endpoint(name, method, url, payload=None):
    print(f"Testing {name}...", end=" ", flush=True)
    start = time.time()
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{url}")
        else:
            response = requests.post(f"{BASE_URL}{url}", json=payload)
            
        duration = (time.time() - start) * 1000
        
        if response.status_code == 200:
            print(f"✅ Success ({duration:.2f}ms)")
            return response.json(), duration
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return None, duration
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None, 0

def main():
    print("=== Verifying Backend Optimizations ===\n")
    
    # 1. Test Single Stock Info (Should cache)
    ticker = "AAPL"
    print(f"1. Testing Caching for {ticker} Info")
    
    # First call (Cold Cache)
    data1, time1 = test_endpoint("Get Stock Info (Cold)", "GET", f"/api/data/stock/{ticker}")
    
    # Second call (Warm Cache)
    data2, time2 = test_endpoint("Get Stock Info (Warm)", "GET", f"/api/data/stock/{ticker}")
    
    if data1 and data2:
        saved = time1 - time2
        print(f"   ℹ️ Cache saved approximately {saved:.2f}ms")
        if time2 < time1 * 0.5 or time2 < 100: # Assuming dramatic speedup or very fast response
            print("   ✅ Caching appears to be working.")
        else:
            print("   ⚠️ Caching might not be effective or network latency dominates.")

    print("\n" + "-"*30 + "\n")

    # 2. Test Batch Endpoint
    print("2. Testing Batch Stock Details")
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    payload = {"tickers": tickers}
    
    batch_data, batch_time = test_endpoint(f"Batch Get {len(tickers)} Stocks", "POST", "/api/data/batch-stock", payload)
    
    if batch_data:
        print(f"   ℹ️ Received {len(batch_data)} items")
        if len(batch_data) == len(tickers):
            print("   ✅ Received data for all requested tickers.")
            # Check structure
            sample = batch_data[0]
            required_keys = ["symbol", "currentPrice", "marketCap", "trailingPE"]
            if all(k in sample for k in required_keys):
                 print("   ✅ Response structure is correct.")
            else:
                 print(f"   ❌ Missing keys in response. Got: {list(sample.keys())}")
        else:
            print(f"   ⚠️ Expected {len(tickers)} items, got {len(batch_data)}")

    print("\n" + "-"*30 + "\n")
            
    # 3. Test Institutional Data (Cached)
    print("3. Testing Institutional Data Caching")
    # First call
    inst1, i_time1 = test_endpoint("Get Institutional (Cold)", "GET", f"/api/data/institutional/{ticker}")
    # Second call
    inst2, i_time2 = test_endpoint("Get Institutional (Warm)", "GET", f"/api/data/institutional/{ticker}")
    
    if inst1 and inst2:
         print(f"   ℹ️ Institutional fetch time improved by {i_time1 - i_time2:.2f}ms")

if __name__ == "__main__":
    main()
