
import time
import yfinance as yf
import concurrent.futures

tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK-B", "LLY", "V", "TSM", "AVGO", "NVO", "JPM", "WMT", "XOM", "MA", "UNH", "PG", "JNJ"]

def test_fast_info_sequential():
    start = time.time()
    batch = yf.Tickers(" ".join(tickers))
    results = []
    for t_str in tickers:
        t = batch.tickers.get(t_str)
        fi = t.fast_info
        results.append(fi.last_price)
    print(f"Sequential fast_info: {time.time() - start:.4f}s")

def test_fast_info_threaded():
    start = time.time()
    batch = yf.Tickers(" ".join(tickers))
    results = []
    def fetch(sym):
        t = batch.tickers.get(sym)
        return t.fast_info.last_price
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        list(executor.map(fetch, tickers))
    print(f"Threaded fast_info: {time.time() - start:.4f}s")

def test_download_batch():
    start = time.time()
    # 1y history for all
    data = yf.download(tickers, period="1y", group_by='ticker', progress=False)
    # Access last price for each
    for t in tickers:
        try:
            _ = data[t]['Close'].iloc[-1]
        except: pass
    print(f"yf.download batch (1y): {time.time() - start:.4f}s")

if __name__ == "__main__":
    print(f"Testing {len(tickers)} tickers...")
    test_fast_info_sequential()
    test_fast_info_threaded()
    test_download_batch()
