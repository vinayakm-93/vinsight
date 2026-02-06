import os
import json
import time
import pickle
import logging
from typing import Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_DIR = Path("cache_data")
CACHE_DIR.mkdir(exist_ok=True)

class DiskCache:
    """
    Persistent disk-based cache to survive server restarts.
    Reduces API calls to Yahoo/Finnhub.
    """
    def __init__(self, cache_name: str = "default", ttl_seconds: int = 3600):
        self.cache_name = cache_name
        self.ttl = ttl_seconds
        
    def _get_path(self, key: str) -> Path:
        # Sanitize key for filesystem
        safe_key = "".join([c if c.isalnum() else "_" for c in key])
        return CACHE_DIR / f"{self.cache_name}_{safe_key}.pkl"

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        path = self._get_path(key)
        data = {
            "expires_at": time.time() + (ttl or self.ttl),
            "payload": value
        }
        try:
            with open(path, "wb") as f:
                pickle.dump(data, f)
        except Exception as e:
            logger.error(f"Disk cache write error: {e}")

    def get(self, key: str) -> Optional[Any]:
        path = self._get_path(key)
        if not path.exists():
            return None
            
        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
            
            if time.time() > data.get("expires_at", 0):
                path.unlink() # Delete expired
                return None
                
            return data.get("payload")
        except Exception as e:
            logger.error(f"Disk cache read error: {e}")
            return None

    def delete(self, key: str):
        path = self._get_path(key)
        if path.exists():
            path.unlink()

# Global cache instances
stock_info_cache = DiskCache("stock_info", ttl_seconds=86400) # 24 hours (mostly static)
price_cache = DiskCache("price", ttl_seconds=300) # 5 minutes
analysis_cache = DiskCache("analysis", ttl_seconds=3600) # 1 hour
holders_cache = DiskCache("holders", ttl_seconds=86400) # 24 hours
