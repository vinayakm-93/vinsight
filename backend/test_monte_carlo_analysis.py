#!/usr/bin/env python3
"""
Monte Carlo Analysis Evaluation Script

Tests Monte Carlo simulation on 10 varied stocks to identify:
1. Whether projected values are unrealistically high
2. Impact on recommendation score projections pillar
3. Statistical validity of the model
"""

import yfinance as yf
import numpy as np
import pandas as pd
from services.simulation import run_monte_carlo
from services.vinsight_scorer import VinSightScorer, Projections

# 10 Varied Stocks: Mix of tech, stable, volatile, and different market caps
TEST_STOCKS = [
    ("AAPL", "Apple - Large Cap Tech"),
    ("MSFT", "Microsoft - Large Cap Tech"),
    ("JNJ", "Johnson & Johnson - Healthcare/Defensive"),
    ("XOM", "Exxon Mobil - Energy"),
    ("TSLA", "Tesla - High Volatility Growth"),
    ("WMT", "Walmart - Retail/Defensive"),
    ("AMD", "AMD - High Volatility Semi"),
    ("PG", "Procter & Gamble - Consumer Staples"),
    ("NVDA", "NVIDIA - High Growth Semi"),
    ("KO", "Coca-Cola - Defensive Consumer")
]


def analyze_stock(ticker: str) -> dict:
    """Analyze a single stock's Monte Carlo simulation."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        
        if hist.empty:
            return {"error": "No history data"}
        
        # Convert to list of dicts as expected by simulation.py
        history = []
        for idx, row in hist.iterrows():
            history.append({
                "Date": str(idx.date()),
                "Open": row["Open"],
                "High": row["High"],
                "Low": row["Low"],
                "Close": row["Close"],
                "Volume": row["Volume"]
            })
        
        current_price = history[-1]["Close"]
        
        # Get some stock stats
        info = stock.info
        beta = info.get("beta", 1.0)
        
        # Calculate historical volatility (annualized)
        close_prices = hist["Close"]
        daily_returns = close_prices.pct_change().dropna()
        daily_volatility = daily_returns.std()
        annualized_vol = daily_volatility * np.sqrt(252) * 100  # As percentage
        
        daily_mean = daily_returns.mean()
        annualized_return = ((1 + daily_mean) ** 252 - 1) * 100
        
        # Run Monte Carlo (90 days, 10000 simulations)
        mc_result = run_monte_carlo(history, days=90, simulations=10000)
        
        if not mc_result:
            return {"error": "Monte Carlo failed"}
        
        p10 = mc_result["p10"][-1] if mc_result.get("p10") else current_price
        p50 = mc_result["p50"][-1] if mc_result.get("p50") else current_price
        p90 = mc_result["p90"][-1] if mc_result.get("p90") else current_price
        
        # Calculate returns
        upside_p50 = ((p50 - current_price) / current_price) * 100
        upside_p90 = ((p90 - current_price) / current_price) * 100
        downside_p10 = ((p10 - current_price) / current_price) * 100
        
        # Risk/Reward Ratio
        upside_diff = max(0, p90 - current_price)
        downside_diff = max(0.01, current_price - p10)
        risk_reward = upside_diff / downside_diff
        
        # Score the projections
        proj = Projections(
            monte_carlo_p50=p50,
            monte_carlo_p90=p90,
            monte_carlo_p10=p10,
            current_price=current_price
        )
        scorer = VinSightScorer()
        proj_score = scorer._score_projections(proj)
        
        return {
            "current_price": current_price,
            "beta": beta,
            "annualized_volatility": annualized_vol,
            "annualized_return": annualized_return,
            "daily_mu": daily_mean * 100,  # As percentage
            "daily_sigma": daily_volatility * 100,  # As percentage
            "p10": p10,
            "p50": p50,
            "p90": p90,
            "upside_p50_pct": upside_p50,
            "upside_p90_pct": upside_p90,
            "downside_p10_pct": downside_p10,
            "risk_reward_ratio": risk_reward,
            "projection_score": proj_score,
            "error": None
        }
        
    except Exception as e:
        return {"error": str(e)}


def expected_theoretical_return(mu: float, sigma: float, days: int = 90) -> dict:
    """
    Calculate theoretical expected value using Geometric Brownian Motion.
    
    For GBM: E[S_T] = S_0 * exp(mu * T)
    But with discrete simulation: E[S_T] ≈ S_0 * (1 + mu)^T
    
    The issue: If daily mu = 0.08%, after 90 days:
    Compound: (1 + 0.0008)^90 = 1.0745 -> 7.45% gain
    
    But simulation draws from N(mu, sigma) each day, which compounds!
    """
    # Discrete compound (simulation approach)
    discrete_return = ((1 + mu/100) ** days - 1) * 100
    
    # Continuous (GBM theory)
    continuous_return = (np.exp(mu/100 * days) - 1) * 100
    
    return {
        "discrete_return": discrete_return,
        "continuous_return": continuous_return
    }


def main():
    print("\n" + "="*80)
    print("MONTE CARLO SIMULATION EVALUATION")
    print("="*80)
    print("\nTesting 10 varied stocks for Monte Carlo simulation accuracy.")
    print("Simulation: 90 days forward, 10000 paths\n")
    
    results = []
    
    for ticker, desc in TEST_STOCKS:
        print(f"Analyzing {ticker: <6} - {desc}...", end=" ")
        result = analyze_stock(ticker)
        result["ticker"] = ticker
        result["description"] = desc
        results.append(result)
        
        if result.get("error"):
            print(f"ERROR: {result['error']}")
        else:
            print(f"Done (P50 upside: {result['upside_p50_pct']:.1f}%, Score: {result['projection_score']}/15)")
    
    print("\n" + "="*80)
    print("DETAILED RESULTS")
    print("="*80)
    
    valid_results = [r for r in results if not r.get("error")]
    
    print("\n### Historical Stats (1 Year)")
    print(f"{'Ticker':<8} {'Price':>10} {'Beta':>6} {'Ann.Vol%':>10} {'Ann.Ret%':>10} {'μ/day%':>8} {'σ/day%':>8}")
    print("-" * 70)
    for r in valid_results:
        print(f"{r['ticker']:<8} ${r['current_price']:>8.2f} {r['beta']:>6.2f} {r['annualized_volatility']:>9.1f}% {r['annualized_return']:>9.1f}% {r['daily_mu']:>7.3f}% {r['daily_sigma']:>7.2f}%")
    
    print("\n### Monte Carlo Results (90 days)")
    print(f"{'Ticker':<8} {'P10':>10} {'P50':>10} {'P90':>10} {'P10→%':>8} {'P50→%':>8} {'P90→%':>8} {'R/R':>6}")
    print("-" * 80)
    for r in valid_results:
        print(f"{r['ticker']:<8} ${r['p10']:>8.2f} ${r['p50']:>8.2f} ${r['p90']:>8.2f} {r['downside_p10_pct']:>7.1f}% {r['upside_p50_pct']:>7.1f}% {r['upside_p90_pct']:>7.1f}% {r['risk_reward_ratio']:>5.2f}")
    
    print("\n### Projection Scores (15 pts max)")
    print(f"{'Ticker':<8} {'P50 Upside':>12} {'R/R Ratio':>10} {'Score':>8} {'% of Max':>10}")
    print("-" * 50)
    for r in valid_results:
        pct_max = (r['projection_score'] / 15) * 100
        print(f"{r['ticker']:<8} {r['upside_p50_pct']:>11.1f}% {r['risk_reward_ratio']:>10.2f} {r['projection_score']:>6}/15 {pct_max:>9.0f}%")
    
    # Summary Statistics
    print("\n" + "="*80)
    print("SUMMARY ANALYSIS")
    print("="*80)
    
    if valid_results:
        p50_upsides = [r['upside_p50_pct'] for r in valid_results]
        scores = [r['projection_score'] for r in valid_results]
        rr_ratios = [r['risk_reward_ratio'] for r in valid_results]
        
        print(f"\nP50 Upside Statistics:")
        print(f"  Mean: {np.mean(p50_upsides):.1f}%")
        print(f"  Median: {np.median(p50_upsides):.1f}%")
        print(f"  Min: {min(p50_upsides):.1f}%")
        print(f"  Max: {max(p50_upsides):.1f}%")
        
        print(f"\nProjection Scores:")
        print(f"  Mean: {np.mean(scores):.1f}/15 ({np.mean(scores)/15*100:.0f}%)")
        print(f"  Min: {min(scores)}/15")
        print(f"  Max: {max(scores)}/15")
        
        print(f"\nRisk/Reward Ratios:")
        print(f"  Mean: {np.mean(rr_ratios):.2f}")
        print(f"  Median: {np.median(rr_ratios):.2f}")
        
        # Theoretical comparison
        print("\n### THEORETICAL ANALYSIS")
        print("\nExpected vs Simulated P50 (Theory Check):")
        print(f"{'Ticker':<8} {'μ/day%':>8} {'Theory90d%':>12} {'Sim P50%':>10} {'Delta':>8}")
        print("-" * 50)
        for r in valid_results:
            theory = expected_theoretical_return(r['daily_mu'], r['daily_sigma'], 90)
            delta = r['upside_p50_pct'] - theory['discrete_return']
            print(f"{r['ticker']:<8} {r['daily_mu']:>7.3f}% {theory['discrete_return']:>11.1f}% {r['upside_p50_pct']:>9.1f}% {delta:>7.1f}%")
        
        # Identify potential issues
        print("\n### POTENTIAL ISSUES IDENTIFIED")
        
        high_upside = [r for r in valid_results if r['upside_p50_pct'] > 15]
        if high_upside:
            print(f"\n⚠️  {len(high_upside)} stocks show >15% 90-day P50 upside:")
            for r in high_upside:
                print(f"   - {r['ticker']}: {r['upside_p50_pct']:.1f}% (Annualized: {r['upside_p50_pct']*4:.0f}%)")
        
        high_scores = [r for r in valid_results if r['projection_score'] >= 12]
        if high_scores:
            print(f"\n⚠️  {len(high_scores)} stocks score ≥12/15 on projections:")
            for r in high_scores:
                print(f"   - {r['ticker']}: {r['projection_score']}/15")
        
        # Core issue analysis
        print("\n### ROOT CAUSE ANALYSIS")
        print("""
The Monte Carlo simulation uses:
  shock = np.random.normal(mu, sigma)
  price = price * (1 + shock)
  
This compounds daily returns, which is correct for GBM.
However, the issue may be:

1. DRIFT ACCUMULATION: Even small positive μ compounds over 90 days
   - If μ = 0.10% daily → (1.001)^90 ≈ 1.094 → 9.4% gain
   
2. UPWARD BIAS: Markets tend to drift up historically, which inflates P50

3. SCORING THRESHOLDS may be too generous:
   - 20%+ upside → 8 pts (full score)
   - 12-20% upside → 6-8 pts (high partial)
   - This essentially rewards historical bull market drift
        """)


if __name__ == "__main__":
    main()
