"""
Unit Tests for VinSight Scorer v7.5 (Spectrum Scoring)
Tests individual scoring components to verify correctness.

v7.5 Key Features:
- Core Score (100 pts): Spectrum-based (Valuation, Profitability, Efficiency, Solvency, Growth, Conviction).
- Modifiers (Spectrum Penalties): Trend Penalty (0 to -15), Risk Penalty (0 to -15).
- Modifiers (Spectrum Bonuses): Income Safety (0 to +5), RSI (+/- 5).
- 10-Theme Benchmarking Mapping.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from services.vinsight_scorer import (
    VinSightScorer, StockData, Fundamentals, Technicals, Sentiment, Projections
)


class TestFundamentalsScoring:
    """Tests for _score_fundamentals_spectrum() method - v7.5: 100 pts total"""
    
    def setup_method(self):
        self.scorer = VinSightScorer()
    
    def test_excellent_fundamentals(self):
        """v7.5: Excellent across board should score near 100"""
        fundamentals = Fundamentals(
            pe_ratio=18.0,
            forward_pe=12.0,
            peg_ratio=0.8,
            profit_margin=0.25,
            operating_margin=0.30,
            roe=0.25,
            roa=0.15,
            debt_to_equity=0.3,
            current_ratio=2.5,
            earnings_growth_qoq=0.20,
            inst_ownership=85.0,
            fcf_yield=0.06,
            eps_surprise_pct=0.15,
            sector_name="Technology" # Maps to Mature Tech
        )
        scores = self.scorer._score_fundamentals_spectrum(fundamentals)
        total_f = sum(scores.values())
        # With spectrum, it should hit max points if above ideal benchmarks
        assert total_f == 100, f"Expected 100, got {total_f}"
    
    def test_moderate_fundamentals(self):
        """Moderate values should give mid-range score"""
        fundamentals = Fundamentals(
            pe_ratio=30.0,
            forward_pe=25.0,
            peg_ratio=1.5,
            profit_margin=0.10,
            operating_margin=0.12,
            roe=0.12,
            roa=0.04,
            debt_to_equity=1.0,
            current_ratio=1.2,
            earnings_growth_qoq=0.05,
            inst_ownership=50.0,
            fcf_yield=0.02,
            eps_surprise_pct=0.05,
            sector_name="Technology"
        )
        scores = self.scorer._score_fundamentals_spectrum(fundamentals)
        total_f = sum(scores.values())
        # Expected around 50-70 range
        assert 50 <= total_f <= 80, f"Expected ~65, got {total_f}"


class TestRiskGates:
    """Tests for Spectrum Modifiers - v7.5"""
    
    def setup_method(self):
        self.scorer = VinSightScorer()
    
    def test_trend_penalty_spectrum(self):
        """Price significantly below SMA200 should trigger max penalty (-15)"""
        technicals = Technicals(
            price=80.0,
            sma50=95.0,
            sma200=100.0, # Ratio 0.8 (Below zero cutoff 0.9)
            rsi=45.0,
            momentum_label="Bearish",
            volume_trend="Falling"
        )
        penalty = self.scorer._check_trend_gate(technicals)
        assert penalty == -15.0
        
    def test_trend_penalty_moderate(self):
        """Price slightly below SMA200 should trigger partial penalty"""
        technicals = Technicals(
            price=95.0,
            sma50=98.0,
            sma200=100.0, # Ratio 0.95 (Between Ideal 1.05 and Zero 0.90)
            rsi=45.0,
            momentum_label="Sideways",
            volume_trend="Neutral"
        )
        penalty = self.scorer._check_trend_gate(technicals)
        # Ratio 0.95: (0.95 - 0.90) / (0.15) = 1/3. Score = 5. Penalty = 5 - 15 = -10.
        assert penalty == -10.0
    
    def test_projection_penalty_spectrum(self):
        """High downside should trigger max penalty (-15)"""
        projections = Projections(
            monte_carlo_p50=100.0,
            monte_carlo_p90=120.0,
            monte_carlo_p10=70.0, # -30% downside (Below zero cutoff -25%)
            current_price=100.0
        )
        penalty = self.scorer._check_projection_gate(projections)
        assert penalty == -15.0


class TestFullScoreIntegration:
    """Integration tests for complete scoring v7.5"""
    
    def setup_method(self):
        self.scorer = VinSightScorer()
    
    def test_total_score_summation(self):
        """Verify pillars and gates sum correctly with granular breakdown"""
        test_data = StockData(
            ticker="NVDA",
            beta=1.5,
            dividend_yield=0.1,
            market_bull_regime=True,
            fundamentals=Fundamentals(
                pe_ratio=40.0, forward_pe=30.0, peg_ratio=1.0,
                profit_margin=0.40, operating_margin=0.45,
                roe=0.35, roa=0.20,
                debt_to_equity=0.3, current_ratio=2.0,
                earnings_growth_qoq=0.50, inst_ownership=80.0,
                fcf_yield=0.03, eps_surprise_pct=0.12,
                sector_name="Technology"
            ),
            technicals=Technicals(
                price=110.0, sma50=105.0, sma200=100.0, rsi=60.0,
                momentum_label="Bullish", volume_trend="Rising"
            ),
            sentiment=Sentiment("Positive", 0.4, 10),
            projections=Projections(150.0, 200.0, 105.0, 110.0) # Downside ~ -4.5% (Safe)
        )
        
        result = self.scorer.evaluate(test_data)
        
        # Fundamental components should be present
        assert "Valuation" in result.breakdown
        assert "Profitability" in result.breakdown
        assert result.breakdown["Valuation"] > 20
        # No penalties
        assert result.breakdown["Penalties"] == 0
        # Rating should be Strong Buy or Buy
        assert result.rating in ["Strong Buy", "Buy"]
    
    def test_income_bonus_spectrum(self):
        """Yield above 4% with low beta should trigger +5 bonus"""
        test_data = StockData(
            ticker="DIV",
            beta=0.7,
            dividend_yield=4.5, # Above ideal 4%
            market_bull_regime=True,
            fundamentals=Fundamentals(
                pe_ratio=15.0, forward_pe=12.0, peg_ratio=1.2,
                profit_margin=0.1, operating_margin=0.15,
                roe=0.1, roa=0.05,
                debt_to_equity=0.5, current_ratio=1.5,
                earnings_growth_qoq=0.05, inst_ownership=60.0,
                fcf_yield=0.04, eps_surprise_pct=0.02, # Fixed missing args
                sector_name="Consumer Defensive"
            ),
            technicals=Technicals(100, 100, 100, 50, "Neutral", "Neutral"),
            sentiment=Sentiment("Neutral", 0, 0),
            projections=Projections(100, 105, 98, 100) # -2% downside
        )
        result = self.scorer.evaluate(test_data)
        assert result.breakdown["Bonuses"] == 5.0


class TestRatingThresholds:
    """Test rating boundaries v7.5"""
    
    def setup_method(self):
        self.scorer = VinSightScorer()
    
    def test_rating_thresholds(self):
        assert self.scorer._get_rating(90) == "Strong Buy"
        assert self.scorer._get_rating(85) == "Strong Buy"
        assert self.scorer._get_rating(84) == "Buy"
        assert self.scorer._get_rating(70) == "Buy"
        assert self.scorer._get_rating(65) == "Hold"
        assert self.scorer._get_rating(50) == "Hold"
        assert self.scorer._get_rating(45) == "Sell"
        assert self.scorer._get_rating(0) == "Sell"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
