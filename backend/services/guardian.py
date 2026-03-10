import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from services import finance, analysis, earnings

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("guardian_service")

# --- Constants & Thresholds ---
PRICE_DROP_THRESHOLD = -0.05  # -5% drop
INSIDER_SELL_SCORE_THRESHOLD = -6  # Cluster sell
SENTIMENT_CRASH_THRESHOLD = -0.5
EARNINGS_MISS_THRESHOLD = -0.10 # -10% surprise

def detect_events(symbol: str, last_known_price: Optional[float] = None) -> Dict[str, Any]:
    """
    Stage 1: Fast Filter.
    Checks for significant events that warrant a full LLM review.
    Returns a dict with 'triggered': bool and 'events': List[str].
    """
    triggered = False
    events = []
    current_price = None

    try:
        # 1. Macro Regime Check
        try:
            regime = finance.get_market_regime()
            if not regime.get('bull_regime', True):
                triggered = True
                events.append("MACRO HEADWIND: S&P 500 is currently below its 200-day SMA, indicating a broad market distribution regime.")
        except Exception as e:
            logger.warning(f"Macro regime check failed: {e}")

        # 2. Price Check
        stock_info = finance.get_stock_info(symbol)
        if stock_info:
            current_price = stock_info.get('currentPrice') or stock_info.get('regularMarketPrice')
            
            # Check vs Last Known Price (if available)
            if last_known_price and current_price:
                pct_change = (current_price - last_known_price) / last_known_price
                if pct_change <= PRICE_DROP_THRESHOLD:
                    triggered = True
                    events.append(f"Price dropped {pct_change*100:.1f}% since last check")

            # Check Daily Change (as a fallback or additional signal)
            daily_change = stock_info.get('regularMarketChangePercent', 0)
            if daily_change and (daily_change / 100) <= PRICE_DROP_THRESHOLD:
                # Deduplicate if we already caught it via last_known_price
                if not any("Price dropped" in e for e in events):
                    triggered = True
                    events.append(f"Price dropped {daily_change:.1f}% in one session")

        # 3. Analyst Downgrades
        analyst_data = finance.get_analyst_targets(symbol)
        if analyst_data:
            rec_key = analyst_data.get('recommendationKey', '').lower()
            if rec_key in ['sell', 'underperform']:
                triggered = True
                events.append(f"Analyst consensus is now {rec_key.upper()}")

        # 4. Sentiment Crash
        sentiment_result = analysis.analyze_sentiment_ondemand(symbol)
        if sentiment_result and sentiment_result.get('quant_score', 0) <= SENTIMENT_CRASH_THRESHOLD:
            triggered = True
            event_str = f"Sentiment score crashed to {sentiment_result.get('quant_score')}."
            # Append specific bearish context so the agents know what broke
            if sentiment_result.get('key_events'):
                event_str += f" Reported risks: {sentiment_result['key_events'][:200]}"
            events.append(event_str)

        # 5. Earnings Miss
        earnings_surprise = finance.get_earnings_surprise(symbol)
        if earnings_surprise is not None and earnings_surprise <= EARNINGS_MISS_THRESHOLD:
            triggered = True
            events.append(f"Earnings missed estimates by {earnings_surprise*100:.1f}%")

    except Exception as e:
        logger.error(f"Error checking events for {symbol}: {e}")
        # On error, we default to False to avoid spam, but log it.
    
    return {
        "triggered": triggered,
        "events": events,
        "current_price": current_price
    }

def gather_evidence(symbol: str) -> Dict[str, Any]:
    """
    Stage 2: Gather Evidence.
    Fetches comprehensive data for the LLM to analyze.
    """
    evidence = {}
    
    try:
        # 1. News
        news_data = finance.get_news(symbol)
        news = []
        if isinstance(news_data, dict):
            news = news_data.get('latest', []) + news_data.get('historical', [])
        elif isinstance(news_data, list):
            news = news_data
            
        evidence['news'] = news[:5] if news else []

        # 2. Financials / Stats
        info = finance.get_stock_info(symbol)
        evidence['fundamentals'] = {
            'price': info.get('currentPrice'),
            'peRatio': info.get('trailingPE'),
            'marketCap': info.get('marketCap'),
            '52WeekHigh': info.get('fiftyTwoWeekHigh'),
            '52WeekLow': info.get('fiftyTwoWeekLow')
        }

        # 3. Analyst Targets
        analyst = finance.get_analyst_targets(symbol)
        evidence['analyst_ratings'] = analyst

        # 4. Sentiment
        sentiment = analysis.analyze_sentiment_ondemand(symbol)
        evidence['sentiment'] = sentiment

        # 5. Insider (if avail)
        # evidence['insider'] = ... 

        # 6. Technicals
        hist = finance.get_stock_history(symbol, period="3mo")
        if hist:
            try:
                # Convert to format expected by analysis service if needed
                # finance.get_stock_history returns list of dicts: {'Date':..., 'Open':..., ...}
                tech_data = analysis.calculate_technical_indicators(hist)
                # Get latest values
                latest = tech_data[-1] if tech_data else {}
                evidence['technicals'] = {
                    'rsi': latest.get('RSI'),
                    'macd': latest.get('MACD'),
                    'macd_signal': latest.get('MACD_Signal'),
                    'sma_20': latest.get('SMA_20'),
                    'sma_50': latest.get('SMA_50')
                }
            except Exception as e:
                logger.warning(f"Error calculating technicals for {symbol}: {e}")
                evidence['technicals'] = {}

    except Exception as e:
        logger.error(f"Error gathering evidence for {symbol}: {e}")
        evidence['error'] = str(e)

    return evidence
