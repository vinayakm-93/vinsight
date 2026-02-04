
import sys
import os
import logging
import pandas as pd
import numpy as np
import random
from typing import List

# --- Setup Paths ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
backend_dir = os.path.join(project_root, 'backend')

if backend_dir not in sys.path: sys.path.insert(0, backend_dir)
if project_root not in sys.path: sys.path.insert(0, project_root)

try:
    from services.vinsight_scorer import VinSightScorer, StockData, Fundamentals, Technicals, Sentiment, Projections
except ImportError:
    pass

# --- Synthetic Data Generator ---
class SyntheticGenerator:
    """Generates random stock profiles to stress-test the scorer."""
    
    SECTORS = [
        "Technology", "Financial Services", "Healthcare", "Energy", 
        "Consumer Cyclical", "Consumer Defensive", "Utilities", "Real Estate"
    ]
    
    def generate_batch(self, n=50) -> List[StockData]:
        stocks = []
        for i in range(n):
            stocks.append(self._create_random_stock(i))
        return stocks

    def _create_random_stock(self, idx) -> StockData:
        ticker = f"SIM_{idx:03d}"
        sector = random.choice(self.SECTORS)
        
        # Random profiles: 
        # 1. High Growth / Overvalued (Tech-like)
        # 2. Value / Low Growth (Bank-like)
        # 3. Distressed / Value Trap
        # 4. Momentum Runner
        
        # Adjusted weights to include "Stagnant/Mediocre" (the "Dead Money")
        # Growth (20%), Value (25%), Distressed (10%), Momentum (15%), Stagnant (30%)
        profile_type = random.choices(
            ['growth', 'value', 'distressed', 'momentum', 'stagnant'], 
            weights=[0.20, 0.25, 0.10, 0.15, 0.30]
        )[0]
        
        price = random.uniform(50, 500)
        
        # Fundamentals Defaults
        pe = 20
        peg = 1.5
        growth = 0.10
        debt = 1.0
        margin = 0.15
        roe = 0.15
        
        # Technicals Defaults
        sma200 = price * 0.95
        sma50 = price * 0.98
        rsi = 50
        
        if profile_type == 'growth':
            pe = random.uniform(30, 80)
            growth = random.uniform(0.15, 0.40)
            peg = pe / (growth*100)
            debt = random.uniform(0.0, 1.5)
            sector = "Technology"
            
        elif profile_type == 'value':
            pe = random.uniform(8, 18)
            growth = random.uniform(0.02, 0.08)
            peg = pe / (growth*100)
            debt = random.uniform(0.5, 3.0)
            margin = random.uniform(0.05, 0.20)
            
        elif profile_type == 'stagnant':
            # The "Mediocre" Middle: Not failing, but not growing. 
            # Often overpriced for their lack of growth.
            pe = random.uniform(20, 35) # Overpriced
            growth = random.uniform(0.01, 0.05) # Low growth
            peg = pe / (growth*100) # Result: High PEG (e.g. 25 / 3 = 8.3) -> Should score low on Quality
            margin = random.uniform(0.02, 0.08) # Low margin
            roe = random.uniform(0.05, 0.10) # Low ROE
            debt = random.uniform(1.5, 3.0) # Moderate debt
            
            # Technicals: Choppy/Flat
            sma200 = price * random.uniform(0.95, 1.05)
            sma50 = price * random.uniform(0.98, 1.02)
            rsi = random.uniform(45, 55)
            
        elif profile_type == 'distressed':
            pe = random.uniform(5, 100) # Erratic
            debt = random.uniform(3.0, 8.0) # High debt
            growth = random.uniform(-0.10, 0.05)
            # Insolvency trigger chance
            interest_cov = random.uniform(0.5, 2.0)
            
        elif profile_type == 'momentum':
            # Price way above SMA
            sma200 = price * 0.70
            sma50 = price * 0.80
            rsi = random.uniform(60, 85)
            pe = random.uniform(25, 60)
            
        # Refine Technicals
        if profile_type != 'momentum':
            sma200 = price * random.uniform(0.8, 1.2)
            sma50 = price * random.uniform(0.9, 1.1)
            rsi = random.uniform(30, 70)
            
        # Insolvency check for Distressed
        int_cov = 5.0
        if profile_type == 'distressed': int_cov = random.uniform(0.8, 2.5)
            
        f = Fundamentals(
            pe_ratio=pe, forward_pe=pe*0.9, peg_ratio=peg,
            fcf_yield=margin*0.8, profit_margin=margin, operating_margin=margin*1.5,
            gross_margin_trend=random.choice(["Rising", "Flat", "Falling"]),
            roe=roe, roa=roe/3, debt_to_equity=debt, debt_to_ebitda=debt*2,
            interest_coverage=int_cov, current_ratio=1.5, altman_z_score=1.8 if profile_type=='distressed' else 3.5,
            earnings_growth_qoq=growth, revenue_growth_3y=growth,
            inst_ownership=0.6, eps_surprise_pct=0.05, sector_name=sector
        )
        
        t = Technicals(
            price=price, sma50=sma50, sma200=sma200, rsi=rsi,
            relative_volume=random.uniform(0.5, 3.0),
            distance_to_high=random.uniform(0.0, 0.2),
            momentum_label="Bullish" if price > sma50 else "Bearish",
            volume_trend="Flat"
        )
        
        # Simulation Logic: Assign a "Future Return" based on Score Quality
        # This is circular but proves the *distribution* logic
        # We don't use this for proving accuracy, just for visualization in the report
        return StockData(ticker, 1.0, 0.0, True, f, t, Sentiment("Neutral",0,0), Projections(0,0,0,price))


def run_stress_test():
    print("--- VinSight Synthetic Stress Test ---")
    gen = SyntheticGenerator()
    scorer = VinSightScorer()
    
    # 1. Generate 100 Scenarios
    stocks = gen.generate_batch(100)
    
    results = []
    
    print(f"\n{'TICKER':<8} | {'SECTOR':<15} | {'PEG':<5} | {'RSI':<5} | {'SCORE':<5} | {'RATING':<11} | {'VETO?'}")
    print("-" * 80)
    
    veto_count = 0
    
    for s in stocks:
        res = scorer.evaluate(s)
        
        veto_msg = "No"
        if res.modifications:
            veto_msg = "YES"
            veto_count += 1
            
        results.append({
            'score': res.total_score,
            'rating': res.rating,
            'sector': s.fundamentals.sector_name,
            'type': 'Distressed' if s.fundamentals.interest_coverage < 1.5 else 'Normal'
        })
        
        # Print sample of 20
        if len(results) <= 20: 
             print(f"{s.ticker:<8} | {s.fundamentals.sector_name:<15} | {s.fundamentals.peg_ratio:<5.1f} | {s.technicals.rsi:<5.0f} | {res.total_score:<5.1f} | {res.rating:<11} | {veto_msg}")

    # --- Analysis ---
    df = pd.DataFrame(results)
    
    print(f"\n--- TEST SUMMARY ---")
    print(f"Total Scenarios: {len(df)}")
    print(f"Vetos Triggered: {veto_count} ({veto_count/len(df)*100:.1f}%)")
    
    print("\n[Score Distribution]")
    print(df['score'].describe())
    
    print("\n[Avg Score by Rating]")
    print(df.groupby('rating')['score'].mean().sort_values(ascending=False))
    
    print("\n[Avg Score by Sector]")
    print(df.groupby('sector')['score'].mean())
    
    print("\n[Score Distribution Curve]")
    # Create buckets
    bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    labels = ['0-9', '10-19', '20-29', '30-39', '40-49', '50-59', '60-69', '70-79', '80-89', '90-100']
    df['bucket'] = pd.cut(df['score'], bins=bins, labels=labels, right=False)
    counts = df['bucket'].value_counts().sort_index()
    
    total = len(df)
    for label, count in counts.items():
        bar = '█' * int(count)
        pct = (count / total) * 100
        print(f"{label:>7} | {bar:<30} ({count} - {pct:.0f}%)")

if __name__ == "__main__":
    run_stress_test()
