import unittest
from unittest.mock import patch, MagicMock
from services import finance
from services.reasoning_scorer import ReasoningScorer
from services.vinsight_scorer import StockData, Sentiment, Fundamentals, Technicals, Projections

class TestPhase0NewsPipeline(unittest.TestCase):
    
    @patch('services.finance.finnhub_news.fetch_company_news')
    @patch('services.finance.get_stock_info')
    def test_get_news_cache_and_fetch(self, mock_get_info, mock_fetch):
        # Setup mocks
        mock_get_info.return_value = {"currentPrice": 100.0, "previousClose": 100.0} # No volatility bypass
        mock_fetch.return_value = {"latest": [{"title": "News 1"}], "historical": [{"title": "News 2"}]}
        
        # Clear cache before test
        finance.cache_news.clear()
        
        # First call should hit mock_fetch
        data1 = finance.get_news("AAPL")
        self.assertEqual(data1["latest"][0]["title"], "News 1")
        mock_fetch.assert_called_once_with("AAPL", days=14)
        
        # Second call should hit cache (mock_fetch not called again)
        mock_fetch.reset_mock()
        data2 = finance.get_news("AAPL")
        self.assertEqual(data2["latest"][0]["title"], "News 1")
        mock_fetch.assert_not_called()

    @patch('services.finance.finnhub_news.fetch_company_news')
    @patch('services.finance.get_stock_info')
    def test_volatility_bypass(self, mock_get_info, mock_fetch):
        # Setup mock for >5% drop
        mock_get_info.return_value = {"currentPrice": 90.0, "previousClose": 100.0} # 10% drop
        mock_fetch.return_value = {"latest": [{"title": "Fresh News"}], "historical": []}
        
        # Clear cache and artificially set it
        finance.cache_news.clear()
        finance.cache_news["AAPL"] = {"latest": [{"title": "Old News"}], "historical": []}
        
        # Since drop is 10%, it should BYPASS cache and hit mock_fetch
        data = finance.get_news("AAPL")
        self.assertEqual(data["latest"][0]["title"], "Fresh News")
        mock_fetch.assert_called_once()
        
    @patch('services.groq_sentiment.get_groq_analyzer')
    def test_reasoning_scorer_context_injection(self, mock_get_groq):
        # Mock the Intelligence Agent output
        mock_agent = MagicMock()
        mock_agent.analyze_dual_period.return_value = {
            "reasoning": "Strong buy because of new product.",
            "key_drivers": ["Product Launch", "Margin Expansion"]
        }
        mock_get_groq.return_value = mock_agent
        
        scorer = ReasoningScorer()
        
        # Create dummy stock data with nested news
        mock_stock = StockData(
            ticker="AAPL", beta=1.0, dividend_yield=0.0, market_bull_regime=True,
            fundamentals=Fundamentals(1,1,1,1,1,1,"Rising",1,1,1,1,1,1,1,1,1,1,"Tech"),
            technicals=Technicals(1,1,1,1,1,1,"Bullish","Rising"),
            projections=Projections(1,1,1,1),
            sentiment=Sentiment(
                news_sentiment_label="Positive",
                news_sentiment_score=0.9,
                news_article_count=5,
                news_data={"latest": [{"title": "t1"}], "historical": [{"title": "t2"}]}
            )
        )
        
        # Build context
        context = scorer._build_context(mock_stock, "CFA", None, mock_stock.sentiment.news_data)
        
        # Assert the Intelligence Report made it into the context
        report = context["sentiment_context"]["Intelligence Report"]
        self.assertIn("Distilled Insight: Strong buy", report)
        self.assertIn("Key Drivers: Product Launch", report)
        
        # Assert the dual period method was actually called
        mock_agent.analyze_dual_period.assert_called_once()

if __name__ == '__main__':
    unittest.main()
