from dataclasses import dataclass, field
from typing import Literal, Optional, List, Dict
import logging
import json
import os

# --- Data Structures ---

@dataclass
class Fundamentals:
    inst_ownership: float  # Percentage
    pe_ratio: float
    peg_ratio: float
    earnings_growth_qoq: float # Percentage
    profit_margin: float # 0.0-1.0
    debt_to_equity: float # Ratio
    fcf_yield: float # 0.0-1.0
    eps_surprise_pct: float # Percentage (e.g. 0.15 for 15%)
    
    # Cluster Data
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
    insider_activity: str

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

# --- Scoring Engine v6.3 ---

class VinSightScorer:
    VERSION = "v6.4"
    
    # v6.3 Weight Distribution (100 pts total)
    WEIGHT_FUNDAMENTALS = 70
    WEIGHT_SENTIMENT = 10
    WEIGHT_PROJECTIONS = 10
    WEIGHT_TECHNICALS = 10

    def __init__(self):
        self.sector_benchmarks, self.defaults = _load_sector_benchmarks()
        self.details = []

    def evaluate(self, stock: StockData) -> ScoreResult:
        self.details = [] # Reset details log
        
        # --- Phase 1: Macro Regime Filter ---
        is_defensive_mode = not stock.market_bull_regime
        high_beta = stock.beta > 1.5
        
        score_cap = 100
        if is_defensive_mode and high_beta:
            score_cap = 70
        
        # --- Phase 2: Core Score (100 Points) ---
        
        # A. Fundamentals (70 Points)
        f_score = self._score_fundamentals(stock.fundamentals)
        
        # B. Technicals (10 Points)
        t_score = self._score_technicals(stock.technicals)
        
        # C. Sentiment (10 Points)
        s_score = self._score_sentiment(stock.sentiment)
        
        # D. Projections (10 Points)
        p_score = self._score_projections(stock.projections)
        
        raw_score = f_score + t_score + s_score + p_score
        
        # --- Phase 3: Bonuses & Penalties ---
        bonuses = 0
        modifications = []
        
        # Safety Bonus
        safety_bonus_val = 15 if is_defensive_mode else 8
        if stock.dividend_yield > 2.5 and stock.beta < 0.8:
            bonuses += safety_bonus_val
            modifications.append(f"Safety Bonus (+{safety_bonus_val})")
            
        # Volatility Penalty
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
        
        return ScoreResult(final_score, rating, narrative, breakdown, modifications, self.details)

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
        Fundamentals: 7 Components * 10 Points = 70 Points Total
        """
        score = 0.0
        benchmarks = self._get_benchmarks(f.sector_name)
        
        peg_fair = benchmarks.get("peg_fair", 1.5)
        growth_strong = benchmarks.get("growth_strong", 0.10) # 10%
        pe_median = benchmarks.get("pe_median", 20)
        margin_healthy = benchmarks.get("margin_healthy", 0.12) # 12%
        debt_safe = benchmarks.get("debt_safe", 1.0)
        fcf_yield_strong = benchmarks.get("fcf_yield_strong", 0.05) # 5%
        eps_surprise_huge = benchmarks.get("eps_surprise_huge", 0.10) # 10%
        
        # 1. Valuation (10 pts)
        val_pts = 0.0
        val_status = "Neutral"
        val_display = f"PE: {f.pe_ratio:.1f}"
        if f.peg_ratio > 0:
            val_display = f"PEG: {f.peg_ratio:.2f}"
            if f.peg_ratio < 1.0:
                val_pts = 10.0
                val_status = "Undervalued"
            elif f.peg_ratio < peg_fair:
                val_pts = 7.5
                val_status = "Fair"
            elif f.peg_ratio < 2.5:
                val_pts = 5.0
                val_status = "Rich"
            else:
                val_pts = 0.0
                val_status = "Overvalued"
        elif f.pe_ratio > 0:
            if f.pe_ratio < pe_median:
                val_pts = 10.0
                val_status = "Undervalued"
            elif f.pe_ratio < pe_median * 1.5:
                val_pts = 5.0
                val_status = "Fair"
            else:
                val_pts = 0.0
                val_status = "Premium"
        else:
            val_pts = 5.0 # Neutral
            val_status = "No Data"
            
        score += val_pts
        self._add_detail("Fundamentals", "Valuation", val_display, f"PEG < 1.0", val_pts, 10, val_status)
        
        # 2. Earnings Growth (10 pts)
        gr_pts = 0.0
        gr_val = f.earnings_growth_qoq
        if gr_val > growth_strong: 
            gr_pts = 10.0
            gr_status = "Strong"
        elif gr_val > 0:
            gr_pts = 5.0
            gr_status = "Positive"
        else:
            gr_pts = 0.0
            gr_status = "Weak"
        score += gr_pts
        self._add_detail("Fundamentals", "Earnings Growth", f"{gr_val*100:.1f}%", f"> {growth_strong*100:.0f}%", gr_pts, 10, gr_status)
        
        # 3. Profit Margins (10 pts)
        mg_pts = 0.0
        mg_val = f.profit_margin
        # Use margin_healthy (e.g. 12%) as the baseline for "Healthy" (7.5pts)
        if mg_val > (margin_healthy * 1.2): # Relaxed from 1.5x (e.g. Tech 0.20->0.24)
            mg_pts = 10.0
            mg_status = "High Quality"
        elif mg_val > margin_healthy:
            mg_pts = 7.5
            mg_status = "Healthy"
        elif mg_val > 0:
            mg_pts = 5.0
            mg_status = "Positive"
        else:
            mg_pts = 0.0
            mg_status = "Negative"
        score += mg_pts
        self._add_detail("Fundamentals", "Profit Margin", f"{mg_val*100:.1f}%", f"> {margin_healthy*100:.0f}%", mg_pts, 10, mg_status)
        
        # 4. Debt Health (10 pts)
        db_pts = 0.0
        db_val = f.debt_to_equity
        # Use debt_safe (e.g. 1.0) as the baseline for "Safe" (7.5pts)
        if db_val < (debt_safe * 0.75): # Relaxed from 0.5x (e.g. Tech 0.5->0.375)
            db_pts = 10.0
            db_status = "Low Debt"
        elif db_val < debt_safe:
            db_pts = 7.5
            db_status = "Safe"
        elif db_val < (debt_safe * 2.0):
            db_pts = 2.5
            db_status = "Leveraged"
        else:
            db_pts = 0.0
            db_status = "High Debt"
        score += db_pts
        self._add_detail("Fundamentals", "Debt/Equity", f"{db_val:.2f}", f"< {debt_safe:.1f}", db_pts, 10, db_status)
        
        # 5. Cash Flow Strength (10 pts)
        cf_pts = 0.0
        cf_val = f.fcf_yield
        if cf_val > fcf_yield_strong: 
            cf_pts = 10.0
            cf_status = "Cash Cow"
        elif cf_val > (fcf_yield_strong * 0.6): # e.g. > 3%
            cf_pts = 7.5
            cf_status = "Strong"
        elif cf_val > 0:
            cf_pts = 5.0
            cf_status = "Positive"
        else:
            cf_pts = 0.0
            cf_status = "Weak/Neg"
        score += cf_pts
        self._add_detail("Fundamentals", "FCF Yield", f"{cf_val*100:.1f}%", f"> {fcf_yield_strong*100:.0f}%", cf_pts, 10, cf_status)
        
        # 6. Institutional Ownership (10 pts)
        io_pts = 0.0
        io_val = f.inst_ownership
        if io_val >= 70:
            io_pts = 10.0
            io_status = "High Conviction"
        elif io_val >= 50:
            io_pts = 7.5
            io_status = "Strong"
        elif io_val >= 20:
            io_pts = 5.0
            io_status = "Moderate"
        else:
            io_pts = 2.5
            io_status = "Low"
        score += io_pts
        self._add_detail("Fundamentals", "Inst. Ownership", f"{io_val:.1f}%", "> 70%", io_pts, 10, io_status)
        
        # 7. EPS Surprise (10 pts)
        eps_pts = 0.0
        eps_val = f.eps_surprise_pct
        if eps_val >= eps_surprise_huge:
            eps_pts = 10.0
            eps_status = "Huge Beat"
        elif eps_val > 0:
            eps_pts = 7.5
            eps_status = "Beat"
        elif eps_val > -0.05:
            eps_pts = 2.5
            eps_status = "In Line"
        else:
            eps_pts = 0.0
            eps_status = "Miss"
        score += eps_pts
        self._add_detail("Fundamentals", "EPS Surprise", f"{eps_val*100:.1f}%", f"> {eps_surprise_huge*100:.0f}%", eps_pts, 10, eps_status)
        
        return int(round(min(70, score)))

    def _score_technicals(self, t: Technicals) -> int:
        """
        Technicals: 10 Points Total.
        """
        score = 0.0
        
        # Trend (5 pts)
        trend_pts = 0.0
        trend_status = "Neutral"
        if t.sma50 > 0 and t.sma200 > 0:
            if t.price > t.sma50 and t.sma50 > t.sma200:
                trend_pts = 5.0
                trend_status = "Golden Cross"
            elif t.price > t.sma200:
                trend_pts = 3.0
                trend_status = "Uptrend"
            else:
                trend_pts = 0.0
                trend_status = "Downtrend"
        score += trend_pts
        self._add_detail("Technicals", "Trend", trend_status, "Golden Cross", trend_pts, 5, trend_status)
        
        # RSI (3 pts)
        rsi_pts = 0.0
        rsi = t.rsi
        if 40 <= rsi <= 70:
            rsi_pts = 3.0
            rsi_status = "Healthy"
        elif rsi < 30:
            rsi_pts = 2.0
            rsi_status = "Oversold"
        else:
            rsi_pts = 1.0
            rsi_status = "Weak/Overbought"
        score += rsi_pts
        self._add_detail("Technicals", "RSI", f"{rsi:.0f}", "40-70", rsi_pts, 3, rsi_status)
        
        # Volume (2 pts)
        vol_pts = 0.0
        if "Rising" in t.volume_trend and "Price Rising" in t.volume_trend:
            vol_pts = 2.0
            vol_status = "Strong"
        else:
            vol_pts = 1.0
            vol_status = "Weak"
        score += vol_pts
        self._add_detail("Technicals", "Volume", t.volume_trend, "Rising", vol_pts, 2, vol_status)
            
        return int(round(min(10, score)))

    def _score_sentiment(self, s: Sentiment, sentiment_score: float = 0.0) -> int:
        """
        Sentiment: 2 * 5 pts = 10 Points Total.
        """
        score = 0.0
        
        # News (5 pts)
        news_pts = 0.0
        raw = s.news_sentiment_score
        
        # v6.4 Update: Stricter Alignment with LLM Analysis
        # LLM uses -1 to 1 scale where > 0.5 is Strong Buy
        if raw > 0.4 or s.news_sentiment_label == "Positive":
            news_pts = 5.0
            news_status = "Positive"
        elif raw < -0.3 or s.news_sentiment_label == "Negative":
            news_pts = 0.0
            news_status = "Negative"
        else:
            news_pts = 2.5
            news_status = "Neutral"
        
        score += news_pts
        self._add_detail("Sentiment", "News", s.news_sentiment_label, "> 0.4", news_pts, 5, news_status)
        
        # Insiders (5 pts)
        ins_pts = 0.0
        if s.insider_activity == "Net Buying":
            ins_pts = 5.0
        elif s.insider_activity == "Heavy Selling":
            ins_pts = 0.0
        else:
            ins_pts = 2.5
        score += ins_pts
        self._add_detail("Sentiment", "Insiders", s.insider_activity, "Net Buying", ins_pts, 5, s.insider_activity)
            
        return int(round(min(10, score)))

    def _score_projections(self, p: Projections) -> int:
        """
        Projections: 2 * 5 pts = 10 Points Total.
        """
        score = 0.0

        if p.current_price is None or p.current_price <= 0:
            return 5 

        # Upside (5 pts)
        up_pts = 0.0
        upside_pct = ((p.monte_carlo_p50 - p.current_price) / p.current_price) * 100
        if upside_pct >= 20:
            up_pts = 5.0
            up_status = "High Upside"
        elif upside_pct >= 10:
            up_pts = 3.0
            up_status = "Moderate"
        else:
            up_pts = 1.0
            up_status = "Low"
        score += up_pts
        self._add_detail("Projections", "AI Upside", f"{upside_pct:.1f}%", "> 20%", up_pts, 5, up_status)

        # Risk/Reward (5 pts)
        rr_pts = 0.0
        upside_diff = max(0, p.monte_carlo_p90 - p.current_price)
        downside_diff = max(0.01, p.current_price - p.monte_carlo_p10)
        ratio = upside_diff / downside_diff
        
        if ratio >= 3.0:
            rr_pts = 5.0
            rr_status = "Excellent"
        elif ratio >= 2.0:
            rr_pts = 3.0
            rr_status = "Good"
        else:
            rr_pts = 1.0
            rr_status = "Poor"
        score += rr_pts
        self._add_detail("Projections", "Risk/Reward", f"{ratio:.1f}x", "> 3.0x", rr_pts, 5, rr_status)

        return int(round(min(10, score)))

    def _get_rating(self, score: int) -> str:
        if score >= 80: return "Strong Buy"
        elif score >= 65: return "Buy"
        elif score >= 45: return "Hold"
        else: return "Sell"

    def _generate_narrative(self, ticker, final, f, t, s, p, mods, defensive) -> str:
        narrative = f"{ticker} is rated {self._get_rating(final)} ({final}/100). "
        if defensive:
             narrative += "Defensive Mode is ACTIVE. "
        
        # Simple highlight
        narrative += f"Fundamentals score is {f}/70. "
        if f > 50:
            narrative += "Company fundamentals are very strong. "
        return narrative

    def print_report(self, stock: StockData, result: ScoreResult):
        print(f"\n--- VinSight v6.3 Analysis: {stock.ticker} ---")
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
            sector_name="Technology",
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
            news_sentiment_score=0.35,
            news_article_count=10,
            insider_activity="Net Buying"
        ),
        projections=Projections(
            monte_carlo_p50=118.0,
            monte_carlo_p90=135.0,
            monte_carlo_p10=98.0,
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
