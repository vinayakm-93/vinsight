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
        
        print(f"\n💼 FUNDAMENTALS:")
        print(f"   Inst Ownership: {inst_own:.1f}%")
        print(f"   P/E Ratio: {pe:.2f}")
        print(f"   PEG Ratio: {peg:.2f}")
        print(f"   Earnings Growth (QoQ): {earnings_growth:.2%}")
        print(f"   Beta: {beta:.2f}")
        print(f"   Yield: {div_yield_pct:.2f}%")
        
        # Get technicals
        indicators = analysis.calculate_technical_indicators(history)
        latest_ind = indicators[-1] if indicators else {}
        rsi = latest_ind.get('RSI', 50)
        sma50 = latest_ind.get('SMA_50', 0)
        sma200 = latest_ind.get('SMA_200', 0)
        momentum = latest_ind.get('Momentum_Signal', 'Bearish').capitalize()
        current_price = history[-1]['Close'] if history else 0
        
        # Volume trend
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
        
        print(f"\n📈 TECHNICALS:")
        print(f"   Price: ${current_price:.2f}")
        print(f"   SMA50: ${sma50:.2f}")
        print(f"   SMA200: ${sma200:.2f}")
        print(f"   RSI: {rsi:.1f}")
        print(f"   Volume Trend: {vol_trend}")
        
        # Sentiment for VinSight
        sent_label = sentiment_result.get('label', 'Neutral')
        news_art_count = sentiment_result.get('article_count', 0)
        news_vol_high = news_art_count > 5
        
        # Insider activity
        txs = institutional.get('insider_transactions', [])
        buys = sum(1 for t in txs if 'purchase' in t.get('Text', '').lower() or 'buy' in t.get('Text', '').lower())
        sells = sum(1 for t in txs if 'sale' in t.get('Text', '').lower() or 'sold' in t.get('Text', '').lower())
        
        if buys > sells:
            insider = "Net Buying"
        elif sells > buys + 2:
            insider = "Heavy Selling"
        else:
            insider = "Mixed/Minor Selling"
        
        # Monte Carlo
        p50_val = sim_result.get('p50', [])[-1] if sim_result.get('p50') else current_price
        p90_val = sim_result.get('p90', [])[-1] if sim_result.get('p90') else current_price
        p10_val = sim_result.get('p10', [])[-1] if sim_result.get('p10') else current_price
        
        # Create VinSight v5.0 data
        # Guard against missing price data – if price is zero or None, skip scoring for this stock
        if not current_price or current_price == 0:
            print(f"⚠️ Skipping {ticker} due to missing price data.")
            return None
        stock_data = StockData(
            ticker=ticker,
            beta=beta,
            dividend_yield=div_yield_pct,
            market_bull_regime=regime["bull_regime"],
            fundamentals=Fundamentals(
                inst_ownership=inst_own,
                inst_changing="Flat", # Placeholder
                pe_ratio=pe,
                peg_ratio=peg,
                earnings_growth_qoq=earnings_growth
            ),
            technicals=Technicals(
                price=current_price,
                sma50=sma50,
                sma200=sma200,
                rsi=rsi,
                momentum_label=momentum,
                volume_trend=vol_trend
            ),
            sentiment=Sentiment(
                news_sentiment_label=sent_label,
                news_sentiment_score=sentiment_result.get('score', 0),
                news_article_count=news_art_count,
                insider_activity=insider
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
        
        print(f"\n🎯 VINSIGHT v5.0 SCORE:")
        print(f"   Score: {result.total_score}/100")
        print(f"   Rating: {result.rating}")
        print(f"   Narrative: {result.verdict_narrative}")
        print(f"   Breakdown:")
        print(f"     - Fundamentals: {result.breakdown['Fundamentals']}/30")
        print(f"     - Technicals: {result.breakdown['Technicals']}/30")
        print(f"     - Sentiment: {result.breakdown['Sentiment']}/20")
        print(f"     - Projections: {result.breakdown['Projections']}/20")
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
