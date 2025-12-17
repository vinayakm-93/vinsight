"""
Unit Tests for VinSight Scorer v6.0
Tests individual scoring components to verify correctness.

v6.0 Weight Distribution:
- Fundamentals: 55 pts
- Technicals: 15 pts
- Sentiment: 15 pts
- Projections: 15 pts
"""
import sys
sys.path.insert(0, '.')

import pytest
from services.vinsight_scorer import (
    VinSightScorer, StockData, Fundamentals, Technicals, Sentiment, Projections
)


class TestSentimentScoring:
    """Tests for _score_sentiment() method - v6.0: 15 pts total (News 7 + Insider 8)"""
    
    def setup_method(self):
        self.scorer = VinSightScorer()
    
    def test_positive_news_net_buying_gives_max_score(self):
        """v6.0: Positive news (7) + Net Buying (8) = 15 points"""
        sentiment = Sentiment(
            news_sentiment_label="Positive",
            news_volume_high=True,
            insider_activity="Net Buying"
        )
        score = self.scorer._score_sentiment(sentiment)
        assert score == 15, f"Expected 15, got {score}"
    
    def test_neutral_news_net_buying(self):
        """v6.0: Neutral news (3.5) + Net Buying (8) = 11-12 points"""
        sentiment = Sentiment(
            news_sentiment_label="Neutral",
            news_volume_high=False,
            insider_activity="Net Buying"
        )
        score = self.scorer._score_sentiment(sentiment)
        assert 11 <= score <= 12, f"Expected 11-12, got {score}"
    
    def test_negative_news_net_buying(self):
        """v6.0: Negative news (1) + Net Buying (8) = 9 points"""
        sentiment = Sentiment(
            news_sentiment_label="Negative",
            news_volume_high=False,
            insider_activity="Net Buying"
        )
        score = self.scorer._score_sentiment(sentiment)
        assert score == 9, f"Expected 9, got {score}"
    
    def test_positive_news_cluster_selling(self):
        """v6.0: Positive news (6-7) + Cluster Selling (0.5) = 6-8 points"""
        sentiment = Sentiment(
            news_sentiment_label="Positive",
            news_volume_high=False,
            insider_activity="Cluster Selling"
        )
        score = self.scorer._score_sentiment(sentiment)
        assert 6 <= score <= 8, f"Expected 6-8, got {score}"


class TestFundamentalsScoring:
    """Tests for _score_fundamentals() method - v6.0: 55 pts total"""
    
    def setup_method(self):
        self.scorer = VinSightScorer()
    
    def test_excellent_fundamentals(self):
        """v6.0: PEG <1 (12) + Growth (10) + Margin (10) + Debt (8) + Inst (8) + Flow (7) = 55"""
        fundamentals = Fundamentals(
            inst_ownership=85.0,
            inst_changing="Rising",
            pe_ratio=15.0,
            peg_ratio=0.8,
            earnings_growth_qoq=0.20,
            sector_pe_median=25.0,
            profit_margin=0.25,
            debt_to_equity=0.3
        )
        score = self.scorer._score_fundamentals(fundamentals)
        assert score >= 50, f"Expected >=50, got {score}"
    
    def test_moderate_fundamentals(self):
        """Moderate values should give mid-range score"""
        fundamentals = Fundamentals(
            inst_ownership=60.0,
            inst_changing="Flat",
            pe_ratio=25.0,
            peg_ratio=1.5,
            earnings_growth_qoq=0.05,
            sector_pe_median=25.0,
            profit_margin=0.10,
            debt_to_equity=0.8
        )
        score = self.scorer._score_fundamentals(fundamentals)
        assert 25 <= score <= 35, f"Expected 25-35, got {score}"
    
    def test_poor_fundamentals(self):
        """Poor values should give low score"""
        fundamentals = Fundamentals(
            inst_ownership=20.0,
            inst_changing="Falling",
            pe_ratio=60.0,
            peg_ratio=3.5,
            earnings_growth_qoq=-0.15,
            sector_pe_median=25.0,
            profit_margin=-0.05,
            debt_to_equity=3.0
        )
        score = self.scorer._score_fundamentals(fundamentals)
        assert score <= 10, f"Expected <=10, got {score}"


class TestTechnicalsScoring:
    """Tests for _score_technicals() method - v6.0: 15 pts total"""
    
    def setup_method(self):
        self.scorer = VinSightScorer()
    
    def test_perfect_bull_trend(self):
        """v6.0: Trend (5) + RSI optimal (5) + Vol Rising (5) = 15"""
        technicals = Technicals(
            price=110.0,
            sma50=100.0,
            sma200=90.0,
            rsi=58.0,
            momentum_label="Bullish",
            volume_trend="Price Rising + Vol Rising"
        )
        score = self.scorer._score_technicals(technicals)
        assert score == 15, f"Expected 15, got {score}"
    
    def test_moderate_technicals(self):
        """Mixed signals should give mid-range score"""
        technicals = Technicals(
            price=95.0,
            sma50=100.0,
            sma200=90.0,
            rsi=72.0,
            momentum_label="Bullish",
            volume_trend="Weak/Mixed"
        )
        score = self.scorer._score_technicals(technicals)
        assert 6 <= score <= 10, f"Expected 6-10, got {score}"


class TestProjectionsScoring:
    """Tests for _score_projections() method - v6.0: 15 pts total"""
    
    def setup_method(self):
        self.scorer = VinSightScorer()
    
    def test_strong_upside_high_reward(self):
        """v6.0: P50 >15% upside (8) + Ratio >3x (7) = 15"""
        projections = Projections(
            monte_carlo_p50=120.0,
            monte_carlo_p90=140.0,
            monte_carlo_p10=95.0,
            current_price=100.0
        )
        score = self.scorer._score_projections(projections)
        assert score == 15, f"Expected 15, got {score}"
    
    def test_moderate_projections(self):
        """v6.0: Moderate upside and ratio"""
        projections = Projections(
            monte_carlo_p50=108.0,
            monte_carlo_p90=118.0,
            monte_carlo_p10=92.0,
            current_price=100.0
        )
        score = self.scorer._score_projections(projections)
        assert 8 <= score <= 12, f"Expected 8-12, got {score}"


class TestFullScoreIntegration:
    """Integration tests for complete scoring v6.0"""
    
    def setup_method(self):
        self.scorer = VinSightScorer()
    
    def test_total_score_sums_correctly(self):
        """Verify all pillars sum to 100 max"""
        test_data = StockData(
            ticker="TEST",
            beta=1.2,
            dividend_yield=1.5,
            market_bull_regime=True,
            fundamentals=Fundamentals(
                inst_ownership=85.0,
                inst_changing="Rising",
                pe_ratio=18.0,
                peg_ratio=0.9,
                earnings_growth_qoq=0.18,
                sector_pe_median=25.0,
                profit_margin=0.22,
                debt_to_equity=0.35
            ),
            technicals=Technicals(
                price=110.0,
                sma50=100.0,
                sma200=90.0,
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
                monte_carlo_p50=125.0,
                monte_carlo_p90=145.0,
                monte_carlo_p10=100.0,
                current_price=110.0
            )
        )
        
        result = self.scorer.evaluate(test_data)
        
        # v6.0 max scores
        assert result.breakdown["Fundamentals"] <= 55, f"Fundamentals exceeds 55: {result.breakdown['Fundamentals']}"
        assert result.breakdown["Technicals"] <= 15, f"Technicals exceeds 15: {result.breakdown['Technicals']}"
        assert result.breakdown["Sentiment"] <= 15, f"Sentiment exceeds 15: {result.breakdown['Sentiment']}"
        assert result.breakdown["Projections"] <= 15, f"Projections exceeds 15: {result.breakdown['Projections']}"
        
        # Sum should be raw score before bonuses
        raw_sum = sum(result.breakdown.values())
        assert raw_sum <= 100, f"Raw sum exceeds 100: {raw_sum}"
        
        # Strong stock should score well
        assert result.total_score >= 85, f"Expected >=85 for excellent stock, got {result.total_score}"
        assert result.rating == "Strong Buy"
    
    def test_defensive_mode_caps_high_beta(self):
        """In bear market, high beta stocks capped at 70"""
        data = StockData(
            ticker="HIGHBETA",
            beta=2.0,
            dividend_yield=0.0,
            market_bull_regime=False,  # Bear market
            fundamentals=Fundamentals(
                inst_ownership=80.0,
                inst_changing="Rising",
                pe_ratio=15.0,
                peg_ratio=0.8,
                earnings_growth_qoq=0.15,
                sector_pe_median=25.0,
                profit_margin=0.20,
                debt_to_equity=0.3
            ),
            technicals=Technicals(
                price=110.0,
                sma50=100.0,
                sma200=90.0,
                rsi=60.0,
                momentum_label="Bullish",
                volume_trend="Price Rising + Vol Rising"
            ),
            sentiment=Sentiment(
                news_sentiment_label="Positive",
                news_volume_high=True,
                insider_activity="Net Buying"
            ),
            projections=Projections(
                monte_carlo_p50=130.0,
                monte_carlo_p90=150.0,
                monte_carlo_p10=100.0,
                current_price=110.0
            )
        )
        
        result = self.scorer.evaluate(data)
        assert result.total_score <= 70, f"Expected <=70 (defensive cap), got {result.total_score}"
        assert "Defensive Mode Cap" in str(result.modifications)


class TestRatingThresholds:
    """Test rating boundaries"""
    
    def setup_method(self):
        self.scorer = VinSightScorer()
    
    def test_rating_thresholds(self):
        """Verify rating thresholds unchanged"""
        assert self.scorer._get_rating(100) == "Strong Buy"
        assert self.scorer._get_rating(80) == "Strong Buy"
        assert self.scorer._get_rating(79) == "Buy"
        assert self.scorer._get_rating(65) == "Buy"
        assert self.scorer._get_rating(64) == "Hold"
        assert self.scorer._get_rating(45) == "Hold"
        assert self.scorer._get_rating(44) == "Sell"
        assert self.scorer._get_rating(0) == "Sell"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
