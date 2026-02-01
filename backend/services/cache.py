from cachetools import TTLCache
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

# TTL Cache: 100 items, 3 Hours (10800 seconds)
_sentiment_cache = TTLCache(maxsize=100, ttl=10800)

def get_cached_sentiment(ticker: str):
    """Get sentiment from in-memory cache."""
    return _sentiment_cache.get(ticker.upper())

def set_cached_sentiment(ticker: str, data: dict):
    """
    Cache sentiment result. 
    Adds 'cached_at' timestamp if not present.
    """
    if not data:
        return
        
    # Ensure timestamp is set
    if 'timestamp' not in data:
        data['timestamp'] = datetime.now().isoformat()
        
    _sentiment_cache[ticker.upper()] = data
    logger.info(f"Cached sentiment for {ticker} at {data['timestamp']}")

def clear_cache():
    """Clear all cached sentiment."""
    _sentiment_cache.clear()
