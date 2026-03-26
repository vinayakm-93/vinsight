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

    # 7. V12 Engine (Phase 1 Plumbing)
    nopat: Optional[float] = None
    invested_capital: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    trailing_eps: List[float] = field(default_factory=list)
    net_income: Optional[float] = None
    total_assets: Optional[float] = None
    net_share_issuance_ttm: Optional[float] = None
    wacc: float = 0.10
    market_cap: Optional[float] = None

    # 8. V12 Engine (Phase 3 RIM Plumbing)
    forward_roe: Optional[float] = None
    book_value_per_share: Optional[float] = None
    shares_outstanding: Optional[float] = None

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

@dataclass
class ScoreResultV13:
    """v13 Three-Axis Scoring Result."""
    conviction_score: float         # 0-100: Persona-weighted blend
    quality_axis: float             # 0-100: Business fundamentals (no valuation)
    value_axis: float               # 0-100: Valuation + RIM
    timing_axis: float              # 0-100: Technical entry signal
    rating: str                     # Human-readable rating label
    verdict_narrative: str          # Generated narrative
    quality_breakdown: Dict         # Per-metric details for Quality
    value_breakdown: Dict           # Per-metric details for Value
    timing_breakdown: Dict          # Per-metric details for Timing
    modifications: List[str]        # Risk flags and adjustments
    penalties_applied: List[Dict]   # Gradient penalty log
    missing_data: List[str]         # Missing data fields
    details: List[Dict]             # Flat detail rows for UI table
    persona: str = "CFA"            # Active persona
    conviction_weights: Dict = None # Weights used {Q, V, T}
    rim_result: Optional[Dict] = None  # RIM valuation details
    fragility: Optional[Dict] = None   # Data fragility details

# --- v13 Conviction Weights per Persona ---
CONVICTION_WEIGHTS = {
    "CFA":      {"Q": 0.45, "V": 0.30, "T": 0.25},
    "Momentum": {"Q": 0.10, "V": 0.05, "T": 0.85},
    "Value":    {"Q": 0.20, "V": 0.55, "T": 0.25},
    "Growth":   {"Q": 0.40, "V": 0.15, "T": 0.45},
    "Income":   {"Q": 0.50, "V": 0.30, "T": 0.20},
}

# --- Sector-specific retention ratios for RIM ---
SECTOR_RETENTION = {
    "⚡ Utilities Sector": 0.25,
    "🏠 Real Estate (REITs)": 0.20,
    "💰 Financial Sector": 0.40,
    "🛒 Consumer Staples": 0.45,
    "💻 Tech & Growth (Nasdaq 100)": 0.85,
    "💾 Semiconductors": 0.80,
    "🏥 Healthcare Sector": 0.70,
    "🛍️ Consumer Discretionary": 0.60,
    "🛢️ Energy Sector": 0.45,
    "🧱 Materials & Mining": 0.50,
    "🏗️ Industrials Sector": 0.55,
    "📱 Technology Sector": 0.75,
    "🇺🇸 Broad Market (S&P 500)": 0.60,
}

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

        # --- V12 Phase 1: The Kill Switches ---
        kill_switch_cap = None
        
        # 1. Value Destroyer Switch (ROIC < WACC - 2%)
        # ROIC = NOPAT / Invested Capital
        if stock.fundamentals.nopat is not None and stock.fundamentals.invested_capital and stock.fundamentals.wacc is not None:
            if stock.fundamentals.invested_capital > 0:
                roic = stock.fundamentals.nopat / stock.fundamentals.invested_capital
                wacc_buffer = stock.fundamentals.wacc - 0.02
                if roic < wacc_buffer:
                     kill_switch_cap = 30  # Hard Sell / Underperform
                     modifications.append(f"KILL SWITCH (Value Destroyer): ROIC ({roic:.1%}) < WACC ({stock.fundamentals.wacc:.1%}) - 2% buffer")

        # 2. Distress Switch (Altman Z < 1.8, ignore Financials)
        if stock.fundamentals.altman_z_score is not None and stock.fundamentals.altman_z_score < 1.8:
            if "Financial" not in stock.fundamentals.sector_name:
                 if kill_switch_cap is None or 20 < kill_switch_cap:
                     kill_switch_cap = 20
                 modifications.append(f"KILL SWITCH (Distress): Altman Z-Score {stock.fundamentals.altman_z_score:.2f} < 1.8")

        # 3. Dilution Switch (TTM net share issuance > 5% of Market Cap)
        if stock.fundamentals.net_share_issuance_ttm is not None and stock.fundamentals.market_cap and stock.fundamentals.market_cap > 0:
            dilution_pct = stock.fundamentals.net_share_issuance_ttm / stock.fundamentals.market_cap
            if dilution_pct > 0.05:
                if kill_switch_cap is None or 30 < kill_switch_cap:
                    kill_switch_cap = 30
                modifications.append(f"KILL SWITCH (Dilution): Net Yield/Dilution +{dilution_pct:.1%}")
        
        # --- V12 Phase 3: RIM Valuation Engine ---
        rim_result = self._compute_rim_valuation(stock)
        rim_bonus = 0.0
        if rim_result and rim_result.get('intrinsic_value') is not None:
            margin_of_safety = rim_result['margin_of_safety']
            # Conviction scaling: +15pts at >=30% discount, 0pts at fair value, -15pts at >=30% premium
            if margin_of_safety >= 0.30:
                rim_bonus = 15.0
            elif margin_of_safety >= 0.0:
                rim_bonus = (margin_of_safety / 0.30) * 15.0
            elif margin_of_safety >= -0.30:
                rim_bonus = (margin_of_safety / 0.30) * 15.0  # Negative
            else:
                rim_bonus = -15.0
            rim_bonus = round(rim_bonus, 1)
            modifications.append(f"RIM Valuation: IV=${rim_result['intrinsic_value']:.2f}, MoS={margin_of_safety:.1%}, Bonus={rim_bonus:+.1f}pts")
            if rim_result.get('iv_low') and rim_result.get('iv_high'):
                modifications.append(f"RIM Sensitivity: ${rim_result['iv_low']:.2f} – ${rim_result['iv_high']:.2f} (WACC±1%)")
        
        # --- V12 Phase 4: Data Fragility Layer ---
        fragility = self._compute_data_fragility(stock)
        fragility_penalty = fragility.get('penalty', 0.0)
        if fragility_penalty > 0:
            modifications.append(f"DATA FRAGILITY: -{fragility_penalty:.0f}pts (Confidence: {fragility['confidence']})")
        for flag in fragility.get('fragility_flags', []):
            modifications.append(flag)
        
        # --- Phase 5: Composite Calculation ---
        # Master Equation: 70% Quality + 30% Timing + RIM Bonus - Fragility Penalty
        final_score = (quality_score * 0.70) + (timing_score * 0.30) + rim_bonus - fragility_penalty
        final_score = max(0.0, min(100.0, final_score))  # Clamp to 0-100
        
        # Apply Insolvency Cap if triggered
        if insolvency_cap and final_score > insolvency_cap:
            final_score = insolvency_cap
            modifications.append(f"Score Capped at {insolvency_cap} due to Insolvency Risk")
            
        # Apply Kill Switch Caps
        if kill_switch_cap and final_score > kill_switch_cap:
            final_score = kill_switch_cap
            modifications.append(f"Score Capped at {kill_switch_cap} due to V12 Defense Protocol")
            
        final_score = round(final_score, 1)
        
        # Combine breakdowns
        full_breakdown = {**q_breakdown, **t_breakdown}
        full_breakdown['Quality Score'] = round(quality_score, 1)
        full_breakdown['Timing Score'] = round(timing_score, 1)
        full_breakdown['RIM Bonus'] = rim_bonus
        if rim_result:
            full_breakdown['RIM Intrinsic Value'] = rim_result.get('intrinsic_value')
            full_breakdown['RIM Margin of Safety'] = rim_result.get('margin_of_safety')
            full_breakdown['RIM Fair Value Range'] = f"${rim_result.get('iv_low', 0):.2f} – ${rim_result.get('iv_high', 0):.2f}"
        full_breakdown['Data Confidence'] = fragility.get('confidence', 'High')
        full_breakdown['Fragility Penalty'] = fragility_penalty
        
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

        # 5. Sloan Accrual Penalty
        # (Net Income - Operating Cash Flow) / Total Assets
        if f.net_income is not None and f.operating_cash_flow is not None and f.total_assets and f.total_assets > 0:
            sloan_ratio = (f.net_income - f.operating_cash_flow) / f.total_assets
            if sloan_ratio > 0.05:
                buffer_pct = 0.05
                gradient_pct = 0.15
                raw_penalty = _buffered_penalty(sloan_ratio, buffer_pct, gradient_pct, 10, direction="above")
                penalty = round(raw_penalty, 1) # Not affected by any specific persona sensitivity for now
                if penalty > 0:
                    deductions += penalty
                    logs.append({
                        "type": "Earnings Quality",
                        "severity": penalty,
                        "raw_value": sloan_ratio,
                        "threshold": 0.05,
                        "detail": f"Accrual Ratio {sloan_ratio:.1%} > 5% (Earnings Quality Risk, -{penalty:.1f}pts)"
                    })

        return round(deductions, 1), logs

    def _compute_data_fragility(self, stock: StockData) -> Dict:
        """
        V12 Phase 4: Data Fragility Layer & AI Auditor.
        
        1. DuPont Triangulation: Decomposes ROE into Margin × Turnover × Leverage.
           If reconstructed ROE deviates from reported ROE by >15%, flags a fragility warning.
        2. Auditor Veto: Applies a deterministic penalty based on fragility severity.
        
        Returns a dict with 'fragility_flags', 'penalty', and 'confidence' level.
        """
        import math
        
        f = stock.fundamentals
        result = {
            'fragility_flags': [],
            'penalty': 0.0,
            'confidence': 'High',  # High, Medium, Low
            'dupont_mismatch': None,
        }
        
        # --- 1. DuPont Triangulation ---
        # ROE = Net Margin × Asset Turnover × Equity Multiplier
        # Net Margin = Net Income / Revenue (proxy: profit_margin)
        # Asset Turnover = Revenue / Total Assets
        # Equity Multiplier = Total Assets / Equity = 1 + D/E
        
        reported_roe = f.roe
        
        if (reported_roe is not None and f.profit_margin is not None 
            and f.total_assets is not None and f.total_assets > 0
            and f.net_income is not None and f.net_income != 0
            and f.debt_to_equity is not None):
            
            net_margin = f.profit_margin
            
            # Asset Turnover proxy: Net Income / (Net Margin * Total Assets)
            # Revenue ≈ Net Income / Net Margin
            if abs(net_margin) > 0.001:
                implied_revenue = f.net_income / net_margin
                asset_turnover = implied_revenue / f.total_assets
            else:
                asset_turnover = 0.0
            
            equity_multiplier = 1.0 + f.debt_to_equity
            
            # DuPont reconstructed ROE
            dupont_roe = net_margin * asset_turnover * equity_multiplier
            
            # Compare with reported ROE
            if abs(reported_roe) > 0.01:
                deviation = abs(dupont_roe - reported_roe) / abs(reported_roe)
                result['dupont_mismatch'] = round(deviation, 4)
                
                if deviation > 0.30:
                    result['fragility_flags'].append(
                        f"CRITICAL: DuPont Mismatch {deviation:.0%} (Reported ROE: {reported_roe:.1%}, DuPont ROE: {dupont_roe:.1%})"
                    )
                    result['confidence'] = 'Low'
                    result['penalty'] += 20.0
                elif deviation > 0.15:
                    result['fragility_flags'].append(
                        f"WARNING: DuPont Mismatch {deviation:.0%} (Reported ROE: {reported_roe:.1%}, DuPont ROE: {dupont_roe:.1%})"
                    )
                    result['confidence'] = 'Medium'
                    result['penalty'] += 10.0
                
                self._add_detail(
                    "Data Integrity", "DuPont Triangulation",
                    f"{deviation:.0%} dev", "< 15%",
                    0, 0,
                    "Pass" if deviation <= 0.15 else ("Warning" if deviation <= 0.30 else "FAIL")
                )
        
        # --- 2. Cross-checks: Revenue vs Net Income Consistency ---
        if f.net_income is not None and f.profit_margin is not None and f.market_cap and f.market_cap > 0:
            if f.profit_margin < -1.0:  # Loss > 100% of revenue — extreme
                result['fragility_flags'].append(
                    f"EXTREME LOSS: Profit Margin {f.profit_margin:.0%} suggests data quality issue"
                )
                result['penalty'] += 5.0
                if result['confidence'] == 'High':
                    result['confidence'] = 'Medium'
        
        # --- 3. Auditor Veto Logic ---
        # Cap the total penalty
        result['penalty'] = min(result['penalty'], 30.0)
        
        return result

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
        
        # 2. Net Shareholder Yield (15 pts) - V12
        import math
        net_shareholder_yield = f.fcf_yield if f.fcf_yield is not None else 0.0
        if f.net_share_issuance_ttm is not None and f.market_cap and f.market_cap > 0:
            repurchase_yield = (-f.net_share_issuance_ttm) / f.market_cap
            net_shareholder_yield += repurchase_yield
            
        target_yield = benchmarks.get('fcf_yield_strong', 0.08) # Slightly higher expectation for total yield
        s_yield = self._linear_score(
            net_shareholder_yield, ideal=target_yield, zero=target_yield * 0.2, max_pts=15,
            label="Net Shareholder Yield", category="Quality (Valuation)", unit="%"
        )
        if s_yield is not None:
            score += s_yield
            available_pts += 15
        breakdown['Net Sh. Yield'] = s_yield if s_yield is not None else 0.0
        
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
        
        # 5. ROIC Spread [ROIC - WACC] (10 pts) - V12
        s_roic = None
        if f.nopat is not None and f.invested_capital and f.invested_capital > 0 and f.wacc is not None:
            roic = f.nopat / f.invested_capital
            spread = roic - f.wacc
            s_roic = self._linear_score(
                spread, ideal=0.05, zero=0.0, max_pts=10,
                label="ROIC Spead", category="Quality (Profitability)", unit="%"
            )
        if s_roic is not None:
            score += s_roic
            available_pts += 10
        breakdown['ROIC Spread'] = s_roic if s_roic is not None else 0.0
        
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

        # --- D. Growth/Stability (10 Pts) ---
        # 8. EPS Stability (10 pts) - V12 variation coefficient
        s_eps = None
        if f.trailing_eps and len(f.trailing_eps) >= 3:
            eps_array = [e for e in f.trailing_eps if e is not None]
            if len(eps_array) >= 3:
                import math
                mean_eps = sum(eps_array) / len(eps_array)
                if mean_eps <= 0:
                    s_eps = 0.0 # Unstable/Loss-making
                    self._add_detail("Quality (Stability)", "EPS Stability", "Neg Mean EPS", "0.1", 0.0, 10.0, "Poor")
                else:
                    variance = sum((x - mean_eps)**2 for x in eps_array) / len(eps_array)
                    std_dev = math.sqrt(variance)
                    cv = std_dev / mean_eps # Coefficient of variation
                    # Ideal CV = 0.10, Zero CV = 1.0
                    s_eps = self._linear_score(
                        -cv, ideal=-0.10, zero=-1.0, max_pts=10,
                        label="EPS Stability (CV)", category="Quality (Stability)"
                    )
        
        if s_eps is not None:
            score += s_eps
            available_pts += 10
        breakdown['EPS Stability'] = s_eps if s_eps is not None else 0.0
        
        # Normalize: scale score to 100-pt basis over available points
        if available_pts >= 50.0:  # Enforce 50% minimum data rule (Total Max is 100)
            normalized_score = (score / available_pts) * 100
        else:
            normalized_score = 50.0  # Insufficient data → neutral
        
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
        if available_pts >= 50.0:  # Enforce 50% minimum data rule (Total Max is 100)
            normalized_score = (score / available_pts) * 100
        else:
            normalized_score = 50.0  # Insufficient data → neutral
        
        breakdown['_available_pts'] = available_pts
        return normalized_score, breakdown

    def _linear_score(self, value: float, ideal: float, zero: float, max_pts: float, label: str, category: str, unit: str = "") -> float:
        """
        Calculates a score based on a linear interpolation between 'ideal' (max_pts) and 'zero' (0 pts).
        """
        import math
        if value is None or (isinstance(value, (int, float)) and math.isnan(value)):
            self._add_detail(category, label, "N/A", f"{ideal}{unit}", None, max_pts, "Skipped")
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

    def _compute_rim_valuation(self, stock: StockData) -> Optional[Dict]:
        """
        V12 Phase 3: Residual Income Model (RIM) Valuation Engine.
        
        Formula: P* = BV₀ + Σ [(ROE_t - WACC) * BV_{t-1}] / (1 + WACC)^t
        
        Uses a 3-year explicit forecast with terminal value fade.
        Returns intrinsic value per share, margin of safety, and WACC sensitivity range.
        """
        import math
        
        f = stock.fundamentals
        price = stock.technicals.price if stock.technicals.price and stock.technicals.price > 0 else None
        
        # Guard: Need critical inputs
        if f.book_value_per_share is None or f.book_value_per_share <= 0:
            return None
        if f.wacc is None or f.wacc <= 0:
            return None
        if price is None:
            return None
            
        bvps = f.book_value_per_share
        wacc = f.wacc
        
        # P/B Ratio sanity check
        pb_ratio = price / bvps
        
        # For extremely asset-light companies (P/B > 10x), RIM is structurally invalid
        # Book value doesn't capture intangible value (brand, IP, network effects)
        if pb_ratio > 10.0:
            self._add_detail(
                "RIM Valuation", "RIM Skipped",
                f"P/B={pb_ratio:.1f}x", "P/B < 10x",
                0, 0, "N/A (Asset-Light)"
            )
            return None
        
        # For moderately high P/B (5-10x), adjust book value anchor upward
        # to partially account for intangible value
        if pb_ratio > 5.0:
            # Blend: 50% BVPS + 50% (Price / 3) as intangible-adjusted anchor
            bvps = (bvps * 0.5) + (price / 3.0) * 0.5
        
        # --- Forward ROE Estimation ---
        # Hybrid: Blend analyst forward ROE (if available) with mean-reverting historical ROE
        historical_roe = f.roe if f.roe is not None else None
        forward_roe_est = f.forward_roe  # From analyst data (FMP/Yahoo)
        
        if forward_roe_est is not None and historical_roe is not None:
            # Blend: 60% analyst, 40% historical (mean-reversion anchor)
            blended_roe = (forward_roe_est * 0.6) + (historical_roe * 0.4)
        elif forward_roe_est is not None:
            blended_roe = forward_roe_est
        elif historical_roe is not None:
            blended_roe = historical_roe
        else:
            return None  # No ROE data at all
        
        # Sanity bounds on ROE: cap at -50% to +60%
        blended_roe = max(-0.50, min(0.60, blended_roe))
        
        # --- Retention Rate (v13: data-driven, not fixed 60%) ---
        # Use actual payout ratio if available, else sector default
        theme = self._map_sector_to_theme(f.sector_name, stock.ticker)
        if f.payout_ratio is not None and 0.0 < f.payout_ratio < 1.0:
            retention_rate = 1.0 - f.payout_ratio
        else:
            retention_rate = SECTOR_RETENTION.get(theme, 0.60)
        
        # Clamp WACC: raised upper bound from 15% to 20% for high-risk stocks
        wacc = max(0.08, min(0.20, wacc))
        
        # --- RIM Calculation ---
        def _rim_intrinsic(bv: float, roe: float, discount_rate: float) -> float:
            """3-year explicit forecast + terminal fade."""
            pv_residual_income = 0.0
            running_bv = bv
            
            for t in range(1, 4):  # Years 1-3
                # ROE mean-reverts toward WACC over time (fade factor)
                fade = 1.0 - (t - 1) * 0.15  # Year 1: 100%, Year 2: 85%, Year 3: 70%
                faded_roe = discount_rate + (roe - discount_rate) * fade
                
                # Residual Income = (ROE_t - WACC) * BV_{t-1}
                residual_income = (faded_roe - discount_rate) * running_bv
                
                # Discount back
                pv_residual_income += residual_income / ((1 + discount_rate) ** t)
                
                # Grow book value: BV_t = BV_{t-1} * (1 + ROE_t * retention_ratio)
                running_bv *= (1 + faded_roe * retention_rate)
            
            # Terminal value: assume residual income fades to zero after year 3
            # (Conservative — no terminal growth premium)
            intrinsic = bv + pv_residual_income
            
            # Floor at 0 (intrinsic value can't be negative in this model)
            return max(0.01, intrinsic)
        
        # Central estimate
        iv_central = _rim_intrinsic(bvps, blended_roe, wacc)
        
        # WACC Sensitivity: ±1%
        iv_low = _rim_intrinsic(bvps, blended_roe, wacc + 0.01)  # Higher WACC = lower value
        iv_high = _rim_intrinsic(bvps, blended_roe, wacc - 0.01)  # Lower WACC = higher value
        
        # Margin of Safety
        margin_of_safety = (iv_central - price) / iv_central if iv_central > 0 else 0.0
        
        # Sanity check: if IV is absurdly high (>10x price), cap it
        if iv_central > price * 10:
            iv_central = price * 10
            margin_of_safety = (iv_central - price) / iv_central
        
        self._add_detail(
            "RIM Valuation", "Intrinsic Value (RIM)",
            f"${iv_central:.2f}", f"Price: ${price:.2f}",
            0, 0,  # No direct score contribution (it's a bonus)
            f"MoS: {margin_of_safety:.1%}"
        )
        
        return {
            'intrinsic_value': round(iv_central, 2),
            'margin_of_safety': round(margin_of_safety, 4),
            'iv_low': round(iv_low, 2),
            'iv_high': round(iv_high, 2),
            'forward_roe_used': round(blended_roe, 4),
            'wacc_used': round(wacc, 4),
            'retention_rate_used': round(retention_rate, 4)
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # v13 THREE-AXIS SCORING ENGINE
    # ═══════════════════════════════════════════════════════════════════════════

    def _score_quality_v13(self, f: 'Fundamentals') -> tuple:
        """
        v13 Quality Score: Business fundamentals ONLY (no valuation metrics).
        Metrics: ROE, Net Margin, ROIC Spread, Debt/EBITDA, Altman Z, EPS Stability, Revenue Growth.
        Max 100 pts, normalized over available data.
        """
        import math
        score = 0.0
        available_pts = 0.0
        breakdown = {}
        benchmarks = self._get_benchmarks(f.sector_name)

        # 1. ROE (20 pts)
        target_roe = benchmarks.get('roe_strong', 0.15)
        s_roe = self._linear_score(
            f.roe, ideal=target_roe, zero=target_roe * 0.3, max_pts=20,
            label="ROE", category="Quality v13 (Profitability)", unit="%"
        )
        if s_roe is not None:
            score += s_roe
            available_pts += 20
        breakdown['ROE'] = s_roe if s_roe is not None else 0.0

        # 2. Net Margin (15 pts)
        target_margin = benchmarks.get('margin_healthy', 0.12)
        s_margin = self._linear_score(
            f.profit_margin, ideal=target_margin, zero=target_margin * 0.4, max_pts=15,
            label="Net Margin", category="Quality v13 (Profitability)", unit="%"
        )
        if s_margin is not None:
            score += s_margin
            available_pts += 15
        breakdown['Net Margin'] = s_margin if s_margin is not None else 0.0

        # 3. ROIC Spread (15 pts)
        s_roic = None
        if f.nopat is not None and f.invested_capital and f.invested_capital > 0 and f.wacc is not None:
            roic = f.nopat / f.invested_capital
            spread = roic - f.wacc
            s_roic = self._linear_score(
                spread, ideal=0.05, zero=0.0, max_pts=15,
                label="ROIC Spread", category="Quality v13 (Profitability)", unit="%"
            )
        if s_roic is not None:
            score += s_roic
            available_pts += 15
        breakdown['ROIC Spread'] = s_roic if s_roic is not None else 0.0

        # 4. Debt/EBITDA (20 pts)
        target_debt = benchmarks.get('debt_safe', 1.0)
        s_debt = self._linear_score(
            f.debt_to_ebitda, ideal=target_debt, zero=target_debt * 2.0, max_pts=20,
            label="Debt/EBITDA", category="Quality v13 (Health)"
        )
        if s_debt is not None:
            score += s_debt
            available_pts += 20
        breakdown['Debt/EBITDA'] = s_debt if s_debt is not None else 0.0

        # 5. Altman Z-Score (10 pts)
        s_z = self._linear_score(
            f.altman_z_score, ideal=3.0, zero=1.8, max_pts=10,
            label="Altman Z-Score", category="Quality v13 (Health)"
        )
        if s_z is not None:
            score += s_z
            available_pts += 10
        breakdown['Altman Z'] = s_z if s_z is not None else 0.0

        # 6. EPS Stability (10 pts)
        s_eps = None
        if f.trailing_eps and len(f.trailing_eps) >= 3:
            eps_array = [e for e in f.trailing_eps if e is not None]
            if len(eps_array) >= 3:
                mean_eps = sum(eps_array) / len(eps_array)
                if mean_eps <= 0:
                    s_eps = 0.0
                    self._add_detail("Quality v13 (Stability)", "EPS Stability", "Neg Mean EPS", "0.1", 0.0, 10.0, "Poor")
                else:
                    variance = sum((x - mean_eps)**2 for x in eps_array) / len(eps_array)
                    std_dev = math.sqrt(variance)
                    cv = std_dev / mean_eps
                    s_eps = self._linear_score(
                        -cv, ideal=-0.10, zero=-1.0, max_pts=10,
                        label="EPS Stability (CV)", category="Quality v13 (Stability)"
                    )
        if s_eps is not None:
            score += s_eps
            available_pts += 10
        breakdown['EPS Stability'] = s_eps if s_eps is not None else 0.0

        # 7. Revenue Growth (10 pts)
        target_growth = benchmarks.get('growth_strong', 0.10)
        s_rev = self._linear_score(
            f.revenue_growth_3y, ideal=target_growth, zero=0.0, max_pts=10,
            label="Revenue Growth (3y)", category="Quality v13 (Growth)", unit="%"
        )
        if s_rev is not None:
            score += s_rev
            available_pts += 10
        breakdown['Revenue Growth'] = s_rev if s_rev is not None else 0.0

        # Normalize to 100-point basis
        if available_pts > 0:
            normalized = (score / available_pts) * 100
        else:
            normalized = 50.0
        breakdown['_available_pts'] = available_pts
        return normalized, breakdown

    def _score_value(self, stock: 'StockData') -> tuple:
        """
        v13 Value Score: ALL valuation metrics consolidated.
        Metrics: PEG, Forward P/E, Net Shareholder Yield, RIM Margin of Safety.
        Max 100 pts, normalized over available data.
        """
        import math
        f = stock.fundamentals
        score = 0.0
        available_pts = 0.0
        breakdown = {}
        benchmarks = self._get_benchmarks(f.sector_name)

        # 1. PEG Ratio (25 pts)
        target_peg = benchmarks.get('peg_fair', 1.5)
        s_peg = self._linear_score(
            f.peg_ratio, ideal=target_peg, zero=target_peg + 2.0, max_pts=25,
            label="PEG Ratio", category="Value v13 (Relative)"
        )
        if s_peg is not None:
            score += s_peg
            available_pts += 25
        breakdown['PEG'] = s_peg if s_peg is not None else 0.0

        # 2. Forward P/E (20 pts)
        pe_median = benchmarks.get('pe_median', 24)
        s_fpe = self._linear_score(
            f.forward_pe, ideal=pe_median, zero=pe_median * 2.5, max_pts=20,
            label="Forward P/E", category="Value v13 (Relative)"
        )
        if s_fpe is not None:
            score += s_fpe
            available_pts += 20
        breakdown['Forward P/E'] = s_fpe if s_fpe is not None else 0.0

        # 3. Net Shareholder Yield (20 pts)
        net_shareholder_yield = f.fcf_yield if f.fcf_yield is not None else 0.0
        if f.net_share_issuance_ttm is not None and f.market_cap and f.market_cap > 0:
            repurchase_yield = (-f.net_share_issuance_ttm) / f.market_cap
            net_shareholder_yield += repurchase_yield
        target_yield = benchmarks.get('fcf_yield_strong', 0.05)
        s_yield = self._linear_score(
            net_shareholder_yield, ideal=target_yield, zero=target_yield * 0.2, max_pts=20,
            label="Net Shareholder Yield", category="Value v13 (Cash Return)", unit="%"
        )
        if s_yield is not None:
            score += s_yield
            available_pts += 20
        breakdown['Net Sh. Yield'] = s_yield if s_yield is not None else 0.0

        # 4. RIM Margin of Safety (35 pts)
        rim_result = self._compute_rim_valuation(stock)
        rim_score = None
        if rim_result and rim_result.get('intrinsic_value') is not None:
            margin_of_safety = rim_result['margin_of_safety']
            # Gradient: +35 at >=30% discount, 0 at fair value, -35 at >=30% premium
            # But clamp to 0 minimum (negative = 0, not negative points)
            if margin_of_safety >= 0.30:
                rim_score = 35.0
            elif margin_of_safety >= 0.0:
                rim_score = (margin_of_safety / 0.30) * 35.0
            elif margin_of_safety >= -0.30:
                rim_score = 0.0  # Overvalued → 0, not negative
            else:
                rim_score = 0.0
            self._add_detail(
                "Value v13 (Intrinsic)", "RIM Margin of Safety",
                f"{margin_of_safety:.1%}", "> 0%",
                round(rim_score, 1), 35.0,
                "Strong" if margin_of_safety > 0.15 else ("Fair" if margin_of_safety > 0 else "Weak")
            )
        if rim_score is not None:
            score += rim_score
            available_pts += 35
        else:
            # RIM skipped — don't penalize, redistribute weight implicitly via normalization
            self._add_detail("Value v13 (Intrinsic)", "RIM Valuation", "Skipped", "N/A", 0, 0, "N/A")
        breakdown['RIM Score'] = rim_score if rim_score is not None else 0.0
        breakdown['RIM Result'] = rim_result

        # Normalize to 100-point basis
        if available_pts >= 50.0:  # Enforce 50% minimum data rule (Total Max is 100)
            normalized = (score / available_pts) * 100
        else:
            normalized = 50.0  # Insufficient data → neutral
        breakdown['_available_pts'] = available_pts
        return normalized, breakdown

    def evaluate_v13(self, stock: 'StockData', persona: str = "CFA", guardian_status: str = "INTACT") -> 'ScoreResultV13':
        """
        v13 Unified Three-Axis Scoring Engine.
        
        Returns independent Quality, Value, and Timing axes (0-100 each)
        plus a persona-weighted Conviction Score.
        
        Args:
            stock: StockData with fundamentals, technicals, sentiment, projections
            persona: Investment persona (CFA, Momentum, Value, Growth, Income)
            guardian_status: Thesis status from GuardianAgent (INTACT, AT_RISK, BROKEN)
        
        Replaces the dual-path architecture of evaluate() + _compute_components().
        """
        self.details = []  # Reset details log

        # 1. Map sector
        theme = self._map_sector_to_theme(stock.fundamentals.sector_name, stock.ticker)
        stock.fundamentals.sector_name = theme

        missing_fields = []
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

        # 2. Compute three independent axes
        quality_score, q_breakdown = self._score_quality_v13(stock.fundamentals)
        value_score, v_breakdown = self._score_value(stock)
        timing_score, t_breakdown = self._score_timing(stock.technicals, stock.beta, theme)

        # 3. Persona-weighted conviction
        weights = CONVICTION_WEIGHTS.get(persona, CONVICTION_WEIGHTS["CFA"])
        conviction = (
            quality_score * weights['Q'] +
            value_score * weights['V'] +
            timing_score * weights['T']
        )

        # 4. Gradient penalties (unified — replaces kill switches for most cases)
        modifications = []
        penalty_total, penalty_logs = self._compute_penalties(stock, persona)
        conviction -= penalty_total
        if penalty_logs:
            for p in penalty_logs:
                modifications.append(f"PENALTY ({p['type']}): -{p['severity']:.1f}pts — {p['detail']}")

        # 5. Data Fragility
        fragility = self._compute_data_fragility(stock)
        fragility_penalty = fragility.get('penalty', 0.0)
        if fragility_penalty > 0:
            conviction -= fragility_penalty
            modifications.append(f"DATA FRAGILITY: -{fragility_penalty:.0f}pts (Confidence: {fragility['confidence']})")
        for flag in fragility.get('fragility_flags', []):
            modifications.append(flag)

        # 6. Emergency brakes (only truly binary cases)
        # Altman Z < 1.8 = bankruptcy risk (stays absolute — not gradual)
        if stock.fundamentals.altman_z_score is not None and stock.fundamentals.altman_z_score < 1.8:
            if "Financial" not in theme:
                conviction = min(conviction, 20)
                modifications.append(f"KILL SWITCH (Distress): Altman Z-Score {stock.fundamentals.altman_z_score:.2f} < 1.8")

        # Financial sector: use ICR + leverage instead of Altman Z
        if "Financial" in theme:
            if stock.fundamentals.interest_coverage < 2.0 and stock.fundamentals.debt_to_equity > 8.0:
                conviction = min(conviction, 25)
                modifications.append("FINANCIAL DISTRESS: ICR < 2.0x + D/E > 8.0x")

        # 7. Guardian Integration (one-way: Guardian → Scoring)
        if guardian_status == "BROKEN":
            conviction = min(conviction, 40)
            modifications.append("⚠️ GUARDIAN: Thesis BROKEN — conviction capped at 40")
        elif guardian_status == "AT_RISK":
            conviction -= 10
            modifications.append("⚡ GUARDIAN: Thesis AT RISK — conviction -10pts")

        # Clamp
        conviction = round(max(0.0, min(100.0, conviction)), 1)
        quality_score = round(quality_score, 1)
        value_score = round(value_score, 1)
        timing_score = round(timing_score, 1)

        # 7. Rating & Narrative
        rating = self._get_rating(conviction)
        narrative = self._generate_narrative_v13(
            stock.ticker, conviction, quality_score, value_score, timing_score, persona, modifications
        )

        return ScoreResultV13(
            conviction_score=conviction,
            quality_axis=quality_score,
            value_axis=value_score,
            timing_axis=timing_score,
            rating=rating,
            verdict_narrative=narrative,
            quality_breakdown=q_breakdown,
            value_breakdown=v_breakdown,
            timing_breakdown=t_breakdown,
            modifications=modifications,
            penalties_applied=penalty_logs,
            missing_data=missing_fields,
            details=self.details,
            persona=persona,
            conviction_weights=weights,
            rim_result=v_breakdown.get('RIM Result'),
            fragility=fragility,
        )

    def _generate_narrative_v13(self, ticker, conviction, q, v, t, persona, mods) -> str:
        """Generates a verdict narrative referencing all three axes."""
        narrative = f"{ticker} is rated {self._get_rating(conviction)} ({conviction:.0f}/100) under {persona} lens. "

        q_label = 'elite' if q > 85 else 'strong' if q > 70 else 'fair' if q > 50 else 'weak'
        v_label = 'cheap' if v > 75 else 'fairly valued' if v > 50 else 'expensive' if v > 30 else 'very expensive'
        t_label = 'bullish' if t > 80 else 'supportive' if t > 60 else 'neutral' if t > 40 else 'bearish'

        narrative += f"Quality ({q:.0f}) is {q_label}, "
        narrative += f"Value ({v:.0f}) is {v_label}, "
        narrative += f"Timing ({t:.0f}) is {t_label}. "

        if mods:
            narrative += f"CAUTION: {len(mods)} Risk Factor(s) Triggered. "

        return narrative

    def _add_detail(self, category: str, metric: str, value: str, benchmark: str, score: float, max_score: float, status: str):
        self.details.append({
            "category": category,
            "metric": metric,
            "value": value,
            "benchmark": benchmark,
            "score": f"{score:.1f}/{max_score:.0f}" if score is not None else f"- /{max_score:.0f}",
            "status": status,
            "points": score
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
