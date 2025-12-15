"""
VinSight Model Testing & Calibration
Tests VinSight v2 on diverse stocks to identify bias and accuracy issues
"""

import sys
sys.path.append('.')

from backend.services import finance, analysis
from backend.services.vinsight_scorer import VinSightScorer, StockData, Fundamentals, Technicals, Sentiment, Projections
from backend.services import simulation

# Diverse test dataset
TEST_STOCKS = {
    "Strong Performers": ["NVDA", "AAPL", "MSFT"],  # Strong companies
    "Moderate": ["F", "INTC", "BAC"],  # Decent but not great
    "Weak/Distressed": ["SNAP", "TDOC", "PARA"]  # Struggling companies
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
        sim_result = simulation.run_monte_carlo(history, days=30, simulations=500)
        
        # Calculate sentiment
        sentiment_result = analysis.calculate_news_sentiment(news, deep_analysis=False)
        print(f"\n📰 NEWS SENTIMENT:")
        print(f"   Label: {sentiment_result.get('label', 'N/A')}")
        print(f"   Score: {sentiment_result.get('score', 0):.3f}")
        print(f"   Confidence: {sentiment_result.get('confidence', 0):.3f}")
        print(f"   Source: {sentiment_result.get('source', 'N/A')}")
        print(f"   Articles: {sentiment_result.get('article_count', 0)}")
        
        # Get fundamentals
        inst_own = institutional.get("institutionsPercentHeld", 0) * 100
        if inst_own < 1 and institutional.get("institutionsPercentHeld", 0) > 0:
            inst_own = institutional.get("institutionsPercentHeld", 0) * 100
        
        pe = fundamentals_info.get("trailingPE", 0) or 0
        peg = finance.get_peg_ratio(ticker)
        
        current_price = history[-1]['Close'] if history else 0
        target_mean = fundamentals_info.get("targetMeanPrice")
        upside = ((target_mean - current_price) / current_price) * 100 if target_mean and current_price > 0 else 0
        
        print(f"\n💼 FUNDAMENTALS:")
        print(f"   Inst Ownership: {inst_own:.1f}%")
        print(f"   P/E Ratio: {pe:.2f}")
        print(f"   PEG Ratio: {peg:.2f}")
        print(f"   Analyst Upside: {upside:.1f}%")
        
        # Get technicals
        indicators = analysis.calculate_technical_indicators(history)
        latest_ind = indicators[-1] if indicators else {}
        rsi = latest_ind.get('RSI', 50)
        sma50 = latest_ind.get('SMA_50', 0)
        sma200 = latest_ind.get('SMA_200', 0)
        momentum = latest_ind.get('Momentum_Signal', 'Bearish').capitalize()
        
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
        print(f"   Momentum: {momentum}")
        print(f"   Volume Trend: {vol_trend}")
        
        # Sentiment for VinSight
        sent_label = sentiment_result.get('label', 'Neutral')
        
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
        
        gain_p90 = max(0, p90_val - current_price)
        loss_p10 = max(0, current_price - p10_val)
        
        # Create VinSight data
        stock_data = StockData(
            ticker=ticker,
            fundamentals=Fundamentals(
                inst_ownership=inst_own,
                pe_ratio=pe,
                peg_ratio=peg,
                analyst_upside=upside
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
                sentiment_label=sent_label,
                insider_activity=insider
            ),
            projections=Projections(
                monte_carlo_p50=p50_val,
                current_price=current_price,
                risk_reward_gain_p90=gain_p90,
                risk_reward_loss_p10=loss_p10
            )
        )
        
        # Score
        scorer = VinSightScorer()
        result = scorer.evaluate(stock_data)
        
        print(f"\n🎯 VINSIGHT v2.0 SCORE:")
        print(f"   Total Score: {result.total_score}/100")
        print(f"   Verdict: {result.verdict}")
        print(f"   Breakdown:")
        print(f"     - Fundamentals: {result.breakdown['Fundamentals']}/30")
        print(f"     - Technicals: {result.breakdown['Technicals']}/30")
        print(f"     - Sentiment: {result.breakdown['Sentiment']}/20")
        print(f"     - Projections: {result.breakdown['Projections']}/20")
        
        return {
            'ticker': ticker,
            'sentiment': sentiment_result,
            'score': result.total_score,
            'verdict': result.verdict,
            'breakdown': result.breakdown,
            'fundamentals': {
                'inst_own': inst_own,
                'pe': pe,
                'peg': peg,
                'upside': upside
            },
            'technicals': {
                'rsi': rsi,
                'momentum': momentum
            }
        }
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("="*80)
    print("VINSIGHT v2.0 MODEL CALIBRATION TEST")
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
    
    # Summary
    print(f"\n\n{'='*80}")
    print("SUMMARY")
    print('='*80)
    
    verdicts = {}
    sentiments = {}
    
    for r in results:
        verdict = r['verdict']
        sent = r['sentiment'].get('label', 'Unknown')
        
        verdicts[verdict] = verdicts.get(verdict, 0) + 1
        sentiments[sent] = sentiments.get(sent, 0) + 1
    
    print("\n📊 VERDICT DISTRIBUTION:")
    for verdict, count in sorted(verdicts.items()):
        pct = (count / len(results)) * 100
        print(f"   {verdict}: {count}/{len(results)} ({pct:.1f}%)")
    
    print("\n📰 SENTIMENT DISTRIBUTION:")
    for sent, count in sorted(sentiments.items()):
        pct = (count / len(results)) * 100
        print(f"   {sent}: {count}/{len(results)} ({pct:.1f}%)")
    
    print(f"\n⚠️ ISSUES TO INVESTIGATE:")
    if verdicts.get('Buy', 0) + verdicts.get('Strong Buy', 0) > len(results) * 0.7:
        print("   - TOO MANY BUY RECOMMENDATIONS (>70%)")
    if sentiments.get('Positive', 0) > len(results) * 0.7:
        print("   - TOO MANY POSITIVE SENTIMENTS (>70%)")
    if len(set(verdicts.keys())) == 1:
        print("   - ALL STOCKS HAVE SAME VERDICT (no discrimination)")
    
    print("\n" + "="*80)
