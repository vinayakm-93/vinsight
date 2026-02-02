from dataclasses import dataclass, field
from typing import Literal, Optional, List, Dict
import logging
import json
import os

# --- Data Structures v7.3/v7.4 ---

@dataclass
class Fundamentals:
    # 1. Valuation (30%)
    pe_ratio: float
    forward_pe: float
    peg_ratio: float
    
    # 2. Profitability (20%)
    profit_margin: float # Net Margin
    operating_margin: float
    
    # 3. Efficiency (20%)
    roe: float # Return on Equity
    roa: float # Return on Assets
    
    # 4. Solvency (10%)
    debt_to_equity: float
    current_ratio: float
    
    # 5. Growth (10%)
    earnings_growth_qoq: float
    
    # 6. Conviction (10%)
    inst_ownership: float
    
    # Helper
    fcf_yield: float
    eps_surprise_pct: float
    sector_name: str = "Technology"

@dataclass
class Technicals:
    price: float
    sma50: float
    sma200: float
    rsi: float
    momentum_label: Literal["Bullish", "Bearish"]
    volume_trend: str
    
@dataclass
class Sentiment:
    news_sentiment_label: str
    news_sentiment_score: float
    news_article_count: int

@dataclass
class Projections:
    monte_carlo_p50: float
    monte_carlo_p90: float
    monte_carlo_p10: float
    current_price: float 

@dataclass
class StockData:
    ticker: str
    beta: float
    dividend_yield: float
    market_bull_regime: bool
    
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
    details: Dict # Structured breakdown for UI

# --- Sector Benchmarks Loader ---

def _load_sector_benchmarks() -> tuple[Dict, Dict, Dict]:
    """Load sector benchmarks from config file, fallback to defaults if not found."""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'sector_benchmarks.json')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            # Return sectors, defaults, AND market_reference
            return config.get('sectors', {}), config.get('defaults', {}), config.get('market_reference', {})
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.getLogger(__name__).warning(f"Could not load sector benchmarks: {e}. Using defaults.")
        return {}, {
            "pe_median": 20, "peg_fair": 1.5, "growth_strong": 0.10,
            "margin_healthy": 0.12, "debt_safe": 1.0,
            "fcf_yield_strong": 0.05
        }, {}

# --- Scoring Engine v7.4 ---

class VinSightScorer:
    VERSION = "v7.5 (Spectrum Scoring)"
    
    # Weight Distribution (Total 100 for Fundamentals)
    WEIGHT_Valuation = 30
    WEIGHT_Profitability = 20
    WEIGHT_Efficiency = 20
    WEIGHT_Solvency = 10
    WEIGHT_Growth = 10
    WEIGHT_Conviction = 10

    def __init__(self):
        self.sector_benchmarks, self.defaults, self.market_ref = _load_sector_benchmarks()
        self.details = []

    def evaluate(self, stock: StockData) -> ScoreResult:
        self.details = [] # Reset details log
        
        # 1. Map Raw Yahoo Sector to 1 of 10 Themes
        theme = self._map_sector_to_theme(stock.fundamentals.sector_name, stock.ticker)
        stock.fundamentals.sector_name = theme 
        
        # --- Phase 1: Core Score (Spectrum Based) ---
        breakdown_scores = self._score_fundamentals_spectrum(stock.fundamentals)
        f_score = sum(breakdown_scores.values())
        
        # --- Phase 2: Risk Gates & Modifications (Spectrum Bonuses/Penalties) ---
        bonuses = 0
        modifications = []
        
        # A. Trend Gate (Spectrum Penalty)
        trend_penalty = self._check_trend_gate(stock.technicals)
        if trend_penalty < 0:
            bonuses += trend_penalty
            modifications.append(f"Trend Gate Penalty ({trend_penalty:.1f})")
            
        # B. Projection Gate (Spectrum Penalty)
        proj_penalty = self._check_projection_gate(stock.projections)
        if proj_penalty < 0:
            bonuses += proj_penalty
            modifications.append(f"Risk Gate Penalty ({proj_penalty:.1f})")
            
        # C. Income Bonus (Spectrum: Yield-based if Beta < 1.0)
        income_bonus = 0
        if stock.beta < 1.0:
            # Ideal: 4% (+5), Zero: 1.5% (0)
            income_bonus = self._linear_score(
                stock.dividend_yield, ideal=4.0, zero=1.5, max_pts=5,
                label="Income Safety", category="Modifiers", unit="%"
            )
            if income_bonus > 0:
                bonuses += income_bonus
                modifications.append(f"Income Safety Bonus (+{income_bonus:.1f})")
        
        # D. RSI (Spectrum: 30-70 band)
        rsi_modifier = 0
        rsi = stock.technicals.rsi
        if rsi:
            # Oversold Bonus: Ideal 20 (+5), Zero 30 (0)
            if rsi < 30:
                rsi_modifier = self._linear_score(
                    rsi, ideal=20.0, zero=30.0, max_pts=5,
                    label="RSI Oversold", category="Modifiers"
                )
                if rsi_modifier > 0:
                    modifications.append(f"Oversold Bonus (+{rsi_modifier:.1f})")
            
            # Overbought Penalty: Ideal 80 (-5), Zero 70 (0)
            elif rsi > 70:
                # Use linear_score but manually handle negative
                penalty_raw = self._linear_score(
                    rsi, ideal=80.0, zero=70.0, max_pts=5,
                    label="RSI Overbought", category="Modifiers"
                )
                rsi_modifier = -penalty_raw
                if rsi_modifier < 0:
                    modifications.append(f"Overbought Penalty ({rsi_modifier:.1f})")
            else:
                self._add_detail("Modifiers", "RSI Momentum", f"{rsi:.1f}", "30 - 70", 0, 5, "Neutral")
        
        bonuses += rsi_modifier

        final_score = f_score + bonuses
        final_score = max(0, min(100, final_score))
        
        # Update breakdown with modifiers
        breakdown_scores["Bonuses"] = round(max(0, income_bonus + (rsi_modifier if rsi_modifier > 0 else 0)), 1)
        breakdown_scores["Penalties"] = round(min(0, trend_penalty + proj_penalty + (rsi_modifier if rsi_modifier < 0 else 0)), 1)
        
        # --- Phase 3: Output Generation ---
        rating = self._get_rating(final_score)
        narrative = self._generate_narrative(stock.ticker, final_score, f_score, trend_penalty, proj_penalty)
        
        return ScoreResult(final_score, rating, narrative, breakdown_scores, modifications, self.details)

    def _linear_score(self, value: float, ideal: float, zero: float, max_pts: float, label: str, category: str, unit: str = "") -> float:
        """
        Calculates a score based on a linear interpolation between 'ideal' (max_pts) and 'zero' (0 pts).
        """
        if value is None:
            self._add_detail(category, label, "N/A", f"{ideal}{unit}", 0, max_pts, "N/A")
            return 0.0

        # Determine direction
        is_higher_better = ideal > zero
        
        score = 0.0
        
        if is_higher_better:
            if value >= ideal:
                score = max_pts
            elif value <= zero:
                score = 0
            else:
                # Interpolate
                pct = (value - zero) / (ideal - zero)
                score = pct * max_pts
        else:
            # Lower is better (e.g. PEG, Debt)
            if value <= ideal:
                score = max_pts
            elif value >= zero:
                score = 0
            else:
                # Interpolate
                pct = (zero - value) / (zero - ideal)
                score = pct * max_pts
                
        # Formatting for detail log
        d_val = f"{value:.2f}{unit}"
        if unit == "%": d_val = f"{value*100:.1f}%"
        
        d_bench = f"{'>' if is_higher_better else '<'} {ideal:.2f}{unit}"
        if unit == "%": d_bench = f"{'>' if is_higher_better else '<'} {ideal*100:.1f}%"
        
        status = "Good"
        if score >= max_pts * 0.9: status = "Excellent"
        elif score >= max_pts * 0.7: status = "Strong"
        elif score >= max_pts * 0.4: status = "Fair"
        elif score > 0: status = "Weak"
        else: status = "Poor"

        self._add_detail(category, label, d_val, d_bench, round(score, 1), max_pts, status)
        
        return score

    def _score_fundamentals_spectrum(self, f: Fundamentals) -> Dict[str, float]:
        """
        Calculates scores using continuous linear interpolation.
        Total Max: 100
        """
        scores = {
            "Valuation": 0.0,
            "Profitability": 0.0,
            "Efficiency": 0.0,
            "Solvency": 0.0,
            "Growth": 0.0,
            "Conviction": 0.0
        }
        
        benchmarks = self._get_benchmarks(f.sector_name)
        
        # Load Dynamic Benchmarks
        peg_fair = benchmarks.get("peg_fair", 1.5)
        fpe_fair = benchmarks.get("forward_pe_fair", 18.0)
        margin_healthy = benchmarks.get("margin_healthy", 0.12)
        roe_strong = benchmarks.get("roe_strong", 0.15)
        roa_strong = benchmarks.get("roa_strong", 0.05)
        debt_safe = benchmarks.get("debt_safe", 1.0)
        curr_ratio_safe = benchmarks.get("current_ratio_safe", 1.5)
        growth_strong = benchmarks.get("growth_strong", 0.10)
        
        # --- 1. Valuation (30 Pts) ---
        # PEG (20 pts)
        # Ideal: 1.0, Zero: 3.0
        scores["Valuation"] += self._linear_score(
            f.peg_ratio, ideal=1.0, zero=3.0, max_pts=20, 
            label="Valuation (PEG)", category="Fundamentals"
        )
        
        # Forward PE (10 pts)
        # Ideal: Fair, Zero: Fair * 2.0
        scores["Valuation"] += self._linear_score(
            f.forward_pe, ideal=fpe_fair, zero=fpe_fair * 2.0, max_pts=10, 
            label="Forward Val (PE)", category="Fundamentals"
        )
        
        # --- 2. Profitability (20 Pts) ---
        # Net Margin (10 pts)
        # Ideal: Healthy, Zero: 0.0
        scores["Profitability"] += self._linear_score(
            f.profit_margin, ideal=margin_healthy, zero=0.0, max_pts=10,
            label="Net Margin", category="Fundamentals", unit="%"
        )
        
        # Operating Margin (10 pts)
        scores["Profitability"] += self._linear_score(
            f.operating_margin, ideal=margin_healthy, zero=0.0, max_pts=10,
            label="Op. Margin", category="Fundamentals", unit="%"
        )
        
        # --- 3. Efficiency (20 Pts) ---
        # ROE (10 pts)
        # Ideal: Strong, Zero: 0.0
        scores["Efficiency"] += self._linear_score(
            f.roe, ideal=roe_strong, zero=0.0, max_pts=10,
            label="ROE", category="Fundamentals", unit="%"
        )
        
        # ROA (10 pts)
        scores["Efficiency"] += self._linear_score(
            f.roa, ideal=roa_strong, zero=0.0, max_pts=10,
            label="ROA", category="Fundamentals", unit="%"
        )
        
        # --- 4. Solvency (10 Pts) ---
        # Debt/Equity (5 pts)
        # NOTE: Lower is better. Ideal: Safe, Zero: Safe * 3.0
        scores["Solvency"] += self._linear_score(
            f.debt_to_equity, ideal=debt_safe, zero=debt_safe * 3.0, max_pts=5,
            label="Debt/Equity", category="Fundamentals"
        )
        
        # Current Ratio (5 pts)
        # Ideal: Safe, Zero: 0.8 (Risk of insolvency)
        scores["Solvency"] += self._linear_score(
            f.current_ratio, ideal=curr_ratio_safe, zero=0.8, max_pts=5,
            label="Current Ratio", category="Fundamentals"
        )
        
        # --- 5. Growth (10 Pts) ---
        # Earnings Growth (10 pts)
        # Ideal: Strong, Zero: -0.10 (Declining)
        scores["Growth"] += self._linear_score(
            f.earnings_growth_qoq, ideal=growth_strong, zero=-0.10, max_pts=10,
            label="Growth (QoQ)", category="Fundamentals", unit="%"
        )
        
        # --- 6. Conviction (10 Pts) ---
        # Inst Ownership (10 pts)
        # Ideal: 80%, Zero: 20%
        # Note: Input is already 0-100, so don't use unit="%" which multiplies by 100
        scores["Conviction"] += self._linear_score(
            f.inst_ownership, ideal=80.0, zero=20.0, max_pts=10,
            label="Inst. Ownership", category="Fundamentals"
        )
        
        # Round buckets for cleaner display
        for k in scores:
            scores[k] = round(scores[k], 1)
            
        return scores

    def _map_sector_to_theme(self, raw_sector: str, ticker: str) -> str:
        """Maps Yahoo Finance sector strings to one of our 10 Wealth Manager Themes."""
        s = raw_sector.lower() if raw_sector else "technology"
        
        # 1. High Growth Tech
        # Heuristic: Tech sector + Keywords or specific tickers known for growth/software
        if "software" in s or "information" in s:
            return "High Growth Tech"
        
        # 2. Mature Tech
        if "technology" in s or "semiconduct" in s or "electronic" in s:
            return "Mature Tech"
            
        # 3. Financials
        if "financial" in s or "bank" in s or "insurance" in s or "capital" in s:
            return "Financials"
            
        # 4. Healthcare
        if "health" in s or "pharma" in s or "biotech" in s or "medical" in s:
            return "Healthcare"
            
        # 5. Consumer Cyclical
        if "cyclical" in s or "vehicle" in s or "auto" in s or "entertainment" in s or "retail" in s or "apparel" in s:
            return "Consumer Cyclical"
            
        # 6. Consumer Defensive
        if "defensive" in s or "food" in s or "drink" in s or "beverage" in s or "household" in s or "tobacco" in s:
            return "Consumer Defensive"
            
        # 7. Energy & Materials
        if "energy" in s or "oil" in s or "gas" in s or "material" in s or "mining" in s or "chemical" in s or "steel" in s:
            return "Energy & Materials"
            
        # 8. Industrials
        if "industr" in s or "aerospace" in s or "defense" in s or "transport" in s or "machinery" in s:
            return "Industrials"
            
        # 9. Real Estate
        if "real estate" in s or "reit" in s:
            return "Real Estate"
            
        # 10. Utilities (and Telecom)
        if "utilit" in s or "communication" in s or "telecom" in s:
            return "Utilities"
            
        # Default Fallback - Be somewhat conservative
        return "Mature Tech"

    def _add_detail(self, category: str, metric: str, value: str, benchmark: str, score: float, max_score: float, status: str):
        self.details.append({
            "category": category,
            "metric": metric,
            "value": value,
            "benchmark": benchmark,
            "score": f"{score}/{max_score}",
            "status": status
        })

    def _get_benchmarks(self, sector_name: str) -> Dict:
        return self.sector_benchmarks.get(sector_name, self.defaults)

    # _score_fundamentals REMOVED - replaced by _score_fundamentals_spectrum

    def _check_projection_gate(self, p: Projections) -> float:
        """
        Projections: Risk Penalty (Spectrum)
        Ideal: Downside >= -5% (0 penalty)
        Zero: Downside <= -25% (-15 penalty)
        """
        if not p.current_price or p.current_price <= 0:
            return 0.0
            
        downside_risk_pct = ((p.monte_carlo_p10 - p.current_price) / p.current_price) * 100
        
        # Use linear_score (max_pts=15)
        # Note: ideal is a higher number (-5), zero is a lower number (-25)
        score = self._linear_score(
            downside_risk_pct, ideal=-5.0, zero=-25.0, max_pts=15.0,
            label="Risk Gate (Downside)", category="Modifiers", unit="%"
        )
        
        # If score is 15 (Excellent), penalty is 0. If score is 0 (Poor), penalty is -15.
        penalty = round(score - 15.0, 1)
        return penalty

    def _check_trend_gate(self, t: Technicals) -> float:
        """
        Technicals: Trend Penalty (Spectrum)
        Ideal: Price >= SMA200 * 1.05 (0 penalty)
        Zero: Price <= SMA200 * 0.90 (-15 penalty)
        """
        if not t.sma200 or t.sma200 <= 0:
            return 0.0
            
        ratio = t.price / t.sma200
        
        # Ideal: 1.05, Zero: 0.90
        score = self._linear_score(
            ratio, ideal=1.05, zero=0.90, max_pts=15.0,
            label="Trend Strength (vs SMA200)", category="Modifiers"
        )
        
        # If score is 15 (Excellent), penalty is 0. If score is 0 (Poor), penalty is -15.
        penalty = round(score - 15.0, 1)
        return penalty

    def _get_rating(self, score: int) -> str:
        if score >= 85: return "Strong Buy"
        elif score >= 70: return "Buy"
        elif score >= 50: return "Hold"
        else: return "Sell"

    def _generate_narrative(self, ticker, final, f, trend_pen, proj_pen) -> str:
        narrative = f"{ticker} is rated {self._get_rating(final)} ({final:.0f}/100). "
        
        if f >= 80: narrative += "Business quality and valuation are exceptional. "
        elif f >= 60: narrative += "Fundamentals are solid. "
        else: narrative += "Fundamentals are weak or expensive. "
            
        if trend_pen < 0: narrative += "PENALTY APPLIED: Primary downtrend. "
        if proj_pen < 0: narrative += "PENALTY APPLIED: High projected downside risk. "
            
        return narrative

    def print_report(self, stock: StockData, result: ScoreResult):
        print(f"\n--- VinSight {self.VERSION}: {stock.ticker} ---")
        print(f"Strategy: Fundamental Purist (Wealth Manager)")
        print(f"Theme: {stock.fundamentals.sector_name}")
        print(f"Score: {result.total_score:.1f}/100 ({result.rating})")
        print(f"Narrative: {result.verdict_narrative}")
        print("\n[PENALTY LOGIC]")
        print(f"  Modifications: {', '.join(result.modifications) if result.modifications else 'None'}")
        
        print("\n[DETAILED SCORE BREAKDOWN]")
        for k, v in result.breakdown.items():
            print(f"  {k:<15}: {v}")
        
        print("\n[BENCHMARK COMPARISON]")
        print(f"  {'METRIC':<20} | {'VALUE':<10} | {'BENCHMARK':<12} | {'MARKET':<10} | {'SCORE':<8} | {'STATUS'}")
        print("-" * 90)
        
        # Map metric names to market ref keys
        m_ref_map = {
             "Valuation (PEG)": "peg_fair",
             "Forward Val (PE)": "forward_pe_fair",
             "Net Margin": "margin_healthy",
             "Op. Margin": "margin_healthy",
             "ROE": "roe_strong", 
             "ROA": "roa_strong",
             "Debt/Equity": "debt_safe",
             "Current Ratio": "current_ratio_safe",
             "Growth (QoQ)": "growth_strong"
        }
        
        for detail in result.details:
            if detail['category'] == "Fundamentals":
                m_key = m_ref_map.get(detail['metric'])
                m_val = self.market_ref.get(m_key, "-") if m_key else "-"
                
                # Format
                if isinstance(m_val, (int, float)):
                    if "Margin" in detail['metric'] or "ROE" in detail['metric'] or "Growth" in detail['metric']:
                        m_val = f"{m_val*100:.0f}%"
                    else:
                        m_val = f"{m_val}"

                print(f"  {detail['metric']:<20} | {detail['value']:<10} | {detail['benchmark']:<12} | {m_val:<10} | {detail['score']:<8} | {detail['status']}")
                
        print("----------------------------------------------\n")

# --- Verification Task ---
def run_test_case():
    # v7.4 Test
    test_data = StockData(
        ticker="TEST",
        beta=0.9,
        dividend_yield=2.5,
        market_bull_regime=True,
        fundamentals=Fundamentals(
            pe_ratio=18.0,
            forward_pe=15.0,
            peg_ratio=1.2,
            profit_margin=0.20,
            operating_margin=0.25,
            roe=0.18,
            roa=0.08,
            debt_to_equity=0.5,
            current_ratio=2.0,
            earnings_growth_qoq=0.15,
            inst_ownership=80.0,
            fcf_yield=0.04,
            eps_surprise_pct=0.10,
            sector_name="Technology" # Should map to Mature Tech or High Growth Tech
        ),
        technicals=Technicals(
            price=150.0, sma50=145.0, sma200=140.0, rsi=55.0,
            momentum_label="Bullish", volume_trend="Rising"
        ),
        sentiment=Sentiment("Positive", 0.35, 10),
        projections=Projections(165.0, 180.0, 145.0, 150.0)
    )
    scorer = VinSightScorer()
    res = scorer.evaluate(test_data)
    scorer.print_report(test_data, res)

if __name__ == "__main__":
    run_test_case()
