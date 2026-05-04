"""
VinSight v13 Backtesting Engine
================================
Score stocks at historical monthly snapshots and measure forward returns.

Strategy:
- Use current fundamentals (change slowly) + historical prices (reconstruct technicals)
- Measure forward 3mo/6mo/12mo returns vs SPY
- Compute hit rate: % of high-conviction stocks that outperformed SPY

Known limitations:
- Survivorship bias: Only currently-listed stocks are tested
- Fundamentals are point-in-time (current), not truly historical
- Monte Carlo / sentiment unavailable historically → neutral defaults used

Usage:
    from services.backtest import Backtester
    bt = Backtester()
    results = bt.run(tickers=["AAPL", "MSFT", ...], lookback_months=12)
    report = bt.analyze(results)
"""

import logging
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
import statistics

logger = logging.getLogger(__name__)


# --- Data Structures ---

@dataclass
class SnapshotResult:
    """Single stock scored at a single date."""
    ticker: str
    snapshot_date: str           # YYYY-MM-DD
    persona: str
    conviction_score: float
    quality_axis: float
    value_axis: float
    timing_axis: float
    rating: str
    price_at_snapshot: float
    # Forward returns (filled after forward prices are known)
    forward_return_3mo: Optional[float] = None
    forward_return_6mo: Optional[float] = None
    forward_return_12mo: Optional[float] = None
    # SPY benchmark returns for same periods
    spy_return_3mo: Optional[float] = None
    spy_return_6mo: Optional[float] = None
    spy_return_12mo: Optional[float] = None
    # Excess returns (stock - SPY)
    excess_3mo: Optional[float] = None
    excess_6mo: Optional[float] = None
    excess_12mo: Optional[float] = None
    modifications: List[str] = field(default_factory=list)


@dataclass
class TierMetrics:
    """Aggregate metrics for a score tier (e.g., 80-100)."""
    tier_label: str
    tier_range: Tuple[int, int]
    count: int
    mean_conviction: float
    mean_excess_3mo: Optional[float] = None
    mean_excess_6mo: Optional[float] = None
    mean_excess_12mo: Optional[float] = None
    hit_rate_3mo: Optional[float] = None   # % that outperformed SPY
    hit_rate_6mo: Optional[float] = None
    hit_rate_12mo: Optional[float] = None
    win_loss_ratio: Optional[float] = None


@dataclass
class BacktestReport:
    """Full backtest results."""
    run_date: str
    lookback_months: int
    tickers_count: int
    snapshots_count: int
    persona: str
    tier_metrics: List[TierMetrics] = field(default_factory=list)
    overall_hit_rate_3mo: Optional[float] = None
    overall_hit_rate_6mo: Optional[float] = None
    overall_hit_rate_12mo: Optional[float] = None
    score_stability: Optional[float] = None  # Avg month-to-month score change
    axis_correlation: Dict = field(default_factory=dict)
    raw_results: List[SnapshotResult] = field(default_factory=list)


# --- Score Tiers ---

SCORE_TIERS = [
    ("Elite (80-100)", (80, 100)),
    ("Strong (70-79)", (70, 79)),
    ("Moderate (60-69)", (60, 69)),
    ("Weak (50-59)", (50, 59)),
    ("Avoid (0-49)", (0, 49)),
]


class Backtester:
    """
    Backtests the v13 scoring engine by:
    1. Fetching historical price data for each ticker
    2. Reconstructing Technicals at each monthly snapshot
    3. Running evaluate_v13() with current fundamentals + historical technicals
    4. Measuring forward returns vs SPY
    """

    def __init__(self):
        from services.vinsight_scorer import VinSightScorer
        self.scorer = VinSightScorer()

    def run(
        self,
        tickers: List[str],
        lookback_months: int = 12,
        persona: str = "CFA",
        end_date: Optional[str] = None,
    ) -> List[SnapshotResult]:
        """
        Run the backtest for a list of tickers.
        
        Args:
            tickers: Stock symbols to backtest
            lookback_months: How many months back to start scoring
            persona: Investor persona for scoring
            end_date: End date (YYYY-MM-DD), defaults to today
            
        Returns:
            List of SnapshotResult with scores and forward returns
        """
        import yfinance as yf
        import numpy as np

        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        else:
            end_dt = datetime.now()

        # We need data from (lookback + 12mo forward) to compute 12mo forward returns
        start_dt = end_dt - timedelta(days=(lookback_months + 13) * 31)

        # Generate monthly snapshot dates
        snapshot_dates = []
        for m in range(lookback_months, 0, -1):
            dt = end_dt - timedelta(days=m * 30)
            snapshot_dates.append(dt)

        logger.info(f"Backtester: {len(tickers)} tickers × {len(snapshot_dates)} snapshots = {len(tickers) * len(snapshot_dates)} evaluations")

        # 1. Fetch all price histories in batch
        all_tickers = tickers + ["SPY"]
        price_cache = self._fetch_prices(all_tickers, start_dt, end_dt + timedelta(days=30))

        if "SPY" not in price_cache or price_cache["SPY"].empty:
            logger.error("Backtester: Cannot proceed without SPY data")
            return []

        spy_prices = price_cache["SPY"]

        # 2. Fetch current fundamentals for each ticker (used as proxy)
        fundamentals_cache = {}
        for ticker in tickers:
            try:
                fund_data = self._fetch_fundamentals(ticker)
                if fund_data:
                    fundamentals_cache[ticker] = fund_data
            except Exception as e:
                logger.warning(f"Backtester: Failed to fetch fundamentals for {ticker}: {e}")

        logger.info(f"Backtester: Fetched fundamentals for {len(fundamentals_cache)}/{len(tickers)} tickers")

        # 3. Score each ticker at each snapshot date
        results = []
        for ticker in tickers:
            if ticker not in fundamentals_cache:
                continue
            if ticker not in price_cache or price_cache[ticker].empty:
                continue

            ticker_prices = price_cache[ticker]

            for snap_date in snapshot_dates:
                try:
                    result = self._score_at_date(
                        ticker, snap_date, ticker_prices, spy_prices,
                        fundamentals_cache[ticker], persona
                    )
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.debug(f"Backtester: Skip {ticker} @ {snap_date.strftime('%Y-%m-%d')}: {e}")

        logger.info(f"Backtester: Generated {len(results)} snapshot results")
        return results

    def _fetch_prices(self, tickers: List[str], start: datetime, end: datetime) -> Dict:
        """Fetch historical price data for all tickers."""
        import yfinance as yf

        price_cache = {}
        # Batch download for efficiency
        try:
            data = yf.download(
                " ".join(tickers),
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                group_by="ticker",
                progress=False,
                auto_adjust=True,
            )
            for ticker in tickers:
                try:
                    if len(tickers) == 1:
                        ticker_data = data
                    else:
                        ticker_data = data[ticker] if ticker in data.columns.get_level_values(0) else None
                    if ticker_data is not None and not ticker_data.empty:
                        # Drop NaN rows
                        ticker_data = ticker_data.dropna(subset=["Close"])
                        price_cache[ticker] = ticker_data
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Backtester: Batch download failed: {e}")

        return price_cache

    def _fetch_fundamentals(self, ticker: str) -> Optional[Dict]:
        """Fetch current fundamentals for a ticker using yfinance."""
        import yfinance as yf

        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            if not info or "currentPrice" not in info:
                return None

            return {
                "pe_ratio": info.get("trailingPE", 20.0),
                "forward_pe": info.get("forwardPE", 18.0),
                "peg_ratio": info.get("pegRatio"),
                "profit_margin": info.get("profitMargins", 0.10),
                "operating_margin": info.get("operatingMargins", 0.15),
                "roe": info.get("returnOnEquity", 0.12),
                "roa": info.get("returnOnAssets", 0.06),
                "debt_to_equity": info.get("debtToEquity", 50.0) / 100.0 if info.get("debtToEquity") else 0.5,
                "current_ratio": info.get("currentRatio", 1.5),
                "earnings_growth_qoq": info.get("earningsGrowth", 0.05),
                "revenue_growth_3y": info.get("revenueGrowth"),
                "inst_ownership": (info.get("heldPercentInstitutions", 0.70) or 0.70) * 100,
                "fcf_yield": info.get("freeCashflow", 0) / info.get("marketCap", 1) if info.get("marketCap") else 0.03,
                "eps_surprise_pct": 0.05,  # Not available historically
                "sector_name": info.get("sector", "Technology"),
                "gross_margin_trend": "Flat",  # Cannot determine historically
                "debt_to_ebitda": info.get("totalDebt", 0) / max(info.get("ebitda", 1), 1) if info.get("ebitda") else 3.0,
                "interest_coverage": info.get("ebitda", 0) / max(info.get("interestExpense", 1) or 1, 1) if info.get("interestExpense") else 10.0,
                "altman_z_score": None,  # Complex — use None to skip
                "nopat": info.get("netIncomeToCommon"),
                "invested_capital": info.get("totalAssets"),
                "wacc": 0.10,
                "trailing_eps": [],  # Not available in batch
                "book_value_per_share": info.get("bookValue"),
                "shares_outstanding": info.get("sharesOutstanding"),
                "forward_roe": info.get("returnOnEquity"),
                "market_cap": info.get("marketCap"),
                "payout_ratio": info.get("payoutRatio"),
                "beta": info.get("beta", 1.0),
                "dividend_yield": (info.get("dividendYield") or 0) * 100,
                "price_to_book": info.get("priceToBook"),
                "ev_to_ebitda": info.get("enterpriseToEbitda"),
                "fifty_two_week_change": info.get("52WeekChange"),
                "held_percent_insiders": info.get("heldPercentInsiders"),
                "short_ratio": info.get("shortRatio"),
            }
        except Exception as e:
            logger.warning(f"Backtester: Fundamentals fetch failed for {ticker}: {e}")
            return None

    def _score_at_date(
        self,
        ticker: str,
        snap_date: datetime,
        ticker_prices,  # DataFrame
        spy_prices,     # DataFrame
        fund_data: Dict,
        persona: str,
    ) -> Optional[SnapshotResult]:
        """Score a stock at a specific historical date and compute forward returns."""
        from services.vinsight_scorer import StockData, Fundamentals, Technicals, Sentiment, Projections
        import numpy as np

        # Find closest trading day to snapshot date
        snap_str = snap_date.strftime("%Y-%m-%d")
        available_dates = ticker_prices.index
        close_dates = available_dates[available_dates <= snap_str]
        if len(close_dates) < 200:
            return None  # Not enough history for SMA200

        snap_idx = close_dates[-1]
        price_at_snap = float(ticker_prices.loc[snap_idx, "Close"])

        # Reconstruct technicals from historical prices
        close_series = ticker_prices["Close"]
        idx_pos = available_dates.get_loc(snap_idx)

        # SMA50 and SMA200
        if idx_pos < 200:
            return None
        sma50 = float(close_series.iloc[max(0, idx_pos - 49):idx_pos + 1].mean())
        sma200 = float(close_series.iloc[max(0, idx_pos - 199):idx_pos + 1].mean())

        # RSI (14-day)
        window = close_series.iloc[max(0, idx_pos - 14):idx_pos + 1]
        deltas = window.diff().dropna()
        gains = deltas.where(deltas > 0, 0).mean()
        losses = (-deltas.where(deltas < 0, 0)).mean()
        rs = gains / losses if losses != 0 else 100
        rsi = float(100 - (100 / (1 + rs)))

        # Relative volume (20-day avg)
        if "Volume" in ticker_prices.columns:
            vol_window = ticker_prices["Volume"].iloc[max(0, idx_pos - 19):idx_pos + 1]
            avg_vol = vol_window.mean()
            current_vol = ticker_prices["Volume"].iloc[idx_pos]
            relative_volume = float(current_vol / avg_vol) if avg_vol > 0 else 1.0
        else:
            relative_volume = 1.0

        # 52-week high distance
        high_52w = float(close_series.iloc[max(0, idx_pos - 252):idx_pos + 1].max())
        distance_to_high = (high_52w - price_at_snap) / high_52w if high_52w > 0 else 0

        # Momentum label
        momentum_label = "Bullish" if price_at_snap > sma200 else "Bearish"
        volume_trend = "Rising" if relative_volume > 1.0 else "Falling"

        # Build StockData
        fundamentals = Fundamentals(
            pe_ratio=fund_data.get("pe_ratio", 20.0),
            forward_pe=fund_data.get("forward_pe", 18.0),
            peg_ratio=fund_data.get("peg_ratio"),
            profit_margin=fund_data.get("profit_margin", 0.10),
            operating_margin=fund_data.get("operating_margin", 0.15),
            roe=fund_data.get("roe", 0.12),
            roa=fund_data.get("roa", 0.06),
            debt_to_equity=fund_data.get("debt_to_equity", 0.5),
            current_ratio=fund_data.get("current_ratio", 1.5),
            earnings_growth_qoq=fund_data.get("earnings_growth_qoq", 0.05),
            revenue_growth_3y=fund_data.get("revenue_growth_3y"),
            inst_ownership=fund_data.get("inst_ownership", 70.0),
            fcf_yield=fund_data.get("fcf_yield", 0.03),
            eps_surprise_pct=fund_data.get("eps_surprise_pct", 0.05),
            sector_name=fund_data.get("sector_name", "Technology"),
            gross_margin_trend=fund_data.get("gross_margin_trend", "Flat"),
            debt_to_ebitda=fund_data.get("debt_to_ebitda", 3.0),
            interest_coverage=fund_data.get("interest_coverage", 10.0),
            altman_z_score=fund_data.get("altman_z_score"),
            nopat=fund_data.get("nopat"),
            invested_capital=fund_data.get("invested_capital"),
            wacc=fund_data.get("wacc", 0.10),
            trailing_eps=fund_data.get("trailing_eps", []),
            book_value_per_share=fund_data.get("book_value_per_share"),
            shares_outstanding=fund_data.get("shares_outstanding"),
            forward_roe=fund_data.get("forward_roe"),
            market_cap=fund_data.get("market_cap"),
            payout_ratio=fund_data.get("payout_ratio"),
            price_to_book=fund_data.get("price_to_book"),
            ev_to_ebitda=fund_data.get("ev_to_ebitda"),
            fifty_two_week_change=fund_data.get("fifty_two_week_change"),
            held_percent_insiders=fund_data.get("held_percent_insiders"),
            short_ratio=fund_data.get("short_ratio"),
        )

        technicals = Technicals(
            price=price_at_snap,
            sma50=sma50,
            sma200=sma200,
            rsi=rsi,
            relative_volume=relative_volume,
            distance_to_high=distance_to_high,
            momentum_label=momentum_label,
            volume_trend=volume_trend,
        )

        sentiment = Sentiment(
            news_sentiment_label="Neutral",
            news_sentiment_score=0.0,
            news_article_count=0,
        )

        projections = Projections(
            monte_carlo_p50=price_at_snap * 1.10,
            monte_carlo_p90=price_at_snap * 1.30,
            monte_carlo_p10=price_at_snap * 0.85,
            current_price=price_at_snap,
        )

        stock = StockData(
            ticker=ticker,
            beta=fund_data.get("beta", 1.0),
            dividend_yield=fund_data.get("dividend_yield", 0.0),
            market_bull_regime=True,  # Can't determine historically — default bullish
            fundamentals=fundamentals,
            technicals=technicals,
            sentiment=sentiment,
            projections=projections,
        )

        # Run v13 scorer
        v13 = self.scorer.evaluate_v13(stock, persona)

        # Compute forward returns
        forward_3mo = self._get_forward_return(ticker_prices, snap_idx, 63)   # ~3 months
        forward_6mo = self._get_forward_return(ticker_prices, snap_idx, 126)  # ~6 months
        forward_12mo = self._get_forward_return(ticker_prices, snap_idx, 252) # ~12 months

        spy_3mo = self._get_forward_return(spy_prices, snap_idx, 63)
        spy_6mo = self._get_forward_return(spy_prices, snap_idx, 126)
        spy_12mo = self._get_forward_return(spy_prices, snap_idx, 252)

        return SnapshotResult(
            ticker=ticker,
            snapshot_date=snap_idx.strftime("%Y-%m-%d"),
            persona=persona,
            conviction_score=v13.conviction_score,
            quality_axis=v13.quality_axis,
            value_axis=v13.value_axis,
            timing_axis=v13.timing_axis,
            rating=v13.rating,
            price_at_snapshot=price_at_snap,
            forward_return_3mo=forward_3mo,
            forward_return_6mo=forward_6mo,
            forward_return_12mo=forward_12mo,
            spy_return_3mo=spy_3mo,
            spy_return_6mo=spy_6mo,
            spy_return_12mo=spy_12mo,
            excess_3mo=round(forward_3mo - spy_3mo, 4) if forward_3mo is not None and spy_3mo is not None else None,
            excess_6mo=round(forward_6mo - spy_6mo, 4) if forward_6mo is not None and spy_6mo is not None else None,
            excess_12mo=round(forward_12mo - spy_12mo, 4) if forward_12mo is not None and spy_12mo is not None else None,
            modifications=v13.modifications,
        )

    def _get_forward_return(self, prices_df, from_date, trading_days: int) -> Optional[float]:
        """Calculate forward return from a date, N trading days ahead."""
        try:
            available = prices_df.index
            from_pos = available.get_loc(from_date)
            target_pos = from_pos + trading_days
            if target_pos >= len(available):
                return None
            from_price = float(prices_df.iloc[from_pos]["Close"])
            target_price = float(prices_df.iloc[target_pos]["Close"])
            return round((target_price - from_price) / from_price, 4)
        except Exception:
            return None

    def analyze(self, results: List[SnapshotResult]) -> BacktestReport:
        """
        Analyze backtest results into a structured report with tier metrics.
        """
        if not results:
            return BacktestReport(
                run_date=datetime.now().strftime("%Y-%m-%d"),
                lookback_months=0,
                tickers_count=0,
                snapshots_count=0,
                persona="CFA",
            )

        persona = results[0].persona
        tickers = set(r.ticker for r in results)
        
        # Compute lookback from date range
        dates = sorted(set(r.snapshot_date for r in results))
        if len(dates) >= 2:
            first = datetime.strptime(dates[0], "%Y-%m-%d")
            last = datetime.strptime(dates[-1], "%Y-%m-%d")
            lookback_months = max(1, int((last - first).days / 30))
        else:
            lookback_months = 1

        # Tier analysis
        tier_metrics = []
        for label, (low, high) in SCORE_TIERS:
            tier_results = [r for r in results if low <= r.conviction_score <= high]
            if not tier_results:
                tier_metrics.append(TierMetrics(
                    tier_label=label, tier_range=(low, high), count=0, mean_conviction=0
                ))
                continue

            # Mean conviction
            mean_conv = statistics.mean(r.conviction_score for r in tier_results)

            # Excess returns
            excess_3 = [r.excess_3mo for r in tier_results if r.excess_3mo is not None]
            excess_6 = [r.excess_6mo for r in tier_results if r.excess_6mo is not None]
            excess_12 = [r.excess_12mo for r in tier_results if r.excess_12mo is not None]

            # Hit rates (% that outperformed SPY)
            hit_3 = len([e for e in excess_3 if e > 0]) / len(excess_3) if excess_3 else None
            hit_6 = len([e for e in excess_6 if e > 0]) / len(excess_6) if excess_6 else None
            hit_12 = len([e for e in excess_12 if e > 0]) / len(excess_12) if excess_12 else None

            tier_metrics.append(TierMetrics(
                tier_label=label,
                tier_range=(low, high),
                count=len(tier_results),
                mean_conviction=round(mean_conv, 1),
                mean_excess_3mo=round(statistics.mean(excess_3), 4) if excess_3 else None,
                mean_excess_6mo=round(statistics.mean(excess_6), 4) if excess_6 else None,
                mean_excess_12mo=round(statistics.mean(excess_12), 4) if excess_12 else None,
                hit_rate_3mo=round(hit_3, 3) if hit_3 is not None else None,
                hit_rate_6mo=round(hit_6, 3) if hit_6 is not None else None,
                hit_rate_12mo=round(hit_12, 3) if hit_12 is not None else None,
            ))

        # Overall hit rates (all tiers combined, weighted by interest in 80+)
        all_excess_3 = [r.excess_3mo for r in results if r.excess_3mo is not None]
        all_excess_6 = [r.excess_6mo for r in results if r.excess_6mo is not None]
        all_excess_12 = [r.excess_12mo for r in results if r.excess_12mo is not None]

        overall_hit_3 = len([e for e in all_excess_3 if e > 0]) / len(all_excess_3) if all_excess_3 else None
        overall_hit_6 = len([e for e in all_excess_6 if e > 0]) / len(all_excess_6) if all_excess_6 else None
        overall_hit_12 = len([e for e in all_excess_12 if e > 0]) / len(all_excess_12) if all_excess_12 else None

        # Score stability (how much does a ticker's score change month-to-month)
        stability_deltas = []
        for ticker in tickers:
            ticker_scores = sorted(
                [(r.snapshot_date, r.conviction_score) for r in results if r.ticker == ticker],
                key=lambda x: x[0]
            )
            for i in range(1, len(ticker_scores)):
                delta = abs(ticker_scores[i][1] - ticker_scores[i - 1][1])
                stability_deltas.append(delta)

        score_stability = round(statistics.mean(stability_deltas), 1) if stability_deltas else None

        # Axis correlation (do high-Quality stocks also tend to be high-Value?)
        quality_scores = [r.quality_axis for r in results]
        value_scores = [r.value_axis for r in results]
        timing_scores = [r.timing_axis for r in results]

        def _pearson(x, y):
            n = len(x)
            if n < 3:
                return 0
            mx, my = statistics.mean(x), statistics.mean(y)
            sx = statistics.stdev(x) if n > 1 else 1
            sy = statistics.stdev(y) if n > 1 else 1
            if sx == 0 or sy == 0:
                return 0
            return round(sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / ((n - 1) * sx * sy), 3)

        axis_correlation = {
            "quality_value": _pearson(quality_scores, value_scores),
            "quality_timing": _pearson(quality_scores, timing_scores),
            "value_timing": _pearson(value_scores, timing_scores),
        }

        return BacktestReport(
            run_date=datetime.now().strftime("%Y-%m-%d"),
            lookback_months=lookback_months,
            tickers_count=len(tickers),
            snapshots_count=len(results),
            persona=persona,
            tier_metrics=tier_metrics,
            overall_hit_rate_3mo=round(overall_hit_3, 3) if overall_hit_3 is not None else None,
            overall_hit_rate_6mo=round(overall_hit_6, 3) if overall_hit_6 is not None else None,
            overall_hit_rate_12mo=round(overall_hit_12, 3) if overall_hit_12 is not None else None,
            score_stability=score_stability,
            axis_correlation=axis_correlation,
            raw_results=results,
        )

    def generate_report_text(self, report: BacktestReport) -> str:
        """Generate a human-readable backtest report."""
        lines = [
            "=" * 65,
            "  VINSIGHT v13 BACKTEST REPORT",
            "=" * 65,
            f"  Run Date:       {report.run_date}",
            f"  Persona:        {report.persona}",
            f"  Lookback:       {report.lookback_months} months",
            f"  Tickers:        {report.tickers_count}",
            f"  Total Snapshots: {report.snapshots_count}",
            f"  Score Stability: {report.score_stability}pts avg monthly change" if report.score_stability else "",
            "",
            "-" * 65,
            "  TIER ANALYSIS",
            "-" * 65,
            f"  {'Tier':<22} {'Count':>6} {'Avg Score':>10} {'Hit 3mo':>8} {'Hit 6mo':>8} {'Hit 12mo':>9} {'Excess 3mo':>11}",
            "-" * 65,
        ]

        for t in report.tier_metrics:
            hit3 = f"{t.hit_rate_3mo:.0%}" if t.hit_rate_3mo is not None else "N/A"
            hit6 = f"{t.hit_rate_6mo:.0%}" if t.hit_rate_6mo is not None else "N/A"
            hit12 = f"{t.hit_rate_12mo:.0%}" if t.hit_rate_12mo is not None else "N/A"
            ex3 = f"{t.mean_excess_3mo:+.1%}" if t.mean_excess_3mo is not None else "N/A"
            lines.append(
                f"  {t.tier_label:<22} {t.count:>6} {t.mean_conviction:>10.1f} {hit3:>8} {hit6:>8} {hit12:>9} {ex3:>11}"
            )

        lines.extend([
            "",
            "-" * 65,
            "  OVERALL HIT RATES (all stocks that outperformed SPY)",
            "-" * 65,
            f"  3-month:  {report.overall_hit_rate_3mo:.1%}" if report.overall_hit_rate_3mo else "  3-month:  N/A",
            f"  6-month:  {report.overall_hit_rate_6mo:.1%}" if report.overall_hit_rate_6mo else "  6-month:  N/A",
            f"  12-month: {report.overall_hit_rate_12mo:.1%}" if report.overall_hit_rate_12mo else "  12-month: N/A",
            "",
            "-" * 65,
            "  AXIS INDEPENDENCE (Pearson correlation)",
            "-" * 65,
            f"  Quality ↔ Value:  {report.axis_correlation.get('quality_value', 'N/A')}",
            f"  Quality ↔ Timing: {report.axis_correlation.get('quality_timing', 'N/A')}",
            f"  Value ↔ Timing:   {report.axis_correlation.get('value_timing', 'N/A')}",
            "",
            "=" * 65,
            "  ⚠ LIMITATIONS",
            "  • Survivorship bias (only currently-listed stocks)",
            "  • Fundamentals are point-in-time (current), not truly historical",
            "  • Sentiment/Monte Carlo unavailable historically",
            "=" * 65,
        ])

        return "\n".join(lines)


# --- Convenience: S&P 500 Top 50 for quick testing ---

SP500_TOP50 = [
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "BRK-B", "LLY", "AVGO", "JPM",
    "TSLA", "UNH", "XOM", "V", "MA", "PG", "COST", "JNJ", "HD", "ABBV",
    "MRK", "WMT", "BAC", "KO", "PEP", "NFLX", "AMD", "CRM", "TMO", "ADBE",
    "LIN", "ORCL", "ACN", "CSCO", "ABT", "PM", "MCD", "DHR", "TXN", "QCOM",
    "NEE", "INTC", "LOW", "UNP", "GE", "CAT", "IBM", "PFE", "RTX", "AMGN",
]
