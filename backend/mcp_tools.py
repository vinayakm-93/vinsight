"""
VinSight MCP Server v2.0 — Online Streamable HTTP
Exposes financial analysis tools to external AI agents (Claude, Cursor, etc.)
via the Model Context Protocol over Streamable HTTP.

Mounted at /mcp in the existing FastAPI backend.

Tools:
    1. analyze_sentiment     — AI sentiment analysis (Groq, 3h cache)
    2. run_monte_carlo       — 10K path Monte Carlo simulation
    3. analyze_earnings_call — Earnings transcript analysis (Groq/Gemini)
    4. get_stock_score       — VinSight Three-Axis scoring engine
    5. search_financial_news — Raw Finnhub news feed

Auth: Bearer token (MCP_API_KEY env var)
Rate Limiting: In-memory TTLCache (daily global + per-tool hourly)
Caching: Per-tool TTLCache with custom TTLs
Telemetry: PostHog events via mcp_telemetry.py
"""

import os
import json
import time
import logging
from datetime import datetime
from functools import wraps

from mcp.server.fastmcp import FastMCP
from cachetools import TTLCache

from mcp_telemetry import track_mcp_tool, track_rate_limit, track_cache_hit, track_auth_failure

logger = logging.getLogger("VinSightMCP")

# ──────────────────────────────────────────────
# MCP Server Instance
# ──────────────────────────────────────────────

mcp = FastMCP(
    "VinSight",
    stateless_http=True,
    instructions=(
        "VinSight is a financial research platform. Use these tools to analyze stocks. "
        "All tickers should be US stock symbols (e.g., AAPL, TSLA, NVDA). "
        "Start with analyze_sentiment or get_stock_score for a quick overview, "
        "then use run_monte_carlo for risk analysis or analyze_earnings_call for deep research."
    ),
)


# ──────────────────────────────────────────────
# Response Caching (Per-Tool TTL)
# ──────────────────────────────────────────────

# Tool-specific caches with different TTLs
_cache_sentiment = TTLCache(maxsize=100, ttl=10800)    # 3 hours (reuses service cache)
_cache_monte_carlo = TTLCache(maxsize=100, ttl=1800)   # 30 min
_cache_earnings = TTLCache(maxsize=50, ttl=21600)      # 6 hours
_cache_score = TTLCache(maxsize=100, ttl=3600)         # 1 hour
_cache_news = TTLCache(maxsize=100, ttl=3600)          # 1 hour

# Map tool names to their caches
_TOOL_CACHES = {
    "analyze_sentiment": _cache_sentiment,
    "run_monte_carlo_simulation": _cache_monte_carlo,
    "analyze_earnings_call": _cache_earnings,
    "get_stock_score": _cache_score,
    "search_financial_news": _cache_news,
}


def mcp_cached(cache_instance):
    """
    Decorator to cache MCP tool responses.
    On cache hit, fires a PostHog event and returns the cached result.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key from function name + args
            key = f"{func.__name__}:{args}:{sorted(kwargs.items())}"

            if key in cache_instance:
                cached_entry = cache_instance[key]
                cache_age = time.time() - cached_entry["cached_at"]
                track_cache_hit(func.__name__, str(args[0] if args else ""), cache_age)
                logger.info(f"MCP CACHE HIT: {func.__name__} (age={cache_age:.0f}s)")
                return cached_entry["result"]

            result = func(*args, **kwargs)

            cache_instance[key] = {
                "result": result,
                "cached_at": time.time(),
            }
            return result
        return wrapper
    return decorator


# ──────────────────────────────────────────────
# Rate Limiting (In-Memory TTLCache Counters)
# ──────────────────────────────────────────────

# Global daily limit counter (resets every 24h)
_daily_counter = TTLCache(maxsize=1, ttl=86400)
DAILY_LIMIT = 500

# Per-tool hourly limits
_hourly_counters = {}
HOURLY_LIMITS = {
    "analyze_sentiment": 60,
    "run_monte_carlo_simulation": 100,
    "analyze_earnings_call": 10,
    "get_stock_score": 30,
    "search_financial_news": 100,
}


def _check_rate_limit(tool_name: str) -> bool:
    """
    Check and increment rate limit counters.
    Returns True if the call is allowed, False if rate-limited.
    """
    # Global daily limit
    daily_count = _daily_counter.get("global", 0)
    if daily_count >= DAILY_LIMIT:
        track_rate_limit(tool_name, "daily")
        return False
    _daily_counter["global"] = daily_count + 1

    # Per-tool hourly limit
    if tool_name not in _hourly_counters:
        _hourly_counters[tool_name] = TTLCache(maxsize=1, ttl=3600)

    hourly_cache = _hourly_counters[tool_name]
    hourly_count = hourly_cache.get("count", 0)
    hourly_limit = HOURLY_LIMITS.get(tool_name, 100)

    if hourly_count >= hourly_limit:
        track_rate_limit(tool_name, "hourly")
        return False
    hourly_cache["count"] = hourly_count + 1

    return True


def rate_limited(func):
    """Decorator to enforce rate limiting on MCP tools."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not _check_rate_limit(func.__name__):
            return json.dumps({
                "error": f"Rate limit exceeded for {func.__name__}. Try again later.",
                "code": "RATE_LIMIT_EXCEEDED",
                "status": "failed",
            })
        return func(*args, **kwargs)
    return wrapper


# ──────────────────────────────────────────────
# Input Sanitization
# ──────────────────────────────────────────────

def _sanitize_ticker(ticker: str) -> str:
    """Sanitize ticker input: uppercase, strip, max 10 chars, alphanumeric + dots."""
    clean = ticker.strip().upper()[:10]
    # Remove any characters that aren't alphanumeric, dot, or dash
    clean = "".join(c for c in clean if c.isalnum() or c in ".-")
    return clean if clean else "INVALID"


# ──────────────────────────────────────────────
# Tool 1: Sentiment Analysis
# ──────────────────────────────────────────────

@mcp.tool()
@track_mcp_tool
@rate_limited
@mcp_cached(_cache_sentiment)
def analyze_sentiment(ticker: str) -> str:
    """Analyze news sentiment for a stock ticker over the last 7 days.

    Returns:
        - score_today: Today's sentiment score (-100 to +100)
        - score_weekly: Weekly sentiment score (-100 to +100)
        - reasoning: AI-generated explanation of sentiment drivers
        - key_drivers: List of key sentiment factors
        - article_count: Number of news articles analyzed

    Uses Groq (Llama 3.3 70B) for deep analysis with Finnhub news data.
    Results are cached for 3 hours.
    """
    ticker = _sanitize_ticker(ticker)
    from services.analysis import analyze_sentiment_ondemand
    result = analyze_sentiment_ondemand(ticker)
    return json.dumps(result, indent=2, default=str)


# ──────────────────────────────────────────────
# Tool 2: Monte Carlo Simulation
# ──────────────────────────────────────────────

@mcp.tool()
@track_mcp_tool
@rate_limited
@mcp_cached(_cache_monte_carlo)
def run_monte_carlo_simulation(ticker: str, days: int = 90) -> str:
    """Run 10,000 Monte Carlo simulations to project future stock price paths.

    Args:
        ticker: Stock ticker symbol (e.g., AAPL, TSLA)
        days: Number of days to simulate (default: 90)

    Returns:
        - p10: Bear case price path (10th percentile)
        - p50: Expected price path (median)
        - p90: Bull case price path (90th percentile)
        - mean_price: Average final price
        - expected_return: Expected return percentage
        - risk_var: Value at Risk (95% confidence)
        - probabilities: Probability of hitting various price targets
        - volatility: Annualized volatility

    Uses NumPy vectorized Geometric Brownian Motion. No LLM cost.
    Results are cached for 30 minutes.
    """
    ticker = _sanitize_ticker(ticker)
    days = max(1, min(365, days))  # Clamp days to reasonable range

    from services import finance
    from services.simulation import run_monte_carlo

    # Fetch 1-year price history
    try:
        history = finance.get_stock_history(ticker, period="1y")
    except Exception:
        # Fallback to yahoo_client on rate limit
        from services.yahoo_client import get_chart_data
        import pandas as pd
        chart = get_chart_data(ticker, interval="1d", range_="1y")
        if chart and chart.get("timestamp"):
            timestamps = chart["timestamp"]
            quotes = chart.get("indicators", {}).get("quote", [{}])[0]
            history = []
            for i, ts in enumerate(timestamps):
                close_val = quotes.get("close", [None])[i] if i < len(quotes.get("close", [])) else None
                if close_val is None:
                    continue
                history.append({
                    "Date": pd.Timestamp(ts, unit='s').isoformat(),
                    "Close": close_val,
                    "Volume": quotes.get("volume", [0])[i] or 0,
                })
        else:
            return json.dumps({
                "error": f"No price data found for {ticker}",
                "code": "NO_DATA",
                "status": "failed",
            })

    if not history:
        return json.dumps({
            "error": f"No price history for {ticker}",
            "code": "NO_DATA",
            "status": "failed",
        })

    result = run_monte_carlo(history, days=days, simulations=10000)

    # Strip the full path data (too large for MCP) — keep summary + first 5 paths
    if "paths" in result:
        result["paths"] = result["paths"][:5]
    for key in ("p10", "p50", "p90", "days"):
        if key in result and isinstance(result[key], list) and len(result[key]) > 10:
            # Keep first, every ~10th point, and last for visualization
            full = result[key]
            step = max(1, len(full) // 10)
            result[key] = [full[0]] + full[1::step] + [full[-1]]

    return json.dumps(result, indent=2, default=str)


# ──────────────────────────────────────────────
# Tool 3: Earnings Analysis
# ──────────────────────────────────────────────

@mcp.tool()
@track_mcp_tool
@rate_limited
@mcp_cached(_cache_earnings)
def analyze_earnings_call(ticker: str) -> str:
    """Analyze the latest earnings call transcript for a stock.

    Returns structured analysis:
        - prepared_remarks: CEO/Management sentiment, key points, forward guidance
        - qa_session: Analyst Q&A tone, management confidence, key revelations
        - verdict: Buy/Hold/Sell rating with reasoning

    Scrapes Motley Fool transcripts and analyzes with Groq (Llama 3.3) or Gemini.
    Results are cached for 6 hours. This is the most expensive tool (~$0.05/call).
    """
    ticker = _sanitize_ticker(ticker)

    from database import SessionLocal
    from services.earnings import analyze_earnings

    # Create a standalone DB session for earnings (needs DB for caching)
    db = SessionLocal()
    try:
        result = analyze_earnings(ticker, db)
        return json.dumps(result, indent=2, default=str)
    finally:
        db.close()


# ──────────────────────────────────────────────
# Tool 4: VinSight Stock Score
# ──────────────────────────────────────────────

@mcp.tool()
@track_mcp_tool
@rate_limited
@mcp_cached(_cache_score)
def get_stock_score(ticker: str) -> str:
    """Get VinSight's quantitative stock score (0-100).

    The score is a composite of:
        - Quality (70%): Valuation (PEG, FCF Yield), Profitability (ROE, ROIC),
          Health (Debt ratios, Altman Z-Score)
        - Timing (30%): SMA trends, RSI, Volume patterns, Momentum

    Also includes:
        - Kill switches: Insolvency, Distress, Dilution vetoes
        - RIM Valuation: Residual Income Model intrinsic value + margin of safety
        - Data Fragility: DuPont triangulation confidence check

    Returns a numerical score, rating (Strong Buy/Buy/Hold/Sell), narrative,
    full breakdown, and risk modifications.
    Results cached for 1 hour.
    """
    ticker = _sanitize_ticker(ticker)

    from services import finance, analysis
    from services.simulation import run_monte_carlo
    from services.vinsight_scorer import (
        VinSightScorer, StockData, Fundamentals, Technicals,
        Sentiment, Projections,
    )

    # Fetch coordinated data bundle (single Ticker instance)
    data_bundle = finance.fetch_coordinated_analysis_data(ticker)
    history = data_bundle.get("history", [])
    info = data_bundle.get("info", {})
    news = data_bundle.get("news", {})
    institutional = data_bundle.get("institutional", {})
    advanced = data_bundle.get("advanced", {})

    if not history:
        return json.dumps({
            "error": f"No data found for {ticker}",
            "code": "NO_DATA",
            "status": "failed",
        })

    # Calculate technical indicators
    indicators = analysis.calculate_technical_indicators(history)
    latest_ind = indicators[-1] if indicators else {}

    # Current price
    current_price = float(history[-1].get("Close", 0)) if history else 0.0
    if not current_price:
        current_price = float(info.get("currentPrice", 0) or info.get("previousClose", 0) or 0)

    # Quick Monte Carlo for projections
    sim_result = run_monte_carlo(history, days=90, simulations=5000)

    # Build StockData (mirrors routes/data.py assembly)
    beta = float(info.get("beta", 1.0) or 1.0)
    div_yield = float(info.get("dividendYield", 0) or 0) * 100
    regime = finance.get_market_regime()

    # Institutional ownership
    inst_own = institutional.get("institutionsPercentHeld", 0)
    if inst_own < 1 and inst_own > 0:
        inst_own *= 100

    # PEG Ratio
    peg = finance.get_peg_ratio(ticker)

    # Key fundamentals
    debt_to_equity = info.get("debtToEquity", 0) or 0
    if debt_to_equity > 10:
        debt_to_equity /= 100

    eps_surprise = finance.get_earnings_surprise(ticker)

    fund_data = Fundamentals(
        pe_ratio=info.get("trailingPE", 0) or 0,
        forward_pe=info.get("forwardPE", 0) or 0,
        peg_ratio=peg,
        fcf_yield=info.get("fcf_yield", 0.0),
        profit_margin=info.get("profitMargins", 0) or 0,
        operating_margin=info.get("operatingMargins", 0) or 0,
        gross_margin_trend=advanced.get("gross_margin_trend", "Flat"),
        roe=info.get("returnOnEquity", 0) or 0,
        roa=info.get("returnOnAssets", 0) or 0,
        debt_to_equity=debt_to_equity,
        debt_to_ebitda=advanced.get("debt_to_ebitda"),
        interest_coverage=advanced.get("interest_coverage", 100.0),
        current_ratio=info.get("currentRatio", 0) or 0,
        altman_z_score=advanced.get("altman_z_score"),
        earnings_growth_qoq=info.get("earningsQuarterlyGrowth", 0) or 0,
        revenue_growth_3y=advanced.get("revenue_growth_3y_cagr"),
        inst_ownership=inst_own,
        eps_surprise_pct=eps_surprise,
        sector_name=info.get("sector", "Technology"),
        # V12 Engine
        nopat=advanced.get("nopat"),
        invested_capital=advanced.get("invested_capital"),
        operating_cash_flow=advanced.get("operating_cash_flow"),
        trailing_eps=advanced.get("trailing_eps", []),
        net_income=advanced.get("net_income"),
        total_assets=advanced.get("total_assets"),
        net_share_issuance_ttm=advanced.get("net_share_issuance_ttm"),
        wacc=advanced.get("wacc", 0.10),
        market_cap=info.get("marketCap"),
        forward_roe=advanced.get("forward_roe"),
        book_value_per_share=advanced.get("book_value_per_share"),
        shares_outstanding=advanced.get("shares_outstanding"),
    )

    # Technicals
    rsi = latest_ind.get("RSI", 50)
    sma50 = latest_ind.get("SMA_50", 0)
    sma200 = latest_ind.get("SMA_200", 0)
    momentum = "Bullish" if current_price > sma50 else "Bearish"

    avg_vol = info.get("averageVolume", 1)
    curr_vol = history[-1].get("Volume", 0) if history else 0
    relative_volume = (curr_vol / avg_vol) if avg_vol and avg_vol > 0 else 1.0
    high52 = info.get("fiftyTwoWeekHigh", current_price)
    distance_to_high = ((high52 - current_price) / high52) if high52 and high52 > 0 else 0.0

    tech_data = Technicals(
        price=current_price,
        sma50=sma50,
        sma200=sma200,
        rsi=rsi,
        relative_volume=relative_volume,
        distance_to_high=distance_to_high,
        momentum_label=momentum,
        volume_trend="Neutral",
    )

    # Sentiment (lightweight — no LLM)
    news_count = 0
    if isinstance(news, dict):
        news_count = len(news.get("latest", [])) + len(news.get("historical", []))
    sentiment_data = Sentiment(
        news_sentiment_label="Neutral",
        news_sentiment_score=0,
        news_article_count=news_count,
    )

    # Projections
    p50 = sim_result.get("p50", [current_price])[-1] if sim_result.get("p50") else current_price
    p90 = sim_result.get("p90", [current_price])[-1] if sim_result.get("p90") else current_price
    p10 = sim_result.get("p10", [current_price])[-1] if sim_result.get("p10") else current_price

    proj_data = Projections(
        monte_carlo_p50=p50,
        monte_carlo_p90=p90,
        monte_carlo_p10=p10,
        current_price=current_price,
    )

    stock_data = StockData(
        ticker=ticker,
        beta=beta,
        dividend_yield=div_yield,
        market_bull_regime=regime["bull_regime"],
        fundamentals=fund_data,
        technicals=tech_data,
        sentiment=sentiment_data,
        projections=proj_data,
    )

    # Score
    scorer = VinSightScorer()
    score_result = scorer.evaluate(stock_data)

    # Format for MCP output (concise, agent-friendly)
    output = {
        "ticker": ticker,
        "score": score_result.total_score,
        "rating": score_result.rating,
        "narrative": score_result.verdict_narrative,
        "breakdown": {
            "quality_score": score_result.breakdown.get("Quality Score", 0),
            "timing_score": score_result.breakdown.get("Timing Score", 0),
            "rim_bonus": score_result.breakdown.get("RIM Bonus", 0),
            "data_confidence": score_result.breakdown.get("Data Confidence", "High"),
        },
        "price": current_price,
        "monte_carlo": {
            "p10": round(p10, 2),
            "p50": round(p50, 2),
            "p90": round(p90, 2),
        },
        "modifications": score_result.modifications[:10],  # Cap for readability
        "missing_data": score_result.missing_data,
    }

    return json.dumps(output, indent=2, default=str)


# ──────────────────────────────────────────────
# Tool 5: News Search
# ──────────────────────────────────────────────

@mcp.tool()
@track_mcp_tool
@rate_limited
@mcp_cached(_cache_news)
def search_financial_news(ticker: str, days: int = 7) -> str:
    """Search recent financial news headlines for a stock ticker.

    Args:
        ticker: Stock ticker symbol (e.g., AAPL, NVDA)
        days: Number of days of news to fetch (default: 7, max: 30)

    Returns:
        - latest: News articles from the last 24 hours
        - historical: News articles from the past week

    Each article includes: headline, source, datetime, URL, and summary.
    No LLM cost — raw Finnhub data. Results cached for 1 hour.
    """
    ticker = _sanitize_ticker(ticker)
    days = max(1, min(30, days))

    from services.finnhub_news import fetch_company_news
    result = fetch_company_news(ticker, days=days)
    return json.dumps(result, indent=2, default=str)
