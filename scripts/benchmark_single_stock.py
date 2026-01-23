import time
import requests
import concurrent.futures

BASE_URL = "http://localhost:8000"  # Adjust if backend is on a different port
TICKER = "AAPL"

ENDPOINTS = [
    (f"/api/data/analysis/{TICKER}", "Analysis"),
    (f"/api/data/news/{TICKER}", "News"),
    (f"/api/data/history/{TICKER}?period=1y&interval=1d", "History (1Y)"),
    (f"/api/data/stock/{TICKER}", "Stock Details"),
    (f"/api/data/simulation/{TICKER}", "Simulation"),
    (f"/api/data/institutional/{TICKER}", "Institutional"),
    (f"/api/data/sentiment/{TICKER}", "Sentiment"),
    (f"/api/data/earnings/{TICKER}", "Earnings"),
]

def benchmark_endpoint(url, label):
    start = time.time()
    try:
        response = requests.get(BASE_URL + url)
        response.raise_for_status()
        duration = (time.time() - start) * 1000
        size = len(response.content) / 1024
        return f"{label:<20} | Status: {response.status_code} | Time: {duration:8.2f} ms | Size: {size:6.2f} KB"
    except Exception as e:
        return f"{label:<20} | Failed: {str(e)}"

def run_benchmarks():
    print(f"Benchmarking Single Stock Load for: {TICKER}")
    print("-" * 60)
    
    # Sequential Benchmark
    print("\nSequential Execution:")
    print("-" * 60)
    total_time = 0
    for url, label in ENDPOINTS:
        result = benchmark_endpoint(url, label)
        print(result)
    
    # Parallel Benchmark (Simulating Dashboard Load)
    print("\nParallel Execution (Simulating Dashboard Load):")
    print("-" * 60)
    start_total = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(benchmark_endpoint, url, label): label for url, label in ENDPOINTS}
        for future in concurrent.futures.as_completed(futures):
            print(future.result())
    
    total_duration = (time.time() - start_total) * 1000
    print("-" * 60)
    print(f"Total Parallel Wall Time: {total_duration:.2f} ms")

if __name__ == "__main__":
    run_benchmarks()
