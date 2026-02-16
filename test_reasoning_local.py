import sys
import os
import json
from dataclasses import dataclass
from typing import Dict, Any, Optional

# Mock the environment
from dotenv import load_dotenv
load_dotenv('backend/.env')
os.environ["AI_PROVIDER"] = "groq"
# Assuming GROQ_API_KEY is already in the environment or .env file

# Add valid path to sys.path to import services
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from services.reasoning_scorer import ReasoningScorer
    from services.vinsight_scorer import StockData, Fundamentals, Technicals, Sentiment, Projections
except ImportError as e:
    print(f"Import Error: {e}")
    print("Ensure you are running this from the project root.")
    sys.exit(1)

def run_test():
    print("Initializing Scorer...")
    scorer = ReasoningScorer()
    
    print(f"Provider: {scorer.provider}")
    if scorer.provider != "groq":
        print("WARNING: Provider is not groq. Check your .env setup.")

    # Create dummy data
    stock = StockData(
        ticker="AAPL",
        beta=1.2,
        dividend_yield=0.005,
        market_bull_regime=True,
        fundamentals=Fundamentals(
            pe_ratio=30.0,
            forward_pe=28.0,
            peg_ratio=2.5,
            fcf_yield=0.03,
            profit_margin=0.25,
            operating_margin=0.30,
            gross_margin_trend="Rising",
            roe=1.45,
            roa=0.25,
            debt_to_equity=1.5,
            debt_to_ebitda=0.8,
            interest_coverage=20.0,
            current_ratio=1.0,
            altman_z_score=8.0,
            earnings_growth_qoq=0.05,
            revenue_growth_3y=0.08,
            inst_ownership=0.60,
            eps_surprise_pct=0.02
        ),
        technicals=Technicals(
            price=220.0,
            sma50=210.0,
            sma200=190.0,
            rsi=65.0,
            relative_volume=1.5,
            distance_to_high=0.02,
            momentum_label="Bullish",
            volume_trend="Rising"
        ),
        sentiment=Sentiment("Positive", 0.6, 20),
        projections=Projections(230.0, 250.0, 200.0, 220.0)
    )

    print("\nRunning Evaluation (this may take 10-15s)...")
    try:
        result = scorer.evaluate(stock, persona="Growth")
        
        print("\n--- RESULT ---")
        print(f"Score: {result['score']}")
        print(f"Rating: {result['rating']}")
        print(f"Justification (Legacy View):\n{result['justification']}")
        
        print("\n--- METADATA (New Fields) ---")
        meta = result.get('meta', {})
        print(f"Source: {meta.get('source')}")
        print(f"Confidence: {meta.get('confidence')}%")
        print(f"Primary Driver: {meta.get('primary_driver')}")
        print(f"Thought Process: {meta.get('thought_process')}")
        
    except Exception as e:
        print(f"Evaluation Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test()
