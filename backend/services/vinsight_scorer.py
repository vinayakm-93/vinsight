from dataclasses import dataclass, field
from typing import Literal, Optional, List, Dict
import logging
import json
import os

# --- Data Structures v7.3/v7.4 ---

@dataclass
class Fundamentals:
    # 1. Valuation
    pe_ratio: float
    forward_pe: float
    peg_ratio: Optional[float]
    fcf_yield: float
    
    # 2. Profitability
    profit_margin: float # Net Margin
    operating_margin: float
    gross_margin_trend: str # "Rising", "Falling", "Flat"
    
    # 3. Efficiency
    roe: float # Return on Equity
    roa: float # Return on Assets
    
    # 4. Solvency / Health
    debt_to_equity: float
    debt_to_ebitda: Optional[float]
    interest_coverage: float
    current_ratio: float
    altman_z_score: Optional[float]
    
    # 5. Growth
    earnings_growth_qoq: float
    revenue_growth_3y: Optional[float]
    
    # 6. Conviction / Other
    inst_ownership: float
    eps_surprise_pct: float
    sector_name: str = "Technology"

    # 7. Extended Metrics (Reasoning Scorer v9.0)
    price_to_book: Optional[float] = None
    ev_to_ebitda: Optional[float] = None
    price_to_sales: Optional[float] = None
    enterprise_to_revenue: Optional[float] = None
    payout_ratio: Optional[float] = None
    five_year_avg_dividend_yield: Optional[float] = None
    trailing_annual_dividend_yield: Optional[float] = None
    short_ratio: Optional[float] = None
    fifty_two_week_change: Optional[float] = None
    held_percent_insiders: Optional[float] = None

@dataclass
class Technicals:
    price: float
    sma50: float
    sma200: float
    rsi: float
    relative_volume: float
    distance_to_high: float
    momentum_label: Literal["Bullish", "Bearish"]
    volume_trend: str
    
@dataclass
class Sentiment:
    news_sentiment_label: str
    news_sentiment_score: float
    news_article_count: int
    news_data: Optional[Dict] = None

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
    missing_data: List[str] # New field
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
    VERSION = "v8.0 (CFA Composite Model)"
    
    def __init__(self):
        self.sector_benchmarks, self.defaults, self.market_ref = _load_sector_benchmarks()
        self.details = []
        self._ensure_log_dir()

    def _ensure_log_dir(self):
        log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, 'missing_data.csv')
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                f.write("timestamp,ticker,missing_field\n")

    def _log_missing_data(self, ticker: str, field_name: str):
        try:
            from datetime import datetime
            with open(self.log_file, 'a') as f:
                f.write(f"{datetime.now().isoformat()},{ticker},{field_name}\n")
        except Exception as e:
            logging.error(f"Failed to log missing data: {e}")

    def evaluate(self, stock: StockData) -> ScoreResult:
        self.details = [] # Reset details log
        
        # 1. Map Raw Yahoo Sector to 1 of 10 Themes
        theme = self._map_sector_to_theme(stock.fundamentals.sector_name, stock.ticker)
        stock.fundamentals.sector_name = theme 
        
        missing_fields = []
        # Check for missing critical data
        if stock.fundamentals.peg_ratio is None:
            self._log_missing_data(stock.ticker, "peg_ratio")
            missing_fields.append("PEG Ratio")
        if stock.fundamentals.debt_to_ebitda is None:
            self._log_missing_data(stock.ticker, "debt_to_ebitda")
            missing_fields.append("Debt/EBITDA")
        if stock.fundamentals.altman_z_score is None:
             self._log_missing_data(stock.ticker, "altman_z_score")
             missing_fields.append("Altman Z-Score")
        if stock.fundamentals.revenue_growth_3y is None:
             self._log_missing_data(stock.ticker, "revenue_growth_3y")
             missing_fields.append("Revenue Growth (3y)")
        
        # --- Phase 1: Quality Score (70% Weight) ---
        # Focus: Solvency, Efficiency, Valuation
        quality_score, q_breakdown = self._score_quality(stock.fundamentals)
        
        # --- Phase 2: Timing Score (30% Weight) ---
        # Focus: Trend, Momentum, Volume
        timing_score, t_breakdown = self._score_timing(stock.technicals, stock.beta, stock.fundamentals.sector_name)
        
        # --- Phase 3: Kill Switches (The Analyst's Veto) ---
        modifications = []
        
        # 1. Insolvency Veto
        # If Interest Coverage < 1.5, Max Final Score = 40 (Strong Sell)
        insolvency_cap = None
        if stock.fundamentals.interest_coverage < 1.5:
             insolvency_cap = 40
             modifications.append("INSOLVENCY RISK: Interest Coverage < 1.5x (Safe < 1.5x)")

        # 2. Valuation Veto
        # If PEG > 4.0, Max Quality Score = 50
        if stock.fundamentals.peg_ratio is not None and stock.fundamentals.peg_ratio > 4.0:
            if quality_score > 50:
                quality_score = 50
                modifications.append("VALUATION VETO: PEG > 4.0 cap applied")
        
        # 3. Downtrend Veto
        # If Price < SMA200 AND Price < SMA50, Max Timing Score = 30
        if stock.technicals.price < stock.technicals.sma200 and stock.technicals.price < stock.technicals.sma50:
             if timing_score > 30:
                 timing_score = 30
                 modifications.append("DOWNTREND VETO: Price below SMA200 & SMA50")
        
        # --- Phase 4: Composite Calculation ---
        # Master Equation: 70% Quality + 30% Timing
        final_score = (quality_score * 0.70) + (timing_score * 0.30)
        
        # Apply Insolvency Cap if triggered
        if insolvency_cap and final_score > insolvency_cap:
            final_score = insolvency_cap
            modifications.append(f"Score Capped at {insolvency_cap} due to Insolvency Risk")
            
        final_score = round(final_score, 1)
        
        # Combine breakdowns
        full_breakdown = {**q_breakdown, **t_breakdown}
        full_breakdown['Quality Score'] = round(quality_score, 1)
        full_breakdown['Timing Score'] = round(timing_score, 1)
        
        # Output Generation
        rating = self._get_rating(final_score)
        narrative = self._generate_narrative(stock.ticker, final_score, quality_score, timing_score, modifications)
        
        return ScoreResult(final_score, rating, narrative, full_breakdown, modifications, missing_fields, self.details)

    # --- Persona Weight Definitions ---
    PERSONAS = {
        "CFA":      {"valuation": 25, "profitability": 25, "health": 20, "growth": 15, "technicals": 15},
        "Momentum": {"valuation": 0,  "profitability": 5,  "health": 5,  "growth": 10, "technicals": 80},
        "Value":    {"valuation": 40, "profitability": 15, "health": 25, "growth": 10, "technicals": 10},
        "Growth":   {"valuation": 10, "profitability": 15, "health": 5,  "growth": 50, "technicals": 20},
        "Income":   {"valuation": 15, "profitability": 25, "health": 35, "growth": 10, "technicals": 15},
    }

    def _score_component(self, scores: list, max_pts_list: list) -> float:
        """
        Averages non-None scores, normalized to 0-10 scale.
        Returns 5.0 (neutral) if all data is missing.
        """
        valid_scores = []
        valid_max = []
        for s, m in zip(scores, max_pts_list):
            if s is not None:
                valid_scores.append(s)
                valid_max.append(m)
        if not valid_scores:
            return 5.0  # No data = neutral, not zero
        total_earned = sum(valid_scores)
        total_available = sum(valid_max)
        if total_available == 0:
            return 5.0
        return (total_earned / total_available) * 10.0

    def _compute_components(self, stock: StockData) -> Dict:
        """
        Returns 5 Python-computed component scores, each 0-10.
        None-safe: missing metrics are excluded per component.
        """
        f = stock.fundamentals
        t = stock.technicals
        benchmarks = self._get_benchmarks(f.sector_name)

        # --- Valuation (PEG, FCF Yield, Forward P/E) ---
        target_peg = benchmarks.get('peg_fair', 1.5)
        target_fcf = benchmarks.get('fcf_yield_strong', 0.05)
        pe_median = benchmarks.get('pe_median', 24)
        s_peg = self._linear_score(f.peg_ratio, ideal=target_peg, zero=target_peg + 2.0, max_pts=10, label="PEG", category="_comp")
        s_fcf = self._linear_score(f.fcf_yield, ideal=target_fcf, zero=target_fcf * 0.2, max_pts=10, label="FCF Yield", category="_comp")
        s_fpe = self._linear_score(f.forward_pe, ideal=pe_median, zero=pe_median * 2.5, max_pts=10, label="Fwd P/E", category="_comp")
        valuation = self._score_component([s_peg, s_fcf, s_fpe], [10, 10, 10])

        # --- Profitability (ROE, Net Margin, Operating Margin) ---
        target_roe = benchmarks.get('roe_strong', 0.15)
        target_margin = benchmarks.get('margin_healthy', 0.12)
        s_roe = self._linear_score(f.roe, ideal=target_roe, zero=target_roe * 0.3, max_pts=10, label="ROE", category="_comp")
        s_margin = self._linear_score(f.profit_margin, ideal=target_margin, zero=target_margin * 0.4, max_pts=10, label="Net Margin", category="_comp")
        s_op_margin = self._linear_score(f.operating_margin, ideal=target_margin * 1.5, zero=target_margin * 0.3, max_pts=10, label="Op Margin", category="_comp")
        profitability = self._score_component([s_roe, s_margin, s_op_margin], [10, 10, 10])

        # --- Health (D/E, Interest Coverage, Current Ratio, Altman Z) ---
        debt_safe = benchmarks.get('debt_safe', 1.0)
        s_de = self._linear_score(f.debt_to_equity, ideal=debt_safe, zero=debt_safe * 3, max_pts=10, label="D/E", category="_comp")
        s_icr = self._linear_score(f.interest_coverage, ideal=8.0, zero=1.5, max_pts=10, label="ICR", category="_comp")
        s_cr = self._linear_score(f.current_ratio, ideal=2.0, zero=0.8, max_pts=10, label="Current Ratio", category="_comp")
        s_z = self._linear_score(f.altman_z_score, ideal=3.0, zero=1.8, max_pts=10, label="Altman Z", category="_comp")
        health = self._score_component([s_de, s_icr, s_cr, s_z], [10, 10, 10, 10])

        # --- Growth (Rev Growth 3y, Earnings QoQ, EPS Surprise) ---
        target_growth = benchmarks.get('growth_strong', 0.10)
        s_rev = self._linear_score(f.revenue_growth_3y, ideal=target_growth, zero=0.0, max_pts=10, label="Rev Growth", category="_comp")
        s_earn = self._linear_score(f.earnings_growth_qoq, ideal=target_growth, zero=0.0, max_pts=10, label="Earn QoQ", category="_comp")
        s_eps = self._linear_score(f.eps_surprise_pct, ideal=0.05, zero=-0.05, max_pts=10, label="EPS Surprise", category="_comp")
        growth = self._score_component([s_rev, s_earn, s_eps], [10, 10, 10])

        # --- Technicals (SMA200, SMA50, RSI continuous, RVOL) ---
        tech_scores = []
        tech_max = []
        if t.sma200 and t.sma200 > 0:
            s_sma200 = self._linear_score(t.price / t.sma200, ideal=1.05, zero=0.95, max_pts=10, label="vs SMA200", category="_comp")
            tech_scores.append(s_sma200)
            tech_max.append(10)
        if t.sma50 and t.sma50 > 0:
            s_sma50 = self._linear_score(t.price / t.sma50, ideal=1.03, zero=0.95, max_pts=10, label="vs SMA50", category="_comp")
            tech_scores.append(s_sma50)
            tech_max.append(10)
        # RSI continuous
        if t.rsi is not None and t.rsi > 0:
            if 45 <= t.rsi <= 60:
                rsi_s = 10.0
            elif t.rsi < 25 or t.rsi > 85:
                rsi_s = 0.0
            elif t.rsi < 45:
                rsi_s = 10.0 * ((t.rsi - 25) / 20)
            else:
                rsi_s = 10.0 * ((85 - t.rsi) / 25)
            tech_scores.append(rsi_s)
            tech_max.append(10)
        s_rvol = self._linear_score(t.relative_volume, ideal=1.5, zero=0.5, max_pts=10, label="RVOL", category="_comp")
        tech_scores.append(s_rvol)
        tech_max.append(10)
        technicals = self._score_component(tech_scores, tech_max)

        return {
            "valuation": round(valuation, 1),
            "profitability": round(profitability, 1),
            "health": round(health, 1),
            "growth": round(growth, 1),
            "technicals": round(technicals, 1),
        }

    def _apply_persona_weights(self, components: Dict, persona: str = "CFA") -> float:
        """
        Applies persona-specific weightings to Python-computed components.
        Returns base score 0-100.
        """
        weights = self.PERSONAS.get(persona, self.PERSONAS["CFA"])
        score = 0.0
        for comp, weight_pct in weights.items():
            comp_score_0_10 = components.get(comp, 5.0)
            score += (comp_score_0_10 * 10) * (weight_pct / 100)
        return round(score, 1)

    # --- Penalty Sensitivity per Persona ---
    PENALTY_SENSITIVITY = {
        "CFA":      {"solvency": 1.0, "overvaluation": 1.0, "trend": 0.7, "revenue": 1.0},
        "Momentum": {"solvency": 0.3, "overvaluation": 0.0, "trend": 1.5, "revenue": 0.3},
        "Value":    {"solvency": 1.2, "overvaluation": 0.5, "trend": 0.3, "revenue": 1.0},
        "Growth":   {"solvency": 0.5, "overvaluation": 0.3, "trend": 0.8, "revenue": 1.5},
        "Income":   {"solvency": 1.5, "overvaluation": 0.8, "trend": 0.5, "revenue": 1.0},
    }

    def _compute_penalties(self, stock: StockData, persona: str = "CFA") -> tuple:
        """
        Continuous proportional penalties with buffer-then-gradient shape.
        Each penalty has: [threshold] → [buffer zone: 0 pts] → [gradient zone: 0 to max] → [cap: max pts]
        Returns (total_deductions: float, logs: list[dict]).
        All None-safe: skip penalty if data is missing.
        """
        deductions = 0.0
        logs = []
        f = stock.fundamentals
        t = stock.technicals
        benchmarks = self._get_benchmarks(f.sector_name)
        sens = self.PENALTY_SENSITIVITY.get(persona, self.PENALTY_SENSITIVITY["CFA"])
        debt_safe = benchmarks.get('debt_safe', 1.0)
        pe_median = benchmarks.get('pe_median', 20)

        # Helper: compute penalty with buffer zone
        def _buffered_penalty(value, buffer_start, gradient_end, max_pts, direction="above"):
            """
            direction='above': penalty when value > buffer_start, full at gradient_end
            direction='below': penalty when value < buffer_start, full at gradient_end
            """
            if direction == "above":
                if value <= buffer_start:
                    return 0.0
                # Ensure gradient_end is greater than buffer_start to avoid division by zero or negative range
                if gradient_end <= buffer_start:
                    return max_pts if value > buffer_start else 0.0
                severity = min(1.0, (value - buffer_start) / (gradient_end - buffer_start))
            else:  # below
                if value >= buffer_start:
                    return 0.0
                # Ensure buffer_start is greater than gradient_end
                if buffer_start <= gradient_end:
                    return max_pts if value < buffer_start else 0.0
                severity = min(1.0, (buffer_start - value) / (buffer_start - gradient_end))
            return severity * max_pts

        # 1. Solvency: Buffer at D/E 2.0 (Double safe), full -20 at D/E 4.0
        # First principle: Debt isn't bad unless it's excessive. 1.5x safe is variance. 2.0x is structural risk.
        if f.debt_to_equity is not None and f.debt_to_equity > debt_safe:
            buffer_start = debt_safe * 2.0   
            gradient_end = debt_safe * 4.0   
            raw_penalty = _buffered_penalty(f.debt_to_equity, buffer_start, gradient_end, 20)
            penalty = round(raw_penalty * sens.get("solvency", 1.0), 1)
            if penalty > 0:
                deductions += penalty
                logs.append({
                    "type": "Solvency Risk",
                    "severity": penalty,
                    "raw_value": f.debt_to_equity,
                    "threshold": debt_safe,
                    "buffer": buffer_start,
                    "detail": f"D/E {f.debt_to_equity:.1f} vs safe {debt_safe:.1f} (buffer {buffer_start:.1f}, -{penalty:.1f}pts)"
                })

        # 2. Overvaluation: Buffer at 2.0x median P/E, full -15 at 4x median
        # First principle: Great companies rightfully trade at premiums. Only punish blatant bubbles.
        if f.pe_ratio is not None and f.pe_ratio > pe_median:
            buffer_start = pe_median * 2.0   
            gradient_end = pe_median * 4.0   
            # Growth offset: high-growth companies get halved penalty (growing into their valuation)
            growth_offset = 0.0
            if f.revenue_growth_3y is not None and f.revenue_growth_3y > 0.15:
                growth_offset = 0.5
            raw_penalty = _buffered_penalty(f.pe_ratio, buffer_start, gradient_end, 15) * (1 - growth_offset)
            penalty = round(raw_penalty * sens.get("overvaluation", 1.0), 1)
            if penalty > 0:
                deductions += penalty
                logs.append({
                    "type": "Overvaluation",
                    "severity": penalty,
                    "raw_value": f.pe_ratio,
                    "threshold": pe_median,
                    "buffer": buffer_start,
                    "detail": f"P/E {f.pe_ratio:.0f} vs median {pe_median} (buffer {buffer_start:.0f}, -{penalty:.1f}pts)"
                })

        # 3. Broken Trend: Buffer at 5% below SMA200, full -10 at 20% below
        # First principle: A 3% dip under a moving average is a normal pullback. 10%+ is an institutional exodus.
        if t.sma200 and t.sma200 > 0 and t.price < t.sma200:
            pct_below = (t.sma200 - t.price) / t.sma200  # 0.0 to 1.0
            buffer_pct = 0.05   # 5% below = no penalty yet 
            gradient_pct = 0.20  # 20% below = full penalty 
            raw_penalty = _buffered_penalty(pct_below, buffer_pct, gradient_pct, 10)
            penalty = round(raw_penalty * sens.get("trend", 1.0), 1)
            if penalty > 0:
                deductions += penalty
                below_pct = -pct_below * 100
                logs.append({
                    "type": "Broken Trend",
                    "severity": penalty,
                    "raw_value": t.price,
                    "threshold": t.sma200,
                    "detail": f"{below_pct:.1f}% below SMA200 (buffer -5%, -{penalty:.1f}pts)"
                })

        # 4. Revenue Decline: Buffer at -10%, full -15 at -30%
        # First principle: A -5% revenue miss is a weak quarter. A -20% contraction is a dying business.
        if f.revenue_growth_3y is not None and f.revenue_growth_3y < 0:
            pct_decline = abs(f.revenue_growth_3y)  # positive number
            buffer_pct = 0.10   # -10% = no penalty yet (cyclical variance)
            gradient_pct = 0.30  # -30% = full penalty 
            raw_penalty = _buffered_penalty(pct_decline, buffer_pct, gradient_pct, 15)
            penalty = round(raw_penalty * sens.get("revenue", 1.0), 1)
            if penalty > 0:
                deductions += penalty
                logs.append({
                    "type": "Revenue Decline",
                    "severity": penalty,
                    "raw_value": f.revenue_growth_3y,
                    "threshold": 0.0,
                    "detail": f"Revenue growth {f.revenue_growth_3y:.1%} (buffer -10%, -{penalty:.1f}pts)"
                })

        return round(deductions, 1), logs

    def _score_quality(self, f: Fundamentals) -> tuple[float, Dict]:
        """
        Calculates the Quality Score (Max 100).
        None-safe: missing metrics are excluded, score normalizes over available points.
        """
        score = 0.0
        available_pts = 0.0
        breakdown = {}
        
        benchmarks = self._get_benchmarks(f.sector_name)
        
        # --- A. Valuation (35 Pts) ---
        # 1. PEG Ratio (20 pts) - Dynamic Target
        target_peg = benchmarks.get('peg_fair', 1.5)
        s_peg = self._linear_score(
            f.peg_ratio, ideal=target_peg, zero=target_peg + 2.0, max_pts=20,
            label="PEG Ratio", category="Quality (Valuation)"
        )
        if s_peg is not None:
            score += s_peg
            available_pts += 20
        breakdown['PEG'] = s_peg if s_peg is not None else 0.0
        
        # 2. FCF Yield (15 pts) - Dynamic Target
        target_fcf = benchmarks.get('fcf_yield_strong', 0.05)
        s_fcf = self._linear_score(
            f.fcf_yield, ideal=target_fcf, zero=target_fcf * 0.2, max_pts=15,
            label="FCF Yield", category="Quality (Valuation)", unit="%"
        )
        if s_fcf is not None:
            score += s_fcf
            available_pts += 15
        breakdown['FCF Yield'] = s_fcf if s_fcf is not None else 0.0
        
        # --- B. Profitability (35 Pts) ---
        # 3. ROE (15 pts) - Dynamic Target
        target_roe = benchmarks.get('roe_strong', 0.15)
        s_roe = self._linear_score(
            f.roe, ideal=target_roe, zero=target_roe * 0.3, max_pts=15,
            label="ROE", category="Quality (Profitability)", unit="%"
        )
        if s_roe is not None:
            score += s_roe
            available_pts += 15
        breakdown['ROE'] = s_roe if s_roe is not None else 0.0
        
        # 4. Net Margin (10 pts) - Dynamic Target
        target_margin = benchmarks.get('margin_healthy', 0.12)
        s_margin = self._linear_score(
            f.profit_margin, ideal=target_margin, zero=target_margin * 0.4, max_pts=10,
            label="Net Margin", category="Quality (Profitability)", unit="%"
        )
        if s_margin is not None:
            score += s_margin
            available_pts += 10
        breakdown['Net Margin'] = s_margin if s_margin is not None else 0.0
        
        # 5. Gross Margin Trend (10 pts) - Rising YoY
        s_gm_trend = 0.0
        if f.gross_margin_trend == "Rising":
            s_gm_trend = 10.0
            status = "Excellent"
        elif f.gross_margin_trend == "Flat":
            s_gm_trend = 5.0
            status = "Neutral"
        else:
            s_gm_trend = 0.0
            status = "Poor"
            
        score += s_gm_trend
        available_pts += 10  # GM Trend is always available (string field)
        breakdown['GM Trend'] = s_gm_trend
        self._add_detail("Quality (Profitability)", "Gross Margin Trend", f.gross_margin_trend, "Rising", s_gm_trend, 10, status)
        
        # --- C. Health (20 Pts) ---
        # 6. Debt Threshold (15 pts) - Dynamic Target
        target_debt = benchmarks.get('debt_safe', 1.0)
        s_debt = self._linear_score(
            f.debt_to_ebitda, ideal=target_debt, zero=target_debt * 2.0, max_pts=15,
            label="Debt/EBITDA", category="Quality (Health)"
        )
        if s_debt is not None:
            score += s_debt
            available_pts += 15
        breakdown['Debt/EBITDA'] = s_debt if s_debt is not None else 0.0
        
        # 7. Altman Z-Score (5 pts) - Standard Target
        s_z = self._linear_score(
            f.altman_z_score, ideal=3.0, zero=1.8, max_pts=5,
            label="Altman Z-Score", category="Quality (Health)"
        )
        if s_z is not None:
            score += s_z
            available_pts += 5
        breakdown['Altman Z'] = s_z if s_z is not None else 0.0

        # --- D. Growth (10 Pts) ---
        # 8. Rev Growth (10 pts) - Dynamic Target
        target_growth = benchmarks.get('growth_strong', 0.10)
        s_growth = self._linear_score(
            f.revenue_growth_3y, ideal=target_growth, zero=0.0, max_pts=10,
            label="Rev Growth (3yr)", category="Quality (Growth)", unit="%"
        )
        if s_growth is not None:
            score += s_growth
            available_pts += 10
        breakdown['Growth'] = s_growth if s_growth is not None else 0.0
        
        # Normalize: scale score to 100-pt basis over available points
        if available_pts > 0:
            normalized_score = (score / available_pts) * 100
        else:
            normalized_score = 50.0  # Total data blackout → neutral
        
        breakdown['_available_pts'] = available_pts
        return normalized_score, breakdown
        
    def _score_timing(self, t: Technicals, beta: float, sector_name: str) -> tuple[float, Dict]:
        """
        Calculates the Timing Score (Max 100).
        None-safe: missing metrics excluded, score normalizes over available points.
        """
        score = 0.0
        available_pts = 0.0
        breakdown = {}
        
        benchmarks = self._get_benchmarks(sector_name)
        
        # --- A. Trend (50 Pts) ---
        # 1. Price vs SMA200 (30 pts) — Ideal raised to 1.05 for discrimination
        if t.sma200 and t.sma200 > 0:
            ratio = t.price / t.sma200
            s_sma200 = self._linear_score(
                ratio, ideal=1.05, zero=0.95, max_pts=30,
                label="Price vs SMA200", category="Timing (Trend)"
            )
            if s_sma200 is not None:
                score += s_sma200
                available_pts += 30
            breakdown['vs SMA200'] = s_sma200 if s_sma200 is not None else 0.0
        else:
            self._add_detail("Timing (Trend)", "Price vs SMA200", "N/A", "> 1.05", 0, 30, "N/A")
        
        # 2. Price vs SMA50 (20 pts) — Ideal raised to 1.03
        if t.sma50 and t.sma50 > 0:
            ratio = t.price / t.sma50
            s_sma50 = self._linear_score(
                ratio, ideal=1.03, zero=0.95, max_pts=20,
                label="Price vs SMA50", category="Timing (Trend)"
            )
            if s_sma50 is not None:
                score += s_sma50
                available_pts += 20
            breakdown['vs SMA50'] = s_sma50 if s_sma50 is not None else 0.0
        else:
            self._add_detail("Timing (Trend)", "Price vs SMA50", "N/A", "> 1.03", 0, 20, "N/A")

        # --- B. Momentum (15 Pts) ---
        # 3. RSI (15 pts) - Continuous linear ramps (replaces step function)
        rsi_score = 0.0
        status = "Neutral"
        if t.rsi is not None and t.rsi > 0:
            if 45 <= t.rsi <= 60:
                rsi_score = 15.0
                status = "Excellent"
            elif t.rsi < 25 or t.rsi > 85:
                rsi_score = 0.0
                status = "Poor"
            elif t.rsi < 45:
                rsi_score = 15.0 * ((t.rsi - 25) / 20)  # Linear ramp 25→45
                status = "Good" if rsi_score >= 10 else "Fair"
            else:  # 60 < rsi <= 85
                rsi_score = 15.0 * ((85 - t.rsi) / 25)  # Linear ramp 60→85
                status = "Good" if rsi_score >= 10 else "Fair"
            available_pts += 15
        score += rsi_score
        breakdown['RSI'] = rsi_score
        self._add_detail("Timing (Momentum)", "RSI (14)", f"{t.rsi:.1f}" if t.rsi else "N/A", "45 - 60", rsi_score, 15, status)

        # --- C. Volume (15 Pts) ---
        # 4. Relative Volume (15 pts) - Target: > 1.5x
        s_rvol = self._linear_score(
            t.relative_volume, ideal=1.5, zero=0.5, max_pts=15,
            label="Rel. Vol (RVOL)", category="Timing (Volume)"
        )
        if s_rvol is not None:
            score += s_rvol
            available_pts += 15
        breakdown['RVOL'] = s_rvol if s_rvol is not None else 0.0

        # --- D. Risk (20 Pts) ---
        # 5. Beta (10 pts) - Dynamic Target
        target_beta = benchmarks.get('beta_safe', 1.2)
        s_beta = self._linear_score(
            beta, ideal=target_beta, zero=target_beta + 0.8, max_pts=10,
            label="Beta", category="Timing (Risk)"
        )
        if s_beta is not None:
            score += s_beta
            available_pts += 10
        breakdown['Beta'] = s_beta if s_beta is not None else 0.0
        
        # 6. Distance to High (10 pts) - Target: Within 15%
        s_dist = self._linear_score(
            t.distance_to_high, ideal=0.15, zero=0.30, max_pts=10,
            label="Dist. to High", category="Timing (Risk)", unit="%"
        )
        if s_dist is not None:
            score += s_dist
            available_pts += 10
        breakdown['Dist to High'] = s_dist if s_dist is not None else 0.0
        
        # Normalize: scale score to 100-pt basis over available points
        if available_pts > 0:
            normalized_score = (score / available_pts) * 100
        else:
            normalized_score = 50.0  # Total data blackout → neutral
        
        breakdown['_available_pts'] = available_pts
        return normalized_score, breakdown

    def _linear_score(self, value: float, ideal: float, zero: float, max_pts: float, label: str, category: str, unit: str = "") -> float:
        """
        Calculates a score based on a linear interpolation between 'ideal' (max_pts) and 'zero' (0 pts).
        """
        if value is None:
            self._add_detail(category, label, "N/A", f"{ideal}{unit}", 0, max_pts, "N/A")
            return None  # Missing data = no contribution, not worst-case

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

    def _map_sector_to_theme(self, raw_sector: str, ticker: str) -> str:
        """Maps Yahoo Finance sector strings to one of our 10 Wealth Manager Themes."""
        s = raw_sector.lower() if raw_sector else "technology"
        
        # 1. Tech & Growth (Nasdaq 100)
        if "software" in s or "information" in s: return "💻 Tech & Growth (Nasdaq 100)"
        
        # 2. Semiconductors (Specific Check)
        if "semiconduct" in s: return "💾 Semiconductors"
        
        # 3. Technology Sector (General Hardware/Electronics)
        if "technology" in s or "electronic" in s: return "📱 Technology Sector"
        
        # 4. Financials
        if "financial" in s or "bank" in s or "insurance" in s or "capital" in s: return "💰 Financial Sector"
        
        # 5. Healthcare
        if "health" in s or "pharma" in s or "biotech" in s or "medical" in s: return "🏥 Healthcare Sector"
        
        # 6. Consumer Discretionary
        if "cyclical" in s or "vehicle" in s or "auto" in s or "entertainment" in s or "retail" in s or "apparel" in s: return "🛍️ Consumer Discretionary"
        
        # 7. Consumer Staples
        if "defensive" in s or "food" in s or "drink" in s or "beverage" in s or "household" in s or "tobacco" in s: return "🛒 Consumer Staples"
        
        # 8. Energy
        if "energy" in s or "oil" in s or "gas" in s: return "🛢️ Energy Sector"
        
        # 9. Materials
        if "material" in s or "mining" in s or "chemical" in s or "steel" in s or "gold" in s: return "🧱 Materials & Mining"
        
        # 10. Industrials
        if "industr" in s or "aerospace" in s or "defense" in s or "transport" in s or "machinery" in s: return "🏗️ Industrials Sector"
        
        # 11. Real Estate
        if "real estate" in s or "reit" in s: return "🏠 Real Estate (REITs)"
        
        # 12. Utilities
        if "utilit" in s or "communication" in s or "telecom" in s: return "⚡ Utilities Sector"
            
        return "🇺🇸 Broad Market (S&P 500)"

    def _add_detail(self, category: str, metric: str, value: str, benchmark: str, score: float, max_score: float, status: str):
        self.details.append({
            "category": category,
            "metric": metric,
            "value": value,
            "benchmark": benchmark,
            "score": f"{score:.1f}/{max_score:.0f}",
            "status": status
        })

    def _get_benchmarks(self, sector_name: str) -> Dict:
        return self.sector_benchmarks.get(sector_name, self.defaults)

    def _get_rating(self, score: float) -> str:
        if score >= 90: return "Generational Buy"
        if score >= 85: return "High Conviction"
        if score >= 80: return "Strong Buy"
        if score >= 75: return "Buy"
        if score >= 70: return "Watchlist Buy"
        if score >= 60: return "Speculative Hold"
        if score >= 50: return "Weak Hold"
        if score >= 40: return "Underperform"
        if score >= 20: return "Hard Sell"
        return "Critical Risk"

    def _generate_narrative(self, ticker, final, q, t, mods) -> str:
        narrative = f"{ticker} is rated {self._get_rating(final)} ({final:.0f}/100). "
        
        narrative += f"Quality ({q:.0f}/100) is {'elite' if q>85 else 'strong' if q>70 else 'fair' if q>50 else 'weak'}, "
        narrative += f"Timing ({t:.0f}/100) is {'bullish' if t>80 else 'supportive' if t>60 else 'neutral' if t>40 else 'bearish'}. "
            
        if mods:
             narrative += f"CAUTION: {len(mods)} Risk Factor(s) Triggered. "
            
        return narrative

    def print_report(self, stock: StockData, result: ScoreResult):
        print(f"\n--- VinSight {self.VERSION}: {stock.ticker} ---")
        print(f"Strategy: CFA Composite Model (70% Quality / 30% Timing)")
        print(f"Score: {result.total_score:.1f}/100 ({result.rating})")
        print(f"Narrative: {result.verdict_narrative}")
        print("\n[RISK FACTORS & VETOS]")
        print(f"  {', '.join(result.modifications) if result.modifications else 'None'}")
        
        print("\n[DETAILED SCORE BREAKDOWN]")
        print(f"  {'CATEGORY':<25} | {'METRIC':<20} | {'VALUE':<10} | {'BENCHMARK':<12} | {'SCORE':<8} | {'STATUS'}")
        print("-" * 100)
        
        for detail in result.details:
                print(f"  {detail['category']:<25} | {detail['metric']:<20} | {detail['value']:<10} | {detail['benchmark']:<12} | {detail['score']:<8} | {detail['status']}")
                
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
            revenue_growth_3y=0.12, # Added
            inst_ownership=80.0,
            fcf_yield=0.04,
            eps_surprise_pct=0.10,
            sector_name="Technology",
            gross_margin_trend="Rising", # Added
            debt_to_ebitda=2.5, # Added
            interest_coverage=8.0, # Added
            altman_z_score=3.5 # Added
        ),
        technicals=Technicals(
            price=150.0, sma50=145.0, sma200=140.0, rsi=55.0,
            relative_volume=1.2, # Added
            distance_to_high=0.05, # Added
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
