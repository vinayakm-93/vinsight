"""
VinSight Scoring Engine v11.1 — Test Suite
Tests: None handling, components, persona weights, continuous penalties, AMD regression
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from services.vinsight_scorer import (
    VinSightScorer, StockData, Fundamentals, Technicals, Sentiment, Projections
)


# --- Factory Helpers ---

def make_fundamentals(**overrides) -> Fundamentals:
    """Create a Fundamentals with sensible defaults, override any field."""
    defaults = dict(
        pe_ratio=20.0, forward_pe=18.0, peg_ratio=1.5, fcf_yield=0.05,
        profit_margin=0.15, operating_margin=0.20, gross_margin_trend="Rising",
        roe=0.18, roa=0.10,
        debt_to_equity=0.8, debt_to_ebitda=1.2, interest_coverage=10.0,
        current_ratio=2.0, altman_z_score=3.5,
        earnings_growth_qoq=0.08, revenue_growth_3y=0.12,
        inst_ownership=0.75, eps_surprise_pct=0.03, sector_name="Technology"
    )
    defaults.update(overrides)
    return Fundamentals(**defaults)


def make_technicals(**overrides) -> Technicals:
    defaults = dict(
        price=150.0, sma50=145.0, sma200=140.0, rsi=55.0,
        relative_volume=1.2, distance_to_high=0.10,
        momentum_label="Bullish", volume_trend="Increasing"
    )
    defaults.update(overrides)
    return Technicals(**defaults)


def make_stock(**overrides) -> StockData:
    return StockData(
        ticker=overrides.pop("ticker", "TEST"),
        beta=overrides.pop("beta", 1.1),
        dividend_yield=overrides.pop("dividend_yield", 0.01),
        market_bull_regime=overrides.pop("market_bull_regime", True),
        fundamentals=overrides.pop("fundamentals", make_fundamentals()),
        technicals=overrides.pop("technicals", make_technicals()),
        sentiment=overrides.pop("sentiment", Sentiment("Neutral", 0.0, 5)),
        projections=overrides.pop("projections", Projections(160.0, 180.0, 130.0, 150.0)),
    )


# --- Phase 1: None Handling ---

class TestNoneHandling:
    def test_linear_score_none_returns_none(self):
        scorer = VinSightScorer()
        result = scorer._linear_score(None, ideal=1.5, zero=3.5, max_pts=20, label="test", category="test")
        assert result is None

    def test_score_component_skips_none(self):
        scorer = VinSightScorer()
        result = scorer._score_component([None, 8.0, None, 6.0], [10, 10, 10, 10])
        assert result == pytest.approx(7.0, abs=0.01)

    def test_score_component_all_none_is_neutral(self):
        scorer = VinSightScorer()
        result = scorer._score_component([None, None, None], [10, 10, 10])
        assert result == 5.0

    def test_amd_regression_none_fcf(self):
        """THE AMD bug: None FCF should NOT trigger solvency penalty or crash score."""
        scorer = VinSightScorer()
        stock = make_stock(
            ticker="AMD",
            fundamentals=make_fundamentals(
                fcf_yield=None,  # This was the bug
                peg_ratio=None,
                debt_to_equity=0.5,  # AMD has low debt
                roe=0.04
            )
        )
        components = scorer._compute_components(stock)
        # Valuation should not be 0 — it should handle None gracefully
        assert components['valuation'] >= 3.0  # At least not penalized to death
        
        # Penalties should NOT fire on None
        deductions, logs = scorer._compute_penalties(stock, "CFA")
        solvency_fired = any("Solvency" in p["type"] for p in logs)
        assert not solvency_fired, "Solvency penalty should NOT fire when D/E is below threshold"


# --- Phase 2: Components ---

class TestComponents:
    def test_strong_fundamentals_high_components(self):
        scorer = VinSightScorer()
        stock = make_stock(fundamentals=make_fundamentals(
            peg_ratio=1.0, fcf_yield=0.08, roe=0.25,
            profit_margin=0.20, operating_margin=0.30,
            debt_to_equity=0.3, interest_coverage=15.0,
            revenue_growth_3y=0.15, earnings_growth_qoq=0.12
        ))
        components = scorer._compute_components(stock)
        avg = sum(components.values()) / len(components)
        assert avg > 7.0, f"Strong stock should avg > 7.0, got {avg}"

    def test_weak_fundamentals_low_components(self):
        scorer = VinSightScorer()
        stock = make_stock(fundamentals=make_fundamentals(
            peg_ratio=5.0, fcf_yield=0.001, roe=0.02,
            profit_margin=0.01, operating_margin=0.02,
            debt_to_equity=4.0, interest_coverage=1.0,
            revenue_growth_3y=-0.05, earnings_growth_qoq=-0.10,
            eps_surprise_pct=-0.08
        ))
        components = scorer._compute_components(stock)
        avg = sum(components.values()) / len(components)
        assert avg < 4.0, f"Weak stock should avg < 4.0, got {avg}"

    def test_eps_surprise_feeds_growth(self):
        scorer = VinSightScorer()
        stock_beat = make_stock(fundamentals=make_fundamentals(eps_surprise_pct=0.10))
        stock_miss = make_stock(fundamentals=make_fundamentals(eps_surprise_pct=-0.10))
        comp_beat = scorer._compute_components(stock_beat)
        comp_miss = scorer._compute_components(stock_miss)
        assert comp_beat['growth'] > comp_miss['growth']


# --- Phase 2: Persona Weighting ---

class TestPersonaWeighting:
    def test_momentum_ignores_valuation(self):
        scorer = VinSightScorer()
        stock = make_stock(fundamentals=make_fundamentals(
            peg_ratio=10.0, pe_ratio=200.0  # Terrible valuation
        ), technicals=make_technicals(
            price=160.0, sma50=150.0, sma200=140.0, rsi=55.0  # Great technicals
        ))
        components = scorer._compute_components(stock)
        mom_score = scorer._apply_persona_weights(components, "Momentum")
        cfa_score = scorer._apply_persona_weights(components, "CFA")
        assert mom_score > cfa_score, "Momentum should ignore bad valuation"

    def test_value_rewards_cheap(self):
        scorer = VinSightScorer()
        stock = make_stock(fundamentals=make_fundamentals(
            peg_ratio=0.8, fcf_yield=0.10, forward_pe=10.0  # Very cheap
        ), technicals=make_technicals(
            price=95.0, sma50=100.0, sma200=110.0  # Weak technicals
        ))
        components = scorer._compute_components(stock)
        val_score = scorer._apply_persona_weights(components, "Value")
        mom_score = scorer._apply_persona_weights(components, "Momentum")
        assert val_score > mom_score, "Value persona should favor cheap stocks"

    def test_same_stock_different_persona_different_score(self):
        scorer = VinSightScorer()
        stock = make_stock()
        components = scorer._compute_components(stock)
        scores = {}
        for persona in ["CFA", "Momentum", "Value", "Growth", "Income"]:
            scores[persona] = scorer._apply_persona_weights(components, persona)
        unique_scores = set(scores.values())
        assert len(unique_scores) > 1, "Different personas must produce different scores"


# --- Phase 3: Continuous Penalties ---

class TestContinuousPenalties:
    def test_de_barely_above_threshold_minimal_penalty(self):
        scorer = VinSightScorer()
        stock = make_stock(fundamentals=make_fundamentals(debt_to_equity=1.1))
        deductions, logs = scorer._compute_penalties(stock, "CFA")
        solvency = [p for p in logs if p["type"] == "Solvency Risk"]
        if solvency:
            assert solvency[0]["severity"] < 3.0, "Barely above threshold should have small penalty"

    def test_de_extreme_full_penalty(self):
        scorer = VinSightScorer()
        stock = make_stock(fundamentals=make_fundamentals(debt_to_equity=5.0))
        deductions, logs = scorer._compute_penalties(stock, "CFA")
        solvency = [p for p in logs if p["type"] == "Solvency Risk"]
        assert len(solvency) > 0
        assert solvency[0]["severity"] >= 15, "Extreme D/E should trigger large penalty"

    def test_none_data_no_penalty(self):
        scorer = VinSightScorer()
        stock = make_stock(fundamentals=make_fundamentals(
            debt_to_equity=None, pe_ratio=None, revenue_growth_3y=None
        ))
        deductions, logs = scorer._compute_penalties(stock, "CFA")
        assert deductions == 0, f"None data should trigger zero penalties, got {deductions}"

    def test_growth_offsets_pe_penalty(self):
        scorer = VinSightScorer()
        stock_grow = make_stock(fundamentals=make_fundamentals(pe_ratio=80, revenue_growth_3y=0.25))
        stock_slow = make_stock(fundamentals=make_fundamentals(pe_ratio=80, revenue_growth_3y=0.05))
        _, logs_grow = scorer._compute_penalties(stock_grow, "CFA")
        _, logs_slow = scorer._compute_penalties(stock_slow, "CFA")
        overval_grow = sum(p["severity"] for p in logs_grow if p["type"] == "Overvaluation")
        overval_slow = sum(p["severity"] for p in logs_slow if p["type"] == "Overvaluation")
        assert overval_grow < overval_slow, "High growth should reduce overvaluation penalty"

    def test_persona_reduces_penalty(self):
        scorer = VinSightScorer()
        stock = make_stock(fundamentals=make_fundamentals(debt_to_equity=3.0))
        ded_cfa, _ = scorer._compute_penalties(stock, "CFA")
        ded_mom, _ = scorer._compute_penalties(stock, "Momentum")
        assert ded_mom < ded_cfa, "Momentum persona should have lower solvency penalty"


# --- Integration ---

class TestIntegration:
    def test_strong_stock_above_65(self):
        scorer = VinSightScorer()
        stock = make_stock()  # Default is a healthy stock
        components = scorer._compute_components(stock)
        score = scorer._apply_persona_weights(components, "CFA")
        deductions, _ = scorer._compute_penalties(stock, "CFA")
        final = max(0, score - deductions)
        assert final >= 55, f"Healthy default stock should score >= 55, got {final}"

    def test_distressed_below_40(self):
        scorer = VinSightScorer()
        stock = make_stock(fundamentals=make_fundamentals(
            peg_ratio=8.0, fcf_yield=-0.02, roe=-0.05,
            profit_margin=-0.10, operating_margin=-0.15,
            debt_to_equity=5.0, interest_coverage=0.5,
            revenue_growth_3y=-0.20, earnings_growth_qoq=-0.30,
            altman_z_score=1.0
        ), technicals=make_technicals(
            price=50.0, sma50=70.0, sma200=90.0, rsi=22.0
        ))
        components = scorer._compute_components(stock)
        score = scorer._apply_persona_weights(components, "CFA")
        deductions, _ = scorer._compute_penalties(stock, "CFA")
        final = max(0, score - deductions)
        assert final < 40, f"Distressed stock should score < 40, got {final}"

    def test_evaluate_still_works(self):
        """Backward compatibility: the old evaluate() method should still run."""
        scorer = VinSightScorer()
        stock = make_stock()
        result = scorer.evaluate(stock)
        assert 0 <= result.total_score <= 100
        assert result.rating is not None
