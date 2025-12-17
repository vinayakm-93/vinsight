"""
Unit Tests for VinSight Scorer v5.0
Tests individual scoring components to verify correctness.
"""
import sys
sys.path.insert(0, '.')

import pytest
from services.vinsight_scorer import (
    VinSightScorer, StockData, Fundamentals, Technicals, Sentiment, Projections
)


class TestSentimentScoring:
    """Tests for _score_sentiment() method"""
    
    def setup_method(self):
        self.scorer = VinSightScorer()
    
    def test_positive_news_net_buying_gives_max_score(self):
        """Positive news (10) + Net Buying (10) = 20 points"""
        sentiment = Sentiment(
            news_sentiment_label="Positive",
            news_volume_high=False,
            insider_activity="Net Buying"
        )
        score = self.scorer._score_sentiment(sentiment)
        assert score == 20, f"Expected 20, got {score}"
    
    def test_neutral_news_net_buying(self):
        """Neutral news (5) + Net Buying (10) = 15 points"""
        sentiment = Sentiment(
            news_sentiment_label="Neutral",
            news_volume_high=False,
            insider_activity="Net Buying"
        )
        score = self.scorer._score_sentiment(sentiment)
        assert score == 15, f"Expected 15, got {score}"
    
    def test_negative_news_net_buying(self):
        """Negative news (0) + Net Buying (10) = 10 points"""
        sentiment = Sentiment(
            news_sentiment_label="Negative",
            news_volume_high=False,
            insider_activity="Net Buying"
        )
        score = self.scorer._score_sentiment(sentiment)
        assert score == 10, f"Expected 10, got {score}"
    
    def test_positive_news_mixed_selling(self):
        """Positive news (10) + Mixed/Minor Selling (5) = 15 points"""
        sentiment = Sentiment(
            news_sentiment_label="Positive",
            news_volume_high=False,
            insider_activity="Mixed/Minor Selling"
        )
        score = self.scorer._score_sentiment(sentiment)
        assert score == 15, f"Expected 15, got {score}"
    
    def test_positive_news_heavy_selling(self):
        """Positive news (10) + Heavy Selling (0) = 10 points"""
        sentiment = Sentiment(
            news_sentiment_label="Positive",
            news_volume_high=False,
            insider_activity="Heavy Selling"
        )
        score = self.scorer._score_sentiment(sentiment)
        assert score == 10, f"Expected 10, got {score}"
    
    def test_positive_news_cluster_selling_FIXED(self):
        """
        FIXED: Positive news (10) + Cluster Selling (0) should be 10, not 0!
        
        Previous buggy behavior: Returns 0 for entire sentiment
        Fixed behavior: Returns 10 (news score preserved, insider = 0)
        """
        sentiment = Sentiment(
            news_sentiment_label="Positive",
            news_volume_high=False,
            insider_activity="Cluster Selling"
        )
        score = self.scorer._score_sentiment(sentiment)
        # After fix: news score (10) + insider score (0) = 10
        assert score == 10, f"Expected 10, got {score}"
    
    def test_high_news_volume_overrides_neutral(self):
        """High news volume + non-negative news should give 10 points"""
        sentiment = Sentiment(
            news_sentiment_label="Neutral",
            news_volume_high=True,
            insider_activity="Net Buying"
        )
        score = self.scorer._score_sentiment(sentiment)
        # High volume + neutral = 10 (not 5)
        assert score == 20, f"Expected 20 (10 news + 10 insider), got {score}"
    
    def test_no_activity_gives_full_insider_points(self):
        """No Activity should give 10 pts (same as Net Buying)"""
        sentiment = Sentiment(
            news_sentiment_label="Neutral",
            news_volume_high=False,
            insider_activity="No Activity"
        )
        score = self.scorer._score_sentiment(sentiment)
        # Neutral news (5) + No Activity (10) = 15
        assert score == 15, f"Expected 15, got {score}"


class TestFundamentalsScoring:
    """Tests for _score_fundamentals() method"""
    
    def setup_method(self):
        self.scorer = VinSightScorer()
    
    def test_cheap_valuation_high_growth_rising_inst(self):
        """PEG < 1 (10) + Growth > 10% (10) + Rising Inst (10) = 30"""
        fundamentals = Fundamentals(
            inst_ownership=80.0,
            inst_changing="Rising",
            pe_ratio=15.0,
            peg_ratio=0.8,  # < 1.0 = Cheap
            earnings_growth_qoq=0.15,  # > 10%
            sector_pe_median=25.0
        )
        score = self.scorer._score_fundamentals(
            fundamentals, 
            vol_trend="Price Rising + Vol Rising",
            price=100.0
        )
        assert score == 30, f"Expected 30, got {score}"
    
    def test_fair_valuation_moderate_growth_flat_inst(self):
        """PEG 1.0-1.5 (5) + Growth 5% (sector-adjusted 5) + Flat Inst (5) = 15
        But with sector PE 25, threshold is 10%/5%, so 5% = 3 pts (positive but below)
        Total: 5 + 3 + 5 = 13"""
        fundamentals = Fundamentals(
            inst_ownership=80.0,
            inst_changing="Flat",
            pe_ratio=25.0,
            peg_ratio=1.3,  # Fair
            earnings_growth_qoq=0.05,  # 5%
            sector_pe_median=25.0
        )
        score = self.scorer._score_fundamentals(
            fundamentals,
            vol_trend="Weak/Mixed",
            price=100.0
        )
        # With sector-adjusted thresholds: 5% growth is below 10% threshold = 3 pts
        assert score == 13, f"Expected 13, got {score}"
    
    def test_expensive_negative_growth_falling_inst(self):
        """PEG > 1.5 (0) + Growth < 0 (0) + Falling Inst (0) = 0"""
        fundamentals = Fundamentals(
            inst_ownership=50.0,
            inst_changing="Falling",
            pe_ratio=60.0,
            peg_ratio=2.5,  # Expensive
            earnings_growth_qoq=-0.10,  # Negative
            sector_pe_median=25.0
        )
        score = self.scorer._score_fundamentals(
            fundamentals,
            vol_trend="Weak/Mixed",
            price=100.0
        )
        assert score == 0, f"Expected 0, got {score}"


class TestTechnicalsScoring:
    """Tests for _score_technicals() method"""
    
    def setup_method(self):
        self.scorer = VinSightScorer()
    
    def test_perfect_bull_trend(self):
        """Price > SMA50 > SMA200 (10) + RSI 60-80 w/vol (10) + Vol Rising (10) = 30"""
        technicals = Technicals(
            price=110.0,
            sma50=100.0,
            sma200=90.0,
            rsi=70.0,
            momentum_label="Bullish",
            volume_trend="Price Rising + Vol Rising"
        )
        score = self.scorer._score_technicals(technicals)
        assert score == 30, f"Expected 30, got {score}"
    
    def test_bearish_trend_with_oversold(self):
        """Price < SMA200, RSI oversold gets turnaround bonus
        Trend: 0 (bear) BUT RSI<30 = +3 turnaround
        RSI 25: +2 (oversold potential)
        Volume weak: 0
        = 3 + 2 + 0 = 5 (not 0 anymore due to turnaround logic)
        
        Note: With RSI=35 (not oversold), it would be 0.
        """
        technicals = Technicals(
            price=80.0,
            sma50=90.0,
            sma200=100.0,
            rsi=25.0,  # Oversold
            momentum_label="Bearish",
            volume_trend="Weak/Mixed"
        )
        score = self.scorer._score_technicals(technicals)
        # With new turnaround logic: oversold bear gets some points
        assert score == 5, f"Expected 5, got {score}"
    
    def test_overbought_rsi_gives_zero(self):
        """RSI > 80 should give 0 points for momentum"""
        technicals = Technicals(
            price=110.0,
            sma50=100.0,
            sma200=90.0,
            rsi=85.0,  # Overbought
            momentum_label="Bullish",
            volume_trend="Price Rising + Vol Rising"
        )
        score = self.scorer._score_technicals(technicals)
        # Trend (10) + RSI overbought (0) + Vol (10) = 20
        assert score == 20, f"Expected 20, got {score}"


class TestProjectionsScoring:
    """Tests for _score_projections() method"""
    
    def setup_method(self):
        self.scorer = VinSightScorer()
    
    def test_strong_upside_high_reward_ratio(self):
        """P50 > 10% upside (10) + Ratio > 2x (10) = 20"""
        projections = Projections(
            monte_carlo_p50=115.0,  # +15% from 100
            monte_carlo_p90=130.0,  # +30 upside
            monte_carlo_p10=90.0,   # -10 downside, ratio = 3.0
            current_price=100.0
        )
        score = self.scorer._score_projections(projections)
        assert score == 20, f"Expected 20, got {score}"
    
    def test_moderate_upside_moderate_ratio(self):
        """P50 5-10% upside (5) + Ratio 1.5-2x (5) = 10"""
        projections = Projections(
            monte_carlo_p50=108.0,  # +8% from 100
            monte_carlo_p90=118.0,  # +18 upside
            monte_carlo_p10=90.0,   # -10 downside, ratio = 1.8
            current_price=100.0
        )
        score = self.scorer._score_projections(projections)
        assert score == 10, f"Expected 10, got {score}"
    
    def test_no_upside_poor_ratio(self):
        """P50 < 5% (0) + Ratio < 1.5 (0) = 0"""
        projections = Projections(
            monte_carlo_p50=102.0,  # +2% from 100
            monte_carlo_p90=110.0,  # +10 upside
            monte_carlo_p10=90.0,   # -10 downside, ratio = 1.0
            current_price=100.0
        )
        score = self.scorer._score_projections(projections)
        assert score == 0, f"Expected 0, got {score}"


class TestFullScoreIntegration:
    """Integration tests for complete scoring"""
    
    def setup_method(self):
        self.scorer = VinSightScorer()
    
    def test_pltr_reference_case(self):
        """Test against the reference PLTR case (updated for industry benchmarks)"""
        pltr_data = StockData(
            ticker="PLTR",
            beta=2.5,
            dividend_yield=0.0,
            market_bull_regime=True,
            fundamentals=Fundamentals(
                inst_ownership=45.0,
                inst_changing="Rising",
                pe_ratio=60.0,
                peg_ratio=1.5,  # Fair = 5 pts
                earnings_growth_qoq=0.20,  # > 15% for tech = 10 pts
                sector_pe_median=30.0  # Tech sector
            ),
            technicals=Technicals(
                price=25.0,
                sma50=22.0,
                sma200=18.0,
                rsi=65.0,  # In 65-75 range with volume = 10
                momentum_label="Bullish",
                volume_trend="Price Rising + Vol Rising"
            ),
            sentiment=Sentiment(
                news_sentiment_label="Positive",
                news_volume_high=True,
                insider_activity="Net Buying"
            ),
            projections=Projections(
                monte_carlo_p50=28.0,  # +12%
                monte_carlo_p90=35.0,  # +10 gain
                monte_carlo_p10=20.0,  # -5 loss, ratio = 2.0
                current_price=25.0
            )
        )
        
        result = self.scorer.evaluate(pltr_data)
        
        # With industry benchmarks:
        # Fundamentals: 5 (PEG 1.5) + 10 (20% > 15% tech threshold) + 10 (Rising) = 25
        assert result.breakdown["Fundamentals"] == 25, f"Fundamentals: expected 25, got {result.breakdown['Fundamentals']}"
        
        # Technicals: 10 (Trend) + 10 (RSI 65 + Vol) + 10 (Vol Rising) = 30
        # Actually RSI 65 is in 65-75 range with vol = 10, but need to check exact scoring
        # Trend: 10, RSI 65 w/vol: 10, Vol: 10 = 30? Let me check
        # RSI 65 is in "65 < rsi <= 75" range with Vol Rising = 10 pts
        # But wait, 65 is the boundary. 65 < 65 is False, so it falls to 50-65 range = 8
        # So Technicals = 10 + 8 + 10 = 28
        assert result.breakdown["Technicals"] == 28, f"Technicals: expected 28, got {result.breakdown['Technicals']}"
        
        assert result.breakdown["Sentiment"] == 20, f"Sentiment: expected 20, got {result.breakdown['Sentiment']}"
        assert result.breakdown["Projections"] == 20, f"Projections: expected 20, got {result.breakdown['Projections']}"
        
        # Total: 25 + 28 + 20 + 20 = 93
        assert result.total_score == 93, f"Total: expected 93, got {result.total_score}"
        assert result.rating == "Strong Buy"
    
    def test_defensive_mode_caps_high_beta(self):
        """In bear market (SPY < SMA200), high beta stocks capped at 70"""
        data = StockData(
            ticker="TEST",
            beta=2.0,  # High beta > 1.5
            dividend_yield=0.0,
            market_bull_regime=False,  # Bear market!
            fundamentals=Fundamentals(
                inst_ownership=80.0,
                inst_changing="Rising",
                pe_ratio=15.0,
                peg_ratio=0.8,
                earnings_growth_qoq=0.15
            ),
            technicals=Technicals(
                price=110.0,
                sma50=100.0,
                sma200=90.0,
                rsi=70.0,
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
        
        # Raw score would be very high (potentially 100), but capped at 70
        assert result.total_score <= 70, f"Expected <= 70 (defensive cap), got {result.total_score}"
        assert "Defensive Mode Cap" in str(result.modifications)


class TestRatingThresholds:
    """Test rating boundaries"""
    
    def setup_method(self):
        self.scorer = VinSightScorer()
    
    def test_rating_thresholds(self):
        """Verify rating thresholds"""
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
