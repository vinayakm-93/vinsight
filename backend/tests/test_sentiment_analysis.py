"""
Unit tests for VinSight v2 Sentiment Analyzers
Tests FinBERT and Groq sentiment analysis capabilities
"""

import pytest
from backend.services.finbert_sentiment import FinBERTSentimentAnalyzer, get_finbert_analyzer
from backend.services.groq_sentiment import GroqSentimentAnalyzer, get_groq_analyzer
import os


class TestFinBERTSentiment:
    """Tests for FinBERT sentiment analyzer"""
    
    def test_finbert_positive_sentiment(self):
        """Test positive financial sentiment detection"""
        analyzer = get_finbert_analyzer()
        result = analyzer.analyze("Apple exceeds earnings expectations, stock rallies 5%")
        
        assert result['label'] == 'positive'
        assert result['score'] > 0
        assert result['confidence'] > 0.5
        assert 'probabilities' in result
    
    def test_finbert_negative_sentiment(self):
        """Test negative financial sentiment detection"""
        analyzer = get_finbert_analyzer()
        result = analyzer.analyze("Company misses revenue targets, CEO announces layoffs")
        
        assert result['label'] == 'negative'
        assert result['score'] < 0
        assert result['confidence'] > 0.5
    
    def test_finbert_neutral_sentiment(self):
        """Test neutral sentiment detection"""
        analyzer = get_finbert_analyzer()
        result = analyzer.analyze("Merger talks continue, no decision expected soon")
        
        # Should be neutral or at least low confidence
        assert result['label'] in ['neutral', 'positive', 'negative']
        assert -0.5 <= result['score'] <= 0.5
    
    def test_finbert_batch_processing(self):
        """Test batch processing of multiple headlines"""
        analyzer = get_finbert_analyzer()
        headlines = [
            "Stock hits all-time high on strong earnings",
            "Earnings disappoint investors",
            "Quarterly report released"
        ]
        
        results = analyzer.analyze_batch(headlines)
        
        assert len(results) == 3
        assert results[0]['label'] == 'positive'
        assert results[1]['label'] == 'negative'
    
    def test_finbert_empty_text(self):
        """Test handling of empty text"""
        analyzer = get_finbert_analyzer()
        result = analyzer.analyze("")
        
        assert result['label'] == 'neutral'
        assert result['score'] == 0.0
        assert result['confidence'] == 0.0
    
    def test_finbert_singleton_pattern(self):
        """Test that get_finbert_analyzer returns singleton"""
        analyzer1 = get_finbert_analyzer()
        analyzer2 = get_finbert_analyzer()
        
        assert analyzer1 is analyzer2  # Should be same instance


class TestGroqSentiment:
    """Tests for Groq sentiment analyzer"""
    
    @pytest.mark.skipif(not os.getenv('GROQ_API_KEY'), reason="No Groq API key")
    def test_groq_sentiment_analysis(self):
        """Test Groq sentiment analysis (requires API key)"""
        analyzer = get_groq_analyzer()
        
        if not analyzer.is_available():
            pytest.skip("Groq API key not configured")
        
        result = analyzer.analyze("Tesla reports record Q4 deliveries, beating analyst estimates")
        
        assert result['label'] in ['positive', 'negative', 'neutral']
        assert -1.0 <= result['score'] <= 1.0
        assert 0.0 <= result['confidence'] <= 1.0
        assert 'reasoning' in result
        assert len(result['reasoning']) > 0
    
    def test_groq_availability_check(self):
        """Test Groq availability check"""
        analyzer = GroqSentimentAnalyzer()
        
        # If no API key, should not be available
        if not os.getenv('GROQ_API_KEY'):
            assert not analyzer.is_available()
    
    def test_groq_empty_text(self):
        """Test Groq handling of empty text"""
        analyzer = get_groq_analyzer()
        result = analyzer.analyze("")
        
        assert result['label'] == 'neutral'
        assert result['score'] == 0.0


class TestHybridSentiment:
    """Integration tests for hybrid sentiment analysis"""
    
    def test_hybrid_sentiment_integration(self):
        """Test hybrid sentiment using analysis.py function"""
        from backend.services.analysis import calculate_news_sentiment
        
        test_news = [
            {'title': 'Apple beats earnings expectations'},
            {'title': 'Strong iPhone sales drive revenue growth'},
            {'title': 'Stock price hits new high'}
        ]
        
        result = calculate_news_sentiment(test_news, deep_analysis=False)
        
        assert 'score' in result
        assert 'label' in result
        assert 'confidence' in result
        assert 'article_count' in result
        assert 'source' in result
        
        assert result['article_count'] == 3
        assert result['label'] in ['Positive', 'Negative', 'Neutral']
        assert result['source'] in ['finbert', 'groq', 'hybrid', 'textblob_fallback']
    
    def test_empty_news_handling(self):
        """Test handling of empty news list"""
        from backend.services.analysis import calculate_news_sentiment
        
        result = calculate_news_sentiment([])
        
        assert result['score'] == 0
        assert result['label'] == 'Neutral'
        assert result['article_count'] == 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
