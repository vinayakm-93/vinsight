import yfinance as yf
import pandas as pd
import numpy as np
import math
from datetime import datetime
import time
import requests
import logging
from typing import Optional
import concurrent.futures

# Configure logger
logger = logging.getLogger(__name__)

# Caching
from services.disk_cache import stock_info_cache, price_cache, analysis_cache, holders_cache
from cachetools import cached, TTLCache
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
def get_peg_ratio(ticker: str) -> Optional[float]:
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
        peg = info.get('pegRatio') or info.get('trailingPegRatio')
        
        # Sometimes yfinance returns negative or very large PEG ratios (data issues)
        # Filter out unreasonable values
        if peg is None or isinstance(peg, dict) or peg < 0 or peg > 10:
            # Fallback: Calculate manually if P/E and Growth are available
            # PEG = P/E / (Annual Growth Rate * 100)
            pe = info.get('trailingPE')
            growth = info.get('earningsQuarterlyGrowth') # Approximation using recent growth
            
            if pe and growth and growth > 0:
                manual_peg = pe / (growth * 100)
                if manual_peg > 0 and manual_peg < 10:
                    return manual_peg
            
            return None
        
        return peg
    except Exception as e:
        print(f"Error fetching PEG ratio for {ticker}: {e}")
        return None


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

def get_institutional_change(ticker: str, stock=None) -> dict:
    """
    Calculate Quarter-over-Quarter (QoQ) change in institutional holdings.
    """
    try:
        stock = stock or yf.Ticker(ticker)
        
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
    # SELLING SIGNALS
    # Cluster Selling: 3+ sells within 14 days
    is_cluster_selling = False
    cluster_size = 0
    if sell_count >= 3:
        sell_dates = []
        for t in transactions:
            text = t.get('Text', '').lower()
            if 'sale' in text and not t.get('isAutomatic', False):
                 # Try to parse date
                 d_str = t.get('Date', '')
                 if d_str:
                     try:
                         # Handle "YYYY-MM-DD"
                         from datetime import datetime
                         dt = datetime.strptime(d_str.split(' ')[0], '%Y-%m-%d')
                         sell_dates.append(dt)
                     except:
                         pass
        
        sell_dates.sort()
        # Check for 3 sells in 14 days
        if len(sell_dates) >= 3:
            for i in range(len(sell_dates) - 2):
                if (sell_dates[i+2] - sell_dates[i]).days <= 14:
                    is_cluster_selling = True
                    cluster_size = len(sell_dates) # Or specific cluster count
                    break

    if is_cluster_selling:
        label = f"{len(sell_dates)} Cluster Selling"
        score = -8 # Red
        summary_text = f"High alert: {len(sell_dates)} insider sells detected (Cluster)."
    elif net_flow < 0:
        label = f"Sell by {len(unique_sellers)} insiders" 
        score = -4 # Yellow
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
def get_institutional_holders(ticker: str, stock_obj=None):
    """Fetch institutional holders with persistent caching."""
    # Note: If stock_obj is provided, we might be bypassing cache if we don't check it.
    # But usually this is called with just ticker from other places, so we keep the cache check.
    cache_key = f"inst_{ticker}"
    cached_data = holders_cache.get(cache_key)
    if cached_data:
        return cached_data

    try:
        stock = stock_obj if stock_obj else yf.Ticker(ticker)
        
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
    Optimized: Uses 1 hour TTL cache (cache_spy).
    """
    try:
        # Check if we have a robust cached value locally first (in case of restart loop)
        # But @cached handles the in-memory part.
        
        spy = yf.Ticker("SPY")
        # Need 200 days for SMA, fetch 1y to be safe
        hist = spy.history(period="1y")
        
        if hist.empty or len(hist) < 200:
             # Fallback: Assume Bull if no data
             return {"bull_regime": True, "spy_price": 0, "spy_sma200": 0}
             
        current_price = hist['Close'].iloc[-1]
        sma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        
        return {
            "bull_regime": bool(current_price > sma200),
            "spy_price": float(current_price),
            "spy_sma200": float(sma200)
        }
    except Exception as e:
        logger.error(f"Error serving market regime: {e}")
        return {"bull_regime": True, "spy_price": 0, "spy_sma200": 0}

def fetch_coordinated_analysis_data(ticker: str):
    """
    Coordinator function that fetches ALL necessary analysis data using a SINGLE yf.Ticker instance.
    This replaces the "waterfall" or "10-thread parallel" approach that created 5+ Ticker objects.
    """
    stock = yf.Ticker(ticker)
    logger.info(f"Coordinator: Created single Ticker object for {ticker}")
    
    # We use a ThreadPool only for the methods that yfinance doesn't auto-batch well or internal processing
    # But crucially, we pass the SAME stock object or rely on its internal shared session if possible.
    
    results = {}
    
    def get_info():
        try:
           return stock.info 
        except Exception as e:
            logger.warning(f"Coordinator [Info] failed for {ticker}: {e}")
            return {}
        
    def get_history():
        try:
            # history() typically handles its own session
            h = stock.history(period="2y", interval="1d")
            # Convert to list of dicts immediately to save memory/processing later
            if h.empty: return []
            return [{
                "Date": index.isoformat(),
                "Open": row['Open'], 
                "High": row['High'], 
                "Low": row['Low'], 
                "Close": row['Close'], 
                "Volume": row['Volume']
            } for index, row in h.iterrows()]
        except Exception as e:
            logger.error(f"Coordinator [History] failed for {ticker}: {e}")
            return []

    def get_news_data():
        try:
            # Reimplementing get_news logic but using the existing stock object
            news_items = stock.news
            clean_news = []
            for item in (news_items or []):
                 try:
                    # Normalize logic (same as get_news)
                    info = item.get('content', item)
                    if not info: continue
                    clean_news.append({
                        "title": info.get('title'),
                        "link": info.get('clickThroughUrl', {}).get('url') or item.get('link'),
                        "publisher": info.get('provider', {}).get('displayName') or "Yahoo",
                        "providerPublishTime": item.get('providerPublishTime') or info.get('pubDate'),
                        "thumbnail": info.get('thumbnail', {}).get('resolutions', [{}])[0].get('url') if info.get('thumbnail') else None
                    })
                 except: continue
            return sorted(clean_news, key=lambda x: x.get('providerPublishTime', 0) or 0, reverse=True)
        except: return []

    def get_institutional():
        try:
            # Manually constructing what get_institutional_holders does, but reusing stock
             # 1. Holders
             # 2. Insider Trans
             # 3. Institutional Change (requires stock.institutional_holders)
             
             holders = {"top_holders": [], "insider_transactions": [], "smart_money": {}}
             
             # Info usage (already fetched? no, yfinance caches info property)
             # But we can access it from the other thread's result if we waited, but better to just hit it.
             i = stock.info
             holders["insidersPercentHeld"] = i.get("heldPercentInsiders", 0)
             holders["institutionsPercentHeld"] = i.get("heldPercentInstitutions", 0)
             
             # Smart Money / Change
             inst_df = stock.institutional_holders
             if inst_df is not None and not inst_df.empty:
                  # Calculate Change Logic (Inline from get_institutional_change)
                  # ... (Simplified for brevity, assuming we want the full logic)
                  # For now, let's call the utility but pass the dataframe if possible? 
                  # get_institutional_change takes ticker, creates new object. 
                  # Let's just use the existing function if we can't easily refactor it to take a Ticker object
                  # *But* the goal is to reuse the object.
                  # Let's trust yfinance's internal caching for now or accept one extra call if unavoidable, 
                  # BUT for "institutional_holders" property, accessing it once caches it on the object.
                  pass
             
             # To deeply integrate, we really should refactor the helper functions to take 'stock' as arg.
             # But as a "Coordinator", we can just do the raw fetches here.
             
             # Let's call the original get_institutional_holders but patch it? No, that's messy.
             # Best approach: This function returns the raw yfinance data, and we let the route/service process it?
             # Or we fully reimplement the extraction logic here. 
             # Let's fallback to calling the separate functions in parallel for now BUT
             # updating them to accept an optional 'stock_obj' would be the cleanest code change.
             
             # STRATEGY: Update get_institutional_holders to accept stock_obj
             return get_institutional_holders(ticker, stock_obj=stock)
        except Exception as e:
            print(f"Inst error: {e}")
            return {}

    def get_financials_metrics():
        # Consolidated advanced metrics
        # Requires: info, quarterly_financials, quarterly_balance_sheet, financials
        metrics = {
            "gross_margin_trend": "Flat", "interest_coverage": 100.0, "debt_to_ebitda": 0.0,
            "altman_z_score": 3.0, "revenue_growth_3y_cagr": 0.0,
            "return_on_assets": 0.0, "current_ratio": 0.0
        }
        try:
            i = stock.info
            metrics['return_on_assets'] = i.get('returnOnAssets', 0.0) or 0.0
            metrics['current_ratio'] = i.get('currentRatio', 0.0) or 0.0
            
            # Debt/EBITDA
            debt = i.get('totalDebt')
            ebitda = i.get('ebitda')
            if debt and ebitda and ebitda > 0: metrics['debt_to_ebitda'] = debt / ebitda
            
            # We need QF, QBS, AF
            qf = stock.quarterly_financials
            qbs = stock.quarterly_balance_sheet
            af = stock.financials
            
            # ... (Rest of logic from get_advanced_metrics, but using these local vars)
            # Re-implementing the core logic inline or calling a refactored version
            # usage: get_advanced_metrics(ticker, stock_obj=stock)
            return get_advanced_metrics(ticker, stock_obj=stock)
        except: return metrics

    # Execute all in parallel using the SHARED stock instance
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        f_info = executor.submit(get_info)
        f_hist = executor.submit(get_history)
        f_news = executor.submit(get_news_data)
        f_inst = executor.submit(get_institutional)
        f_fin = executor.submit(get_financials_metrics)
        
        # Earnings is separate (scraped/different source usually, or requires specialized parsing)
        # analyze_earnings takes a DB session, so we leave it to the route or call it here if we want.
        # But analyze_earnings creates its own Ticker usually.
        # Let's return the main data chunks.
        
        results['info'] = f_info.result()
        results['history'] = f_hist.result()
        results['news'] = f_news.result()
        results['institutional'] = f_inst.result()
        results['advanced'] = f_fin.result()
        
    return results

def get_batch_prices(tickers: list):
    """
    Lightweight fetch for Watchlist Sidebar using yf.Tickers (Batch).
    """
    from services import yahoo_client
    results = []
    
    if not tickers: return []
    
    try:
        # Use yf.Tickers for batching
        # Note: yf.Tickers("A B C") creates a Tickers object
        # We need to access .tickers dict
        batch = yf.Tickers(" ".join(tickers))
        
        # Accessing .tickers triggers the initialization, but the data fetch for fast_info 
        # is per-ticker but shared session helps. 
        # Actually yf.download is the only true "batch" fetch for history.
        # fast_info is still iterative but lightweight.
        # However, reusing the session in Tickers is better than new Ticker() each time.
        
        def fetch_fast(t_obj, symbol):
            try:
                fi = t_obj.fast_info
                last = fi.last_price
                prev = fi.previous_close
                change = last - prev if prev else 0
                pct = (change / prev * 100) if prev else 0
                return {
                    "symbol": symbol,
                    "currentPrice": last,
                    "previousClose": prev,
                    "regularMarketChange": change,
                    "regularMarketChangePercent": pct,
                    "companyName": symbol 
                }
            except: 
                return None

        # Threaded access to the batch objects
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            # batch.tickers is a dict { "SYM": Ticker object }
            # If a symbol is invalid, it might not be in the dict or accessing it works but fast_info fails
            futures = []
            for sym in tickers:
                # Tickers access might correspond to lazy loading
                t = batch.tickers.get(sym)
                if not t: t = yf.Ticker(sym) # Fallback
                futures.append(executor.submit(fetch_fast, t, sym))
                
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if res: results.append(res)
                
    except Exception as e:
        logger.error(f"Batch fetch error: {e}")
        # Fallback to old method?
        return []

    return results

def get_batch_stock_details(tickers: list):
    """
    Fetch details for multiple stocks in parallel (Optimized v9.2).
    Uses yf.download() for single-shot history retrieval + yf.Tickers for info.
    """
    if not tickers: return []
    
    results = []
    try:
        # 1. Fetch History for ALL tickers in ONE call
        # group_by='ticker' makes it easy to access data per symbol
        # auto_adjust=True gives us adjusted closes appropriate for returns
        hist_data = yf.download(tickers, period="1y", group_by='ticker', progress=False, auto_adjust=True)
        
        # 2. Fetch Info (Fast Access)
        batch = yf.Tickers(" ".join(tickers))
        
        for ticker in tickers:
            try:
                # Helper to get scalar from 1-level or 2-level DF
                # If only 1 ticker in list, columns are (Open, High...), not (AAPL, Open)
                if len(tickers) == 1:
                    df = hist_data
                else:
                    try:
                        df = hist_data[ticker]
                    except KeyError:
                         # Ticker might be missing in history download (delisted/error)
                         df = pd.DataFrame()
                
                # Get basic info
                t_obj = batch.tickers.get(ticker) or yf.Ticker(ticker)
                # fast_info is faster than .info dictionary
                fi = t_obj.fast_info
                
                current = fi.last_price
                prev_close = fi.previous_close
                if not current and not df.empty:
                    current = df['Close'].iloc[-1]
                
                # Metrics Calculation
                five_day = None
                one_month = None
                six_month = None
                ytd_change = None
                sma20 = None
                sma50 = None
                
                if not df.empty and len(df) > 0:
                    closes = df['Close']
                    
                    def get_pct(days):
                        if len(closes) > days:
                            past = closes.iloc[-days-1] # -days-1 to mimic N trading days ago roughly
                            if past > 0:
                                return ((current - past) / past) * 100
                        return None
                    
                    five_day = get_pct(5)
                    one_month = get_pct(21)
                    six_month = get_pct(126)
                    
                    # SMA
                    if len(closes) >= 20:
                        sma20 = closes.rolling(window=20).mean().iloc[-1]
                    if len(closes) >= 50:
                        sma50 = closes.rolling(window=50).mean().iloc[-1]
                        
                    # YTD
                    try:
                        current_year = pd.Timestamp.now().year
                        # Find last close of previous year
                        last_year_end = df[df.index.year == (current_year - 1)]
                        if not last_year_end.empty:
                            start_price = last_year_end['Close'].iloc[-1]
                            if start_price > 0:
                                ytd_change = ((current - start_price) / start_price) * 100
                    except: pass
                
                # PE/EPS - Hard to get from fast_info, fall back to "info" lazily or skip if slow
                # For dashboard table, PE is often displayed.
                # Accessing .info triggers a request per stock. 
                # Optimization: For simple dashboard tables, maybe skip or fetch async if critical?
                # Let's try to get it from info but catch timeout?
                # Actually, skipping PE for batch speed is better, or use cached info.
                
                # Let's just use 0/None for now to keep it fast, or maybe t_obj.info (slow)
                # Given user wants SPEED, we rely on fast_info.
                # If we really need PE, we'd need separate calls.
                # Check if we have cached info?
                
                info = {} # Empty by default to skip heavy call
                # If you want to enable slow info fetch, uncomment:
                # try: info = t_obj.info
                # except: pass
                
                results.append({
                    "symbol": ticker,
                    "currentPrice": current,
                    "regularMarketChange": (current - prev_close) if prev_close else 0,
                    "regularMarketChangePercent": ((current - prev_close)/prev_close * 100) if prev_close else 0,
                    "previousClose": prev_close,
                    "fiveDayChange": five_day,
                    "oneMonthChange": one_month,
                    "sixMonthChange": six_month,
                    "ytdChangePercent": ytd_change,
                    "sma20": sma20,
                    "sma50": sma50,
                    "trailingEps": info.get('trailingEps'),
                    "trailingPE": info.get('trailingPE'),
                    "fiftyTwoWeekHigh": fi.year_high
                })
                
            except Exception as inner_e:
                print(f"Error processing batch ticker {ticker}: {inner_e}")
                
    except Exception as e:
        print(f"Batch download error: {e}")
        return []

    return results
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



def get_advanced_metrics(ticker: str, stock_obj=None) -> dict:
    """
    Fetch advanced financial metrics required for CFA-level scoring.
    """
    metrics = {
        "gross_margin_trend": "Flat",
        "interest_coverage": 100.0, # Default to safe
        "debt_to_ebitda": 0.0,
        "altman_z_score": 3.0,
        "revenue_growth_3y_cagr": 0.0, # 3-year CAGR
        "return_on_assets": 0.0,
        "current_ratio": 0.0
    }
    
    try:
        stock = stock_obj if stock_obj else yf.Ticker(ticker)
        
        # 1. Info extraction
        info = stock.info
        metrics['return_on_assets'] = info.get('returnOnAssets', 0.0) or 0.0
        metrics['current_ratio'] = info.get('currentRatio', 0.0) or 0.0
        
        # Debt/EBITDA
        total_debt = info.get('totalDebt')
        ebitda = info.get('ebitda')
        if total_debt and ebitda and ebitda > 0:
            metrics['debt_to_ebitda'] = total_debt / ebitda
            
        # 2. Quarterly Financials (For Margin Trend & Coverage)
        qf = stock.quarterly_financials
        if not qf.empty:
            # Gross Margin Trend
            if 'Gross Profit' in qf.index and 'Total Revenue' in qf.index:
                rev = qf.loc['Total Revenue']
                gp = qf.loc['Gross Profit']
                margins = (gp / rev).dropna()
                
                if len(margins) >= 2:
                    current = margins.iloc[0] # Most recent
                    previous = margins.iloc[1] # Previous quarter
                    
                    if current > previous * 1.01:
                        metrics['gross_margin_trend'] = "Rising"
                    elif current < previous * 0.99:
                        metrics['gross_margin_trend'] = "Falling"
            
            # Interest Coverage
            if 'EBIT' in qf.index and 'Interest Expense' in qf.index:
                ebit_series = qf.loc['EBIT']
                int_series = qf.loc['Interest Expense']
                
                # Take most recent non-NaN
                ebit = ebit_series.iloc[0] if not pd.isna(ebit_series.iloc[0]) else 0
                interest = int_series.iloc[0] if not pd.isna(int_series.iloc[0]) else 0
                
                if interest and interest != 0:
                    metrics['interest_coverage'] = ebit / abs(interest)
                else:
                    metrics['interest_coverage'] = 100.0 # Infinite coverage
        
        # 3. Revenue Growth (3y CAGR)
        af = stock.financials
        if not af.empty and 'Total Revenue' in af.index:
             revs = af.loc['Total Revenue'].dropna()
             if len(revs) >= 3:
                 current_rev = revs.iloc[0]
                 # Ideally 3 years ago (iloc[3]) but often only 4 cols avail
                 years = min(len(revs)-1, 3)
                 old_rev = revs.iloc[years]
                 
                 if old_rev > 0 and current_rev > 0:
                     cagr = (current_rev / old_rev) ** (1/years) - 1
                     metrics['revenue_growth_3y_cagr'] = cagr
        
        # 4. Altman Z-Score
        qbs = stock.quarterly_balance_sheet
        if not qbs.empty and not qf.empty:
             try:
                 total_assets = qbs.loc['Total Assets'].iloc[0] if 'Total Assets' in qbs.index else 0
                 
                 # Liabilities
                 total_liab = 0
                 if 'Total Liabilities Net Minority Interest' in qbs.index:
                     total_liab = qbs.loc['Total Liabilities Net Minority Interest'].iloc[0]
                 elif 'Total Liab' in qbs.index:
                     total_liab = qbs.loc['Total Liab'].iloc[0]
                 else:
                     # Estimate
                     total_liab = total_assets * 0.5
                 
                 # Working Capital
                 working_capital = 0
                 if 'Working Capital' in qbs.index:
                     working_capital = qbs.loc['Working Capital'].iloc[0]
                 elif 'Total Assets' in qbs.index: # Rough proxy if missing
                      working_capital = total_assets * 0.1
                      
                 retained_earnings = qbs.loc['Retained Earnings'].iloc[0] if 'Retained Earnings' in qbs.index else 0
                 
                 # Components from Financials
                 ebit = qf.loc['EBIT'].iloc[0] if ('EBIT' in qf.index and not pd.isna(qf.loc['EBIT'].iloc[0])) else 0
                 sales = qf.loc['Total Revenue'].iloc[0] if ('Total Revenue' in qf.index and not pd.isna(qf.loc['Total Revenue'].iloc[0])) else 0
                 market_cap = info.get('marketCap', 0)
                 
                 if total_assets > 0:
                     A = working_capital / total_assets
                     B = retained_earnings / total_assets
                     C = (ebit * 4) / total_assets # Annualized EBIT
                     D = market_cap / total_liab if total_liab > 0 else 10.0
                     E = (sales * 4) / total_assets # Annualized Sales
                     
                     # Altman Z-Score Formula
                     z_score = 1.2*A + 1.4*B + 3.3*C + 0.6*D + 1.0*E
                     metrics['altman_z_score'] = z_score
             except Exception as ez:
                 print(f"Z-Score calc error: {ez}")
                 
    except Exception as e:
        print(f"Error fetching advanced metrics for {ticker}: {e}")
        
    return metrics
