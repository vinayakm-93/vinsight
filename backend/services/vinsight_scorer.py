from dataclasses import dataclass, field
from typing import Literal, Optional, List, Dict

# --- Data Structures ---

@dataclass
class Fundamentals:
    inst_ownership: float  # Percentage (e.g., 81.3 for 81.3%)
    inst_changing: Literal["Rising", "Flat", "Falling"] # Derived from changes
    pe_ratio: float
    peg_ratio: float
    earnings_growth_qoq: float # Percentage
    
    # Cluster Data (Approximated)
    sector_pe_median: float = 25.0 # Benchmark, default if peer data unavailable

@dataclass
class Technicals:
    price: float
    sma50: float
    sma200: float
    rsi: float
    momentum_label: Literal["Bullish", "Bearish"] # Derived from SMA5 > SMA10
    volume_trend: Literal["Price Rising + Vol Rising", "Price Rising + Vol Falling", "Price Falling + Vol Rising", "Weak/Mixed"]
    
@dataclass
class Sentiment:
    news_sentiment_label: Literal["Positive", "Neutral", "Negative"] # From News
    news_volume_high: bool # Proxy for "Social Volume"
    insider_activity: Literal["Net Buying", "No Activity", "Mixed/Minor Selling", "Heavy Selling", "Cluster Selling"]

@dataclass
class Projections:
    monte_carlo_p50: float
    monte_carlo_p90: float # Upside
    monte_carlo_p10: float # Downside
    current_price: float 

@dataclass
class StockData:
    ticker: str
    beta: float
    dividend_yield: float # Percentage
    market_bull_regime: bool # From SPY Check
    
    fundamentals: Fundamentals
    technicals: Technicals
    sentiment: Sentiment
    projections: Projections

@dataclass
class ScoreResult:
    total_score: int
    rating: str
    verdict_narrative: str
    breakdown: dict
    modifications: List[str]

# --- Scoring Engine v5.0 ---

class VinSightScorer:
    VERSION = "v5.0" 

    def evaluate(self, stock: StockData) -> ScoreResult:
        # --- Phase 1: Macro Regime Filter (The Gatekeeper) ---
        # "Defensive Mode" triggers if Market is Bearish (SPY < SMA200)
        # In Defensive Mode, High Beta (>1.5) stocks are capped at 70.
        is_defensive_mode = not stock.market_bull_regime
        high_beta = stock.beta > 1.5
        
        score_cap = 100
        if is_defensive_mode and high_beta:
            score_cap = 70
        
        # --- Phase 2: Core Score (100 Points) ---
        
        # A. Fundamentals (30 Points)
        f_score = self._score_fundamentals(stock.fundamentals, stock.technicals.volume_trend, stock.technicals.price)
        
        # B. Technicals (30 Points)
        t_score = self._score_technicals(stock.technicals)
        
        # C. Sentiment (20 Points)
        s_score = self._score_sentiment(stock.sentiment)
        
        # D. Projections (20 Points)
        p_score = self._score_projections(stock.projections)
        
        raw_score = f_score + t_score + s_score + p_score
        
        # --- Phase 3: Bonuses & Penalties ---
        bonuses = 0
        modifications = []
        
        # Safety Bonus: Yield > 2.5% AND Beta < 0.8
        # v5.0 Rule: Double weight in Defensive Mode? (Prompt says "Double the 'Safety Bonus' weight")
        # Standard Bonus = +10. Market Bear = +20.
        safety_bonus_val = 20 if is_defensive_mode else 10
        if stock.dividend_yield > 2.5 and stock.beta < 0.8:
            bonuses += safety_bonus_val
            modifications.append(f"Safety Bonus (+{safety_bonus_val})")
            
        # Volatility Penalty: Beta > 2.0 AND Trend is Down (Price < SMA200)
        if stock.beta > 2.0 and stock.technicals.price < stock.technicals.sma200:
            bonuses -= 10
            modifications.append("Volatility Penalty (-10)")
        
        final_score = raw_score + bonuses
        
        # Apply Cap
        if final_score > score_cap:
            final_score = score_cap
            modifications.append(f"Defensive Mode Cap ({score_cap})")
            
        # Clamp 0-100
        final_score = max(0, min(100, final_score))
        
        # --- Phase 4: Output Generation ---
        rating = self._get_rating(final_score)
        narrative = self._generate_narrative(stock.ticker, final_score, f_score, t_score, s_score, p_score, modifications, is_defensive_mode)
        
        breakdown = {
            "Fundamentals": f_score,
            "Technicals": t_score,
            "Sentiment": s_score,
            "Projections": p_score
        }
        
        return ScoreResult(final_score, rating, narrative, breakdown, modifications)

    def _score_fundamentals(self, f: Fundamentals, vol_trend: str, price: float) -> int:
        score = 0
        
        # 1. Cluster-Relative Valuation (10 pts)
        # Industry benchmark: PEG < 1.0 = undervalued (Peter Lynch)
        # P/E < 15 = value (Benjamin Graham)
        is_price_rising = "Price Rising" in vol_trend
        
        # Check Valuation using industry standards
        is_cheap = False
        is_fair = False
        
        if f.peg_ratio > 0:
            # Peter Lynch PEG thresholds
            if f.peg_ratio < 1.0: 
                is_cheap = True  # Undervalued
            elif f.peg_ratio <= 1.5: 
                is_fair = True   # Fair value
            # PEG > 1.5 = potentially overvalued
        else:
            # Benjamin Graham P/E thresholds when PEG unavailable
            if f.pe_ratio > 0 and f.pe_ratio < 15:
                is_cheap = True  # Graham value threshold
            elif f.pe_ratio > 0 and f.pe_ratio < f.sector_pe_median:
                is_fair = True   # Below sector average
            
        if is_cheap:
            score += 10
        elif is_fair:
            score += 5
        else:
            score += 0
            
        # 2. Earnings Momentum (10 pts) - Sector-adjusted thresholds
        # Industry benchmarks vary by sector:
        #   Tech/Growth: Need >15% to be impressive
        #   Utilities/Staples: >5% is strong
        #   General: >10% is good
        SECTOR_GROWTH_THRESHOLDS = {
            30.0: (0.15, 0.08),  # Tech sectors (high PE) need higher growth
            22.0: (0.12, 0.05),  # Healthcare, Consumer
            18.0: (0.10, 0.04),  # Industrials, Communication
            15.0: (0.08, 0.03),  # Financials, Energy, Utilities
        }
        
        # Find appropriate threshold based on sector PE
        strong_growth = 0.10  # Default
        moderate_growth = 0.05
        for pe_threshold, (strong, moderate) in sorted(SECTOR_GROWTH_THRESHOLDS.items(), reverse=True):
            if f.sector_pe_median >= pe_threshold:
                strong_growth = strong
                moderate_growth = moderate
                break
        
        if f.earnings_growth_qoq > strong_growth:
            score += 10
        elif f.earnings_growth_qoq > moderate_growth:
            score += 5
        elif f.earnings_growth_qoq > 0:
            score += 3  # Positive but below threshold
        else:
            score += 0
            
        # 3. Smart Money Flow (10 pts)
        if f.inst_changing == "Rising":
            score += 10
        elif f.inst_changing == "Flat":
            score += 5
        else: # Selling/Falling
            score += 0
            
        return score

    def _score_technicals(self, t: Technicals) -> int:
        score = 0
        
        # 1. Trend & Turnaround (10 pts)
        if t.price > t.sma50 and t.sma50 > t.sma200:
            score += 10 # Standard Bull - Golden Cross territory
        elif t.price < t.sma200:
            # Below long-term trend = bearish
            # But check for oversold bounce potential (RSI < 30)
            if t.rsi < 30:
                score += 3  # Potential turnaround signal
            else:
                score += 0
        elif t.price > t.sma200 and t.price < t.sma50:
            # Consolidating: Above SMA200 but below SMA50 - mild positive
            score += 5
        else:
            # Price above both but SMA50 < SMA200 (recovering)
            score += 3

        # 2. Momentum / RSI (10 pts) - Industry Standard Thresholds
        # RSI 30-70 is neutral range (industry standard)
        # RSI < 30 = Oversold, RSI > 70 = Overbought
        if t.rsi < 30:
            # Oversold - potential bounce, but risky
            score += 2  # Slight positive for turnaround potential
        elif 30 <= t.rsi < 50:
            # Below average momentum, recovering
            score += 3
        elif 50 <= t.rsi <= 65:
            # Healthy momentum range
            if "Vol Rising" in t.volume_trend:
                score += 8
            else:
                score += 5
        elif 65 < t.rsi <= 75:
            # Strong momentum, potentially extended
            if "Vol Rising" in t.volume_trend:
                score += 10  # Breakout confirmation
            else:
                score += 6
        elif t.rsi > 75:
            # Overbought - industry standard is >70, using 75 for buffer
            score += 0  # Risk of pullback
            
        # 3. Volume Conviction (10 pts)
        if t.volume_trend == "Price Rising + Vol Rising":
            score += 10  # Strong conviction
        elif t.volume_trend == "Price Rising + Vol Falling":
            score += 5   # Weak rally, potential exhaustion
        elif t.volume_trend == "Price Falling + Vol Rising":
            score += 2   # Distribution or capitulation
        else:
            score += 0
            
        return score

    def _score_sentiment(self, s: Sentiment) -> int:
        score = 0
        
        # 1. News & Social (10 pts)
        # Bullish Headlines (Positive) -> 10
        # Neutral -> 5
        if s.news_sentiment_label == "Positive" or (s.news_volume_high and s.news_sentiment_label != "Negative"):
            score += 10
        elif s.news_sentiment_label == "Neutral":
            score += 5
        else:
            score += 0
            
        # 2. Insider Activity (10 pts)
        # Net Buying or No Activity: 10 pts
        # Mixed/Minor Selling: 5 pts
        # Heavy Selling: 0 pts
        # Cluster Selling: 0 pts (CRITICAL - but doesn't wipe news score)
        if s.insider_activity == "Net Buying" or s.insider_activity == "No Activity":
            score += 10
        elif s.insider_activity == "Mixed/Minor Selling":
            score += 5
        elif s.insider_activity in ["Heavy Selling", "Cluster Selling"]:
            score += 0  # No early return - news score preserved
        else:
            score += 0  # Unknown - default to 0
            
        return score

    def _score_projections(self, p: Projections) -> int:
        score = 0
        
        # 1. Probabilistic Upside (10 pts)
        # P50 Forecast > 10% -> 10 pts
        # > 5% -> 5 pts
        upside_pct = ((p.monte_carlo_p50 - p.current_price) / p.current_price) * 100
        
        if upside_pct > 10:
            score += 10
        elif upside_pct > 5:
            score += 5
        else:
            score += 0
            
        # 2. Risk/Reward (10 pts)
        # Upside (P90) > 2x Downside (P10) -> 10 pts
        # > 1.5x -> 5 pts
        upside_diff = max(0, p.monte_carlo_p90 - p.current_price)
        downside_diff = max(0, p.current_price - p.monte_carlo_p10)
        
        if downside_diff == 0:
            ratio = 100 # Infinite
        else:
            ratio = upside_diff / downside_diff
            
        if ratio >= 2.0:
            score += 10
        elif ratio > 1.5:
            score += 5
        else:
            score += 0
            
        return score

    def _get_rating(self, score: int) -> str:
        if score >= 80: return "Strong Buy"
        elif score >= 65: return "Buy"
        elif score >= 45: return "Hold"
        else: return "Sell"

    def _generate_narrative(self, ticker, final, f, t, s, p, mods, defensive) -> str:
        # Simple template-based narrative
        pillars = [("Fundamentals", f), ("Technicals", t), ("Sentiment", s), ("Projections", p)]
        # Sort by impact
        # We need relative strength. Max pts: F=30, T=30, S=20, P=20
        # Normalize to % for comparison?
        # Let's just pick the strongest and weakest.
        
        sorted_pillars = sorted(pillars, key=lambda x: x[1], reverse=True)
        strongest = sorted_pillars[0]
        weakest = sorted_pillars[-1]
        
        narrative = f"{ticker} is rated {self._get_rating(final)} ({final}/100). "
        
        if defensive:
             narrative += "Defensive Mode is ACTIVE due to Bearish Market. "
             
        narrative += f"The score is anchored by strong {strongest[0]} ({strongest[1]} pts), "
        
        if mods:
            narrative += f"boosted by {mods[0]}, "
        
        narrative += f"but weighed down by weak {weakest[0]} ({weakest[1]} pts)."
        return narrative

    def print_report(self, stock: StockData, result: ScoreResult):
        print(f"\n--- VinSight v5.0 Analysis: {stock.ticker} ---")
        print(f"Score: {result.total_score}/100 ({result.rating})")
        print(f"Narrative: {result.verdict_narrative}")
        print("\nScorecard:")
        print(f"  Fundamentals: {result.breakdown['Fundamentals']}/30")
        print(f"  Technicals:   {result.breakdown['Technicals']}/30")
        print(f"  Sentiment:    {result.breakdown['Sentiment']}/20")
        print(f"  Projections:  {result.breakdown['Projections']}/20")
        print(f"  Modifications: {', '.join(result.modifications) if result.modifications else 'None'}")
        print("----------------------------------------------\n")

# --- Verification Task ---

def run_test_case():
    # v5.0 Test Case: PLTR
    # Market: Bull (SPY > SMA) -> No Cap.
    # Fundamentals: PEG 1.5 (Fair, 5pts), Growth 20% (10pts), Smart Money Rising (10pts) -> 25/30
    # Technicals: Price > SMA50 > SMA200 (10pts), RSI 65 + Vol Rising (10pts), Vol Rising (10pts) -> 30/30
    # Sentiment: Positive (10pts), Net Buying (10pts) -> 20/20
    # Projections: +12% Upside (10pts), Ratio 1.8 (5pts) -> 15/20
    # Modifiers: Beta 2.5 (High), but Trend Up -> No penalty. Yield 0 -> No bonus.
    
    # Total: 25 + 30 + 20 + 15 = 90. Strong Buy.
    
    pltr_data = StockData(
        ticker="PLTR",
        beta=2.5,
        dividend_yield=0.0,
        market_bull_regime=True,
        fundamentals=Fundamentals(
            inst_ownership=45.0, 
            inst_changing="Rising", 
            pe_ratio=60.0, 
            peg_ratio=1.5,
            earnings_growth_qoq=0.20
        ),
        technicals=Technicals(
            price=25.0, 
            sma50=22.0, 
            sma200=18.0, 
            rsi=65.0, 
            momentum_label="Bullish", 
            volume_trend="Price Rising + Vol Rising"
        ),
        sentiment=Sentiment(
            news_sentiment_label="Positive", 
            news_volume_high=True, 
            insider_activity="Net Buying"
        ),
        projections=Projections(
            monte_carlo_p50=28.0, # +12%
            monte_carlo_p90=35.0, # +10 gain
            monte_carlo_p10=20.0, # -5 loss. Ratio 2.0
            current_price=25.0
        )
    )
    
    scorer = VinSightScorer()
    result = scorer.evaluate(pltr_data)
    scorer.print_report(pltr_data, result)
    
    # Check logic
    # Fundamentals: 5 (Val) + 10 (Growth) + 10 (Inst) = 25
    # Technicals: 10 (Trend) + 10 (RSI Breakout) + 10 (Vol) = 30
    # Sentiment: 10 (News) + 10 (Insd) = 20
    # Projections: 10 (>10%) + 10 (Ratio=2.0) = 20
    # Total: 95
    # Wait, my manual calculcation above said 15 for Projections (Ratio 1.8).
    # Data has p90=35 (gain 10), p10=20 (loss 5). Ratio = 2.0. So 10 pts.
    # Total should be 95.
    
    assert result.total_score == 95, f"Expected 95, got {result.total_score}. Check logic."
    print("Verification Successful for PLTR v5.0!")

if __name__ == "__main__":
    run_test_case()
