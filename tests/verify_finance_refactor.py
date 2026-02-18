
import sys
import os
import time

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from services import finance

tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK-B", "LLY", "V", "TSM", "AVGO", "NVO", "JPM", "WMT", "XOM", "MA", "UNH", "PG", "JNJ"]

def test_get_batch_prices():
    print("Testing get_batch_prices...")
    start = time.time()
    results = finance.get_batch_prices(tickers)
    duration = time.time() - start
    print(f"Time: {duration:.4f}s")
    print(f"Results: {len(results)}")
    if results:
        print(f"Sample: {results[0]}")

def test_get_batch_stock_details():
    print("\nTesting get_batch_stock_details...")
    start = time.time()
    results = finance.get_batch_stock_details(tickers)
    duration = time.time() - start
    print(f"Time: {duration:.4f}s")
    print(f"Results: {len(results)}")
    if results:
        print(f"Sample: {results[0]}")

if __name__ == "__main__":
    test_get_batch_prices()
    test_get_batch_stock_details()
