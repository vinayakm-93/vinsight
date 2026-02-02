# Yahoo Finance Client with Rate Limit Protection
# Uses query2 endpoint and proper User-Agent to avoid blocking

import requests
import logging
import pandas as pd
from typing import Optional, Dict, Any, List
from cachetools import TTLCache
from services.disk_cache import price_cache, stock_info_cache, holders_cache

logger = logging.getLogger(__name__)

# Cache for API responses (1 hour TTL)
_cache = TTLCache(maxsize=200, ttl=3600)

# Browser User-Agent to avoid rate limiting
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'

# Session with proper headers
_session = requests.Session()
_session.headers.update({
    'User-Agent': USER_AGENT,
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9',
})


def get_chart_data(ticker: str, interval: str = "1d", range_: str = "1y") -> Optional[Dict[str, Any]]:
    """
    Fetch chart data directly from Yahoo Finance API.
    Uses query2 endpoint which is less rate-limited.
    """
    cache_key = f"chart_{ticker}_{interval}_{range_}"
    if cache_key in _cache:
        return _cache[cache_key]
        
    cached_data = price_cache.get(cache_key)
    if cached_data:
        return cached_data
    
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {
        "interval": interval,
        "range": range_,
        "includePrePost": "false",
    }
    
    try:
        response = _session.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("chart", {}).get("error"):
            logger.error(f"Yahoo API error for {ticker}: {data['chart']['error']}")
            return None
            
        result = data.get("chart", {}).get("result", [{}])[0]
        _cache[cache_key] = result
        price_cache.set(cache_key, result)
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching chart data for {ticker}: {e}")
        return None


def get_quote_summary(ticker: str, modules: str = "price,summaryDetail,financialData") -> Optional[Dict[str, Any]]:
    """
    Fetch quote summary from Yahoo Finance API.
    Uses query2 endpoint with proper headers.
    """
    cache_key = f"quote_{ticker}_{modules}"
    if cache_key in _cache:
        return _cache[cache_key]
        
    cached_data = stock_info_cache.get(cache_key)
    if cached_data:
        return cached_data
    
    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}"
    params = {
        "modules": modules,
    }
    
    try:
        response = _session.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("quoteSummary", {}).get("error"):
            logger.error(f"Yahoo API error for {ticker}: {data['quoteSummary']['error']}")
            return None
            
        result = data.get("quoteSummary", {}).get("result", [{}])[0]
        _cache[cache_key] = result
        stock_info_cache.set(cache_key, result)
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching quote summary for {ticker}: {e}")
        return None


def get_price(ticker: str) -> Optional[float]:
    """Get current price for a ticker."""
    chart = get_chart_data(ticker, interval="1d", range_="1d")
    if not chart:
        return None
    return chart.get("meta", {}).get("regularMarketPrice")


def get_news(ticker: str) -> List[Dict[str, Any]]:
    """
    Fetch news for a ticker from Yahoo Finance RSS.
    """
    cache_key = f"news_{ticker}"
    if cache_key in _cache:
        return _cache[cache_key]
        
    cached_data = holders_cache.get(cache_key) # Reusing holders_cache for news (1d ttl)
    if cached_data:
        return cached_data
    
    # Using the RSS feed which is generally public and less throttled
    url = f"https://finance.yahoo.com/rss/headline?s={ticker}"
    
    try:
        response = _session.get(url, timeout=10)
        response.raise_for_status()
        
        # Simple XML parsing (could use defusedxml for security in prod)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        news = []
        for item in root.findall(".//item"):
            news.append({
                "title": item.findtext("title"),
                "link": item.findtext("link"),
                "publisher": "Yahoo Finance",
                "providerPublishTime": int(pd.Timestamp(item.findtext("pubDate")).timestamp()) if item.findtext("pubDate") else 0,
                "type": "STORY"
            })
        
        _cache[cache_key] = news
        holders_cache.set(cache_key, news)
        return news
        
    except Exception as e:
        logger.error(f"Error fetching news for {ticker}: {e}")
        return []


def clear_cache():
    """Clear the API cache."""
    _cache.clear()
