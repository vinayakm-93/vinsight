from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from services import finance, analysis, simulation, search, earnings
from services.search import search_ticker
from services.vinsight_scorer import VinSightScorer, StockData, Fundamentals, Technicals, Sentiment, Projections, ScoreResult
import yfinance as yf
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data", tags=["data"])

@router.get("/quote/{ticker}")
def get_quick_quote(ticker: str):
    """
    Lightweight endpoint for current price data.
    Returns only essential real-time information with minimal API calls.
    Perfect for frequent polling without exhausting rate limits.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Get the most recent price data
        current_price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 0)
        previous_close = info.get('regularMarketPreviousClose') or info.get('previousClose', 0)
        
        # Calculate change
        change = current_price - previous_close if current_price and previous_close else 0
        change_percent = (change / previous_close * 100) if previous_close else 0
        
        return {
            "symbol": ticker.upper(),
            "currentPrice": current_price,
            "previousClose": previous_close,
            "change": change,
            "changePercent": change_percent,
            "marketState": info.get('marketState', 'CLOSED'),  # REGULAR, PRE, POST, CLOSED
            "timestamp": info.get('regularMarketTime', None)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching quote: {str(e)}")

@router.get("/earnings/{ticker}")
def get_earnings_analysis(ticker: str, db: Session = Depends(get_db)):
    return earnings.analyze_earnings(ticker, db)

@router.get("/search")
def search_stocks(q: str):
    return search_ticker(q)

@router.get("/stock/{ticker}")
def get_stock_details(ticker: str):
    try:
        info = finance.get_stock_info(ticker)
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch-stock")
def get_batch_stock_details(payload: dict):
    """
    Fetch details for multiple stocks in one request.
    Payload: { "tickers": ["AAPL", "MSFT", ...] }
    """
    tickers = payload.get("tickers", [])
    if not tickers:
        return []
        
    try:
        return finance.get_batch_stock_details(tickers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{ticker}")
def get_stock_history_data(ticker: str, period: str = "1mo", interval: str = "1d"):
    try:
        history = finance.get_stock_history(ticker, period, interval)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/news/{ticker}")
def get_stock_news(ticker: str):
    try:
        news = finance.get_news(ticker)
        return news
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analysis/{ticker}")
def get_technical_analysis(ticker: str, period: str = "2y", interval: str = "1d", include_sentiment: bool = False):
    try:
        # 1. Fetch Basic Data
        history = finance.get_stock_history(ticker, period, interval)
        if not history:
            raise HTTPException(status_code=404, detail="No history data found")
        
        # 2. Calculate Technical Indicators FIRST (needed for VinSight)
        indicators = analysis.calculate_technical_indicators(history)
        risk = analysis.calculate_risk_metrics(history)
        
        # 3. Fetch Additional Data for VinSight
        fundamentals_info = finance.get_stock_info(ticker)
        news = finance.get_news(ticker)
        
        if include_sentiment:
            sentiment_result = analysis.calculate_news_sentiment(news, deep_analysis=True)
            # Default to neutral if None
            if not sentiment_result:
                 sentiment_result = {"label": "Neutral", "score": 0, "confidence": 0, "article_count": 0}
        else:
            sentiment_result = None
            
        institutional = finance.get_institutional_holders(ticker)
        sim_result = simulation.run_monte_carlo(history, days=30, simulations=500) # Quick run
        
        # v5.0 Data Fetching
        # v5.0 Data Fetching
        regime = finance.get_market_regime()
        
        # Ensure beta is a float (handle None or missing)
        raw_beta = fundamentals_info.get("beta")
        beta = float(raw_beta) if raw_beta is not None else 1.0
        
        # Yield is often 0 if missing. yfinance provides 'dividendYield' (decimal)
        raw_yield = fundamentals_info.get("dividendYield")
        div_yield = float(raw_yield) if raw_yield is not None else 0.0
        div_yield_pct = div_yield * 100

        # 4. Adapt Data for VinSight Scorer v5.0
        
        # --- Fundamentals ---
        # Inst Ownership
        inst_own = institutional.get("institutionsPercentHeld", 0) * 100 # Convert to % if decimal
        if inst_own < 1 and institutional.get("institutionsPercentHeld", 0) > 0:
             inst_own = institutional.get("institutionsPercentHeld", 0) * 100
        elif inst_own == 0 and "institutionsPercentHeld" in institutional:
             inst_own = institutional["institutionsPercentHeld"] * 100

        # Inst Ownership Change
        # Simple heuristic from transaction text or simply assuming "Flat" if unknown
        # Since we don't have historical ownership array easily here, we look at insider activity as proxy or just default to Flat/Rising
        # User spec: "Inst. Holdings Rising (10 pts). Flat (5 pts). Selling (0 pts)."
        # We'll use a placeholder logic or derived from `institutional` dict if we had trend.
        # For now, let's assume "Flat" unless we see huge buying in insiders (correlated) or if we had diff data.
        # IMPROVEMENT: Use 'net_institutional_buying' if available. 
        # Hack: Random determinism or default to Flat for MVP v5.0
        inst_changing = "Flat" 

        current_price = history[-1]['Close'] if history else 0
        
        # Handle sentiment safely - use default values if sentiment is None
        if sentiment_result:
            sentiment_score = sentiment_result.get('score', 0)
            sentiment_label = sentiment_result.get('label', 'Neutral')
            news_art_count = sentiment_result.get('article_count', 0)
        else:
            sentiment_score = 0
            sentiment_label = 'Neutral'
            news_art_count = 0
            
        # Social Volume Proxy: High if article count > 5 (arbitrary for now)
        news_vol_high = news_art_count > 5
        
        analyst_data = fundamentals_info.get('analyst', {})
        target_price = analyst_data.get('targetMeanPrice', current_price)
        num_analysts = analyst_data.get('numberOfAnalystOpinions', 0)
        
        upside = ((target_price / current_price) - 1) * 100 if current_price > 0 and target_price > 0 else 0

        earnings_growth = fundamentals_info.get("earningsQuarterlyGrowth", 0) # decimal
        
        # P/E
        pe = fundamentals_info.get("trailingPE", 0)
        
        # PEG Ratio
        peg = finance.get_peg_ratio(ticker)
        
        fund_data = Fundamentals(
            inst_ownership=inst_own,
            inst_changing=inst_changing,
            pe_ratio=pe or 0,
            peg_ratio=peg,
            earnings_growth_qoq=earnings_growth,
            sector_pe_median=25.0 # hardcoded benchmark for now
        )

        # --- Technicals ---
        latest_ind = indicators[-1] if indicators else {}
        rsi = latest_ind.get('RSI', 50)
        sma50 = latest_ind.get('SMA_50', 0)
        sma200 = latest_ind.get('SMA_200', 0)
        momentum = latest_ind.get('Momentum_Signal', 'Bearish').capitalize()
        if momentum not in ["Bullish", "Bearish"]:
            momentum = "Bearish"

        # Volume Trend
        if len(history) >= 2:
            p_change = history[-1]['Close'] - history[-2]['Close']
            v_change = history[-1]['Volume'] - history[-2]['Volume']
            if p_change > 0 and v_change > 0:
                vol_trend = "Price Rising + Vol Rising"
            elif p_change > 0 and v_change < 0:
                vol_trend = "Price Rising + Vol Falling"
            elif p_change < 0 and v_change > 0:
                vol_trend = "Price Falling + Vol Rising"
            else:
                vol_trend = "Weak/Mixed"
        else:
            vol_trend = "Weak/Mixed"
            
        tech_data = Technicals(
            price=current_price,
            sma50=sma50,
            sma200=sma200,
            rsi=rsi,
            momentum_label=momentum,
            volume_trend=vol_trend
        )

        # Insider Activity Detection
        ins_activity = "Neutral"
        txs = institutional.get('insider_transactions', [])
        # Checking for "Sale" or "Buy" in Text or Position
        # finance.py returns lists of dicts with 'Text', 'Position'
        insider_buy = 0
        insider_sell = 0
        for t in txs[:10]:  # Last 10 transactions
            text = t.get('Text', '').lower()
            if 'sale' in text or 'sell' in text:
                insider_sell += 1
            elif 'purchase' in text or 'buy' in text:
                insider_buy += 1
        
        if insider_buy > insider_sell and insider_buy >= 2:
            ins_activity = "Net Buying"
        elif insider_sell > insider_buy and insider_sell >= 3:
            ins_activity = "Heavy Selling"
        else:
            ins_activity = "Mixed/Minor Selling"
        
        sentiment_data = Sentiment(
            news_sentiment_label=sentiment_label,
            news_volume_high=news_vol_high,
            insider_activity=ins_activity # We need to map this carefully
        )
        
        # Mapper for Insider to v5.0 labels
        # v2 labels: "Net Buying", "Heavy Selling", "Mixed/Minor Selling"
        # v5 labels: "Net Buying", "Mixed/Minor Selling", "Heavy Selling", "Cluster Selling"
        # We'll use the existing "ins_activity" var which has compatible values mostly.
        sentiment_data.insider_activity = ins_activity
            
        # --- Projections ---
        # Simulation returns p50 list. We need the FINAL P50 value.
        p50_val = sim_result.get('p50', [])[-1] if sim_result.get('p50') else current_price
        
        # Risk/Reward
        # Gain to P90: P90_final - Current
        # Loss to P10: Current - P10_final
        p90_val = sim_result.get('p90', [])[-1] if sim_result.get('p90') else current_price
        p10_val = sim_result.get('p10', [])[-1] if sim_result.get('p10') else current_price
        
        gain_p90 = max(0, p90_val - current_price)
        loss_p10 = max(0, current_price - p10_val)
        
        # v5.0 Projections
        # Need P50, P90, P10
        # Sim result usually gives a list of paths. We need distribution of FINAL tips.
        # Actually v4 implementation returned simple p50/p90/p10 lines.
        # We need the FINAL value of those lines.
        
        p50_final = sim_result.get('p50', [])[-1] if sim_result.get('p50') else current_price
        p90_final = sim_result.get('p90', [])[-1] if sim_result.get('p90') else current_price
        p10_final = sim_result.get('p10', [])[-1] if sim_result.get('p10') else current_price
        
        proj_data = Projections(
            monte_carlo_p50=p50_final,
            monte_carlo_p90=p90_final,
            monte_carlo_p10=p10_final,
            current_price=current_price
        )

        # 4. Evaluate
        stock_data = StockData(
            ticker=ticker,
            beta=beta,
            dividend_yield=div_yield_pct,
            market_bull_regime=regime["bull_regime"],
            fundamentals=fund_data,
            technicals=tech_data,
            sentiment=sentiment_data,
            projections=proj_data
        )
        
        scorer = VinSightScorer()
        score_result = scorer.evaluate(stock_data)

        # 5. Format Output for Frontend (Backward Compatible wrapper)
        # We map v5.0 result to the shape frontend expects
        
        # Frontend expects: Use color/rating/score directly.
        # New field: "narrative" (or repurpose justification to be a narrative summary)
        
        # Mapping Verdict to Colors
        rating_color_map = {
            "Strong Buy": "emerald",
            "Buy": "emerald",
            "Hold": "yellow",
            "Sell": "red"
        }
        
        color = rating_color_map.get(score_result.rating, "yellow")
        
        ai_analysis_response = {
            "rating": score_result.rating.upper(), # BUY/SELL
            "color": color,
            "score": score_result.total_score,
            "justification": score_result.verdict_narrative,
            "outlooks": {
                "short_term": [f"Momentum: {momentum}", f"Volume: {vol_trend}"],
                "medium_term": [f"Rank: {score_result.rating}", f"Regime: {'Bull' if regime['bull_regime'] else 'Bear/Defensive'}"],
                "long_term": [f"P/E: {pe:.1f}", f"Beta: {beta:.2f}"]
            },
            "raw_breakdown": score_result.breakdown,
            "modifications": score_result.modifications 
        }

        # Prepare SMA dict for frontend
        sma_data = {
            "sma_5": latest_ind.get('SMA_5'),
            "sma_10": latest_ind.get('SMA_10'),
            "sma_50": latest_ind.get('SMA_50'),
            "sma_200": latest_ind.get('SMA_200')
        }
        
        return {
            "indicators": indicators, 
            "risk": risk, 
            "sentiment": sentiment_result,  # Can be None
            "ai_analysis": ai_analysis_response, 
            "sma": sma_data
        }
    except Exception as e:
        logger.exception(f"Error in technical analysis for {ticker}")
        raise HTTPException(status_code=500, detail="Analysis failed. Please try again.")

@router.get("/institutional/{ticker}")
def get_institutional_data(ticker: str):
    try:
        data = finance.get_institutional_holders(ticker)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/simulation/{ticker}")
def get_simulation(ticker: str):
    try:
        history = finance.get_stock_history(ticker, period="1y")
        sim_result = simulation.run_monte_carlo(history)
        return sim_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sentiment/{ticker}")
def get_sentiment(ticker: str):
    """
    Dedicated endpoint for sentiment analysis (lazy-loaded).
    Returns sentiment calculated using Groq-only approach.
    """
    try:
        news = finance.get_news(ticker)
        sentiment_result = analysis.calculate_news_sentiment(news, deep_analysis=True)
        return sentiment_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
