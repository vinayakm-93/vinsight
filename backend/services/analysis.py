import pandas as pd
import ta
import numpy as np
from typing import Dict, List
from textblob import TextBlob

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
    Calculates sentiment from news using Alpha Vantage (preferred) or Groq (fallback).
    
    v2.5: Alpha Vantage primary (has built-in sentiment + summaries)
          Falls back to yfinance + Groq if Alpha Vantage unavailable
    
    Args:
        news_items: List of news items with 'title' (used for fallback)
        deep_analysis: Legacy parameter (kept for compatibility)
        ticker: Stock ticker symbol (required for Alpha Vantage)
    
    Returns: {
        'score': float (-1 to 1),
        'label': str ('Positive', 'Negative', 'Neutral'),
        'confidence': float (0 to 1),
        'article_count': int,
        'source': str ('alpha_vantage' or 'groq')
    }
    """
    # Try Alpha Vantage first (has built-in sentiment)
    if ticker:
        try:
            from services.alpha_vantage_news import get_alpha_vantage_news, is_available
            
            if is_available():
                av_result = get_alpha_vantage_news(ticker, limit=10)
                
                if av_result and av_result.get('articles'):
                    overall = av_result.get('overall_sentiment', {})
                    return {
                        "score": overall.get('score', 0),
                        "label": overall.get('label', 'Neutral'),
                        "confidence": 0.85,  # Alpha Vantage is generally reliable
                        "article_count": av_result.get('article_count', 0),
                        "source": "alpha_vantage",
                        "articles": av_result.get('articles', [])  # Include article details
                    }
        except Exception as e:
            print(f"[Sentiment] Alpha Vantage failed, falling back to Groq: {e}")
    
    # Fallback: Use yfinance news + Groq analysis
    if not news_items:
        return {
            "score": 0,
            "label": "Neutral",
            "confidence": 0.0,
            "article_count": 0,
            "source": "none"
        }
    
    try:
        from services.groq_sentiment import get_groq_analyzer
        from datetime import datetime, timezone
        
        groq = get_groq_analyzer()
        
        if not groq.is_available():
            raise Exception("Groq API not available")
        
        # Bearish keywords for spin detection (keep these for safety)
        BEARISH_KEYWORDS = [
            'layoff', 'layoffs', 'job cuts', 'firing', 'downsizing',
            'miss', 'misses', 'missed', 'disappointing', 'shortfall',
            'decline', 'declines', 'declining', 'drop', 'drops', 'fell',
            'lower', 'lowers', 'lowering', 'cut', 'cuts', 'cutting',
            'loss', 'losses', 'losing', 'unprofitable',
            'bankruptcy', 'bankrupt', 'insolvent',
            'investigation', 'lawsuit', 'sued', 'fraud',
            'downgrade', 'downgrades', 'downgraded',
            'weak', 'weakness', 'softer', 'slowing'
        ]
        
        # Extract headlines and detect bearish content
        headlines = []
        dates = []
        bearish_flags = []
        
        for item in news_items:
            title = item.get('title', '')
            if title:
                headlines.append(title)
                
                # Check for bearish keywords
                title_lower = title.lower()
                has_bearish = any(keyword in title_lower for keyword in BEARISH_KEYWORDS)
                bearish_flags.append(has_bearish)
                
                # Parse date
                pub_date = item.get('published')
                if pub_date:
                    try:
                        if isinstance(pub_date, str):
                            date_obj = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                        else:
                            date_obj = pub_date
                        dates.append(date_obj)
                    except:
                        dates.append(datetime.now(timezone.utc))
                else:
                    dates.append(datetime.now(timezone.utc))
        
        if not headlines:
            return {
                "score": 0,
                "label": "Neutral",
                "confidence": 0.0,
                "article_count": 0,
                "source": "none"
            }
        
        # Analyze top 10 headlines with Groq
        top_n = min(10, len(headlines))
        
        # Sort by recency
        headline_data = list(zip(headlines, dates, bearish_flags))
        headline_data.sort(key=lambda x: x[1], reverse=True)
        
        now = datetime.now(timezone.utc)
        
        groq_scores = []
        groq_confidences = []
        weights = []
        analyzed_bearish = []
        
        for headline, date, is_bearish in headline_data[:top_n]:
            groq_result = groq.analyze(headline)
            groq_scores.append(groq_result['score'])
            groq_confidences.append(groq_result['confidence'])
            analyzed_bearish.append(is_bearish)
            
            # Temporal weight (recent = higher)
            try:
                days_ago = (now - date).total_seconds() / 86400
                weight = 1.0 / (1.0 + 0.1 * days_ago)
                weights.append(weight)
            except:
                weights.append(1.0)
        
        # Calculate weighted average
        total_weight = sum(weights)
        avg_score = sum(s * w for s, w in zip(groq_scores, weights)) / total_weight if total_weight > 0 else 0
        avg_confidence = sum(c * w for c, w in zip(groq_confidences, weights)) / total_weight if total_weight > 0 else 0
        
        # Apply bearish spin detection penalty
        bearish_count = sum(analyzed_bearish)
        if bearish_count > 0 and avg_score > 0:
            penalty_factor = 1.0 - (bearish_count / len(analyzed_bearish)) * 0.5
            avg_score *= penalty_factor
            print(f"[Spin Detection] {bearish_count}/{len(analyzed_bearish)} bearish headlines, penalty {penalty_factor:.2f}x")
        
        # Classify with thresholds
        if avg_score > 0.4:
            label = "Positive"
        elif avg_score < -0.25:
            label = "Negative"
        else:
            label = "Neutral"
        
        # Low confidence defaults to neutral
        if avg_confidence < 0.70 and label != "Neutral":
            label = "Neutral"
        
        # Force negative if bearish keywords + weak positive
        if bearish_count >= 2 and 0 < avg_score < 0.3:
            label = "Negative"
            print(f"[Spin Override] Forcing negative due to {bearish_count} bearish keywords")
        
        return {
            "score": avg_score,
            "label": label,
            "confidence": avg_confidence,
            "article_count": len(headlines),
            "source": "groq"
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
            "source": "textblob_fallback"
        }

