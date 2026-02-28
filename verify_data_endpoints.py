
import os
import json
import sys
import logging
import time

# Setup basic logging
logging.basicConfig(level=logging.DEBUG)

# Mock environment path to match backend
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, 'backend')
sys.path.append(backend_dir)

def test_batch_prices():
    print("\nTesting get_batch_prices...")
    try:
        from services import finance
        tickers = ["AAPL", "NVDA", "MSFT"]
        
        print(f"Run 1 (Cache Miss expected)...")
        start = time.time()
        results = finance.get_batch_prices(tickers)
        print(f"Run 1 took {time.time() - start:.2f}s. Results: {len(results)}")
        
        print(f"Run 2 (Cache Hit expected)...")
        start = time.time()
        results2 = finance.get_batch_prices(tickers)
        print(f"Run 2 took {time.time() - start:.2f}s. Results: {len(results2)}")
        
    except Exception as e:
        print(f"FAIL: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_batch_prices()
