
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from routes.data import get_technical_analysis

def benchmark_new_state(ticker="AAPL"):
    print(f"Benchmarking New State for {ticker}...")
    
    start_time = time.time()
    
    # New Flow: Single call does everything
    result = get_technical_analysis(ticker, period="1y", interval="1d")
    
    end_time = time.time()
    
    print(f"New Full Flow Time: {end_time - start_time:.4f} seconds")
    
    # Verify consolidated data presence
    keys = result.keys()
    print(f"Keys present: {list(keys)}")
    
    if 'history' in keys and 'stock_details' in keys and 'simulation' in keys:
        print("VERIFICATION: SUCCESS - All consolidated data present.")
    else:
        print("VERIFICATION: FAILURE - Missing keys.")

if __name__ == "__main__":
    try:
        benchmark_new_state()
    except Exception as e:
        print(f"Error: {e}")
