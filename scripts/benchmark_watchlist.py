
import time
import yfinance as yf
import concurrent.futures
import pandas as pd


TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "BRK-B", "JNJ", "V", 
    "WMT", "JPM", "PG", "MA", "UNH", "HD", "DIS", "PYPL", "BAC", "VZ", 
    "ADBE", "CMCSA", "NFLX", "KO", "NKE", "PEP", "MRK", "T", "PFE", "INTC", 
    "CSCO", "ABT", "XOM", "CVX", "CRM", "ABBV", "COST", "MCD", "MDT", "DHR",
    "NEE", "TXN", "HON", "UPS", "PM", "QCOM", "BMY", "UNP", "LOW", "ORCL"
]


def fetch_one_current(ticker):
    try:
        stock = yf.Ticker(ticker)
        # Simulate the current implementation
        info = stock.info
        hist = stock.history(period="1y")
        return info.get('currentPrice'), len(hist)
    except Exception as e:
        return None

def fetch_batch_optimized(tickers):
    try:
        # 1. Batch history
        start_hist = time.time()
        hist_data = yf.download(tickers, period="1y", group_by='ticker', progress=False)
        hist_time = time.time() - start_hist
        print(f"Batch History fetch: {hist_time:.2f}s")
        
        # 2. Fast Info (simulated loop but lighter)
        start_info = time.time()
        # Newer yfinance has .fast_info or we can use the history last close
        # But for 'info', let's see if we can avoid it or use fast_info
        
        results = {}
        for t in tickers:
             stock = yf.Ticker(t)
             # fast_info is much faster for price
             try:
                 price = stock.fast_info['last_price']
             except:
                 price = 0
             results[t] = price
             
        info_time = time.time() - start_info
        print(f"Fast Info fetch: {info_time:.2f}s")
        
        return results
    except Exception as e:
        print(e)
        return None

def benchmark_current():
    print(f"Benchmarking Current Implementation (10 threads) for {len(TICKERS)} tickers...")
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        list(executor.map(fetch_one_current, TICKERS))
    end = time.time()
    print(f"Current Implementation Total Time: {end - start:.2f}s")

def benchmark_proposed():
    print(f"Benchmarking Proposed Implementation (Batch download + FastInfo)...")
    start = time.time()
    fetch_batch_optimized(TICKERS)
    end = time.time()
    print(f"Proposed Implementation Total Time: {end - start:.2f}s")

if __name__ == "__main__":
    benchmark_current()
    print("-" * 20)
    benchmark_proposed()
