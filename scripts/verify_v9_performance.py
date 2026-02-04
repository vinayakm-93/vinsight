
import time
import requests
import json
import logging
import sys
import os
import argparse
import concurrent.futures
import statistics

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
TICKER = "AAPL"
BASELINE_FILE = "performance_baseline.json"

def check_backend():
    try:
        requests.get(BASE_URL + "/api/data/sector-benchmarks", timeout=2)
        return True
    except:
        return False

def validate_integrity(data):
    """Deep check of response data quality."""
    issues = []
    
    # Check Price
    try:
        price = data.get("stock_details", {}).get("currentPrice")
        if not price or price <= 0:
            issues.append("Invalid/Missing Price")
    except: issues.append("Missing Price Structure")

    # Check History
    hist = data.get("history", [])
    if not hist or len(hist) < 10:
        issues.append("Sparse/Empty History")

    # Check News
    news = data.get("news", [])
    if not isinstance(news, list):
        issues.append("Invalid News Format")

    return issues

def benchmark_analysis(concurrency=1):
    """Measures the main analysis endpoint with optional concurrency."""
    url = f"{BASE_URL}/api/data/analysis/{TICKER}"
    
    def fetch():
        start = time.time()
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            return time.time() - start, resp.json()
        except Exception as e:
            return None, str(e)

    results = []
    errors = []
    
    start_total = time.time()
    
    if concurrency == 1:
        dur, res = fetch()
        if dur:
            results.append(dur)
            integrity_issues = validate_integrity(res)
        else:
            errors.append(res)
            integrity_issues = ["Request Failed"]
            
        data_size = len(json.dumps(res)) / 1024 if dur else 0
    else:
        # Concurrent Stampede
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(fetch) for _ in range(concurrency)]
            for f in concurrent.futures.as_completed(futures):
                dur, res = f.result()
                if dur:
                    results.append(dur)
                else:
                    errors.append(res)
        
        # We only check integrity on one sample for concurrent runs
        integrity_issues = [] 
        data_size = 0

    total_wall_time = time.time() - start_total
    
    if not results:
        return {"success": False, "error": f"All requests failed: {errors}"}

    return {
        "success": True,
        "avg_duration": statistics.mean(results),
        "p95_duration": sorted(results)[int(len(results)*0.95)] if len(results) > 1 else results[0],
        "total_wall_time": total_wall_time,
        "integrity_issues": integrity_issues,
        "size_kb": data_size,
        "concurrency": concurrency
    }

def benchmark_watchlist_batch(tickers):
    """Measures batch price fetching."""
    url = f"{BASE_URL}/api/data/batch-prices"
    payload = {"tickers": tickers}
    
    start = time.time()
    try:
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        end = time.time()
        return {
            "success": True,
            "duration": end - start,
            "count": len(resp.json())
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def save_baseline(metrics):
    with open(BASELINE_FILE, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"\n💾 Baseline saved to {BASELINE_FILE}")

def load_baseline():
    if os.path.exists(BASELINE_FILE):
        with open(BASELINE_FILE, 'r') as f:
            return json.load(f)
    return None

def run_suite(args):
    print("\n" + "="*50)
    print("🚀 VinSight v9.1 Performance Verification (Enhanced)")
    print("="*50)
    
    if not check_backend():
        logger.error(f"Backend not found at {BASE_URL}. Please start it using run_local.sh")
        sys.exit(1)
        
    metrics = {}
    
    # 1. Dashboard Analysis (Single)
    print(f"\n[1] Single Analysis Load ({TICKER})")
    print("-" * 30)
    res1 = benchmark_analysis(concurrency=1)
    if res1["success"]:
        print(f"✅ Duration: {res1['avg_duration']:.3f}s")
        if res1['integrity_issues']:
            print(f"⚠️ Data Issues: {res1['integrity_issues']}")
        else:
            print(f"✨ Data Integrity: 100% Pass")
        metrics['single_analysis'] = res1['avg_duration']
    else:
        print(f"❌ Failed: {res1.get('error')}")

    # 2. Concurrency Stress Test
    print(f"\n[2] Concurrency Stress (5 simultaneous reqs)")
    print("-" * 30)
    res_conc = benchmark_analysis(concurrency=5)
    if res_conc["success"]:
        print(f"✅ Wall Time: {res_conc['total_wall_time']:.3f}s")
        print(f"📊 Avg Latency: {res_conc['avg_duration']:.3f}s")
        metrics['concurrent_5_wall'] = res_conc['total_wall_time']
    else:
         print(f"❌ Failed: {res_conc.get('error')}")

    # 3. Watchlist Batch Performance
    print("\n[3] Watchlist Batching (10 Tickers)")
    print("-" * 30)
    watchlist = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "NFLX", "AMD", "PYPL"]
    res2 = benchmark_watchlist_batch(watchlist)
    if res2["success"]:
        print(f"✅ Batch Time: {res2['duration']:.3f}s")
        metrics['watchlist_10'] = res2['duration']
    else:
        print(f"❌ Failed: {res2.get('error')}")

    # 4. Comparison Logic
    if args.save_baseline:
        save_baseline(metrics)
        
    if args.compare:
        baseline = load_baseline()
        if baseline:
            print("\n" + "="*50)
            print("🆚 BASELINE COMPARISON")
            print("-" * 50)
            for k, v in metrics.items():
                base_v = baseline.get(k)
                if base_v:
                    delta = v - base_v
                    pct = (delta / base_v) * 100
                    icon = "🟢" if delta < 0 else "🔴"
                    print(f"{k:<20}: {base_v:.3f}s -> {v:.3f}s ({pct:+.1f}%) {icon}")
                else:
                    print(f"{k:<20}: New Metric")
        else:
            print("\n❌ No baseline found to compare against.")

    print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--save-baseline", action="store_true", help="Save current metrics as baseline")
    parser.add_argument("--compare", action="store_true", help="Compare against saved baseline")
    args = parser.parse_args()
    run_suite(args)
