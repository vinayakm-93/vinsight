from dataclasses import dataclass
from typing import Literal, Optional

# --- Data Structures ---

@dataclass
class Fundamentals:
    inst_ownership: float  # Percentage (e.g., 81.3 for 81.3%)
    pe_ratio: float
    peg_ratio: float  # NEW in v2: P/E to Growth ratio
    analyst_upside: float  # Percentage (e.g., 6.2 for 6.2%)

@dataclass
class Technicals:
    price: float
    sma50: float
    sma200: float
    rsi: float
    momentum_label: Literal["Bullish", "Bearish"]
    volume_trend: Literal["Price Rising + Vol Rising", "Price Rising + Vol Falling", "Price Falling + Vol Rising", "Weak/Mixed"]

@dataclass
class Sentiment:
    sentiment_label: Literal["Positive", "Neutral", "Negative"]
    insider_activity: Literal["Net Buying", "Mixed/Minor Selling", "Heavy Selling"]

@dataclass
class Projections:
    monte_carlo_p50: float
    current_price: float # Redundant if using technicals.price, but kept for projection context if needed, or we can just use technicals.price
    risk_reward_gain_p90: float # Potential Gain amount
    risk_reward_loss_p10: float # Potential Loss amount

@dataclass
class StockData:
    ticker: str
    fundamentals: Fundamentals
    technicals: Technicals
    sentiment: Sentiment
    projections: Projections

@dataclass
class ScoreResult:
    total_score: int
    verdict: str
    breakdown: dict

# --- Scoring Engine ---

class VinSightScorer:
    VERSION = "v2.2"  # VinSight version - sentiment calibration update
    def evaluate(self, stock: StockData) -> ScoreResult:
        score_fundamentals = self._score_fundamentals(stock.fundamentals)
        score_technicals = self._score_technicals(stock.technicals)
        score_sentiment = self._score_sentiment(stock.sentiment)
        score_projections = self._score_projections(stock.projections, stock.technicals.price)
        
        total_score = score_fundamentals + score_technicals + score_sentiment + score_projections
        
        verdict = self._get_verdict(total_score)
        
        breakdown = {
            "Fundamentals": score_fundamentals,
            "Technicals": score_technicals,
            "Sentiment": score_sentiment,
            "Projections": score_projections,
            "Version": self.VERSION  # v2 tracking
        }
        
        return ScoreResult(total_score, verdict, breakdown)

    def _score_fundamentals(self, f: Fundamentals) -> int:
        score = 0
        # Inst. Ownership (Max 10)
        if f.inst_ownership > 70:
            score += 10
        elif 40 <= f.inst_ownership <= 70:
            score += 5
        else: # < 40
            score += 0
            
        # PEG Ratio (Max 10) - v2 improvement over simple P/E
        # PEG = P/E / Growth Rate
        # < 1.0: Undervalued (great)
        # 1.0-2.0: Fair value
        # > 2.0: Overvalued
        if f.peg_ratio > 0:  # Only score if PEG available
            if f.peg_ratio < 1.0:
                score += 10
            elif f.peg_ratio <= 2.0:
                score += 5
            else: # > 2.0
                score += 0
        else:
            # Fallback to P/E if PEG not available
            if f.pe_ratio < 25:
                score += 10
            elif 25 <= f.pe_ratio <= 35:
                score += 5
            else:
                score += 0
            
        # Analyst Upside (Max 10)
        if f.analyst_upside > 15:
            score += 10
        elif 5 <= f.analyst_upside <= 15:
            score += 5
        else: # < 5
            score += 0
            
        return score

    def _score_technicals(self, t: Technicals) -> int:
        score = 0
        # Moving Avgs (Max 10)
        if t.price > t.sma50 and t.price > t.sma200:
            score += 10
        elif t.price > t.sma200:
            score += 5
        else:
            score += 0
            
        # RSI (Max 5) - v2 fix: granular scoring for 60-70 range
        # < 30: Oversold (good for buying) -> 5 points
        # 30-60: Healthy range -> 5 points
        # 60-70: Slightly overbought -> 3 points (v2 fix)
        # > 70: Overbought (poor for buying) -> 0 points
        if t.rsi <= 60:
            score += 5
        elif t.rsi <= 70:
            score += 3  # v2 fix: middle ground for 60-70 range
        else:  # > 70
            score += 0 

        # Momentum Label (Max 5)
        if t.momentum_label == "Bullish":
            score += 5
        else:
            score += 0
            
        # Volume Trend (Max 10)
        if t.volume_trend == "Price Rising + Vol Rising":
            score += 10
        elif t.volume_trend == "Price Rising + Vol Falling":
            score += 5
        else:
            # Price Falling + Vol Rising (0) AND any other case (Weak/Mixed)
            score += 0
            
        return score

    def _score_sentiment(self, s: Sentiment) -> int:
        score = 0
        # Sentiment Label (Max 10)
        if s.sentiment_label == "Positive":
            score += 10
        elif s.sentiment_label == "Neutral":
            score += 5
        else: # Negative
            score += 0
            
        # Insider Activity (Max 10)
        if s.insider_activity == "Net Buying":
            score += 10
        elif s.insider_activity == "Mixed/Minor Selling":
            score += 5
        else: # Heavy Selling
            score += 0
            
        return score

    def _score_projections(self, p: Projections, current_price_from_technicals: float) -> int:
        score = 0
        
        # Monte Carlo P50 Outlook (Max 10) - v2.1: More stringent
        # Require significant upside for full points
        if p.monte_carlo_p50 > current_price_from_technicals * 1.15:  # +15% or more
            score += 10
        elif p.monte_carlo_p50 > current_price_from_technicals * 1.05:  # +5% to +15%
            score += 5
        elif p.monte_carlo_p50 >= current_price_from_technicals:  # At least neutral
            score += 3
        else:  # Projected decline
            score += 0
            
        # Risk/Reward Ratio (Max 10) - v2.1: More stringent
        # Require strong asymmetric payoff (2:1 or better)
        if p.risk_reward_loss_p10 > 0:
            risk_reward_ratio = p.risk_reward_gain_p90 / p.risk_reward_loss_p10
            if risk_reward_ratio >= 2.0:  # 2:1 or better reward/risk
                score += 10
            elif risk_reward_ratio >= 1.2:  # Positive but not great
                score += 5
            else:  # Poor risk/reward
                score += 0
        else:
            # No downside risk detected
            if p.risk_reward_gain_p90 > current_price_from_technicals * 0.10:
                score += 10  # At least 10% upside potential
            elif p.risk_reward_gain_p90 > 0:
                score += 5
            else:
                score += 0
        
        return score

    def _get_verdict(self, score: int) -> str:
        if 80 <= score <= 100:
            return "Strong Buy"
        elif 60 <= score <= 79:
            return "Buy"
        elif 40 <= score <= 59:
            return "Hold"
        else:
            return "Sell"

    def print_report(self, stock: StockData, result: ScoreResult):
        print(f"\n--- VinSight Score Report: {stock.ticker} ---")
        print(f"Final Score: {result.total_score}/100")
        print(f"Verdict: {result.verdict}\n")
        print("Breakdown:")
        print(f"  Fundamentals: {result.breakdown['Fundamentals']}/30")
        print(f"  Technicals:   {result.breakdown['Technicals']}/30")
        print(f"  Sentiment:    {result.breakdown['Sentiment']}/20")
        print(f"  Projections:  {result.breakdown['Projections']}/20")
        print("------------------------------------------\n")

# --- Verification Task ---

def run_test_case():
    # GOOGL Test Case
    # Inst Own: 81.3% -> >70 (+10)
    # P/E: 30.5 -> 25-35 (+5)
    # Upside: 6.2% -> 5-15 (+5)
    # Fundamentals Score: 10 + 5 + 5 = 20
    
    # Price: $309
    # SMA50: $281, SMA200: $208 -> Price > Both (+10)
    # RSI: 55.7 -> 30-60 (+5)
    # Momentum: Bearish -> (0)
    # Volume: Weak/Mixed (Rising Price + Falling Volume logic requested? No, prompt says 'Use logic for "Rising Price + Falling Volume"' IS NOT what it says. 
    # Wait, prompt says: "Volume: Weak/Mixed (Use logic for 'Rising Price + Falling Volume')".
    # Uh, actually looking at Prompt V.2 section 4: "Volume: Weak/Mixed (Use logic for 'Rising Price + Falling Volume')" -> This implies we treat 'Weak/Mixed' AS IF it were 'Rising Price + Falling Volume' for the test, OR the prompt meant that specific case maps to logic.
    # Logic for "Price Rising + Vol Falling" is +5.
    # So Technicals Score: 10 + 5 + 0 + 5 = 20.
    
    # Sentiment: Positive (+10)
    # Insiders: Heavy Selling (0)
    # Sentiment Score: 10 + 0 = 10.
    
    # Monte Carlo: P50 (326) > Current (309) -> (+10)
    # Risk/Reward: Gain (66) > Loss (24) -> (+10)
    # Projections Score: 10 + 10 = 20.
    
    # Total Expected: 20 + 20 + 10 + 20 = 70.
    # Verdict: 60-79 -> Buy.
    
    googl_data = StockData(
        ticker="GOOGL",
        fundamentals=Fundamentals(inst_ownership=81.3, pe_ratio=30.5, peg_ratio=1.5, analyst_upside=6.2),
        technicals=Technicals(
            price=309, 
            sma50=281, 
            sma200=208, 
            rsi=55.7, 
            momentum_label="Bearish", 
            volume_trend="Price Rising + Vol Falling" # Mapping test case "Weak/Mixed" to this as per instructions
        ),
        sentiment=Sentiment(sentiment_label="Positive", insider_activity="Heavy Selling"),
        projections=Projections(
            monte_carlo_p50=326, 
            current_price=309, 
            risk_reward_gain_p90=66, 
            risk_reward_loss_p10=24
        )
    )
    
    scorer = VinSightScorer()
    result = scorer.evaluate(googl_data)
    scorer.print_report(googl_data, result)
    
    assert result.total_score == 70, f"Expected 70, got {result.total_score}"
    assert result.verdict == "Buy", f"Expected Buy, got {result.verdict}"
    print("Verification Successful for GOOGL!")

if __name__ == "__main__":
    run_test_case()
