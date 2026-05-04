import os
import requests
import logging
from cachetools import cached, TTLCache
from typing import Dict, Any, List, Optional
import math

logger = logging.getLogger(__name__)

# Cache setup
fmp_cache = TTLCache(maxsize=100, ttl=86400) # 24 hour cache for financial data
fmp_estimates_cache = TTLCache(maxsize=100, ttl=86400)

def get_fmp_api_key() -> str:
    key = os.environ.get("FMP_API_KEY")
    if not key:
        logger.warning("FMP_API_KEY not found in environment variables.")
    return key or ""

@cached(fmp_cache)
def get_v12_financial_metrics(ticker: str) -> Dict[str, Any]:
    """
    Fetches historical NOPAT, Operating Cash Flow, Invested Capital, and explicit trailing EPS arrays
    from FMP for V12 Defensive Layer.
    """
    api_key = get_fmp_api_key()
    if not api_key:
        return {}

    metrics = {
        "nopat": None,
        "invested_capital": None,
        "operating_cash_flow": None,
        "trailing_eps": [],
        "net_income": None,
        "total_assets": None,
        "net_share_issuance_ttm": None,
        "fcf_yield": None
    }

    try:
        # 1. Income Statement (for EPS and NOPAT calculation)
        is_url = f"https://financialmodelingprep.com/api/v3/income-statement/{ticker}?period=annual&limit=5&apikey={api_key}"
        is_resp = requests.get(is_url, timeout=10)
        is_data = is_resp.json() if is_resp.status_code == 200 else []

        # 2. Balance Sheet (for Invested Capital and Total Assets)
        bs_url = f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{ticker}?period=annual&limit=5&apikey={api_key}"
        bs_resp = requests.get(bs_url, timeout=10)
        bs_data = bs_resp.json() if bs_resp.status_code == 200 else []

        # 3. Cash Flow Statement (for Operating Cash Flow and Net Share Issuance)
        cv_url = f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{ticker}?period=annual&limit=5&apikey={api_key}"
        cv_resp = requests.get(cv_url, timeout=10)
        cv_data = cv_resp.json() if cv_resp.status_code == 200 else []

        if is_data and len(is_data) > 0:
            latest_is = is_data[0]
            metrics["net_income"] = latest_is.get("netIncome", 0)
            
            # Trailing EPS (Array of last 5 years as proxy, for stability check later)
            metrics["trailing_eps"] = [item.get("eps", 0) for item in is_data]
            
            # Approximation of NOPAT
            operating_income = latest_is.get("operatingIncome", 0)
            income_tax_expense = latest_is.get("incomeTaxExpense", 0)
            income_before_tax = latest_is.get("incomeBeforeTax", 1) # Prevent div by zero
            if income_before_tax != 0:
                tax_rate = income_tax_expense / income_before_tax
            else:
                tax_rate = 0.21 # Default corporate tax rate
            
            metrics["nopat"] = operating_income * (1 - tax_rate)

        if bs_data and len(bs_data) > 0:
            latest_bs = bs_data[0]
            metrics["total_assets"] = latest_bs.get("totalAssets", 0)
            
            # Invested Capital = Total Debt + Total Equity - Cash & Equivalents
            total_debt = latest_bs.get("totalDebt", 0)
            total_equity = latest_bs.get("totalStockholdersEquity", 0)
            cash = latest_bs.get("cashAndCashEquivalents", 0)
            metrics["invested_capital"] = total_debt + total_equity - cash
            
        if cv_data and len(cv_data) > 0:
            latest_cv = cv_data[0]
            metrics["operating_cash_flow"] = latest_cv.get("operatingCashFlow", 0)
            
            # Net Share Issuance (Stock issued - Stock repurchased)
            common_stock_issued = latest_cv.get("commonStockIssued", 0)
            common_stock_repurchased = latest_cv.get("commonStockRepurchased", 0) # usually negative
            metrics["net_share_issuance_ttm"] = common_stock_issued + common_stock_repurchased # Net

        return metrics
    except Exception as e:
        logger.error(f"FMP metrics error for {ticker}: {e}")
        return {}


@cached(fmp_estimates_cache)
def get_analyst_estimates(ticker: str) -> Dict[str, Any]:
    """
    Fetches Forward ROE and next-12-month EPS estimates for RIM engine.
    """
    api_key = get_fmp_api_key()
    if not api_key:
        return {}
        
    estimates = {
        "forward_eps": None,
        "forward_roe": None,
        "estimated_eps_growth": None
    }
    
    try:
        url = f"https://financialmodelingprep.com/api/v3/analyst-estimates/{ticker}?limit=4&apikey={api_key}"
        resp = requests.get(url, timeout=10)
        data = resp.json() if resp.status_code == 200 else []
        
        if data and len(data) > 0:
            # Sort by date
            sorted_data = sorted(data, key=lambda x: x.get('date', '1970-01-01'), reverse=True)
            # Find the next fiscal year estimate (where date > now)
            from datetime import datetime
            now_iso = datetime.now().isoformat()
            
            future_ests = [d for d in sorted_data if d.get('date', '') > now_iso]
            if future_ests:
                next_est = future_ests[-1] # closest future date
                estimates["forward_eps"] = next_est.get("estimatedEpsAvg", None)
                
            # If no future, just use the most recent report's next period estimate if available, or first item's estimatedEpsAvg
            if not estimates["forward_eps"]:
                estimates["forward_eps"] = sorted_data[0].get("estimatedEpsAvg", None)
                
        return estimates
    except Exception as e:
        logger.error(f"FMP estimates error for {ticker}: {e}")
        return {}
