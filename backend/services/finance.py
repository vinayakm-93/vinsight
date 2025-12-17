import yfinance as yf
import pandas as pd
import math
from cachetools import cached, TTLCache
import concurrent.futures
import time

# Separate caches to avoid key collisions since functions share the same `ticker` argument
cache_info = TTLCache(maxsize=100, ttl=600)
cache_peg = TTLCache(maxsize=100, ttl=600)
cache_inst = TTLCache(maxsize=100, ttl=600)
cache_spy = TTLCache(maxsize=1, ttl=3600) # Cache SPY for 1 hour

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
        
        # Try to get Finnhub MSPR for more accurate insider sentiment
        try:
            from services.finnhub_insider import get_insider_sentiment, is_available
            
            if is_available():
                finnhub_data = get_insider_sentiment(ticker)
                if finnhub_data:
                    holders["insider_mspr"] = finnhub_data.get("mspr", 0.5)
                    holders["insider_activity"] = finnhub_data.get("activity_label", "No Activity")
                    holders["insider_source"] = "finnhub"
                else:
                    holders["insider_mspr"] = 0.5
                    holders["insider_activity"] = "No Activity"
                    holders["insider_source"] = "finnhub_unavailable"
            else:
                holders["insider_mspr"] = 0.5
                holders["insider_activity"] = "No Activity"
                holders["insider_source"] = "yfinance_fallback"
        except Exception as e:
            print(f"Error getting Finnhub insider data: {e}")
            holders["insider_mspr"] = 0.5
            holders["insider_activity"] = "No Activity"
            holders["insider_source"] = "error_fallback"
            
        return holders
    except Exception as e:
        print(f"Error getting holders: {e}")
        return {"top_holders": [], "insider_transactions": [], "insider_mspr": 0.5, "insider_activity": "No Activity"}

@cached(cache_spy)
def get_market_regime():
    """
    Fetch S&P 500 (SPY) status to determine Macro Regime.
    Returns:
        {
            "bull_regime": bool, # True if Price > SMA200
            "spy_price": float,
            "spy_sma200": float
        }
    """
    try:
        spy = yf.Ticker("SPY")
        # Need 200 days for SMA, fetch 1y to be safe
        hist = spy.history(period="1y")
        
        if hist.empty or len(hist) < 200:
             # Fallback: Assume Bull if no data
             return {"bull_regime": True, "spy_price": 0, "spy_sma200": 0}
             
        current_price = hist['Close'].iloc[-1]
        sma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        
        # Determine regime
        is_bull = current_price > sma200
        
        return {
            "bull_regime": bool(is_bull),
            "spy_price": float(current_price),
            "spy_sma200": float(sma200)
        }
    except Exception as e:
        print(f"Error fetching SPY regime: {e}")
        return {"bull_regime": True, "spy_price": 0, "spy_sma200": 0}

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
    Rule-based 'AI' analyst with industry-standard benchmarks.
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
    # RSI with industry standard thresholds (30/70)
    rsi = analysis.get('rsi', 50)
    if rsi < 30:
        score += 2
        short_term_signals.append("📈 RSI Oversold (<30): Potential bounce opportunity.")
    elif rsi > 70:
        score -= 2
        short_term_signals.append("⚠️ RSI Overbought (>70): Risk of pullback.")
    elif 50 <= rsi <= 65:
        score += 0.5
        short_term_signals.append("✓ RSI Healthy (50-65): Good momentum.")
    else:
        short_term_signals.append("○ RSI Neutral (30-50): Below average momentum.")
    
    # Beta risk for short-term volatility
    beta = fundamentals.get('beta', 1.0)
    if beta and beta > 1.5:
        short_term_signals.append(f"⚡ High volatility (Beta: {beta:.2f}): Expect larger swings.")
    elif beta and beta < 0.8:
        short_term_signals.append(f"🛡️ Low volatility (Beta: {beta:.2f}): More stable price action.")
         
    # --- Medium Term (Weeks/Months) ---
    # SMA 50 Trend
    sma50 = analysis.get('sma', {}).get('sma_50')
    if sma50:
        if current_price > sma50 * 1.05:  # 5% above SMA50
            score += 1.5
            medium_term_signals.append("📈 Strong: Price >5% above 50-day SMA.")
        elif current_price > sma50:
            score += 1
            medium_term_signals.append("✓ Bullish: Price above 50-day SMA.")
        elif current_price > sma50 * 0.95:  # Within 5% below
            score -= 0.5
            medium_term_signals.append("○ Neutral: Price within 5% of 50-day SMA.")
        else:
            score -= 1
            medium_term_signals.append("📉 Bearish: Price below 50-day SMA.")

    # PEG Ratio (Peter Lynch: <1.0 undervalued, >2.0 overvalued)
    peg = fundamentals.get('pegRatio')
    if peg and peg > 0:
        if peg < 1.0:
            score += 1.5
            medium_term_signals.append(f"💎 Undervalued: PEG {peg:.2f} < 1.0 (Peter Lynch).")
        elif peg <= 1.5:
            score += 0.5
            medium_term_signals.append(f"✓ Fair Value: PEG {peg:.2f} (reasonable growth price).")
        elif peg > 2.0:
            score -= 0.5
            medium_term_signals.append(f"⚠️ Expensive: PEG {peg:.2f} > 2.0.")

    # Sentiment with aligned thresholds (matching Groq analysis)
    sent_score = sentiment.get('polarity', 0)
    sent_label = sentiment.get('label', 'Neutral')
    if sent_label == "Positive" or sent_score > 0.4:
        score += 1
        medium_term_signals.append("📰 Positive: Bullish news sentiment detected.")
    elif sent_label == "Negative" or sent_score < -0.25:
        score -= 1
        medium_term_signals.append("📰 Negative: Bearish news sentiment detected.")
    else:
        medium_term_signals.append("📰 Neutral: Mixed/neutral news sentiment.")

    # --- Long Term (Months/Years) ---
    # P/E Evaluation (Benjamin Graham: <15 = value)
    pe = fundamentals.get('trailingPE')
    if pe and pe > 0:
        if pe < 15:
            score += 1.5
            long_term_signals.append(f"💎 Graham Value: P/E {pe:.1f} < 15 (classic value territory).")
        elif pe < 25:
            score += 0.5
            long_term_signals.append(f"✓ Reasonable: P/E {pe:.1f} (market average range).")
        elif pe > 60:
            score -= 1
            long_term_signals.append(f"⚠️ Expensive: P/E {pe:.1f} > 60 (high growth expectations).")
        else:
            long_term_signals.append(f"○ Growth premium: P/E {pe:.1f}.")

    # Profitability (Margins)
    margins = fundamentals.get('profitMargins')
    if margins:
        if margins > 0.20:
            score += 1
            long_term_signals.append(f"💪 High Quality: {margins*100:.1f}% profit margins (>20%).")
        elif margins > 0.10:
            long_term_signals.append(f"✓ Healthy margins: {margins*100:.1f}%.")
        elif margins > 0:
            long_term_signals.append(f"○ Thin margins: {margins*100:.1f}%.")
        else:
            score -= 0.5
            long_term_signals.append("⚠️ Unprofitable: Negative margins.")
    
    # 52-Week position
    high_52w = fundamentals.get('fiftyTwoWeekHigh')
    low_52w = fundamentals.get('fiftyTwoWeekLow')
    if high_52w and low_52w and current_price:
        range_pct = (current_price - low_52w) / (high_52w - low_52w) if high_52w != low_52w else 0.5
        if range_pct > 0.9:
            long_term_signals.append(f"📍 Near 52-week high ({range_pct*100:.0f}% of range).")
        elif range_pct < 0.2:
            score += 0.5
            long_term_signals.append(f"📍 Near 52-week low ({range_pct*100:.0f}% of range) - potential opportunity.")
        
    # SMA 200 (The ultimate trend filter)
    sma200 = analysis.get('sma', {}).get('sma_200')
    if sma200:
        if current_price > sma200 * 1.1:  # 10% above SMA200
            score += 1.5
            long_term_signals.append("🚀 Strong Uptrend: Price >10% above 200-day SMA.")
        elif current_price > sma200:
            score += 1
            long_term_signals.append("✓ Long-term Uptrend: Price above 200-day SMA.")
        else:
            score -= 1
            long_term_signals.append("📉 Long-term Downtrend: Price below 200-day SMA.")

    # Decision Logic with industry-aligned thresholds
    if score >= 4:
        rating = "STRONG BUY"
        color = "emerald"
    elif score >= 2:
        rating = "BUY"
        color = "emerald"
    elif score <= -3:
        rating = "SELL"
        color = "red"
    elif score <= -1:
        rating = "WEAK HOLD"
        color = "yellow"
    else:
        rating = "HOLD"
        color = "yellow"
        
    # Flatten reasons for backward compatibility
    all_reasons = short_term_signals + medium_term_signals + long_term_signals
    
    # Normalize score to 0-100 for frontend display
    # Raw score range is approx -6 to +10
    normalized_score = int(max(0, min(100, 50 + (score * 8))))

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
