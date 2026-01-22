import yfinance as yf
import pandas as pd
import math
from cachetools import cached, TTLCache
import concurrent.futures
import time
from datetime import datetime

# Separate caches to avoid key collisions since functions share the same `ticker` argument
cache_info = TTLCache(maxsize=100, ttl=600)
cache_peg = TTLCache(maxsize=100, ttl=600)
cache_inst = TTLCache(maxsize=100, ttl=600)
cache_spy = TTLCache(maxsize=1, ttl=3600) # Cache SPY for 1 hour

[... keep all existing functions unchanged until get_batch_stock_details ...]

def get_batch_stock_details(tickers: list):
    """
    Fetch details for multiple stocks in parallel.
    Optimized for Dashboard Watchlist Summary.
    Now includes 5D, 1M,6M, YTD performance and EPS.
    """
    def fetch_one(ticker):
        try:
            info = get_stock_info(ticker)
            
            def safe_val(val):
                if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                    return None
                return val
            
            # Get historical data for performance
            five_day = one_month = six_month = ytd = None
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1y")
                
                if not hist.empty:
                    current = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 0)
                    
                    # Calculate changes
                    def pct_change(days):
                        if len(hist) > days and current:
                            past = hist['Close'].iloc[-days]
                            if past > 0:
                                return ((current - past) / past) * 100
                        return None
                    
                    five_day = pct_change(5)
                    one_month = pct_change(21)
                    six_month = pct_change(126)
                    
                    # YTD
                    year_start = datetime(datetime.now().year, 1, 1)
                    ytd_hist = hist[hist.index >= year_start]
                    if len(ytd_hist) > 0 and current:
                        ytd_price = ytd_hist['Close'].iloc[0]
                        if ytd_price > 0:
                            ytd = ((current - ytd_price) / ytd_price) * 100
            except:
                pass

            return {
                "symbol": ticker,
                "current Price": safe_val(info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 0)),
                "regularMarketChange": safe_val(info.get('regularMarketChange') or 0),
                "regularMarketChangePercent": safe_val(info.get('regularMarketChangePercent') or 0),
                "previousClose": safe_val(info.get('regularMarketPreviousClose') or info.get('previousClose', 0)),
                "fiveDayChange": safe_val(five_day),
                "oneMonthChange": safe_val(one_month),
                "sixMonthChange": safe_val(six_month),
                "ytdChange": safe_val(ytd),
                "trailingEps": safe_val(info.get('trailingEps')),
                "trailingPE": safe_val(info.get('trailingPE')),
                "fiftyTwoWeekHigh": safe_val(info.get('fiftyTwoWeekHigh'))
            }
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            return None

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_ticker = {executor.submit(fetch_one, t): t for t in tickers}
        for future in concurrent.futures.as_completed(future_to_ticker):
            data = future.result()
            if data:
                results.append(data)
    
    return results
