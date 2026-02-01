import pandas as pd
import ta
import numpy as np
from typing import Dict, List, Optional
from textblob import TextBlob
from datetime import datetime
from services import finnhub_news, cache
from services.groq_sentiment import get_groq_analyzer

def calculate_technical_indicators(history: List[Dict]) -> List[Dict]:
    """
    Adds RSI, MACD, SMA to the historical data.
    Input: List of dicts (from yfinance history)
    """
    if not history:
        return []
    
    df = pd.DataFrame(history)
    # Ensure numeric
    df['Close'] = pd.to_numeric(df['Close'])
    
    # RSI
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    
    # MACD
    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    
    # SMA
    df['SMA_5'] = ta.trend.sma_indicator(df['Close'], window=5)
    df['SMA_10'] = ta.trend.sma_indicator(df['Close'], window=10)
    df['SMA_20'] = ta.trend.sma_indicator(df['Close'], window=20)
    df['SMA_50'] = ta.trend.sma_indicator(df['Close'], window=50)
    df['SMA_200'] = ta.trend.sma_indicator(df['Close'], window=200)

    # Momentum Signal
    df['Momentum_Signal'] = np.where(df['SMA_5'] > df['SMA_10'], "BULLISH", "BEARISH")
    
    # RSI Signal
    conditions = [
        (df['RSI'] > 70),
        (df['RSI'] < 30)
    ]
    choices = ['Overbought', 'Oversold']
    df['RSI_Signal'] = np.select(conditions, choices, default='Neutral')
    
    # Fill NaNs
    df = df.fillna(0)
    
    return df.to_dict(orient="records")

def calculate_risk_metrics(history: List[Dict]) -> Dict:
    """
    Calculates VaR, Volatility, Sharpe Ratio.
    """
    if not history:
        return {}
        
    df = pd.DataFrame(history)
    df['Close'] = pd.to_numeric(df['Close'])
    
    # Daily Returns
    df['Returns'] = df['Close'].pct_change()
    
    # Metrics
    volatility = df['Returns'].std() * np.sqrt(252) # Annualized
    mean_return = df['Returns'].mean() * 252
    sharpe_ratio = mean_return / volatility if volatility != 0 else 0
    
    # Value at Risk (95% confidence)
    var_95 = np.percentile(df['Returns'].dropna(), 5)
    
    return {
        "volatility": volatility,
        "sharpe_ratio": sharpe_ratio,
        "var_95": var_95
    }
    return {
        "volatility": volatility,
        "sharpe_ratio": sharpe_ratio,
        "var_95": var_95
    }

def calculate_news_sentiment(news_items: List[Dict], deep_analysis: bool = True, ticker: str = None) -> Dict:
    """
    Calculates sentiment from news using Groq + Finnhub MSPR (insider sentiment).
    
    v3.0: Merged Finnhub MSPR into sentiment section
          - News sentiment via Groq/TextBlob
          - Insider sentiment via Finnhub MSPR (consolidated API call)
    
    Args:
        news_items: List of news items with 'title' (used for fallback)
        deep_analysis: Legacy parameter (kept for compatibility)
        ticker: Stock ticker symbol (required for MSPR fetch)
    
    Returns: {
        'score': float (-1 to 1),
        'label': str ('Positive', 'Negative', 'Neutral'),
        'confidence': float (0 to 1),
        'article_count': int,
        'source': str,
        'insider_mspr': float (-100 to 100),       # NEW
        'insider_mspr_label': str,                  # NEW
    }
    """
    # Default MSPR values (no data)
    insider_mspr = 0.0
    insider_mspr_label = "No Data"
    
    # 1. Fetch Finnhub MSPR if ticker provided
    if ticker:
        try:
            from services.finnhub_insider import get_insider_sentiment, is_available
            
            if is_available():
                finnhub_data = get_insider_sentiment(ticker)
                if finnhub_data:
                    insider_mspr = finnhub_data.get("mspr", 0.0)
                    insider_mspr_label = finnhub_data.get("activity_label", "No Activity")
        except Exception as e:
            print(f"Error fetching Finnhub MSPR for {ticker}: {e}")
    
    # 2. Gather News Data
    articles_to_analyze = []
    source_name = "yfinance + Groq"
    
    if news_items:
        for item in news_items:
            title = item.get('title', '')
            if title:
                articles_to_analyze.append(f"Headline: {title}")

    if not articles_to_analyze:
        return {
            "score": 0,
            "label": "Neutral",
            "confidence": 0.0,
            "article_count": 0,
            "source": "none",
            "insider_mspr": insider_mspr,
            "insider_mspr_label": insider_mspr_label
        }

    # 3. Analyze with Groq (Batch)
    try:
        from services.groq_sentiment import get_groq_analyzer
        groq = get_groq_analyzer()
        
        if not groq.is_available():
            raise Exception("Groq API not available")

        # Context for analysis
        context = ticker if ticker else "Company"
        
        # Batch Analysis
        result = groq.analyze_batch(articles_to_analyze, context=context)
        
        return {
            "score": result['score'],
            "label": result['label'].capitalize(),
            "confidence": result['confidence'],
            "article_count": len(articles_to_analyze),
            "source": f"{source_name} (Deep Analysis)",
            "reasoning": result.get('reasoning', ''),
            "insider_mspr": insider_mspr,
            "insider_mspr_label": insider_mspr_label
        }
        
    except Exception as e:
        # Fallback to TextBlob if Groq fails
        import traceback
        traceback.print_exc()
        print(f"Error in Groq sentiment analysis, falling back to TextBlob: {e}")
        
        from textblob import TextBlob
        
        total_polarity = 0
        count = 0
        
        for item in news_items:
            title = item.get('title', '')
            if title:
                blob = TextBlob(title)
                total_polarity += blob.sentiment.polarity
                count += 1
        
        avg_polarity = total_polarity / count if count > 0 else 0
        
        # Use stricter thresholds matching Groq analysis
        if avg_polarity > 0.5:
            label = "Positive"
        elif avg_polarity < -0.3:
            label = "Negative"
        else:
            label = "Neutral"
        
        return {
            "score": avg_polarity,
            "label": label,
            "confidence": 0.5,
            "article_count": count,
            "source": "TextBlob (Tier 3)",
            "insider_mspr": insider_mspr,
            "insider_mspr_label": insider_mspr_label
        }



def analyze_sentiment_ondemand(ticker: str) -> Dict:
    """
    On-Demand Sentiment Analysis (v2.5)
    1. Checks Cache (3-Hour TTL).
    2. Fetches Finnhub News (Last 7 Days).
    3. Performs Dual-Period Analysis (Today vs Weekly) via Groq.
    4. Caches and returns result.
    """
    # 1. Check Cache
    cached_result = cache.get_cached_sentiment(ticker)
    if cached_result:
        cached_result['source'] = 'cache'
        return cached_result

    # 2. Fetch News (Finnhub)
    news_data = finnhub_news.fetch_company_news(ticker, days=7)
    latest = news_data.get('latest', [])
    historical = news_data.get('historical', [])
    
    total_articles = len(latest) + len(historical)
    
    if total_articles == 0:
        return {
            "score_today": 0,
            "score_weekly": 0,
            "score_quant": 0,
            "reasoning": "No recent news found for analysis.",
            "key_drivers": [],
            "news_flow": news_data,
            "timestamp": datetime.now().isoformat(),
            "source": "finnhub_v2_empty"
        }

    # 3. Analyze (Groq)
    start_time = datetime.now()
    groq = get_groq_analyzer()
    if groq.is_available():
        analysis = groq.analyze_dual_period(latest, historical, context=ticker)
    else:
        # Fallback if Groq key missing
        analysis = {
            "score_today": 0,
            "score_weekly": 0,
            "reasoning": "Groq API key missing. Cannot perform deep analysis.",
            "key_drivers": []
        }
    
    end_time = datetime.now()
    duration_ms = (end_time - start_time).total_seconds() * 1000

    # 4. Quant Check (TextBlob - Standard "Bag of Words" model)
    # This acts as a "second opinion" or the "Finnhub Weighted Score" proxy.
    def calc_quant_score(items):
        if not items: return 0.0
        details = [TextBlob(i['title'] + " " + i.get('summary','')).sentiment.polarity for i in items]
        return sum(details) / len(details) if details else 0.0

    quant_today = calc_quant_score(latest)
    quant_weekly = calc_quant_score(historical)
    quant_total = (quant_today * 0.6) + (quant_weekly * 0.4) # Weighted

    # 5. Construct Result
    result = {
        "score_today": analysis.get('score_today', 0),
        "score_weekly": analysis.get('score_weekly', 0),
        "score_quant": quant_total, # The "Algorithmic" score
        "reasoning": analysis.get('reasoning', ''),
        "key_drivers": analysis.get('key_drivers', []),
        "news_flow": news_data,
        "article_count": total_articles,
        "timestamp": datetime.now().isoformat(),
        "duration_ms": duration_ms,
        "source": "finnhub_v2"
    }

    # 6. Cache
    cache.set_cached_sentiment(ticker, result)
    
    return result
