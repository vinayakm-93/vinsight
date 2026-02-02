
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.vinsight_scorer import VinSightScorer, StockData, Fundamentals, Technicals, Projections, Sentiment

def run_test():
    print(f"Testing VinSightScorer {VinSightScorer.VERSION}")
    scorer = VinSightScorer()
    
    # Case 1: Perfect Stock (High Quality, Strong Trend)
    stock_perfect = StockData(
        ticker="AAPL",
        fundamentals=Fundamentals(
            inst_ownership=85.0,
            pe_ratio=25.0,
            forward_pe=20.0,
            peg_ratio=1.5, # Slightly high but common
            earnings_growth_qoq=0.25,
            revenue_growth_3y=0.15,
            sector_name="Technology",
            profit_margin=0.25,
            operating_margin=0.30,
            gross_margin_trend="Rising",
            roe=0.40,
            roa=0.15,
            debt_to_equity=1.5,
            debt_to_ebitda=2.0,
            interest_coverage=20.0,
            current_ratio=1.5,
            altman_z_score=5.0,
            fcf_yield=0.04,
            eps_surprise_pct=0.10
        ),
        technicals=Technicals(
            price=200.0,
            sma50=180.0,
            sma200=160.0,
            rsi=60.0,
            relative_volume=2.0,
            distance_to_high=0.02, # 2% from high
            momentum_label="Bullish",
            volume_trend="Strong"
        ),
        sentiment=Sentiment(
            news_sentiment_label="Bullish",
            news_sentiment_score=0.8,
            news_article_count=10
        ),
        projections=Projections(
            monte_carlo_p50=220.0,
            monte_carlo_p90=250.0,
            monte_carlo_p10=190.0, # -5% downside
            current_price=200.0
        ),
        beta=1.1,
        dividend_yield=0.005,
        market_bull_regime=True
    )

    
    print("\n--- Test Case 1: Quality Growth Leader ---")
    result1 = scorer.evaluate(stock_perfect)
    scorer.print_report(stock_perfect, result1)
    
    # Case 2: Value Trap (Low PE, but Weak Trend & Declining Margins)
    stock_trap = StockData(
        ticker="INTC-like",
        fundamentals=Fundamentals(
            inst_ownership=60.0,
            pe_ratio=10.0, # Cheap
            forward_pe=12.0, # Increasing? Bad.
            peg_ratio=2.5,
            earnings_growth_qoq=-0.10,
            revenue_growth_3y=0.0,
            sector_name="Technology",
            profit_margin=0.10,
            operating_margin=0.12,
            gross_margin_trend="Falling",
            roe=0.10,
            roa=0.04,
            debt_to_equity=0.8,
            debt_to_ebitda=2.5,
            interest_coverage=8.0,
            current_ratio=1.8,
            altman_z_score=2.2,
            fcf_yield=0.02,
            eps_surprise_pct=-0.05
        ),
        technicals=Technicals(
            price=30.0,
            sma50=35.0,
            sma200=40.0, # Downtrend
            rsi=35.0,
            relative_volume=0.8,
            distance_to_high=0.40, # 40% from high
            momentum_label="Bearish",
            volume_trend="Weak"
        ),
        sentiment=None,
        projections=Projections(
            monte_carlo_p50=28.0,
            monte_carlo_p10=20.0,
            monte_carlo_p90=35.0,
            current_price=30.0
        ),
        beta=1.2,
        dividend_yield=0.04,
        market_bull_regime=False
    )

    print("\n--- Test Case 2: Value Trap ---")
    result2 = scorer.evaluate(stock_trap)
    scorer.print_report(stock_trap, result2)

    # Case 3: Kill Switch Test (Insolvency)
    stock_broke = StockData(
        ticker="ZOMBIE",
        fundamentals=Fundamentals(
            inst_ownership=10.0,
            pe_ratio=5.0,
            forward_pe=5.0,
            peg_ratio=0.5,
            earnings_growth_qoq=0.0,
            revenue_growth_3y=0.0,
            sector_name="Industrials",
            profit_margin=0.01,
            operating_margin=0.05,
            gross_margin_trend="Flat",
            roe=0.02,
            roa=0.01,
            debt_to_equity=5.0, # High Debt
            debt_to_ebitda=8.0,
            interest_coverage=0.8, # < 1.5 -> KILL SWITCH
            current_ratio=0.5,
            altman_z_score=0.9, # Distress
            fcf_yield=-0.10,
            eps_surprise_pct=0.0
        ),
        technicals=Technicals(
            price=10.0,
            sma50=12.0,
            sma200=15.0,
            rsi=40.0,
            relative_volume=1.0, 
            distance_to_high=0.50,
            momentum_label="Bearish",
            volume_trend="Weak"
        ),
        sentiment=None,
        projections=Projections(
            monte_carlo_p50=9.0,
            monte_carlo_p90=11.0,
            monte_carlo_p10=7.0,
            current_price=10.0
        ),
        beta=2.5,
        dividend_yield=0.0,
        market_bull_regime=True
    )
    
    print("\n--- Test Case 3: Insolvency Kill Switch ---")
    result3 = scorer.evaluate(stock_broke)
    scorer.print_report(stock_broke, result3)
    
if __name__ == "__main__":
    run_test()
