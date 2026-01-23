import requests
import time
import concurrent.futures
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
BACKEND_URL = "http://localhost:8000"
TICKER = "NVDA"

def benchmark_endpoint(url, name):
    try:
        start_time = time.time()
        response = requests.get(url)
        end_time = time.time()
        duration = (end_time - start_time) * 1000
        status = response.status_code
        size = len(response.content) / 1024
        print(f"{name:<20} | Status: {status} | Time: {duration:8.2f} ms | Size: {size:6.2f} KB")
        return duration
    except Exception as e:
        print(f"{name:<20} | Error: {e}")
        return 0

def run_benchmark():
    print(f"\nBenchmarking Single Stock Optimization for {TICKER}")
    print("=" * 60)
    
    # 1. Warmup
    print("Warming up backend...")
    requests.get(f"{BACKEND_URL}/api/data/quote/{TICKER}")
    time.sleep(1)

    print("\noptimized /analysis Call (Consolidated):")
    print("-" * 60)
    
    # Measure the new consolidated endpoint
    # It should return analysis + news + simulation + institutional
    t_analysis = benchmark_endpoint(f"{BACKEND_URL}/api/data/analysis/{TICKER}", "Consolidated Analysis")
    
    # For comparison, let's look at what the "Sequential/Parallel" load WAS
    # Previous baseline was ~2600ms (Parallel) or ~4000ms (Sequential)
    
    print("-" * 60)
    print(f"New Load Time: {t_analysis:.2f} ms")
    
    # Verify Content
    try:
        resp = requests.get(f"{BACKEND_URL}/api/data/analysis/{TICKER}").json()
        print("\nVerifying Response Content:")
        has_sim = "simulation" in resp and len(resp["simulation"]) > 0
        has_news = "news" in resp and len(resp["news"]) > 0
        has_inst = "institutional" in resp and len(resp["institutional"]) > 0
        
        print(f"- Has Simulation: {has_sim}")
        print(f"- Has News:       {has_news}")
        print(f"- Has Inst Data:  {has_inst}")
        
        if has_sim and has_news and has_inst:
            print("\n✅ SUCCESS: Response contains all consolidated data.")
        else:
            print("\n❌ FAILURE: Missing data fields.")
            
    except Exception as e:
        print(f"Verification Failed: {e}")

if __name__ == "__main__":
    run_benchmark()
