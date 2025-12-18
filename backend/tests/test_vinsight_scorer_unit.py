"""
Unit Tests for VinSight Scorer v6.1 (Research-Based Rebalance)
Tests individual scoring components to verify correctness.

v6.1 Weight Distribution:
- Fundamentals: 55 pts
- Technicals: 15 pts
- Sentiment: 15 pts
- Projections: 15 pts
"""
import sys
sys.path.insert(0, 'backend')

import pytest
from services.vinsight_scorer import (
    VinSightScorer, StockData, Fundamentals, Technicals, Sentiment, Projections
)


class TestSentimentScoring:
    """Tests for _score_sentiment() method - v6.0: 15 pts total (News 7 + Insider 8)"""
    
    def setup_method(self):
        self.scorer = VinSightScorer()
    
    def test_positive_news_net_buying_gives_max_score(self):
        """v6.0: Positive news (10) + Net Buying (5) = 15 points"""
        sentiment = Sentiment(
            news_sentiment_label="Positive",
            news_sentiment_score=0.4,  # Max positive
            news_article_count=10,
            insider_activity="Net Buying"
        )
        score = self.scorer._score_sentiment(sentiment)
        assert score == 15, f"Expected 15, got {score}"
    
    def test_neutral_news_net_buying(self):
        """v6.0: Neutral news (5) + Net Buying (5) = 10 points"""
        sentiment = Sentiment(
            news_sentiment_label="Neutral",
            news_sentiment_score=0.0,  # Neutral
            news_article_count=10,
            insider_activity="Net Buying"
        )
        score = self.scorer._score_sentiment(sentiment)
        assert score == 10, f"Expected 10, got {score}"
    
    def test_negative_news_net_buying(self):
        """v6.0: Negative news (0) + Net Buying (5) = 5 points"""
        sentiment = Sentiment(
            news_sentiment_label="Negative",
            news_sentiment_score=-0.4,  # Max negative
            news_article_count=10,
            insider_activity="Net Buying"
        )
        score = self.scorer._score_sentiment(sentiment)
        assert score == 5, f"Expected 5, got {score}"
    
    def test_positive_news_cluster_selling(self):
        """v6.0: Positive news (10) + Cluster Selling (0) = 10 points"""
        sentiment = Sentiment(
            news_sentiment_label="Positive",
            news_sentiment_score=0.4,  # Max positive
            news_article_count=10,
            insider_activity="Cluster Selling"
        )
        score = self.scorer._score_sentiment(sentiment)
        assert score == 10, f"Expected 10, got {score}"


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
            sector_name="Technology",
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
            sector_name="Technology",
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
            sector_name="Technology",
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
        """v6.1: P50 >=30% upside (8) + Ratio >=4x (7) = 15"""
        projections = Projections(
            monte_carlo_p50=135.0,  # 35% upside for max
            monte_carlo_p90=160.0,
            monte_carlo_p10=85.0,   # 4:1 ratio
            current_price=100.0
        )
        score = self.scorer._score_projections(projections)
        assert score == 15, f"Expected 15, got {score}"
    
    def test_moderate_projections(self):
        """v6.1: Moderate upside and ratio - stricter thresholds"""
        projections = Projections(
            monte_carlo_p50=108.0,  # 8% upside
            monte_carlo_p90=118.0,
            monte_carlo_p10=92.0,
            current_price=100.0
        )
        score = self.scorer._score_projections(projections)
        assert 5 <= score <= 9, f"Expected 5-9, got {score}"


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
                sector_name="Technology",
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
                news_sentiment_score=0.4,
                news_article_count=10,
                insider_activity="Net Buying"
            ),
            projections=Projections(
                monte_carlo_p50=145.0,  # 32% upside for strong score
                monte_carlo_p90=170.0,
                monte_carlo_p10=90.0,   # 4:1 ratio
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
                sector_name="Technology",
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
                news_sentiment_score=0.4,
                news_article_count=10,
                insider_activity="Net Buying"
            ),
            projections=Projections(
                monte_carlo_p50=145.0,  # 32% upside
                monte_carlo_p90=165.0,
                monte_carlo_p10=90.0,
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
