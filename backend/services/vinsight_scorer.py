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
    VERSION = "v7.4 (10-Theme + Market Ref)"
    
    # v7.3 Weight Distribution (100% Fundamentals)
    # Philosophy: Score the Business Quality. Use Charts/Projections as Veto Gates only.
    WEIGHT_FUNDAMENTALS = 100
    WEIGHT_PROJECTIONS = 0
    WEIGHT_SENTIMENT = 0 
    WEIGHT_TECHNICALS = 0

    def __init__(self):
        # Unpack the 3 return values
        self.sector_benchmarks, self.defaults, self.market_ref = _load_sector_benchmarks()
        self.details = []

    def evaluate(self, stock: StockData) -> ScoreResult:
        self.details = [] # Reset details log
        
        # 1. Map Raw Yahoo Sector to 1 of 10 Themes (New in v7.4)
        theme = self._map_sector_to_theme(stock.fundamentals.sector_name, stock.ticker)
        # We update the sector_name to the Theme so _score_fundamentals picks the right benchmark
        stock.fundamentals.sector_name = theme 
        
        # --- Phase 1: Core Score (100 Points - Fundamentals Only) ---
        f_score = self._score_fundamentals(stock.fundamentals)
        
        # --- Phase 2: Risk Gates (Bonuses/Penalties) ---
        bonuses = 0
        modifications = []
        
        # A. Trend Gate
        trend_penalty = self._check_trend_gate(stock.technicals)
        if trend_penalty < 0:
            bonuses += trend_penalty
            modifications.append(f"Trend Gate Penalty ({trend_penalty})")
            
        # B. Projection Gate (Risk Check)
        proj_penalty = self._check_projection_gate(stock.projections)
        if proj_penalty < 0:
            bonuses += proj_penalty
            modifications.append(f"Risk Gate Penalty ({proj_penalty})")
            
        # C. Income Bonus (Safety)
        if stock.dividend_yield > 2.5 and stock.beta < 0.9:
            bonuses += 5
            modifications.append("Income Safety Bonus (+5)")
            
        final_score = f_score + bonuses
        
        # Clamp 0-100
        final_score = max(0, min(100, final_score))
        
        # --- Phase 3: Output Generation ---
        rating = self._get_rating(final_score)
        narrative = self._generate_narrative(stock.ticker, final_score, f_score, trend_penalty, proj_penalty)
        
        breakdown = {
            "Fundamentals": f_score,
            "Technicals": 0,
            "Sentiment": 0,
            "Projections": 0
        }
        
        return ScoreResult(final_score, rating, narrative, breakdown, modifications, self.details)

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

    def _score_fundamentals(self, f: Fundamentals) -> int:
        """
        Fundamentals: 100 Points Total
        1. Valuation (30): PEG, Forward PE
        2. Profitability (20): Margins
        3. Efficiency (20): ROE, ROA
        4. Solvency (10): Debt, Current Ratio
        5. Growth (10): Earnings
        6. Conviction (10): Inst Ownership
        """
        score = 0.0
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
        val_pts = 0.0
        
        # PEG (20 pts)
        peg_score = 0
        current_peg = f.peg_ratio
        if current_peg > 0:
            if current_peg < 1.0: peg_score = 20
            elif current_peg < peg_fair: peg_score = 15
            elif current_peg < (peg_fair * 1.5): peg_score = 10
            elif current_peg < (peg_fair * 2.0): peg_score = 5
        elif f.pe_ratio > 0 and f.pe_ratio < 15: # Fallback
            peg_score = 15
        val_pts += peg_score
        self._add_detail("Fundamentals", "Valuation (PEG)", f"{current_peg:.2f}", f"< {peg_fair}", peg_score, 20, "Undervalued" if peg_score >= 15 else "Fair" if peg_score >= 10 else "Premium")
        
        # Forward PE (10 pts)
        fpe_score = 0 
        fpe = f.forward_pe
        if fpe > 0:
            if fpe < fpe_fair: fpe_score = 10
            elif fpe < fpe_fair * 1.3: fpe_score = 7
            elif fpe < fpe_fair * 1.6: fpe_score = 4
        val_pts += fpe_score
        self._add_detail("Fundamentals", "Forward Val (PE)", f"{fpe:.1f}", f"< {fpe_fair}", fpe_score, 10, "Cheap" if fpe_score == 10 else "Fair")
        
        score += val_pts
        
        # --- 2. Profitability (20 Pts) ---
        prof_pts = 0.0
        
        # Net Margin (10 pts)
        nm_score = 0
        if f.profit_margin > margin_healthy: nm_score = 10
        elif f.profit_margin > 0: nm_score = 5
        prof_pts += nm_score
        self._add_detail("Fundamentals", "Net Margin", f"{f.profit_margin*100:.1f}%", f"> {margin_healthy*100:.1f}%", nm_score, 10, "Strong" if nm_score == 10 else "Positive")

        # Operating Margin (10 pts)
        om_score = 0
        if f.operating_margin > margin_healthy: om_score = 10
        elif f.operating_margin > 0: om_score = 5
        prof_pts += om_score
        self._add_detail("Fundamentals", "Op. Margin", f"{f.operating_margin*100:.1f}%", f"> {margin_healthy*100:.1f}%", om_score, 10, "Strong" if om_score == 10 else "Positive")
        
        score += prof_pts
        
        # --- 3. Efficiency (20 Pts) ---
        eff_pts = 0.0
        
        # ROE (10 pts)
        roe_score = 0
        if f.roe > roe_strong: roe_score = 10
        elif f.roe > (roe_strong * 0.5): roe_score = 7
        elif f.roe > 0: roe_score = 3
        eff_pts += roe_score
        self._add_detail("Fundamentals", "ROE", f"{f.roe*100:.1f}%", f"> {roe_strong*100:.1f}%", roe_score, 10, "Elite" if roe_score == 10 else "Good")
        
        # ROA (10 pts)
        roa_score = 0
        if f.roa > roa_strong: roa_score = 10
        elif f.roa > (roa_strong * 0.4): roa_score = 5
        eff_pts += roa_score
        self._add_detail("Fundamentals", "ROA", f"{f.roa*100:.1f}%", f"> {roa_strong*100:.1f}%", roa_score, 10, "Efficient" if roa_score == 10 else "Average")

        score += eff_pts
        
        # --- 4. Solvency (10 Pts) ---
        sol_pts = 0.0
        
        # Debt/Equity
        if f.debt_to_equity < debt_safe: sol_pts += 5
        
        # Current Ratio
        if f.current_ratio > curr_ratio_safe: sol_pts += 5
        elif f.current_ratio > 1.0: sol_pts += 3
        
        score += sol_pts
        self._add_detail("Fundamentals", "Solvency", f"D/E: {f.debt_to_equity:.1f}", f"D/E < {debt_safe}", sol_pts, 10, "Safe" if sol_pts >= 8 else "Risky")
        
        # --- 5. Growth (10 Pts) ---
        gr_pts = 0.0
        if f.earnings_growth_qoq > growth_strong: gr_pts = 10
        elif f.earnings_growth_qoq > 0: gr_pts = 5
        score += gr_pts
        self._add_detail("Fundamentals", "Growth", f"{f.earnings_growth_qoq*100:.1f}%", f"> {growth_strong*100:.1f}%", gr_pts, 10, "High" if gr_pts == 10 else "Slow")
        
        # --- 6. Conviction (10 Pts) ---
        inst_pts = 0.0
        if f.inst_ownership > 70: inst_pts = 10
        elif f.inst_ownership > 40: inst_pts = 5
        score += inst_pts
        self._add_detail("Fundamentals", "Inst. Own", f"{f.inst_ownership:.1f}%", "> 70%", inst_pts, 10, "High" if inst_pts == 10 else "Moderate")

        return int(round(min(100, score)))

    def _check_projection_gate(self, p: Projections) -> int:
        """
        Projections: Risk Gate.
        """
        if not p.current_price or p.current_price <= 0:
            return 0
            
        downside_risk_pct = ((p.monte_carlo_p10 - p.current_price) / p.current_price) * 100
        
        penalty = 0
        status = "Pass"
        
        if downside_risk_pct < -15.0:
            penalty = -15
            status = "Fail (< -15%)"
        
        self._add_detail("Projections", "Risk Gate (P10)", f"{downside_risk_pct:.1f}%", "> -15%", penalty, 0, status)
        return penalty

    def _check_trend_gate(self, t: Technicals) -> int:
        """
        Technicals: Trend Gate.
        """
        penalty = 0
        status = "Pass"
        
        if t.sma200 > 0 and t.price < t.sma200:
            penalty = -15
            status = "Fail (< SMA200)"
            
        self._add_detail("Technicals", "Trend Gate", status, "Price > SMA200", penalty, 0, status)
        return penalty

    def _get_rating(self, score: int) -> str:
        if score >= 85: return "Strong Buy"
        elif score >= 70: return "Buy"
        elif score >= 50: return "Hold"
        else: return "Sell"

    def _generate_narrative(self, ticker, final, f, trend_pen, proj_pen) -> str:
        narrative = f"{ticker} is rated {self._get_rating(final)} ({final}/100). "
        
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
        print(f"Score: {result.total_score}/100 ({result.rating})")
        print(f"Narrative: {result.verdict_narrative}")
        print("\n[PENALTY LOGIC]")
        print(f"  Trend Gate:   {result.modifications[0] if result.modifications and 'Trend' in result.modifications[0] else 'Pass'} (Price < SMA200 = -15 Pts)")
        print(f"  Risk Gate:    {result.modifications[1] if len(result.modifications)>1 and 'Risk' in result.modifications[1] else (result.modifications[0] if result.modifications and 'Risk' in result.modifications[0] else 'Pass')} (P10 < -15% = -15 Pts)")
        
        print("\n[DETAILED SCORE BREAKDOWN]")
        print(f"  Fundamentals: {result.breakdown['Fundamentals']}/100")
        
        print("\n[BENCHMARK COMPARISON]")
        print(f"  {'METRIC':<20} | {'VALUE':<10} | {'THEME':<12} | {'MARKET':<10} | {'SCORE':<8} | {'STATUS'}")
        print("-" * 90)
        
        # Map metric names to market ref keys
        m_ref_map = {
             "Valuation (PEG)": "peg_fair",
             "Forward Val (PE)": "forward_pe_fair",
             "Net Margin": "margin_healthy",
             "Op. Margin": "margin_healthy",
             "ROE": "roe_strong", 
             "ROA": "roa_strong",
             "Solvency": "debt_safe",
             "Growth": "growth_strong"
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
