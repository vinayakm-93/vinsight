from dataclasses import dataclass, field
from typing import Literal, Optional, List, Dict
import logging
import json
import os

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
    
    # v6.0 NEW FIELDS
    profit_margin: float = 0.0  # 0.0-1.0 (e.g., 0.20 = 20%)
    debt_to_equity: float = 0.0  # Ratio (e.g., 0.5 = 50% debt)

@dataclass
class Technicals:
    price: float
    sma50: float
    sma200: float
    rsi: float
    momentum_label: Literal["Bullish", "Bearish"] # Derived from SMA5 > SMA10
    volume_trend: Literal["Price Rising + Vol Rising", "Price Rising + Vol Falling", "Price Falling + Vol Rising", "Price Falling + Vol Falling", "Weak/Mixed"]
    
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

# --- Sector Benchmarks Loader ---

def _load_sector_benchmarks() -> Dict:
    """Load sector benchmarks from config file, fallback to defaults if not found."""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'sector_benchmarks.json')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config.get('sectors', {}), config.get('defaults', {})
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.getLogger(__name__).warning(f"Could not load sector benchmarks: {e}. Using defaults.")
        return {}, {
            "pe_median": 20, "peg_fair": 1.5, "growth_strong": 0.10,
            "margin_healthy": 0.12, "debt_safe": 1.0
        }

# --- Scoring Engine v6.0 ---

class VinSightScorer:
    VERSION = "v6.0"
    
    # v6.0 Weight Distribution (100 pts total)
    WEIGHT_FUNDAMENTALS = 55
    WEIGHT_TECHNICALS = 15
    WEIGHT_SENTIMENT = 15
    WEIGHT_PROJECTIONS = 15

    def __init__(self):
        self.sector_benchmarks, self.defaults = _load_sector_benchmarks()

    def evaluate(self, stock: StockData) -> ScoreResult:
        # --- Phase 1: Macro Regime Filter (The Gatekeeper) ---
        is_defensive_mode = not stock.market_bull_regime
        high_beta = stock.beta > 1.5
        
        score_cap = 100
        if is_defensive_mode and high_beta:
            score_cap = 70
        
        # --- Phase 2: Core Score (100 Points) ---
        
        # A. Fundamentals (55 Points)
        f_score = self._score_fundamentals(stock.fundamentals)
        
        # B. Technicals (15 Points)
        t_score = self._score_technicals(stock.technicals)
        
        # C. Sentiment (15 Points)
        s_score = self._score_sentiment(stock.sentiment)
        
        # D. Projections (15 Points)
        p_score = self._score_projections(stock.projections)
        
        raw_score = f_score + t_score + s_score + p_score
        
        # --- Phase 3: Bonuses & Penalties ---
        bonuses = 0
        modifications = []
        
        # Safety Bonus: Yield > 2.5% AND Beta < 0.8
        safety_bonus_val = 15 if is_defensive_mode else 8
        if stock.dividend_yield > 2.5 and stock.beta < 0.8:
            bonuses += safety_bonus_val
            modifications.append(f"Safety Bonus (+{safety_bonus_val})")
            
        # Volatility Penalty: Beta > 2.0 AND Trend is Down
        if stock.beta > 2.0 and stock.technicals.price < stock.technicals.sma200:
            bonuses -= 8
            modifications.append("Volatility Penalty (-8)")
        
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

    def _get_benchmarks(self, sector_pe_median: float) -> Dict:
        """Get sector benchmarks by matching PE median."""
        if sector_pe_median > 0:
            for sector, bm in self.sector_benchmarks.items():
                if abs(bm.get("pe_median", 0) - sector_pe_median) < 3:
                    return bm
        return self.defaults

    def _score_fundamentals(self, f: Fundamentals) -> int:
        """
        Score fundamentals using range-based partial credits.
        
        v6.0 Breakdown (55 pts total):
        - Valuation (PEG/PE): 12 pts
        - Earnings Growth: 10 pts  
        - Profit Margins: 10 pts (NEW)
        - Debt Health: 8 pts (NEW)
        - Institutional Ownership: 8 pts
        - Smart Money Flow: 7 pts
        """
        score = 0.0
        benchmarks = self._get_benchmarks(f.sector_pe_median)
        
        peg_fair = benchmarks.get("peg_fair", 1.5)
        growth_strong = benchmarks.get("growth_strong", 0.10)
        pe_median = benchmarks.get("pe_median", 20)
        margin_healthy = benchmarks.get("margin_healthy", 0.12)
        debt_safe = benchmarks.get("debt_safe", 1.0)
        
        # 1. Valuation Score (12 pts) - Range-based
        val_score = 0.0
        if f.peg_ratio > 0:
            if f.peg_ratio < 1.0:
                val_score = 12.0
            elif f.peg_ratio < peg_fair:
                val_score = 12.0 - (f.peg_ratio - 1.0) / (peg_fair - 1.0) * 6.0
            elif f.peg_ratio < 3.0:
                val_score = 6.0 - (f.peg_ratio - peg_fair) / (3.0 - peg_fair) * 6.0
            else:
                val_score = 0.0
        elif f.pe_ratio > 0:
            if f.pe_ratio < 15:
                val_score = 12.0
            elif f.pe_ratio < pe_median:
                val_score = 12.0 - (f.pe_ratio - 15) / (pe_median - 15) * 6.0
            elif f.pe_ratio < pe_median * 2:
                val_score = 6.0 - (f.pe_ratio - pe_median) / pe_median * 6.0
            else:
                val_score = 0.0
        else:
            val_score = 6.0  # No data = neutral
            
        score += max(0, min(12, val_score))
        
        # 2. Earnings Momentum (10 pts)
        growth = f.earnings_growth_qoq
        growth_score = 0.0
        
        if growth > growth_strong:
            growth_score = 10.0
        elif growth > growth_strong * 0.5:
            growth_score = 5.0 + (growth - growth_strong * 0.5) / (growth_strong * 0.5) * 5.0
        elif growth > 0:
            growth_score = 2.5 + (growth / (growth_strong * 0.5)) * 2.5
        elif growth > -0.10:
            growth_score = 1.0 + (growth + 0.10) / 0.10 * 1.5
        else:
            growth_score = 0.0
            
        score += max(0, min(10, growth_score))
        
        # 3. Profit Margins (10 pts) - NEW in v6.0
        margin = f.profit_margin
        margin_score = 0.0
        
        if margin >= margin_healthy:
            margin_score = 10.0
        elif margin >= margin_healthy * 0.5:
            margin_score = 5.0 + (margin - margin_healthy * 0.5) / (margin_healthy * 0.5) * 5.0
        elif margin > 0:
            margin_score = 2.0 + (margin / (margin_healthy * 0.5)) * 3.0
        else:
            margin_score = 0.0  # Unprofitable
            
        score += max(0, min(10, margin_score))
        
        # 4. Debt Health (8 pts) - NEW in v6.0
        debt = f.debt_to_equity
        debt_score = 0.0
        
        if debt <= 0:
            debt_score = 8.0  # No debt = excellent
        elif debt <= debt_safe * 0.5:
            debt_score = 8.0
        elif debt <= debt_safe:
            debt_score = 5.0 + (debt_safe - debt) / (debt_safe * 0.5) * 3.0
        elif debt <= debt_safe * 2:
            debt_score = 2.0 + (debt_safe * 2 - debt) / debt_safe * 3.0
        else:
            debt_score = 0.5  # High debt
            
        score += max(0, min(8, debt_score))
        
        # 5. Institutional Ownership (8 pts)
        inst_pct = f.inst_ownership
        inst_score = 0.0
        
        if inst_pct >= 80:
            inst_score = 8.0
        elif inst_pct >= 60:
            inst_score = 5.5 + (inst_pct - 60) / 20 * 2.5
        elif inst_pct >= 40:
            inst_score = 3.0 + (inst_pct - 40) / 20 * 2.5
        elif inst_pct >= 20:
            inst_score = 1.0 + (inst_pct - 20) / 20 * 2.0
        else:
            inst_score = inst_pct / 20
            
        score += max(0, min(8, inst_score))
        
        # 6. Smart Money Flow (7 pts)
        flow_score = 0.0
        if f.inst_changing == "Rising":
            flow_score = 7.0
        elif f.inst_changing == "Flat":
            flow_score = 4.0
        else:  # Falling
            flow_score = 1.0
            
        score += flow_score
        
        return int(round(min(55, max(0, score))))

    def _score_technicals(self, t: Technicals) -> int:
        """
        Score technicals using range-based partial credits.
        
        v6.0 Breakdown (15 pts total):
        - Trend Position: 5 pts
        - RSI Momentum: 5 pts
        - Volume Conviction: 5 pts
        """
        score = 0.0
        
        # 1. Trend Position (5 pts)
        if t.sma50 > 0 and t.sma200 > 0:
            if t.price > t.sma50 and t.sma50 > t.sma200:
                score += 5.0  # Golden Cross
            elif t.price > t.sma200 and t.price > t.sma50:
                score += 4.0  # Above both
            elif t.price > t.sma200:
                score += 3.0  # Above 200 only
            elif t.price > t.sma200 * 0.95:
                score += 1.5  # Near support
            else:
                score += 0.5  # Below both
        else:
            score += 2.5  # No data
        
        # 2. RSI Momentum (5 pts)
        rsi = t.rsi
        if 50 <= rsi <= 65:
            score += 5.0
        elif 45 <= rsi < 50 or 65 < rsi <= 70:
            score += 4.0
        elif 35 <= rsi < 45 or 70 < rsi <= 80:
            score += 2.5
        elif rsi < 35:
            score += 2.0  # Oversold bounce potential
        else:  # > 80
            score += 1.0  # Overbought
        
        # 3. Volume Conviction (5 pts)
        if t.volume_trend == "Price Rising + Vol Rising":
            score += 5.0
        elif t.volume_trend == "Price Rising + Vol Falling":
            score += 3.0
        elif t.volume_trend == "Price Falling + Vol Falling":
            score += 2.0
        elif t.volume_trend == "Price Falling + Vol Rising":
            score += 1.5
        else:
            score += 2.5
            
        return int(round(min(15, max(0, score))))

    def _score_sentiment(self, s: Sentiment, sentiment_score: float = 0.0) -> int:
        """
        Score sentiment using range-based partial credits.
        
        v6.0 Breakdown (15 pts total):
        - News Sentiment: 7 pts (was 12)
        - Insider Activity: 8 pts (was 8)
        """
        score = 0.0
        
        # 1. News Sentiment (7 pts)
        if s.news_sentiment_label == "Positive":
            if s.news_volume_high:
                score += 7.0
            else:
                score += 6.0
        elif s.news_sentiment_label == "Neutral":
            if s.news_volume_high:
                score += 4.5
            else:
                score += 3.5
        elif s.news_sentiment_label == "Negative":
            score += 1.0
        else:
            score += 3.5  # Unknown = neutral
        
        # 2. Insider Activity (8 pts)
        if s.insider_activity == "Net Buying":
            score += 8.0
        elif s.insider_activity == "No Activity":
            score += 6.0
        elif s.insider_activity == "Mixed/Minor Selling":
            score += 4.0
        elif s.insider_activity == "Heavy Selling":
            score += 1.5
        elif s.insider_activity == "Cluster Selling":
            score += 0.5
        else:
            score += 4.0  # Unknown
            
        return int(round(min(15, max(0, score))))

    def _score_projections(self, p: Projections) -> int:
        """
        Score projections using range-based partial credits.
        
        v6.0 Breakdown (15 pts total):
        - Probabilistic Upside: 8 pts (was 12)
        - Risk/Reward Ratio: 7 pts (was 8)
        """
        score = 0.0

        if p.current_price is None or p.current_price <= 0:
            return 8  # Neutral

        # 1. Probabilistic Upside (8 pts)
        upside_pct = ((p.monte_carlo_p50 - p.current_price) / p.current_price) * 100
        
        if upside_pct >= 15:
            score += 8.0
        elif upside_pct >= 10:
            score += 6.0 + (upside_pct - 10) / 5 * 2
        elif upside_pct >= 5:
            score += 4.0 + (upside_pct - 5) / 5 * 2
        elif upside_pct > 0:
            score += 2.0 + upside_pct / 5 * 2
        elif upside_pct > -5:
            score += 1.0
        else:
            score += 0.5

        # 2. Risk/Reward Ratio (7 pts)
        upside_diff = max(0, p.monte_carlo_p90 - p.current_price)
        downside_diff = max(0.01, p.current_price - p.monte_carlo_p10)
        ratio = upside_diff / downside_diff

        if ratio >= 3.0:
            score += 7.0
        elif ratio >= 2.0:
            score += 5.0 + (ratio - 2.0) * 2
        elif ratio >= 1.5:
            score += 3.5 + (ratio - 1.5) * 3
        elif ratio >= 1.0:
            score += 2.0 + (ratio - 1.0) * 3
        elif ratio >= 0.5:
            score += 1.0 + (ratio - 0.5) * 2
        else:
            score += 0.5

        return int(round(min(15, max(0, score))))

    def _get_rating(self, score: int) -> str:
        if score >= 80: return "Strong Buy"
        elif score >= 65: return "Buy"
        elif score >= 45: return "Hold"
        else: return "Sell"

    def _generate_narrative(self, ticker, final, f, t, s, p, mods, defensive) -> str:
        # Normalize scores to percentages for comparison
        pillars = [
            ("Fundamentals", f, self.WEIGHT_FUNDAMENTALS),
            ("Technicals", t, self.WEIGHT_TECHNICALS),
            ("Sentiment", s, self.WEIGHT_SENTIMENT),
            ("Projections", p, self.WEIGHT_PROJECTIONS)
        ]
        
        # Sort by percentage of max
        sorted_pillars = sorted(pillars, key=lambda x: x[1] / x[2], reverse=True)
        strongest = sorted_pillars[0]
        weakest = sorted_pillars[-1]
        
        narrative = f"{ticker} is rated {self._get_rating(final)} ({final}/100). "
        
        if defensive:
             narrative += "Defensive Mode is ACTIVE due to Bearish Market. "
             
        narrative += f"The score is anchored by strong {strongest[0]} ({strongest[1]}/{strongest[2]} pts), "
        
        if mods:
            narrative += f"boosted by {mods[0]}, "
        
        narrative += f"but weighed down by weak {weakest[0]} ({weakest[1]}/{weakest[2]} pts)."
        return narrative

    def print_report(self, stock: StockData, result: ScoreResult):
        print(f"\n--- VinSight v6.0 Analysis: {stock.ticker} ---")
        print(f"Score: {result.total_score}/100 ({result.rating})")
        print(f"Narrative: {result.verdict_narrative}")
        print("\nScorecard:")
        print(f"  Fundamentals: {result.breakdown['Fundamentals']}/{self.WEIGHT_FUNDAMENTALS}")
        print(f"  Technicals:   {result.breakdown['Technicals']}/{self.WEIGHT_TECHNICALS}")
        print(f"  Sentiment:    {result.breakdown['Sentiment']}/{self.WEIGHT_SENTIMENT}")
        print(f"  Projections:  {result.breakdown['Projections']}/{self.WEIGHT_PROJECTIONS}")
        print(f"  Modifications: {', '.join(result.modifications) if result.modifications else 'None'}")
        print("----------------------------------------------\n")

# --- Verification Task ---

def run_test_case():
    # v6.0 Test Case: Strong stock with good fundamentals
    test_data = StockData(
        ticker="TEST",
        beta=1.2,
        dividend_yield=1.5,
        market_bull_regime=True,
        fundamentals=Fundamentals(
            inst_ownership=75.0,
            inst_changing="Rising",
            pe_ratio=20.0,
            peg_ratio=1.2,
            earnings_growth_qoq=0.12,
            sector_pe_median=25.0,
            profit_margin=0.18,
            debt_to_equity=0.4
        ),
        technicals=Technicals(
            price=105.0,
            sma50=100.0,
            sma200=95.0,
            rsi=58.0,
            momentum_label="Bullish",
            volume_trend="Price Rising + Vol Rising"
        ),
        sentiment=Sentiment(
            news_sentiment_label="Positive",
            news_volume_high=True,
            insider_activity="Net Buying"
        ),
        projections=Projections(
            monte_carlo_p50=115.0,
            monte_carlo_p90=128.0,
            monte_carlo_p10=95.0,
            current_price=105.0
        )
    )
    
    scorer = VinSightScorer()
    result = scorer.evaluate(test_data)
    scorer.print_report(test_data, result)
    
    print(f"Expected: Strong fundamentals-heavy score")
    print(f"Fundamentals: {result.breakdown['Fundamentals']}/55")
    print(f"Technicals: {result.breakdown['Technicals']}/15")
    print(f"Sentiment: {result.breakdown['Sentiment']}/15")
    print(f"Projections: {result.breakdown['Projections']}/15")

if __name__ == "__main__":
    run_test_case()
