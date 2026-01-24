import sys
import os
import time
import pandas as pd

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.services import finance

def benchmark_watchlist_optimization():
    tickers = [
        "AAPL", "MSFT", "GOOG", "AMZN", "NVDA", "TSLA", "META", "BRK-B", "UNH", "JNJ",
        "XOM", "V", "JPM", "PG", "TSM", "NVO", "MA", "HD", "CVX", "LLY",
        "PEP", "ABBV", "KO", "MRK", "BAC", "COST", "AVGO", "MCD", "DIS", "PFE",
        "TMO", "CSCO", "ACN", "ABT", "DHR", "ADBE", "LIN", "NKE", "NFLX", "NEE",
        "CRM", "TXN", "UPS", "PM", "BMY", "WMT", "RTX", "MS", "HON", "QCOM"
    ]
    
    print(f"Benchmarking {len(tickers)} tickers...")
    
    # 1. Test Light Function
    print("\n--- Testing Light Function (get_batch_prices) ---")
    start_time = time.time()
    results_light = finance.get_batch_prices(tickers)
    end_time = time.time()
    duration_light = end_time - start_time
    print(f"Time taken (Light): {duration_light:.4f} seconds")
    print(f"Average time per ticker: {duration_light / len(tickers):.4f} seconds")
    
    if results_light:
        print(f"Sample Light Result for {results_light[0]['symbol']}: Price={results_light[0].get('currentPrice')}, Change%={results_light[0].get('regularMarketChangePercent')}")

    # 2. Test Heavy Function
    print("\n--- Testing Heavy Function (get_batch_stock_details) ---")
    start_time = time.time()
    results_heavy = finance.get_batch_stock_details(tickers)
    end_time = time.time()
    duration_heavy = end_time - start_time
    print(f"Time taken (Heavy): {duration_heavy:.4f} seconds")
    print(f"Average time per ticker: {duration_heavy / len(tickers):.4f} seconds")
    
    if results_heavy:
        sample = results_heavy[0]
        print(f"Sample Heavy Result for {sample['symbol']}: YTD%={sample.get('ytdChangePercent')}")

if __name__ == "__main__":
    benchmark_watchlist_optimization()
