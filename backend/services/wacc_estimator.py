import yfinance as yf
import logging
from cachetools import cached, TTLCache
import pandas as pd
import math

logger = logging.getLogger(__name__)

# Cache the Risk-Free Rate and ERP to avoid hammering Yahoo Finance
wacc_cache = TTLCache(maxsize=10, ttl=86400) # 24 hour cache

@cached(wacc_cache)
def get_risk_free_rate() -> float:
    """
    Fetches the current 10-Year Treasury Yield (^TNX) from Yahoo Finance.
    Returns as a decimal (e.g., 0.045 for 4.5%).
    Default fallback is 0.04 (4.0%) if fetch fails.
    """
    try:
        tnx = yf.Ticker("^TNX")
        # Fetch last 5 days to ensure we get a valid close price
        hist = tnx.history(period="5d")
        if not hist.empty:
            latest_yield = hist['Close'].iloc[-1]
            if not pd.isna(latest_yield) and latest_yield > 0:
                # ^TNX is quoted in absolute terms (e.g., 4.25 for 4.25%)
                return latest_yield / 100.0
    except Exception as e:
        logger.error(f"Error fetching ^TNX for risk-free rate: {e}")
        
    logger.warning("Falling back to default 4.0% risk-free rate.")
    return 0.04

def get_equity_risk_premium() -> float:
    """
    Returns the Equity Risk Premium.
    In a full dynamic model this could be tied to the VIX or macroeconomic indicators.
    For V12 Phase 1, we use a fixed proxy (e.g., 5.5%).
    """
    return 0.055

def calculate_wacc(ticker: str, fmp_metrics: dict = None) -> float:
    """
    Calculates Weighted Average Cost of Capital (WACC).
    Initial proxy: Fixed Equity Risk Premium + Risk-Free Rate since calculating distinct 
    cost of debt for every stock robustly is complex. We bound the WACC between 8% and 15% 
    as per Phase 3 RIM constraints.
    """
    rf = get_risk_free_rate()
    erp = get_equity_risk_premium()
    
    # Ideally, we would add Cost of Debt * Weight of Debt, but as a base constraint:
    # WACC base = Risk Free Rate + Equity Risk Premium (assumes un-leveraged firm or industry avg leverage)
    
    # Beta could be fetched from yfinance info
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        beta = info.get('beta', 1.0)
        
        # Ensure beta is sensible
        if beta is None or math.isnan(beta) or beta < 0:
            beta = 1.0
        elif beta > 3.0:
             beta = 3.0 # Cap Beta
             
        # CAPM for Cost of Equity: Ke = Rf + Beta * ERP
        ke = rf + (beta * erp)
        
        # WACC approximation for now (Ke only, assuming no debt tax shield benefit for simplicity in Phase 1)
        wacc = ke
        
        # Bound Constraints for WACC (Phase 3 Requirement)
        if wacc < 0.08:
            wacc = 0.08
        elif wacc > 0.15:
            wacc = 0.15
            
        return wacc
        
    except Exception as e:
        logger.error(f"Error calculating WACC for {ticker}: {e}")
        # Default fallback WACC
        return rf + erp

