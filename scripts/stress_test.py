
import requests
import time
import concurrent.futures
import statistics

# Configuration
BASE_URL = "http://localhost:8000"
NUM_REQUESTS = 50
CONCURRENCY = 10

def check_health(i):
    try:
        start = time.time()
        # Using a lightweight endpoint to measure pure overhead
        response = requests.get(f"{BASE_URL}/") 
        end = time.time()
        return (end - start) * 1000, response.status_code
    except Exception as e:
        return None, str(e)

def run_stress_test():
    print(f"Starting Stress Test: {NUM_REQUESTS} requests with concurrency {CONCURRENCY}...")
    
    latencies = []
    errors = 0
    
    start_total = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        results = list(executor.map(check_health, range(NUM_REQUESTS)))
        
    for duration, status in results:
        if duration is None:
            errors += 1
            print(f"Error: {status}")
        else:
            latencies.append(duration)
            if status != 200:
                errors += 1

    end_total = time.time()
    total_time = end_total - start_total
    
    if not latencies:
        print("All requests failed!")
        return

    print("\n--- Stress Test Results ---")
    print(f"Total Time: {total_time:.2f}s")
    print(f"Throughput: {NUM_REQUESTS / total_time:.2f} req/s")
    print(f"Avg Latency: {statistics.mean(latencies):.2f}ms")
    print(f"Median Latency: {statistics.median(latencies):.2f}ms")
    print(f"P95 Latency: {statistics.quantiles(latencies, n=20)[18]:.2f}ms") # approx P95
    print(f"Max Latency: {max(latencies):.2f}ms")
    print(f"Errors: {errors}")
    
    if statistics.mean(latencies) > 200:
        print("\n[WARNING] Average latency is high (>200ms).")
    else:
        print("\n[PASS] Latency is within acceptable limits.")

if __name__ == "__main__":
    run_stress_test()
