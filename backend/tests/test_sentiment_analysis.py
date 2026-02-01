"""
Unit tests for VinSight v2.2+ Sentiment Analyzers
Tests Groq sentiment analysis capabilities including batch processing
"""

import pytest
import os
import sys

# Ensure backend modules can be imported
# Add project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
# Add backend dir so 'from services...' works
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import MagicMock, patch
from backend.services.groq_sentiment import GroqSentimentAnalyzer, get_groq_analyzer

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
    
    @pytest.mark.skipif(not os.getenv('GROQ_API_KEY'), reason="No Groq API key")
    def test_groq_batch_analysis(self):
        """Test Groq batch analysis"""
        analyzer = get_groq_analyzer()
        
        if not analyzer.is_available():
            pytest.skip("Groq API key not configured")
        
        items = [
            "Headline: Tesla beats earnings. Summary: Strong growth in Q4.",
            "Headline: Musk announces new factory. Summary: Production to increase.",
            "Headline: Safety recall issued. Summary: Minor software update required."
        ]
        
        result = analyzer.analyze_batch(items, context="Tesla (TSLA)")
        
        print(f"Batch Result: {result}")
        assert result['label'] in ['positive', 'negative', 'neutral']
        assert -1.0 <= result['score'] <= 1.0
        assert 'reasoning' in result
    
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
    
    @patch('services.groq_sentiment.GroqSentimentAnalyzer.analyze_batch')
    def test_hybrid_sentiment_integration_mock(self, mock_analyze_batch):
        """Test hybrid sentiment using analysis.py function with mocked Groq"""
        from backend.services.analysis import calculate_news_sentiment
        
        # Mock behavior
        mock_analyze_batch.return_value = {
            'label': 'positive',
            'score': 0.8,
            'confidence': 0.9,
            'reasoning': 'Mocked reasoning'
        }
        
        test_news = [
            {'title': 'Apple beats earnings expectations', 'summary': 'Good stuff'},
            {'title': 'Strong iPhone sales drive revenue growth'}
        ]
        
        # We need to ensure get_groq_analyzer returns a valid mock or the real one that we patched
        # Since analysis.py imports 'services.groq_sentiment', we must patch that specific path
        with patch('services.groq_sentiment.get_groq_analyzer') as mock_get:
            mock_instance = MagicMock()
            mock_instance.is_available.return_value = True
            mock_instance.analyze_batch = mock_analyze_batch
            mock_get.return_value = mock_instance
            
            result = calculate_news_sentiment(test_news, ticker="AAPL")
            
            assert result['score'] == 0.8
            assert result['label'] == 'Positive'
            assert 'Deep Analysis' in result['source']
            
            # Verify analyze_batch was called
            mock_analyze_batch.assert_called_once()
            args, kwargs = mock_analyze_batch.call_args
            assert len(args[0]) >= 1 # Should have items
            assert "Headline: Apple beats earnings" in args[0][0]

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
