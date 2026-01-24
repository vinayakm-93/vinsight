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
    """Tests for _score_sentiment() method - v6.3: 10 pts total (News 5 + Insider 5)"""
    
    def setup_method(self):
        self.scorer = VinSightScorer()
    
    def test_positive_news_net_buying_gives_max_score(self):
        """v6.3: Positive news (5) + Net Buying (5) = 10 points"""
        sentiment = Sentiment(
            news_sentiment_label="Positive",
            news_sentiment_score=0.4,  # Max positive
            news_article_count=10,
            insider_activity="Net Buying"
        )
        score = self.scorer._score_sentiment(sentiment)
        assert score == 10, f"Expected 10, got {score}"
    
    def test_neutral_news_net_buying(self):
        """v6.3: Neutral news (2.5) + Net Buying (5) = 7.5 -> 8 points"""
        sentiment = Sentiment(
            news_sentiment_label="Neutral",
            news_sentiment_score=0.0,
            news_article_count=10,
            insider_activity="Net Buying"
        )
        score = self.scorer._score_sentiment(sentiment)
        assert score >= 7, f"Expected >= 7, got {score}"
    
    def test_negative_news_net_buying(self):
        """v6.3: Negative news (0) + Net Buying (5) = 5 points"""
        sentiment = Sentiment(
            news_sentiment_label="Negative",
            news_sentiment_score=-0.4,
            news_article_count=10,
            insider_activity="Net Buying"
        )
        score = self.scorer._score_sentiment(sentiment)
        assert score == 5, f"Expected 5, got {score}"


class TestFundamentalsScoring:
    """Tests for _score_fundamentals() method - v6.3: 70 pts total"""
    
    def setup_method(self):
        self.scorer = VinSightScorer()
    
    def test_excellent_fundamentals(self):
        """v6.3: Excellent across board should score 70"""
        fundamentals = Fundamentals(
            inst_ownership=85.0,
            pe_ratio=15.0,
            peg_ratio=0.8,
            earnings_growth_qoq=0.20,
            sector_name="Technology",
            profit_margin=0.25,
            debt_to_equity=0.3,
            fcf_yield=0.06,
            eps_surprise_pct=0.15
        )
        score = self.scorer._score_fundamentals(fundamentals)
        assert score == 70, f"Expected 70, got {score}"
    
    def test_moderate_fundamentals(self):
        """Moderate values should give mid-range score"""
        fundamentals = Fundamentals(
            inst_ownership=40.0, # 5pts
            pe_ratio=25.0,
            peg_ratio=1.8, # 5pts
            earnings_growth_qoq=0.05, # 5pts
            sector_name="Technology",
            profit_margin=0.05, # 5pts
            debt_to_equity=1.5, # 2.5pts (Leveraged)
            fcf_yield=0.02, # 5pts
            eps_surprise_pct=0.02 # 7.5pts
        )
        score = self.scorer._score_fundamentals(fundamentals)
        # 5+5+5+5+2.5+5+7.5 = 35
        assert 30 <= score <= 40, f"Expected ~35, got {score}"


class TestTechnicalsScoring:
    """Tests for _score_technicals() method - v6.3: 10 pts total"""
    
    def setup_method(self):
        self.scorer = VinSightScorer()
    
    def test_perfect_bull_trend(self):
        """v6.3: Perfect trend"""
        technicals = Technicals(
            price=110.0,
            sma50=100.0,
            sma200=90.0,
            rsi=58.0,
            momentum_label="Bullish",
            volume_trend="Price Rising + Vol Rising"
        )
        score = self.scorer._score_technicals(technicals)
        assert score == 10, f"Expected 10, got {score}"


class TestProjectionsScoring:
    """Tests for _score_projections() method - v6.3: 10 pts total"""
    
    def setup_method(self):
        self.scorer = VinSightScorer()
    
    def test_strong_upside(self):
        """v6.3: Strong upside"""
        projections = Projections(
            monte_carlo_p50=135.0,
            monte_carlo_p90=160.0,
            monte_carlo_p10=100.0,
            current_price=100.0
        )
        score = self.scorer._score_projections(projections)
        assert score == 10, f"Expected 10, got {score}"


class TestFullScoreIntegration:
    """Integration tests for complete scoring v6.3"""
    
    def setup_method(self):
        self.scorer = VinSightScorer()
    
    def test_total_score_sums_correctly(self):
        """Verify all pillars sum logic"""
        test_data = StockData(
            ticker="TEST",
            beta=1.2,
            dividend_yield=1.5,
            market_bull_regime=True,
            fundamentals=Fundamentals(
                inst_ownership=85.0,
                pe_ratio=18.0,
                peg_ratio=0.9,
                earnings_growth_qoq=0.18,
                sector_name="Technology",
                profit_margin=0.22,
                debt_to_equity=0.35,
                fcf_yield=0.06,
                eps_surprise_pct=0.12
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
                monte_carlo_p50=145.0,
                monte_carlo_p90=170.0,
                monte_carlo_p10=90.0,
                current_price=110.0
            )
        )
        
        result = self.scorer.evaluate(test_data)
        
        assert result.breakdown["Fundamentals"] <= 70
        assert result.breakdown["Technicals"] <= 10
        assert result.breakdown["Sentiment"] <= 10
        assert result.breakdown["Projections"] <= 10
        
        # Should be max score
        assert result.total_score >= 90
        
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
                pe_ratio=15.0,
                peg_ratio=0.8,
                earnings_growth_qoq=0.15,
                sector_name="Technology",
                profit_margin=0.20,
                debt_to_equity=0.3,
                fcf_yield=0.04,
                eps_surprise_pct=0.10
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
