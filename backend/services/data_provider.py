"""
DataProvider — Abstraction layer over market data sources.

Purpose: De-risk Yahoo Finance dependency by wrapping all data access
behind a pluggable interface. Current implementation: YahooProvider wraps
the existing finance.py functions. Future: FMPProvider, PolygonProvider.

Usage:
    from services.data_provider import get_provider
    provider = get_provider()  # Returns YahooProvider by default
    info = provider.get_stock_info("AAPL")
    history = provider.get_history("AAPL", period="1y")
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Data Contracts — normalized shapes regardless of source
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PriceBar:
    """Single OHLCV bar."""
    date: str       # ISO format
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class StockQuote:
    """Real-time quote snapshot."""
    symbol: str
    price: float
    previous_close: Optional[float]
    change: Optional[float]
    change_pct: Optional[float]


# ═══════════════════════════════════════════════════════════════════════════
# Abstract Base — the contract all providers must implement
# ═══════════════════════════════════════════════════════════════════════════

class DataProvider(ABC):
    """
    Abstract base for market data providers.
    
    All methods are None-safe: they return empty dicts/lists on failure,
    never raise exceptions to callers.
    """

    @abstractmethod
    def get_stock_info(self, ticker: str) -> dict:
        """
        Fetch comprehensive stock info (fundamentals, metadata).
        Returns a flat dict with keys matching Yahoo Finance field names.
        """
        ...

    @abstractmethod
    def get_history(self, ticker: str, period: str = "1y", interval: str = "1d") -> List[dict]:
        """
        Fetch OHLCV history.
        Returns list of dicts with keys: Date, Open, High, Low, Close, Volume.
        """
        ...

    @abstractmethod
    def get_batch_prices(self, tickers: List[str]) -> List[dict]:
        """
        Fetch current prices for multiple tickers in one call.
        Returns list of dicts: symbol, currentPrice, previousClose, change, change_pct.
        """
        ...

    @abstractmethod
    def get_analyst_targets(self, ticker: str) -> dict:
        """
        Fetch analyst consensus price targets.
        Returns: target_low, target_mean, target_high, num_analysts, recommendation_key.
        """
        ...

    @abstractmethod
    def get_advanced_metrics(self, ticker: str) -> dict:
        """
        Fetch CFA-level metrics: debt_to_ebitda, altman_z_score, interest_coverage,
        book_value_per_share, wacc, trailing_eps, nopat, invested_capital, etc.
        """
        ...

    @abstractmethod
    def get_institutional_holders(self, ticker: str) -> dict:
        """
        Fetch institutional holder data and insider transactions.
        """
        ...

    @abstractmethod
    def get_market_regime(self) -> dict:
        """
        Returns SPY-based bull/bear regime: {bull_regime: bool, spy_price, spy_sma200}.
        """
        ...

    def get_peg_ratio(self, ticker: str) -> Optional[float]:
        """Optional: some providers bundle this in info, others need a separate call."""
        info = self.get_stock_info(ticker)
        return info.get('pegRatio')

    def get_earnings_surprise(self, ticker: str) -> float:
        """Optional: EPS surprise percentage."""
        return 0.0


# ═══════════════════════════════════════════════════════════════════════════
# YahooProvider — wraps the existing finance.py functions
# ═══════════════════════════════════════════════════════════════════════════

class YahooProvider(DataProvider):
    """
    Production provider wrapping existing finance.py Yahoo Finance calls.
    
    This is a thin delegation layer — it does NOT duplicate logic from finance.py.
    All caching, fallback, and enrichment logic stays in finance.py.
    """

    def get_stock_info(self, ticker: str) -> dict:
        try:
            from services.finance import get_stock_info
            return get_stock_info(ticker) or {}
        except Exception as e:
            logger.error(f"YahooProvider.get_stock_info({ticker}) failed: {e}")
            return {}

    def get_history(self, ticker: str, period: str = "1y", interval: str = "1d") -> List[dict]:
        try:
            from services.finance import get_stock_history
            return get_stock_history(ticker, period=period, interval=interval) or []
        except Exception as e:
            logger.error(f"YahooProvider.get_history({ticker}) failed: {e}")
            return []

    def get_batch_prices(self, tickers: List[str]) -> List[dict]:
        try:
            from services.finance import get_batch_prices
            return get_batch_prices(tickers) or []
        except Exception as e:
            logger.error(f"YahooProvider.get_batch_prices failed: {e}")
            return []

    def get_analyst_targets(self, ticker: str) -> dict:
        try:
            from services.finance import get_analyst_targets
            return get_analyst_targets(ticker) or {}
        except Exception as e:
            logger.error(f"YahooProvider.get_analyst_targets({ticker}) failed: {e}")
            return {"has_data": False}

    def get_advanced_metrics(self, ticker: str) -> dict:
        try:
            from services.finance import get_advanced_metrics
            return get_advanced_metrics(ticker) or {}
        except Exception as e:
            logger.error(f"YahooProvider.get_advanced_metrics({ticker}) failed: {e}")
            return {}

    def get_institutional_holders(self, ticker: str) -> dict:
        try:
            from services.finance import get_institutional_holders
            return get_institutional_holders(ticker) or {}
        except Exception as e:
            logger.error(f"YahooProvider.get_institutional_holders({ticker}) failed: {e}")
            return {"top_holders": [], "insider_transactions": []}

    def get_market_regime(self) -> dict:
        try:
            from services.finance import get_market_regime
            return get_market_regime() or {"bull_regime": True}
        except Exception as e:
            logger.error(f"YahooProvider.get_market_regime failed: {e}")
            return {"bull_regime": True, "spy_price": 0, "spy_sma200": 0}

    def get_peg_ratio(self, ticker: str) -> Optional[float]:
        try:
            from services.finance import get_peg_ratio
            return get_peg_ratio(ticker)
        except Exception as e:
            logger.error(f"YahooProvider.get_peg_ratio({ticker}) failed: {e}")
            return None

    def get_earnings_surprise(self, ticker: str) -> float:
        try:
            from services.finance import get_earnings_surprise
            return get_earnings_surprise(ticker) or 0.0
        except Exception as e:
            logger.error(f"YahooProvider.get_earnings_surprise({ticker}) failed: {e}")
            return 0.0


# ═══════════════════════════════════════════════════════════════════════════
# FMPProvider — stub for Financial Modeling Prep (future integration)
# ═══════════════════════════════════════════════════════════════════════════

class FMPProvider(DataProvider):
    """
    Financial Modeling Prep provider stub.
    
    FMP offers: real-time quotes, historical prices, financial statements,
    analyst estimates, insider trading, institutional holders.
    API key required ($14/mo for starter plan).
    
    TODO: Implement when ready to add FMP as primary or fallback source.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"

    def get_stock_info(self, ticker: str) -> dict:
        raise NotImplementedError("FMPProvider not yet implemented")

    def get_history(self, ticker: str, period: str = "1y", interval: str = "1d") -> List[dict]:
        raise NotImplementedError("FMPProvider not yet implemented")

    def get_batch_prices(self, tickers: List[str]) -> List[dict]:
        raise NotImplementedError("FMPProvider not yet implemented")

    def get_analyst_targets(self, ticker: str) -> dict:
        raise NotImplementedError("FMPProvider not yet implemented")

    def get_advanced_metrics(self, ticker: str) -> dict:
        raise NotImplementedError("FMPProvider not yet implemented")

    def get_institutional_holders(self, ticker: str) -> dict:
        raise NotImplementedError("FMPProvider not yet implemented")

    def get_market_regime(self) -> dict:
        raise NotImplementedError("FMPProvider not yet implemented")


# ═══════════════════════════════════════════════════════════════════════════
# Factory — singleton accessor
# ═══════════════════════════════════════════════════════════════════════════

_provider_instance: Optional[DataProvider] = None


def get_provider(provider_name: str = "yahoo") -> DataProvider:
    """
    Returns the active DataProvider singleton.
    
    Usage:
        provider = get_provider()
        info = provider.get_stock_info("AAPL")
    
    To switch providers (e.g. for testing or FMP migration):
        set_provider(FMPProvider(api_key="..."))
    """
    global _provider_instance
    if _provider_instance is None:
        if provider_name == "yahoo":
            _provider_instance = YahooProvider()
        elif provider_name == "fmp":
            import os
            api_key = os.environ.get("FMP_API_KEY", "")
            _provider_instance = FMPProvider(api_key=api_key)
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
    return _provider_instance


def set_provider(provider: DataProvider):
    """Override the active provider (useful for tests or migration)."""
    global _provider_instance
    _provider_instance = provider
    logger.info(f"DataProvider switched to: {type(provider).__name__}")
