import yfinance as yf
import pandas as pd
import math
from cachetools import cached, TTLCache
import concurrent.futures
import time
import requests

from services.disk_cache import stock_info_cache, price_cache, analysis_cache, holders_cache
from services.finnhub_insider import is_available

# yf_session removed to allow yfinance to handle its own session (v7.4 fix)

cache_info = TTLCache(maxsize=100, ttl=600)
cache_peg = TTLCache(maxsize=100, ttl=600)
cache_inst = TTLCache(maxsize=100, ttl=600)
cache_spy = TTLCache(maxsize=1, ttl=3600)
cache_analyst = TTLCache(maxsize=100, ttl=3600)


@cached(cache_info)
def get_stock_info(ticker: str):
    """Fetch basic info for a stock with persistent caching."""
    # 1. Check persistent disk cache first
    cached_data = stock_info_cache.get(f"info_{ticker}")
    if cached_data:
        return cached_data

    # 2. Fetch from yfinance
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Clean info of NaN/Inf for JSON safety
        cleaned_info = {}
        for k, v in info.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                cleaned_info[k] = None
            else:
                cleaned_info[k] = v
    except Exception as e:
        print(f"yfinance info error for {ticker}: {e}")
        # Raise so fallback can catch
        raise e

    # Enrich with calculated flags
    peg = cleaned_info.get('pegRatio')
    if peg is not None and peg < 1.0:
        cleaned_info['valuation_flag'] = "Undervalued"
        
    # Calculate FCF Yield
    fcf = cleaned_info.get('freeCashflow')
    mkt_cap = cleaned_info.get('marketCap')
    if fcf and mkt_cap and mkt_cap > 0:
        cleaned_info['fcf_yield'] = fcf / mkt_cap
    else:
        cleaned_info['fcf_yield'] = 0.0

    # v7.3 Enhancements: Ensure specific keys exist for Scorer
    # ... (skipping mapping for brevity as I'll include it in the replace)
    if 'returnOnEquity' not in cleaned_info:
        cleaned_info['returnOnEquity'] = 0.0
    if 'returnOnAssets' not in cleaned_info:
        cleaned_info['returnOnAssets'] = 0.0
    if 'forwardPE' not in cleaned_info:
        cleaned_info['forwardPE'] = cleaned_info.get('trailingPE', 0.0) # Fallback
    if 'currentRatio' not in cleaned_info:
        cleaned_info['currentRatio'] = 0.0
    if 'operatingMargins' not in cleaned_info:
        cleaned_info['operatingMargins'] = cleaned_info.get('profitMargins', 0.0)
    
    # 3. Store in disk cache before returning
    if cleaned_info:
        stock_info_cache.set(f"info_{ticker}", cleaned_info)
        
    return cleaned_info

@cached(cache_analyst)
def get_analyst_targets(ticker: str) -> dict:
    """
    Fetch analyst price targets and recommendations from Yahoo Finance.
    Returns: target_low, target_mean, target_high, target_median, 
             recommendation_mean, recommendation_key, number_of_analysts
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Get current price for upside/downside calculation
        current_price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
        
        # Extract analyst target data
        target_low = info.get('targetLowPrice')
        target_high = info.get('targetHighPrice')
        target_mean = info.get('targetMeanPrice')
        target_median = info.get('targetMedianPrice')
        num_analysts = info.get('numberOfAnalystOpinions', 0)
        
        # Recommendation data
        rec_mean = info.get('recommendationMean')  # 1=Strong Buy, 5=Sell
        rec_key = info.get('recommendationKey', 'none')  # e.g., "buy", "hold", "sell"
        
        # Calculate upside/downside if we have data
        upside_pct = None
        if target_mean and current_price and current_price > 0:
            upside_pct = ((target_mean - current_price) / current_price) * 100
        
        # Clean NaN values
        def clean_val(v):
            if v is None:
                return None
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                return None
            return v
        
        return {
            "current_price": clean_val(current_price),
            "target_low": clean_val(target_low),
            "target_high": clean_val(target_high),
            "target_mean": clean_val(target_mean),
            "target_median": clean_val(target_median),
            "upside_pct": clean_val(upside_pct),
            "num_analysts": num_analysts or 0,
            "recommendation_mean": clean_val(rec_mean),
            "recommendation_key": rec_key,
            "has_data": target_mean is not None and num_analysts > 0
        }
    except Exception as e:
        print(f"Error fetching analyst targets for {ticker}: {e}")
        return {
            "current_price": None,
            "target_low": None,
            "target_high": None,
            "target_mean": None,
            "target_median": None,
            "upside_pct": None,
            "num_analysts": 0,
            "recommendation_mean": None,
            "recommendation_key": "none",
            "has_data": False
        }

def get_earnings_surprise(ticker: str) -> float:

    """Fetch recent EPS surprise %."""
    try:
        stock = yf.Ticker(ticker)
        # earnings_history returns DataFrame
        hist = stock.earnings_history
        if hist is not None and not hist.empty:
            # Sort by date desc just in case
            # Usually indexed by date
            # It usually has 'Surprise' column
            recent = hist.iloc[0] # Most recent
            return recent.get('Surprise', 0)
    except:
        return 0.0
    return 0.0

def get_stock_history(ticker: str, period="1mo", interval="1d"):
    """Fetch historical data with persistent caching."""
    cache_key = f"hist_{ticker}_{period}_{interval}"
    cached_data = price_cache.get(cache_key)
    if cached_data:
        return cached_data

    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period, interval=interval)
        
        if hist.empty:
            return []
            
        # Convert to list of dicts for frontend
        data = []
        for index, row in hist.iterrows():
            data.append({
                "Date": index.isoformat(),
                "Open": row['Open'],
                "High": row['High'],
                "Low": row['Low'],
                "Close": row['Close'],
                "Volume": row['Volume']
            })
            
        if data:
            price_cache.set(cache_key, data)
            
        return data
    except Exception as e:
        print(f"Error fetching history for {ticker}: {e}")
        # Raise so route fallback can catch
        raise e

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
    for item in (news or []):
        if not item:
            continue
        try:
            # Check if data is nested in 'content' (common in new yfinance structure)
            info = item.get('content', item)
            
            if not info or not isinstance(info, dict):
                continue

            # Extract fields with fallbacks
            title = info.get('title')
            
            # Link can be in clickThroughUrl (object) or link (string)
            link = info.get('clickThroughUrl', {}).get('url')
            if not link:
                link = item.get('link') # Fallback to top-level
                
            # Publisher
            publisher = info.get('provider', {}).get('displayName') or "Yahoo Finance"
            
            publish_time = item.get('providerPublishTime') or info.get('providerPublishTime')
            if not publish_time and 'pubDate' in info:
                publish_time = info['pubDate']
                
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

def get_institutional_change(ticker: str) -> dict:
    """
    Calculate Quarter-over-Quarter (QoQ) change in institutional holdings.
    Returns:
        {
            "change_pct": float, # Percentage change
            "change_shares": int, # Net share change
            "accumulating": bool, # True if positive change
            "label": str, # Descriptive label
            "period": str # Reporting period (e.g., "Q4 2025")
        }
    """
    try:
        stock = yf.Ticker(ticker)
        
        # We need the institutional holders DataFrame
        inst_df = stock.institutional_holders
        
        if inst_df is None or inst_df.empty:
            return {"change_pct": 0.0, "change_shares": 0, "accumulating": False, "label": "No Data"}
            
        # Check if we have pctChange column (standard in yfinance)
        if 'pctChange' not in inst_df.columns and '% Change' not in inst_df.columns:
            return {"change_pct": 0.0, "change_shares": 0, "accumulating": False, "label": "No Data"}
            
        col_name = 'pctChange' if 'pctChange' in inst_df.columns else '% Change'
        shares_col = 'Shares'
        
        # Calculate weighted change
        total_shares = 0
        weighted_change_sum = 0
        net_shares_change = 0
        
        for index, row in inst_df.iterrows():
            shares = row.get(shares_col, 0)
            change = row.get(col_name, 0)
            
            if pd.isna(shares) or pd.isna(change):
                continue
                
            total_shares += shares
            weighted_change_sum += (shares * change)
            
            # Estimate net shares change
            # If change is 0.05 (5%), original shares were shares / (1 + 0.05)
            original_shares = shares / (1 + change)
            diff = shares - original_shares
            net_shares_change += diff
            
        if total_shares == 0:
             return {"change_pct": 0.0, "change_shares": 0, "accumulating": False, "label": "Neutral", "period": "N/A"}
             
        avg_change_pct = weighted_change_sum / total_shares
        
        # Determine label
        if avg_change_pct >= 0.02: # +2%
            label = "Strong Accumulation"
        elif avg_change_pct >= 0.005: # +0.5%
            label = "Accumulating"
        elif avg_change_pct <= -0.02: # -2%
            label = "Strong Distribution"
        elif avg_change_pct <= -0.005: # -0.5%
            label = "Distributing"
        else:
            label = "Hold / Stable"
            
        # Get most recent reporting date
        latest_date = "N/A"
        if not inst_df.empty and 'Date Reported' in inst_df.columns:
            try:
                most_recent = inst_df['Date Reported'].max()
                if isinstance(most_recent, pd.Timestamp) or hasattr(most_recent, 'month'):
                    q = (most_recent.month - 1) // 3 + 1
                    latest_date = f"Q{q} {most_recent.year}"
                else:
                    latest_date = str(most_recent).split(' ')[0]
            except:
                latest_date = "Recent"

        return {
            "change_pct": float(avg_change_pct),
            "change_shares": int(net_shares_change),
            "accumulating": avg_change_pct > 0,
            "label": label,
            "period": latest_date
        }
        
    except Exception as e:
        print(f"Error calculating institutional change for {ticker}: {e}")
        return {"change_pct": 0.0, "change_shares": 0, "accumulating": False, "label": "No Data", "period": "N/A"}

def calculate_insider_signal(transactions: list) -> dict:
    """
    Analyzes 90-day discretionary insider transactions to determine a signal.
    transactions: List of dicts with 'Text', 'Value', 'Shares', 'is_automatic' keys.
    """
    if not transactions:
        return {
            "label": "No Recent Activity",
            "score": 0,
            "net_flow": 0,
            "total_bought": 0,
            "total_sold": 0,
            "trans_count": 0
        }
        
    total_bought = 0
    total_sold = 0
    buy_count = 0
    sell_count = 0
    unique_buyers = set()
    unique_sellers = set()
    
    # NEW: Track top official buying and repeat buyers
    top_official_titles = ['ceo', 'cfo', 'coo', 'president', 'chairman', 'chief', 'director']
    top_official_buying = False
    top_official_buyer_name = None
    top_official_selling = False
    top_official_seller_name = None
    buyer_counts = {}  # Track repeat buyers
    seller_counts = {}  # Track repeat sellers
    
    for t in transactions:
        # We only analyze discretionary trades for the signal to be meaningful
        text = t.get('Text', '').lower()
        # Fallback check if isAutomatic not present
        if t.get('isAutomatic', False) or 'gift' in text or 'award' in text or 'grant' in text:
            continue
            
        value = t.get('Value', 0) or 0
        insider = t.get('Insider', 'Unknown')
        position = t.get('Position', '').lower()
        
        if 'purchase' in text or 'buy' in text:
            total_bought += value
            buy_count += 1
            unique_buyers.add(insider)
            
            # Track repeat buyers
            buyer_counts[insider] = buyer_counts.get(insider, 0) + 1
            
            # Check if top official is buying
            if any(title in position for title in top_official_titles):
                top_official_buying = True
                top_official_buyer_name = insider
                
        elif 'sale' in text:
            total_sold += value
            sell_count += 1
            unique_sellers.add(insider)
            
            # Track repeat sellers
            seller_counts[insider] = seller_counts.get(insider, 0) + 1
            
            # Check if top official is selling
            if any(title in position for title in top_official_titles):
                top_official_selling = True
                top_official_seller_name = insider
            
    net_flow = total_bought - total_sold
    
    # Find repeat buyers/sellers (2+ times)
    repeat_buyers = [name for name, count in buyer_counts.items() if count >= 2]
    repeat_sellers = [name for name, count in seller_counts.items() if count >= 2]
    has_repeat_buying = len(repeat_buyers) > 0
    has_repeat_selling = len(repeat_sellers) > 0
    
    # Determine Label
    label = "Neutral"
    score = 0 # -10 to +10
    
    # Logic Trees (Simplified: Executive Buying, Buying, Cluster Selling, Selling)
    if buy_count == 0 and sell_count == 0:
        label = "No Activity"
        summary_text = "No discretionary trades in the last 90 days."
    # BUYING SIGNALS
    elif top_official_buying and net_flow > 0:
        label = "Executive Buying"
        score = 9
        summary_text = f"Top executive ({top_official_buyer_name.split()[0] if top_official_buyer_name else 'Official'}) buying shares."
    elif net_flow > 0:
        label = "Buying"
        score = 6
        if len(unique_buyers) >= 3:
            summary_text = f"Coordinated buying by {len(unique_buyers)} insiders."
        elif has_repeat_buying:
            summary_text = f"{repeat_buyers[0].split()[0]} buying multiple times."
        else:
            summary_text = f"{len(unique_buyers)} insider(s) accumulating shares."
    # SELLING SIGNALS
    elif len(unique_sellers) >= 3 and sell_count > buy_count:
        label = "Cluster Selling"
        score = -8
        summary_text = f"Cluster of {len(unique_sellers)} executives selling."
    elif net_flow < 0:
        label = "Selling"
        score = -5
        summary_text = f"Net selling pressure by {len(unique_sellers)} insider(s)."
    else:
        label = "Mixed"
        summary_text = "Mixed buying and selling activity."
        
    return {
        "label": label,
        "score": score,
        "net_flow": net_flow,
        "total_bought": total_bought,
        "total_sold": total_sold,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "trans_count": buy_count + sell_count,
        "unique_insiders": len(unique_buyers | unique_sellers),
        "summary_text": summary_text,
        "top_official_buying": top_official_buying,
        "repeat_buyers": repeat_buyers
    }

@cached(cache_inst)
def get_institutional_holders(ticker: str):
    """Fetch institutional holders with persistent caching."""
    cache_key = f"inst_{ticker}"
    cached_data = holders_cache.get(cache_key)
    if cached_data:
        return cached_data

    try:
        stock = yf.Ticker(ticker)
        
        # Initialize holders with defaults
        holders = {
            "top_holders": [],
            "insider_transactions": [],
            "insidersPercentHeld": 0,
            "institutionsPercentHeld": 0,
            "institutionsCount": 0,
            "smart_money": {"change_pct": 0.0, "change_shares": 0, "accumulating": False, "label": "No Data"}
        }

        # Try to get info safely
        try:
            info = stock.info
            holders["insidersPercentHeld"] = info.get("heldPercentInsiders", 0)
            holders["institutionsPercentHeld"] = info.get("heldPercentInstitutions", 0)
        except Exception as e:
            print(f"yfinance info error in holders for {ticker}: {e}")
        
        # Parse Institutional Holders
        try:
            inst_df = stock.institutional_holders
            if inst_df is not None and not inst_df.empty:
                # Fetch all holders (removed head(5) limit for frontend sorting)
                top_holders = inst_df.to_dict(orient='records')
                # Clean keys
                cleaned_holders = []
                for h in top_holders:
                    shares = h.get("Shares", 0)
                    pct_out = h.get("% Out", h.get("pctHeld", 0))
                    
                    if isinstance(shares, float) and math.isnan(shares):
                        shares = None
                    if isinstance(pct_out, float) and math.isnan(pct_out):
                        pct_out = None

                    cleaned_holders.append({
                        "Holder": h.get("Holder", "Unknown"),
                        "Shares": shares,
                        "Date Reported": str(h.get("Date Reported", "")),
                        "% Out": pct_out
                    })
                holders["top_holders"] = cleaned_holders
            
            # Calculate Smart Money Signal (Institutional Change)
            change_data = get_institutional_change(ticker)
            holders["smart_money"] = change_data
            
        except Exception as e:
            print(f"Institutional fetch error for {ticker}: {e}")
            holders["top_holders"] = []
            holders["smart_money"] = {"change_pct": 0.0, "change_shares": 0, "accumulating": False, "label": "No Data (Rate Limited)"}
            holders["status"] = "rate_limited"

        # Parse Insider Transactions - Use yfinance with heuristic 10b5-1 detection
        try:
            trans_df = stock.insider_transactions
            if trans_df is not None and not trans_df.empty:
                # TOP 50 recent transactions (increased from 15 for 90-day window)
                recent_trans = trans_df.to_dict(orient='records')
                cleaned_trans = []
                automatic_count = 0
                discretionary_count = 0
                
                # Use a 90-day window for SIGNALS, but return ALL for TABLE
                from datetime import datetime, timedelta
                cutoff_date = datetime.now() - timedelta(days=90)
                
                # Validation checks for signal calculation
                signal_trans = []

                for t in recent_trans:
                    # Handle Date
                    date_val = t.get("Start Date")
                    if not date_val:
                        continue
                    
                    try:
                        # yfinance usually returns pandas Timestamp or string
                        if isinstance(date_val, str):
                            tx_date = datetime.strptime(date_val.split(" ")[0], '%Y-%m-%d')
                        else:
                            tx_date = date_val.to_pydatetime()
                            
                        # Format for JSON
                        date_str = str(t.get("Start Date", "")).split(" ")[0] if t.get("Start Date") else "N/A"
                        
                        # Filter ALL transactions for the last 90 days
                        if tx_date < cutoff_date:
                            continue
                    except Exception as e:
                        print(f"Error parsing date {date_val}: {e}")
                        continue

                    # Handle NaN values for JSON serialization
                    shares = t.get("Shares", 0)
                    value = t.get("Value", 0)
                    text = t.get("Text", "").lower()
                    
                    # Convert NaN to None for proper JSON serialization
                    if isinstance(shares, float) and math.isnan(shares):
                        shares = None
                    if isinstance(value, float) and math.isnan(value):
                        value = None
                    
                    # HEURISTIC 10b5-1 DETECTION based on transaction type
                    is_automatic = False
                    detection_reason = "discretionary"
                    
                    # Rule 1: Stock gifts - always exclude (not real trades)
                    if 'gift' in text:
                        is_automatic = True
                        detection_reason = "stock_gift"
                    # Rule 2: Stock awards/grants - compensation plans (automatic)
                    elif 'award' in text or 'grant' in text:
                        is_automatic = True
                        detection_reason = "compensation_award"
                    # Rule 3: Option exercises - typically scheduled (automatic)
                    elif 'option exercise' in text or 'exercise' in text:
                        is_automatic = True
                        detection_reason = "option_exercise"
                    # Rule 4: Conversion transactions - typically automatic
                    elif 'conversion' in text or 'converted' in text:
                        is_automatic = True
                        detection_reason = "conversion"
                    # Rule 5: Sales/Purchases at price - likely discretionary
                    elif 'sale at price' in text or 'purchase at price' in text:
                        is_automatic = False
                        detection_reason = "market_trade"
                    
                    # Only contribute to Signal counts if within 90 days
                    if tx_date >= cutoff_date:
                        if is_automatic:
                            automatic_count += 1
                        else:
                            discretionary_count += 1
                        
                        # Add to signal calculation list
                        # We reconstruct the dict to match what calculate_insider_signal expects (or pass the clean one)
                        signal_obj = {
                            "Date": date_str,
                            "Insider": t.get("Insider", "Unknown"),
                            "Position": t.get("Position", "Unknown"),
                            "Text": text,
                            "Value": value,
                            "Shares": shares,
                            "isAutomatic": is_automatic,
                            "detectionReason": detection_reason
                        }
                        signal_trans.append(signal_obj)
                    
                    cleaned_trans.append({
                        "Date": date_str,
                        "Insider": t.get("Insider", "Unknown"),
                        "Position": t.get("Position", "Unknown"),
                        "Text": text,
                        "Value": value,
                        "Shares": shares,
                        "isAutomatic": is_automatic,
                        "detectionReason": detection_reason
                    })
                    
                holders["insider_transactions"] = cleaned_trans
                holders["insider_source"] = "yfinance_heuristic"
                holders["insider_metadata"] = {
                    "total": len(cleaned_trans),
                    "discretionary_90d": discretionary_count,
                    "automatic_10b5_1_90d": automatic_count,
                    "days_analyzed": 90,
                    "detection_method": "heuristic_text_patterns"
                }

                # --- NEW: Calculate Insider Signal Summary ---
                # Use ONLY the 90-day window transactions for the signal
                sid = calculate_insider_signal(signal_trans)
                # Attach counts for UI (Level 2 Hierarchy)
                sid['discretionary_count'] = discretionary_count
                sid['automatic_count'] = automatic_count
                holders["insider_signal"] = sid
                
                print(f"Heuristic 10b5-1 detection for {ticker}: {discretionary_count} discretionary, {automatic_count} automatic (90d)")
            else:
                holders["insider_transactions"] = []
                holders["insider_signal"] = calculate_insider_signal([])
                holders["insider_source"] = "yfinance"

                # Trigger fallback if empty
                if is_available():
                    print(f"yfinance insiders empty for {ticker}, trying Finnhub fallback")
                    from services import finnhub_insider
                    finnhub_trans = finnhub_insider.get_insider_transactions(ticker)
                    if finnhub_trans:
                        holders["insider_transactions"] = finnhub_trans
                        holders["insider_source"] = "finnhub"
                        discretionary = sum(1 for t in finnhub_trans if not t.get('isAutomatic', False))
                        automatic = sum(1 for t in finnhub_trans if t.get('isAutomatic', False))
                        holders["insider_signal"] = calculate_insider_signal(finnhub_trans)
                        holders["insider_signal"]['discretionary_count'] = discretionary
                        holders["insider_signal"]['automatic_count'] = automatic
        except Exception as e:
            print(f"Error getting insider transactions from yfinance: {e}")
            
            # --- FALLBACK: Use Finnhub for Insiders if yfinance fails ---
            if is_available():
                print(f"Attempting Finnhub fallback for {ticker} insiders")
                try:
                    from services.finnhub_insider import get_insider_sentiment
                    # We can use the insider sentiment we already have or fetch transactions
                    # but for the TABLE we want transactions. Let's add that to finnhub_insider.py
                    from services import finnhub_insider
                    finnhub_trans = finnhub_insider.get_insider_transactions(ticker)
                    if finnhub_trans:
                        holders["insider_transactions"] = finnhub_trans
                        holders["insider_source"] = "finnhub"
                        # Calc simple signal from finnhub data
                        discretionary = sum(1 for t in finnhub_trans if not t.get('isAutomatic', False))
                        automatic = sum(1 for t in finnhub_trans if t.get('isAutomatic', False))
                        holders["insider_signal"] = calculate_insider_signal(finnhub_trans)
                        holders["insider_signal"]['discretionary_count'] = discretionary
                        holders["insider_signal"]['automatic_count'] = automatic
                        if holders:
                            holders_cache.set(f"inst_{ticker}", holders)
                        return holders
                except Exception as ef:
                    print(f"Finnhub fallback failed: {ef}")

            holders["insider_transactions"] = []
            holders["insider_signal"] = calculate_insider_signal([])
            holders["insider_source"] = "error"
            
        return holders
    except Exception as e:
        print(f"Error getting holders for {ticker}: {e}")
        # Raise so route fallback can catch
        raise e

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
        return {"bull_regime": True, "spy_price": 0, "spy_sma200": 0}

def get_batch_prices(tickers: list):
    """
    Lightweight fetch for Watchlist Sidebar.
    Only fetches price and prev_close to calculate change.
    Uses yf.Ticker.fast_info which is much faster than .info or .history.
    Falls back to direct Yahoo API if rate limited.
    """
    from services import yahoo_client
    
    def fetch_fast_price(ticker):
        try:
            t = yf.Ticker(ticker)
            # accessing fast_info constitutes the fetch
            fi = t.fast_info
            last_price = fi.last_price
            prev_close = fi.previous_close
            
            change = last_price - prev_close if prev_close else 0
            change_percent = (change / prev_close * 100) if prev_close else 0
            
            return {
                "symbol": ticker,
                "currentPrice": last_price,
                "previousClose": prev_close,
                "regularMarketChange": change,
                "regularMarketChangePercent": change_percent,
                "companyName": ticker # Fallback since we aren't doing the slow Info fetch
            }
        except Exception as e:
            # Fallback to yahoo_client on rate limit
            if "Too Many Requests" in str(e) or "Rate limited" in str(e):
                print(f"Rate limited for {ticker}, using yahoo_client fallback")
                chart = yahoo_client.get_chart_data(ticker, interval="1d", range_="5d")
                if chart and chart.get("meta"):
                    meta = chart["meta"]
                    last_price = meta.get("regularMarketPrice", 0)
                    prev_close = meta.get("chartPreviousClose", 0)
                    change = last_price - prev_close if prev_close else 0
                    change_percent = (change / prev_close * 100) if prev_close else 0
                    return {
                        "symbol": ticker,
                        "currentPrice": last_price,
                        "previousClose": prev_close,
                        "regularMarketChange": change,
                        "regularMarketChangePercent": change_percent,
                        "companyName": meta.get("shortName", ticker)
                    }
            print(f"Error fetching {ticker}: {e}")
            return None

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_fast_price, t): t for t in tickers}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                results.append(res)
                
    return results

def get_batch_stock_details(tickers: list):
    """
    Fetch details for multiple stocks in parallel.
    Optimized: Single API call per stock for all metrics.
    Calculates: 5D%, 1M%, 6M%, SMA20, SMA50, EPS, P/E, YTD%
    """
    from services import yahoo_client
    
    def fetch_one(ticker):
        try:
            # Single yfinance call for ALL data
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="1y")
            
            def safe_val(val):
                if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                    return None
                return val
            
            # Get current price
            current = safe_val(info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 0))
            
            # Initialize metrics
            five_day = one_month = six_month = None
            sma20 = sma50 = None
            ytd_change = None

            # Calculate from historical data if available
            if not hist.empty and current:
                # Performance metrics
                def pct_change(days):
                    if len(hist) > days:
                        past = hist['Close'].iloc[-days]
                        if past > 0:
                            return ((current - past) / past) * 100
                    return None
                
                five_day = pct_change(5)
                one_month = pct_change(21)
                six_month = pct_change(126)
                
                # YTD Calculation
                try:
                    current_year = pd.Timestamp.now().year
                    prev_year = current_year - 1
                    # Ensure index is datetime
                    if not isinstance(hist.index, pd.DatetimeIndex):
                         hist.index = pd.to_datetime(hist.index)
                    
                    last_year_data = hist[hist.index.year == prev_year]
                    if not last_year_data.empty:
                        start_price = last_year_data.iloc[-1]['Close']
                        if start_price > 0:
                            ytd_change = ((current - start_price) / start_price) * 100
                except Exception as e:
                    print(f"Error calculating YTD for {ticker}: {e}")
                
                # SMA20 and SMA50
                closes = hist['Close']
                if len(closes) >= 20:
                    sma20 = safe_val(closes.rolling(window=20).mean().iloc[-1])
                if len(closes) >= 50:
                    sma50 = safe_val(closes.rolling(window=50).mean().iloc[-1])

            return {
                "symbol": ticker,
                "currentPrice": current,
                "regularMarketChange": safe_val(info.get('regularMarketChange') or 0),
                "regularMarketChangePercent": safe_val(info.get('regularMarketChangePercent') or 0),
                "previousClose": safe_val(info.get('regularMarketPreviousClose') or info.get('previousClose', 0)),
                "fiveDayChange": safe_val(five_day),
                "oneMonthChange": safe_val(one_month),
                "sixMonthChange": safe_val(six_month),
                "ytdChangePercent": safe_val(ytd_change),
                "sma20": sma20,
                "sma50": sma50,
                "trailingEps": safe_val(info.get('trailingEps')),
                "trailingPE": safe_val(info.get('trailingPE')),
                "fiftyTwoWeekHigh": safe_val(info.get('fiftyTwoWeekHigh'))
            }
        except Exception as e:
            # Fallback to yahoo_client on rate limit
            if "Too Many Requests" in str(e) or "Rate limited" in str(e) or "429" in str(e):
                print(f"Rate limited for {ticker} details, using yahoo_client fallback")
                chart = yahoo_client.get_chart_data(ticker, interval="1d", range_="1y")
                if chart and chart.get("meta"):
                    meta = chart["meta"]
                    current = meta.get("regularMarketPrice", 0)
                    prev_close = meta.get("chartPreviousClose", 0)
                    
                    # Performance from chart indicators
                    five_day = one_month = six_month = None
                    sma20 = sma50 = None
                    ytd_change = None
                    
                    quotes = chart.get("indicators", {}).get("quote", [{}])[0]
                    closes = quotes.get("close", [])
                    
                    if closes and current:
                        def pct_change_fallback(days):
                            if len(closes) > days:
                                past = closes[-days]
                                if past and past > 0:
                                    return ((current - past) / past) * 100
                            return None
                        
                        five_day = pct_change_fallback(5)
                        one_month = pct_change_fallback(21)
                        six_month = pct_change_fallback(126)
                        
                        # SMA Fallback
                        if len(closes) >= 20:
                            valid_closes = [c for c in closes[-20:] if c is not None]
                            if valid_closes:
                                sma20 = sum(valid_closes) / len(valid_closes)
                        if len(closes) >= 50:
                            valid_closes = [c for c in closes[-50:] if c is not None]
                            if valid_closes:
                                sma50 = sum(valid_closes) / len(valid_closes)

                    # Basic info
                    change = current - prev_close if prev_close else 0
                    change_pct = (change / prev_close * 100) if prev_close else 0
                    
                    # Try to get extra info from summary (might fail but we have defaults)
                    summary = yahoo_client.get_quote_summary(ticker, modules="defaultKeyStatistics,financialData")
                    eps = None
                    pe = None
                    high_52 = None
                    
                    if summary:
                        stats = summary.get("defaultKeyStatistics", {})
                        fin_data = summary.get("financialData", {})
                        eps = stats.get("trailingEps", {}).get("raw")
                        pe = stats.get("trailingPE", {}).get("raw")
                        high_52 = stats.get("fiftyTwoWeekHigh", {}).get("raw")

                    return {
                        "symbol": ticker,
                        "currentPrice": current,
                        "regularMarketChange": change,
                        "regularMarketChangePercent": change_pct,
                        "previousClose": prev_close,
                        "fiveDayChange": five_day,
                        "oneMonthChange": one_month,
                        "sixMonthChange": six_month,
                        "ytdChangePercent": ytd_change, # Harder to calc without pandas in fallback
                        "sma20": sma20,
                        "sma50": sma50,
                        "trailingEps": eps,
                        "trailingPE": pe,
                        "fiftyTwoWeekHigh": high_52
                    }
            
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


def generate_ai_recommendation(ticker: str, analysis: dict, sentiment: dict, fundamentals: dict = {}):
    """
    Rule-based 'AI' analyst with industry-standard benchmarks.
    Inputs: 
       analysis: { rsi: number, sma: { sma_50: number, ... }, current_price: number }
       sentiment: { polarity: number, label: string }
       fundamentals: { trailingPE, beta, profitMargins, fiftyTwoWeekHigh, fiftyTwoWeekLow, ... }
    
    Outlook Time Horizons:
       - 3 Months: Technical/Momentum Focus (RSI, SMA50, Volume, Sentiment)
       - 6 Months: Valuation/Growth Focus (PEG, P/E, Earnings Growth, SMA200)
       - 12 Months: Quality/Fundamental Focus (Margins, Debt, 52W Range, Dividends)
    """
    score = 0
    reasons = []
    
    current_price = analysis.get('current_price', 0)
    
    # Outlook buckets - REFOCUSED
    outlook_3m = []  # Technical/Momentum
    outlook_6m = []  # Valuation/Growth  
    outlook_12m = []  # Quality/Fundamental

    # === 3-MONTH OUTLOOK: TECHNICAL/MOMENTUM ===
    
    # RSI Momentum
    rsi = analysis.get('rsi', 50)
    if rsi < 30:
        score += 2
        outlook_3m.append("📈 RSI Oversold (<30): High bounce probability.")
    elif rsi > 70:
        score -= 2
        outlook_3m.append("⚠️ RSI Overbought (>70): Pullback risk elevated.")
    elif 50 <= rsi <= 65:
        score += 0.5
        outlook_3m.append(f"✓ Healthy momentum (RSI: {rsi:.0f}).")
    else:
        outlook_3m.append(f"○ Neutral momentum (RSI: {rsi:.0f}).")
    
    # SMA 50 Trend (3-month focus)
    sma50 = analysis.get('sma', {}).get('sma_50')
    if sma50 and current_price:
        pct_from_sma50 = ((current_price - sma50) / sma50) * 100
        if pct_from_sma50 > 5:
            score += 1.5
            outlook_3m.append(f"📈 Strong trend: +{pct_from_sma50:.1f}% above 50-day SMA.")
        elif pct_from_sma50 > 0:
            score += 1
            outlook_3m.append(f"✓ Uptrend: +{pct_from_sma50:.1f}% above 50-day SMA.")
        elif pct_from_sma50 > -5:
            score -= 0.5
            outlook_3m.append(f"○ Near support: {pct_from_sma50:.1f}% from 50-day SMA.")
        else:
            score -= 1
            outlook_3m.append(f"📉 Downtrend: {pct_from_sma50:.1f}% below 50-day SMA.")
    
    # News Sentiment (near-term catalyst)
    sent_score = sentiment.get('polarity', 0)
    sent_label = sentiment.get('label', 'Neutral')
    if sent_label == "Positive" or sent_score > 0.2:
        score += 1
        outlook_3m.append("📰 Bullish sentiment: Positive news flow.")
    elif sent_label == "Negative" or sent_score < -0.15:
        score -= 1
        outlook_3m.append("📰 Bearish sentiment: Negative news flow.")
    else:
        outlook_3m.append("📰 Neutral sentiment: Mixed news coverage.")
    
    # Beta (short-term volatility expectation)
    beta = fundamentals.get('beta', 1.0)
    if beta and beta > 1.5:
        outlook_3m.append(f"⚡ High volatility (β={beta:.2f}): Larger price swings expected.")
    elif beta and beta < 0.7:
        outlook_3m.append(f"🛡️ Low volatility (β={beta:.2f}): More stable price action.")

    # === 6-MONTH OUTLOOK: VALUATION/GROWTH ===
    
    # PEG Ratio (Peter Lynch growth-adjusted value)
    peg = fundamentals.get('pegRatio')
    if peg and peg > 0:
        if peg < 1.0:
            score += 1.5
            outlook_6m.append(f"💎 Undervalued: PEG {peg:.2f} < 1.0 (growth at discount).")
        elif peg <= 1.5:
            score += 0.5
            outlook_6m.append(f"✓ Fair value: PEG {peg:.2f} (reasonable growth price).")
        elif peg <= 2.0:
            outlook_6m.append(f"○ Slightly rich: PEG {peg:.2f}.")
        else:
            score -= 0.5
            outlook_6m.append(f"⚠️ Expensive: PEG {peg:.2f} > 2.0 (high expectations priced in).")
    
    # P/E Relative to Market
    pe = fundamentals.get('trailingPE')
    if pe and pe > 0:
        if pe < 15:
            score += 1.5
            outlook_6m.append(f"💎 Deep value: P/E {pe:.1f} (Benjamin Graham territory).")
        elif pe < 25:
            score += 0.5
            outlook_6m.append(f"✓ Reasonable: P/E {pe:.1f} (near market average).")
        elif pe > 50:
            score -= 1
            outlook_6m.append(f"⚠️ Premium: P/E {pe:.1f} (requires strong growth).")
        else:
            outlook_6m.append(f"○ Growth premium: P/E {pe:.1f}.")
    
    # SMA 200 (intermediate trend)
    sma200 = analysis.get('sma', {}).get('sma_200')
    if sma200 and current_price:
        pct_from_sma200 = ((current_price - sma200) / sma200) * 100
        if pct_from_sma200 > 10:
            score += 1.5
            outlook_6m.append(f"🚀 Strong uptrend: +{pct_from_sma200:.1f}% above 200-day SMA.")
        elif pct_from_sma200 > 0:
            score += 1
            outlook_6m.append(f"✓ Uptrend intact: +{pct_from_sma200:.1f}% above 200-day SMA.")
        else:
            score -= 1
            outlook_6m.append(f"📉 Below trend: {pct_from_sma200:.1f}% from 200-day SMA.")
    
    # Earnings Growth (forward-looking)
    earnings_growth = fundamentals.get('earningsGrowth') or fundamentals.get('earningsQuarterlyGrowth')
    if earnings_growth:
        growth_pct = earnings_growth * 100
        if growth_pct > 20:
            outlook_6m.append(f"📈 Strong growth: +{growth_pct:.1f}% earnings growth.")
        elif growth_pct > 0:
            outlook_6m.append(f"✓ Positive growth: +{growth_pct:.1f}% earnings growth.")
        else:
            outlook_6m.append(f"⚠️ Declining: {growth_pct:.1f}% earnings contraction.")

    # === 12-MONTH OUTLOOK: QUALITY/FUNDAMENTAL ===
    
    # Profit Margins (business quality)
    margins = fundamentals.get('profitMargins')
    if margins:
        margin_pct = margins * 100
        if margin_pct > 20:
            score += 1
            outlook_12m.append(f"💪 High quality: {margin_pct:.1f}% profit margin (>20%).")
        elif margin_pct > 10:
            outlook_12m.append(f"✓ Healthy margins: {margin_pct:.1f}%.")
        elif margin_pct > 0:
            outlook_12m.append(f"○ Thin margins: {margin_pct:.1f}%.")
        else:
            score -= 0.5
            outlook_12m.append("⚠️ Unprofitable: Negative margins.")
    
    # Debt-to-Equity (financial health)
    debt_equity = fundamentals.get('debtToEquity')
    if debt_equity:
        de_ratio = debt_equity / 100 if debt_equity > 10 else debt_equity  # Normalize
        if de_ratio < 0.5:
            outlook_12m.append(f"🛡️ Low debt: {de_ratio:.2f}x D/E ratio.")
        elif de_ratio < 1.0:
            outlook_12m.append(f"✓ Moderate debt: {de_ratio:.2f}x D/E ratio.")
        else:
            outlook_12m.append(f"⚠️ High leverage: {de_ratio:.2f}x D/E ratio.")
    
    # 52-Week Range Position
    high_52w = fundamentals.get('fiftyTwoWeekHigh')
    low_52w = fundamentals.get('fiftyTwoWeekLow')
    if high_52w and low_52w and current_price:
        range_pct = (current_price - low_52w) / (high_52w - low_52w) if high_52w != low_52w else 0.5
        if range_pct > 0.9:
            outlook_12m.append(f"📍 Near 52-week high ({range_pct*100:.0f}% of range).")
        elif range_pct < 0.2:
            score += 0.5
            outlook_12m.append(f"📍 Near 52-week low ({range_pct*100:.0f}%) - potential value.")
        else:
            outlook_12m.append(f"📊 Mid-range: {range_pct*100:.0f}% of 52-week range.")
    
    # Dividend Yield (income component)
    div_yield = fundamentals.get('dividendYield') or fundamentals.get('trailingAnnualDividendYield')
    if div_yield and div_yield > 0.01:
        yield_pct = div_yield * 100
        if yield_pct > 3:
            outlook_12m.append(f"💰 Strong income: {yield_pct:.2f}% dividend yield.")
        else:
            outlook_12m.append(f"💵 Income: {yield_pct:.2f}% dividend yield.")
    
    # Market Cap Size (stability indicator)
    market_cap = fundamentals.get('marketCap')
    if market_cap:
        if market_cap > 200e9:
            outlook_12m.append("🏛️ Mega-cap: High stability, lower growth potential.")
        elif market_cap > 10e9:
            outlook_12m.append("📊 Large-cap: Balanced stability and growth.")
        elif market_cap > 2e9:
            outlook_12m.append("📈 Mid-cap: Growth potential with moderate risk.")
        else:
            outlook_12m.append("🚀 Small-cap: Higher risk, higher reward potential.")

    # Decision Logic
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
    all_reasons = outlook_3m + outlook_6m + outlook_12m
    
    # Normalize score to 0-100
    normalized_score = int(max(0, min(100, 50 + (score * 8))))

    return {
        "rating": rating,
        "color": color,
        "score": normalized_score,
        "justification": " ".join(all_reasons),
        "outlooks": {
            "short_term": outlook_3m,    # 3 months
            "medium_term": outlook_6m,   # 6 months
            "long_term": outlook_12m     # 12 months
        }
    }

