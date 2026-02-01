
import sys
import os
import json
import logging

# Add the backend directory to sys.path so we can import services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services import finance, analysis, simulation
from services.vinsight_scorer import VinSightScorer, StockData, Fundamentals, Technicals, Sentiment, Projections

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_scorer")

def fetch_and_score(ticker: str):
    logger.info(f"Fetching data for {ticker}...")

    # 1. Fetch Data
    try:
        history = finance.get_stock_history(ticker, period="2y", interval="1d")
        fundamentals_info = finance.get_stock_info(ticker)
        news = finance.get_news(ticker)
        institutional = finance.get_institutional_holders(ticker)
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return

    logger.info("Data fetched successfully.")

    # 2. Process Data (Mimic routes/data.py)
    
    # Technicals
    indicators = analysis.calculate_technical_indicators(history)
    current_price = history[-1]['Close'] if history else 0
    
    latest_ind = indicators[-1] if indicators else {}
    rsi = latest_ind.get('RSI', 50)
    sma50 = latest_ind.get('SMA_50', 0)
    sma200 = latest_ind.get('SMA_200', 0)
    
    if current_price > sma50:
        momentum = "Bullish"
    else:
        momentum = "Bearish"
        
    # Simple Volume Trend Proxy
    vol_trend = "Weak/Mixed" # Simplified for debug

    tech_data = Technicals(
        price=current_price,
        sma50=sma50,
        sma200=sma200,
        rsi=rsi,
        momentum_label=momentum,
        volume_trend=vol_trend
    )

    # Fundamentals
    inst_own = institutional.get("institutionsPercentHeld", 0) * 100
    earnings_growth = fundamentals_info.get("earningsQuarterlyGrowth", 0)
    pe = fundamentals_info.get("trailingPE", 0) or 0
    peg = finance.get_peg_ratio(ticker)
    profit_margin = fundamentals_info.get("profitMargins", 0) or 0
    operating_margin = fundamentals_info.get("operatingMargins", 0) or 0
    debt_to_equity = fundamentals_info.get("debtToEquity", 0) or 0
    if debt_to_equity > 10: debt_to_equity /= 100
    
    current_ratio = fundamentals_info.get("currentRatio") or 0.0
    roe = fundamentals_info.get("returnOnEquity") or 0.0
    roa = fundamentals_info.get("returnOnAssets") or 0.0
    forward_pe = fundamentals_info.get("forwardPE") or 0.0
    fcf_yield = fundamentals_info.get("fcf_yield", 0.0)
    eps_surprise = finance.get_earnings_surprise(ticker)
    
    detected_sector = fundamentals_info.get("sector", "Technology")

    fund_data = Fundamentals(
        inst_ownership=inst_own,
        pe_ratio=pe,
        forward_pe=forward_pe,
        peg_ratio=peg,
        earnings_growth_qoq=earnings_growth,
        sector_name=detected_sector,
        profit_margin=profit_margin,
        operating_margin=operating_margin,
        roe=roe,
        roa=roa,
        debt_to_equity=debt_to_equity,
        current_ratio=current_ratio,
        fcf_yield=fcf_yield,
        eps_surprise_pct=eps_surprise
    )

    # Sentiment (Using basic calculation or mock if analysis fails)
    sentiment_result = analysis.calculate_news_sentiment(news, deep_analysis=False) # Fast mode
    if not sentiment_result:
        sentiment_result = {"label": "Neutral", "score": 0, "article_count": len(news)}
    
    sentiment_data = Sentiment(
        news_sentiment_label=sentiment_result.get('label', 'Neutral'),
        news_sentiment_score=sentiment_result.get('score', 0),
        news_article_count=len(news)
    )

    # Projections (Monte Carlo)
    sim_result = simulation.run_monte_carlo(history, days=90, simulations=1000) # Faster sim
    p50 = sim_result.get('p50', [])[-1] if sim_result.get('p50') else current_price
    p90 = sim_result.get('p90', [])[-1] if sim_result.get('p90') else current_price
    p10 = sim_result.get('p10', [])[-1] if sim_result.get('p10') else current_price

    proj_data = Projections(
        monte_carlo_p50=p50,
        monte_carlo_p90=p90,
        monte_carlo_p10=p10,
        current_price=current_price
    )
    
    # Market Regime
    regime = finance.get_market_regime()
    raw_beta = fundamentals_info.get("beta")
    beta = float(raw_beta) if raw_beta is not None else 1.0
    raw_yield = fundamentals_info.get("dividendYield")
    div_yield_pct = (float(raw_yield) * 100) if raw_yield is not None else 0.0

    # Stock Data
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

    # 3. Print Input Data
    print("\n" + "="*50)
    print(f" INPUT DATA FOR {ticker} SCORER")
    print("="*50)
    print(json.dumps({
        "Ticker": stock_data.ticker,
        "Market Regime": "Bull" if stock_data.market_bull_regime else "Defensive",
        "Fundamentals": vars(stock_data.fundamentals),
        "Technicals": vars(stock_data.technicals),
        "Sentiment": vars(stock_data.sentiment),
        "Projections": vars(stock_data.projections)
    }, indent=2, default=str))

    # 4. Score
    scorer = VinSightScorer()
    result = scorer.evaluate(stock_data)
    
    # 5. Print Output
    scorer.print_report(stock_data, result)
    
    print("\nDetailed Breakdown:")
    for detail in result.details:
        print(f" - {detail['category']} | {detail['metric']}: {detail['value']} (Score: {detail['score']}) -> {detail['status']}")

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    fetch_and_score(ticker)
