import yfinance as yf
import pandas as pd
import math
from cachetools import cached, TTLCache
import concurrent.futures

# Separate caches to avoid key collisions since functions share the same `ticker` argument
cache_info = TTLCache(maxsize=100, ttl=600)
cache_peg = TTLCache(maxsize=100, ttl=600)
cache_inst = TTLCache(maxsize=100, ttl=600)

@cached(cache_info)
def get_stock_info(ticker: str):
    """Fetch basic info for a stock."""
    stock = yf.Ticker(ticker)
    info = stock.info
    
    # Enrich with calculated flags
    peg = info.get('pegRatio')
    if peg is not None and peg < 1.0:
        info['valuation_flag'] = "Undervalued"
        
    return info

def get_stock_history(ticker: str, period="1mo", interval="1d"):
    """Fetch historical data."""
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period, interval=interval)
    hist.reset_index(inplace=True)
    
    # Standardize Date column for frontend
    if 'Datetime' in hist.columns:
        hist.rename(columns={'Datetime': 'Date'}, inplace=True)
    
    # Convert dates to string for JSON serialization
    if 'Date' in hist.columns:
        hist['Date'] = hist['Date'].astype(str)
        
    return hist.to_dict(orient="records")

@cached(cache_peg)
def get_peg_ratio(ticker: str) -> float:
    """
    Fetch PEG ratio (Price/Earnings to Growth) from yfinance.
    Returns 0 if not available.
    
    PEG Ratio = P/E Ratio / Earnings Growth Rate
    < 1.0: Potentially undervalued
    1.0-2.0: Fair value
    > 2.0: Potentially overvalued
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        peg = info.get('pegRatio', 0) or info.get('trailingPegRatio', 0) or 0
        
        # Sometimes yfinance returns negative or very large PEG ratios (data issues)
        # Filter out unreasonable values
        if isinstance(peg, dict):
            return 0
            
        if peg < 0 or peg > 10:
            return 0
        
        return peg
    except Exception as e:
        print(f"Error fetching PEG ratio for {ticker}: {e}")
        return 0


def get_news(ticker: str):
    """Fetch news for a stock."""
    stock = yf.Ticker(ticker)
    news = stock.news
    # Normalize data for frontend
    data = []
    for item in news:
        try:
            # Check if data is nested in 'content' (common in new yfinance structure)
            info = item.get('content', item)
            
            if not isinstance(info, dict):
                continue

            # Extract fields with fallbacks
            title = info.get('title')
            
            # Link can be in clickThroughUrl (object) or link (string)
            link = info.get('clickThroughUrl', {}).get('url')
            if not link:
                link = item.get('link') # Fallback to top-level
                
            # Publisher
            publisher = info.get('provider', {}).get('displayName') or "Yahoo Finance"
            
            # Time: prefer providerPublishTime (unix), else pubDate (iso)
            publish_time = item.get('providerPublishTime')
            if not publish_time and 'pubDate' in info:
                publish_time = info['pubDate'] # Frontend might need to parse this
                
            # Thumbnail
            thumb = info.get('thumbnail', {}).get('resolutions', [{}])[0].get('url') if info.get('thumbnail') else None
            
            data.append({
                "title": title,
                "link": link,
                "publisher": publisher,
                "providerPublishTime": publish_time,
                "thumbnail": thumb
            })
        except Exception as e:
            print(f"Error parsing news item: {e}")
            continue
    # Sort by latest first
    data.sort(key=lambda x: x.get('providerPublishTime', 0) or 0, reverse=True)
    return data

@cached(cache_inst)
def get_institutional_holders(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        # We'll just get major holders for the summary
        # inst = stock.institutional_holders # Returns DataFrame, need to serialize
        # major = stock.major_holders # Returns DataFrame
        # For simplicity in this MVP, we will try to get raw dicts if possible or convert DF
        
        # Let's try to get a summary
        info = stock.info
        holders = {
            "insidersPercentHeld": info.get("heldPercentInsiders", 0),
            "institutionsPercentHeld": info.get("heldPercentInstitutions", 0),
            "institutionsCount": 0 # Not easily available in simple info, needing DataFrame parsing
        }
        
        # Parse Institutional Holders
        try:
            inst_df = stock.institutional_holders
            if inst_df is not None and not inst_df.empty:
                # Top 5
                top_holders = inst_df.head(5).to_dict(orient='records')
                # Clean keys
                cleaned_holders = []
                for h in top_holders:
                    cleaned_holders.append({
                        "Holder": h.get("Holder", "Unknown"),
                        "Shares": h.get("Shares", 0),
                        "Date Reported": str(h.get("Date Reported", "")),
                        "% Out": h.get("% Out", h.get("pctHeld", 0))
                    })
                holders["top_holders"] = cleaned_holders
        except:
            holders["top_holders"] = []

        # Parse Insider Transactions (New)
        try:
            trans_df = stock.insider_transactions
            if trans_df is not None and not trans_df.empty:
                # Top 10 recent
                recent_trans = trans_df.head(10).to_dict(orient='records')
                cleaned_trans = []
                for t in recent_trans:
                    # Handle NaN values for JSON serialization
                    shares = t.get("Shares", 0)
                    value = t.get("Value", 0)
                    
                    # Convert NaN to None for proper JSON serialization
                    if isinstance(shares, float) and math.isnan(shares):
                        shares = None
                    if isinstance(value, float) and math.isnan(value):
                        value = None
                    
                    cleaned_trans.append({
                        "Date": str(t.get("Start Date", "")).split(" ")[0], # Keep just date part
                        "Insider": t.get("Insider", "Unknown"),
                        "Position": t.get("Position", ""),
                        "Text": t.get("Text", ""), # e.g. "Sale at price..."
                        "Shares": shares,
                        "Value": value
                    })
                holders["insider_transactions"] = cleaned_trans
            else:
                holders["insider_transactions"] = []
        except Exception as e:
            print(f"Error getting insider transactions: {e}")
            holders["insider_transactions"] = []
            
        return holders
    except Exception as e:
        print(f"Error getting holders: {e}")
        return {"top_holders": [], "insider_transactions": []}

def get_batch_stock_details(tickers: list):
    """
    Fetch details for multiple stocks in parallel.
    Optimized for Dashboard Watchlist Summary.
    """
    def fetch_one(ticker):
        try:
            # We use get_stock_info because it's now cached!
            # If we call this for 10 stocks, and they were recently accessed, it's instant.
            # Even if not, we run in parallel.
            info = get_stock_info(ticker)
            return {
                "symbol": ticker,
                "currentPrice": info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 0),
                "regularMarketChange": info.get('regularMarketChange') or 0,
                "regularMarketChangePercent": info.get('regularMarketChangePercent') or 0,
                "previousClose": info.get('regularMarketPreviousClose') or info.get('previousClose', 0),
                "marketCap": info.get('marketCap'),
                "trailingPE": info.get('trailingPE'),
                "fiftyTwoWeekHigh": info.get('fiftyTwoWeekHigh')
            }
        except Exception as e:
            print(f"Error fetching batch detail for {ticker}: {e}")
            return None

    results = []
    # Use ThreadPoolExecutor for parallel I/O
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_ticker = {executor.submit(fetch_one, t): t for t in tickers}
        for future in concurrent.futures.as_completed(future_to_ticker):
            data = future.result()
            if data:
                results.append(data)
    
    return results

def generate_ai_recommendation(ticker: str, analysis: dict, sentiment: dict, fundamentals: dict = {}):
    """
    Rule-based 'AI' analyst.
    Inputs: 
       analysis: { rsi: number, sma: { sma_50: number, ... }, current_price: number }
       sentiment: { polarity: number, label: string }
       fundamentals: { trailingPE, beta, profitMargins, fiftyTwoWeekHigh, fiftyTwoWeekLow, ... }
    """
    score = 0
    reasons = []
    
    current_price = analysis.get('current_price', 0)
    
    # Outlook buckets
    short_term_signals = []
    medium_term_signals = []
    long_term_signals = []

    # --- Short Term (Days/Weeks) ---
    # 1. Momentum (SMA 5 vs 10) - implied from `analysis` dict structure if available, 
    # but we might need to rely on what's passed. 
    # Assumes 'analysis' dict has been updated to include these from the `calculate_technical_indicators` 
    # output IF that was passed in. However, the `analysis` arg here usually comes from `analysis.py`'s result structure.
    # We will need to adapt if the caller didn't pass specific fields.
    
    # RSI
    rsi = analysis.get('rsi', 50)
    if rsi < 30:
        score += 2
        short_term_signals.append("RSI Oversold: Potential knee-jerk bounce.")
    elif rsi > 70:
        score -= 2
        short_term_signals.append("RSI Overbought: Risk of immediate pullback.")
    else:
        short_term_signals.append("RSI Neutral.")
        
    # --- Medium Term (Weeks/Months) ---
    # SMA 50 Trend
    sma50 = analysis.get('sma', {}).get('sma_50')
    if sma50:
        if current_price > sma50:
            score += 1
            medium_term_signals.append("Bullish: Price above 50-day SMA.")
        else:
            score -= 1
            medium_term_signals.append("Bearish: Price below 50-day SMA.")

    # PEG Ratio (Growth at a Reasonable Price)
    peg = fundamentals.get('pegRatio')
    if peg:
        if peg < 1.0:
            score += 1
            medium_term_signals.append(f"Undervalued: PEG {peg:.2f} < 1.0.")
        elif peg > 2.0:
            score -= 0.5
            medium_term_signals.append(f"Overvalued Growth: PEG {peg:.2f} > 2.0.")

    # Sentiment
    sent_score = sentiment.get('polarity', 0)
    if sent_score > 0.1:
        score += 0.5
        medium_term_signals.append("News sentiment is Positive.")
    elif sent_score < -0.1:
        score -= 0.5
        medium_term_signals.append("News sentiment is Negative.")

    # --- Long Term (Months/Years) ---
    # P/E Evaluation
    pe = fundamentals.get('trailingPE')
    if pe:
        if pe < 15: # Traditional value
            score += 1
            long_term_signals.append(f"Value Territory: P/E {pe:.2f} is low.")
        elif pe > 60: # High growth/risk
            score -= 1
            long_term_signals.append(f"High Valuation: P/E {pe:.2f}.")

    # Profitability (Margins)
    margins = fundamentals.get('profitMargins')
    if margins and margins > 0.20:
        score += 1
        long_term_signals.append("High Quality: Strong Profit Margins (>20%).")
        
    # SMA 200 (The ultimate trend filter) - extracted from analysis if passed
    # NOTE: The current `finance.py` calling this might need to ensure SMA_200 is passed in `analysis['sma']`
    # We'll handle it gracefully if missing.
    sma200 = analysis.get('sma', {}).get('sma_200')
    if sma200:
        if current_price > sma200:
            score += 1
            long_term_signals.append("Long-term Uptrend: Price above 200-day SMA.")
        else:
            score -= 1
            long_term_signals.append("Long-term Downtrend: Price below 200-day SMA.")

    # Decision Logic
    if score >= 3:
        rating = "BUY"
        color = "emerald"
    elif score <= -2:
        rating = "SELL"
        color = "red"
    else:
        rating = "HOLD"
        color = "yellow"
        
    # Flatten reasons for backward compatibility, but we really want the structure
    all_reasons = short_term_signals + medium_term_signals + long_term_signals
    
    # Normalize score to 0-100 for frontend display
    # Raw score range is approx -6 to +8
    # 0 = Hold/Neutral (50)
    # +5 = Strong Buy (100)
    # -5 = Strong Sell (0)
    normalized_score = int(max(0, min(100, 50 + (score * 10))))

    return {
        "rating": rating,
        "color": color,
        "score": normalized_score,
        "justification": " ".join(all_reasons),
        "outlooks": {
            "short_term": short_term_signals,
            "medium_term": medium_term_signals,
            "long_term": long_term_signals
        }
    }
