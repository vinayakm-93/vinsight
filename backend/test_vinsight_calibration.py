"""
VinSight Model Testing & Calibration
Tests VinSight v5.0 on diverse stocks to identify bias and accuracy issues
"""

import sys
sys.path.append('.')

from backend.services import finance, analysis
from backend.services.vinsight_scorer import VinSightScorer, StockData, Fundamentals, Technicals, Sentiment, Projections
from backend.services import simulation
from dotenv import load_dotenv

load_dotenv()

# Diverse test dataset
TEST_STOCKS = {
    "Strong Performers": ["NVDA", "AAPL", "MSFT", "PLTR"], 
    "Moderate": ["F", "INTC", "BAC"],  
    "Weak/Distressed": ["SNAP", "TDOC", "PARA"] 
}

def test_stock(ticker: str):
    """Test VinSight on a single stock"""
    print(f"\n{'='*80}")
    print(f"Testing: {ticker}")
    print('='*80)
    
    try:
        # Fetch data
        history = finance.get_stock_history(ticker, period="2y", interval="1d")
        fundamentals_info = finance.get_stock_info(ticker)
        news = finance.get_news(ticker)
        institutional = finance.get_institutional_holders(ticker)
        sim_result = simulation.run_monte_carlo(history, days=90, simulations=500)
        
        # v5.0 Specific Data
        regime = finance.get_market_regime()
        beta = fundamentals_info.get("beta", 1.0)
        div_yield = fundamentals_info.get("dividendYield", 0) or 0
        div_yield_pct = div_yield * 100
        
        # Calculate sentiment
        sentiment_result = analysis.calculate_news_sentiment(news, deep_analysis=False)
        print(f"\n📰 NEWS SENTIMENT:")
        print(f"   Label: {sentiment_result.get('label', 'N/A')}")
        print(f"   Score: {sentiment_result.get('score', 0):.3f}")
        print(f"   Articles: {sentiment_result.get('article_count', 0)}")
        
        # Get fundamentals
        inst_own = institutional.get("institutionsPercentHeld", 0) * 100
        # Fix for <1 issue if any
        if inst_own < 1 and institutional.get("institutionsPercentHeld", 0) > 0:
            inst_own = institutional.get("institutionsPercentHeld", 0) * 100
            
        pe = fundamentals_info.get("trailingPE", 0) or 0
        peg = finance.get_peg_ratio(ticker)
        earnings_growth = fundamentals_info.get("earningsQuarterlyGrowth", 0)
            
        # v8.0 Specific Data Fetching
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
        
        # Advanced Metrics fetch for new fields
        # Ideally this should be a real fetch, but for test script we can mock or lightweight fetch
        # Let's try to get what we can from basic info or default to None to test missing data handling
        rev_growth_3y = None # advanced_metrics not easily available in this script scope without more imports
        gross_margin_trend = "Flat"
        debt_to_ebitda = None
        altman_z = None
        interest_cov = 100.0

        print(f"\n💼 FUNDAMENTALS:")
        print(f"   Inst Ownership: {inst_own:.1f}%")
        print(f"   P/E Ratio: {pe:.2f}")
        print(f"   PEG Ratio: {peg if peg is not None else 'Missing'}")
        print(f"   Earnings Growth (QoQ): {earnings_growth:.2%}")
        
        # Get technicals
        indicators = analysis.calculate_technical_indicators(history)
        latest_ind = indicators[-1] if indicators else {}
        rsi = latest_ind.get('RSI', 50)
        sma50 = latest_ind.get('SMA_50', 0)
        sma200 = latest_ind.get('SMA_200', 0)
        
        current_price = history[-1]['Close'] if history else 0
        momentum = "Bullish" if current_price > sma50 else "Bearish" # v8.0 logic
        
        # Calculate Volume Trend (v8.0 logic) and other Techs
        avg_vol = fundamentals_info.get('averageVolume')
        curr_vol = history[-1]['Volume'] if history else 0
        relative_volume = (curr_vol / avg_vol) if avg_vol and avg_vol > 0 else 1.0
        
        high52 = fundamentals_info.get('fiftyTwoWeekHigh')
        distance_to_high = ((high52 - current_price) / high52) if high52 and high52 > 0 else 0.0

        # ... (Volume trend logic omitted for brevity as it's complex to re-implement, using default)
        vol_trend = "Weak/Mixed"
        
        # Sentiment Variables
        sent_label = sentiment_result.get('label', 'Neutral')
        news_art_count = sentiment_result.get('article_count', 0)
        
        # Monte Carlo
        p50_val = sim_result.get('p50', [])[-1] if sim_result.get('p50') else current_price
        p90_val = sim_result.get('p90', [])[-1] if sim_result.get('p90') else current_price
        p10_val = sim_result.get('p10', [])[-1] if sim_result.get('p10') else current_price
        
        # StockData v8.0
        stock_data = StockData(
            ticker=ticker,
            beta=beta,
            dividend_yield=div_yield_pct,
            market_bull_regime=regime["bull_regime"],
            fundamentals=Fundamentals(
                inst_ownership=inst_own,
                pe_ratio=pe,
                forward_pe=forward_pe,
                peg_ratio=peg,
                earnings_growth_qoq=earnings_growth,
                revenue_growth_3y=rev_growth_3y,
                sector_name=fundamentals_info.get("sector", "Technology"),
                profit_margin=profit_margin,
                operating_margin=operating_margin,
                gross_margin_trend=gross_margin_trend,
                roe=roe,
                roa=roa,
                debt_to_equity=debt_to_equity,
                debt_to_ebitda=debt_to_ebitda,
                interest_coverage=interest_cov,
                current_ratio=current_ratio,
                altman_z_score=altman_z,
                fcf_yield=fcf_yield,
                eps_surprise_pct=eps_surprise
            ),
            technicals=Technicals(
                price=current_price,
                sma50=sma50,
                sma200=sma200,
                rsi=rsi,
                relative_volume=relative_volume,
                distance_to_high=distance_to_high,
                momentum_label=momentum,
                volume_trend=vol_trend
            ),
            sentiment=Sentiment(
                news_sentiment_label=sent_label,
                news_sentiment_score=sentiment_result.get('score', 0),
                news_article_count=news_art_count
            ),
            projections=Projections(
                monte_carlo_p50=p50_val,
                monte_carlo_p90=p90_val,
                monte_carlo_p10=p10_val,
                current_price=current_price
            )
        )
        
        # Score
        scorer = VinSightScorer()
        result = scorer.evaluate(stock_data)
        
        print(f"\n🎯 VINSIGHT v8.0 SCORE:")
        print(f"   Score: {result.total_score}/100")
        print(f"   Rating: {result.rating}")
        print(f"   Narrative: {result.verdict_narrative}")
        print(f"   Breakdown:")
        print(f"     - Quality Score: {result.breakdown.get('Quality Score', 0)}/100")
        print(f"     - Timing Score: {result.breakdown.get('Timing Score', 0)}/100")
        print(f"   Modifications: {result.modifications}")

        return {
            'ticker': ticker,
            'rating': result.rating,
            'score': result.total_score
        }
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("="*80)
    print("VINSIGHT v5.0 MODEL CALIBRATION TEST")
    print("="*80)
    
    results = []
    
    for category, tickers in TEST_STOCKS.items():
        print(f"\n\n{'#'*80}")
        print(f"# Category: {category}")
        print(f"{'#'*80}")
        
        for ticker in tickers:
            result = test_stock(ticker)
            if result:
                results.append(result)
