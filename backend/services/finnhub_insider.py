# Finnhub Insider Sentiment Service
# Provides MSPR (Monthly Share Purchase Ratio) for insider activity analysis

import os
import requests
import logging
from typing import Optional, Dict, List
from cachetools import TTLCache

logger = logging.getLogger(__name__)

# Cache for 15 minutes to respect rate limits (60 calls/min free tier)
_insider_cache = TTLCache(maxsize=100, ttl=900)

def is_available() -> bool:
    """Check if Finnhub API key is configured."""
    return bool(os.getenv("FINNHUB_API_KEY"))

def get_insider_sentiment(ticker: str) -> Optional[Dict]:
    """
    Fetch insider sentiment from Finnhub API.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        {
            'mspr': float,          # 0-1 (1=all buying, 0=all selling)
            'change': int,          # Net share change (last 3 months)
            'activity_label': str,  # 'Net Buying', 'No Activity', 'Mixed/Minor Selling', 'Heavy Selling'
            'source': 'finnhub'
        }
        
        Returns None if API unavailable or error occurs.
    """
    api_key = os.getenv("FINNHUB_API_KEY")
    
    if not api_key:
        logger.warning("FINNHUB_API_KEY not set, falling back to yfinance")
        return None
    
    # Check cache
    cache_key = f"finnhub_insider_{ticker}"
    if cache_key in _insider_cache:
        logger.info(f"Returning cached Finnhub insider data for {ticker}")
        return _insider_cache[cache_key]
    
    try:
        url = "https://finnhub.io/api/v1/stock/insider-sentiment"
        params = {
            "symbol": ticker,
            "token": api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Check for valid response
        sentiment_data = data.get("data", [])
        if not sentiment_data:
            logger.info(f"No insider sentiment data for {ticker}")
            return None
        
        # Get last 3 months of data
        recent_data = sentiment_data[-3:] if len(sentiment_data) >= 3 else sentiment_data
        
        # Calculate average MSPR and total change
        total_mspr = 0.0
        total_change = 0
        count = 0
        
        for month in recent_data:
            mspr = month.get("mspr", 0.5)  # Default to neutral
            change = month.get("change", 0)
            total_mspr += mspr
            total_change += change
            count += 1
        
        avg_mspr = total_mspr / count if count > 0 else 0
        
        # Classify activity based on MSPR (-100 to 100 range)
        # Positive = more buying, Negative = more selling
        if avg_mspr > 20:
            activity_label = "Net Buying"
        elif avg_mspr > -20:
            activity_label = "No Activity"  # Neutral zone
        elif avg_mspr > -50:
            activity_label = "Mixed/Minor Selling"
        else:
            activity_label = "Heavy Selling"
        
        result = {
            "mspr": round(avg_mspr, 3),
            "change": total_change,
            "activity_label": activity_label,
            "months_analyzed": count,
            "source": "finnhub"
        }
        
        # Cache the result
        _insider_cache[cache_key] = result
        
        logger.info(f"Finnhub insider sentiment for {ticker}: MSPR={avg_mspr:.2f}, Label={activity_label}")
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching Finnhub insider data: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in Finnhub insider: {e}")
        return None
def get_insider_transactions(ticker: str) -> List[Dict]:
    """
    Fetch raw insider transactions from Finnhub API and format for the UI.
    Includes heuristic 10b5-1 detection for the fallback.
    """
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return []

    try:
        url = "https://finnhub.io/api/v1/stock/insider-transactions"
        params = {"symbol": ticker, "token": api_key}
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        raw_trans = data.get("data", [])
        if not raw_trans:
            return []
            
        formatted = []
        for t in raw_trans[:50]: # Top 50 recent
            # Heuristic detection for Finnhub's transaction types
            # Finnhub provides 'transactionCode' (e.g., 'S' for Sell, 'P' for Purchase, 'A' for Award)
            code = t.get("transactionCode", "")
            is_automatic = code in ['A', 'M', 'X'] # Award, Exercise, etc.
            
            # Map labels
            reason = "market_trade"
            if code == 'A': reason = "compensation_award"
            if code == 'M' or code == 'X': reason = "option_exercise"
            
            formatted.append({
                "Date": t.get("transactionDate", "N/A"),
                "Insider": t.get("name", "Unknown"),
                "Position": "Officer/Director", # Finnhub doesn't always provide specific position here
                "Text": f"Finnhub Code: {code}",
                "Value": t.get("transactionPrice", 0) * t.get("change", 0) if t.get("transactionPrice") else 0,
                "Shares": t.get("change", 0),
                "isAutomatic": is_automatic,
                "detectionReason": reason
            })
        return formatted
    except Exception as e:
        logger.error(f"Finnhub transaction fallback error: {e}")
        return []
