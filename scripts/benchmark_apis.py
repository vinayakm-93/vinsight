import time
import requests
import statistics
import concurrent.futures

BASE_URL = "http://localhost:8000/api/data"
STOCKS_TO_TEST = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
BATCH_STOCKS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX", "AMD", "INTC"]

def timed_request(name, url, method="GET", json=None):
    start = time.perf_counter()
    try:
        if method == "GET":
            response = requests.get(url)
        else:
            response = requests.post(url, json=json)
        response.raise_for_status()
        duration = (time.perf_counter() - start) * 1000  # ms
        return duration, True
    except Exception as e:
        duration = (time.perf_counter() - start) * 1000
        print(f"FAILED {name}: {e}")
        return duration, False

def benchmark():
    print(f"Benchmarking API at {BASE_URL}...\n")
    results = {}

    # 1. Single Stock Details (yfinance usually)
    print("1. Benchmarking Single Stock Fetch (5 sequential calls)...")
    durations = []
    for ticker in STOCKS_TO_TEST:
        d, success = timed_request(f"Stock {ticker}", f"{BASE_URL}/stock/{ticker}")
        if success: durations.append(d)
    
    if durations:
        avg = statistics.mean(durations)
        print(f"   Average: {avg:.2f}ms | Min: {min(durations):.2f}ms | Max: {max(durations):.2f}ms")
        results['single_stock'] = avg
    else:
        print("   All failed.")

    # 2. Batch Stock Details
    print("\n2. Benchmarking Batch Stock Fetch (10 stocks in 1 call)...")
    d, success = timed_request("Batch Stocks", f"{BASE_URL}/batch-stock", "POST", {"tickers": BATCH_STOCKS})
    if success:
        print(f"   Batch Call Time: {d:.2f}ms (for {len(BATCH_STOCKS)} stocks)")
        print(f"   Effective per-stock time: {d/len(BATCH_STOCKS):.2f}ms")
        results['batch_stock'] = d
    
    # 3. Simulate "Standard" Frontend Load (Multiple Single Calls)
    # This simulates what Watchlist.tsx is doing currently
    print("\n3. Simulating 'Bad' Frontend Load (10 parallel single calls)...")
    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(requests.get, f"{BASE_URL}/stock/{ticker}") for ticker in BATCH_STOCKS]
        for f in concurrent.futures.as_completed(futures):
            pass 
    total_time = (time.perf_counter() - start) * 1000
    print(f"   Total Time for 10 parallel requests: {total_time:.2f}ms")
    results['parallel_single'] = total_time

    # 4. News/Sentiment (Alpha Vantage check)
    print("\n4. Benchmarking News/Sentiment (cached potentially)...")
    d, success = timed_request("News AAPL", f"{BASE_URL}/news/AAPL")
    if success:
        print(f"   News Fetch Time: {d:.2f}ms")
        results['news'] = d
    
    return results

if __name__ == "__main__":
    benchmark()
