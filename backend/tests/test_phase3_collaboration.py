import unittest
from unittest.mock import patch, MagicMock
from services.guardian_client import get_guardian_status
from services.reasoning_scorer import ReasoningScorer
from services.vinsight_scorer import StockData, ScoreResult, Fundamentals, Technicals, Sentiment, Projections

class TestPhase3Collaboration(unittest.TestCase):
    
    @patch('services.guardian_client.SessionLocal')
    def test_get_guardian_status_broken(self, mock_session_local):
        """Test that the client correctly identifies a broken thesis."""
        # Setup mock db session
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        # Setup mock query chain returning a broken alert
        mock_alert = MagicMock()
        mock_alert.thesis_status = "BROKEN"
        
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_order = mock_filter.order_by.return_value
        mock_order.first.return_value = mock_alert
        
        status = get_guardian_status("AAPL")
        self.assertEqual(status, "BROKEN")
        mock_db.close.assert_called_once()

    @patch('services.guardian_client.SessionLocal')
    def test_get_guardian_status_intact(self, mock_session_local):
        """Test that the client identifies an intact thesis (no unread broken alerts)."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        # Setup mock query chain returning None
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_order = mock_filter.order_by.return_value
        mock_order.first.return_value = None
        
        status = get_guardian_status("AAPL")
        self.assertEqual(status, "INTACT")

    def test_reasoning_scorer_context_injection(self):
        """Test that Guardian Status and Algo Base Score are injected into context."""
        scorer = ReasoningScorer()
        
        dummy_stock = StockData(
            ticker="TEST", beta=1.0, dividend_yield=0.0, market_bull_regime=True,
            fundamentals=Fundamentals(
                pe_ratio=20, forward_pe=15, peg_ratio=1, profit_margin=0.2, operating_margin=0.2, 
                roe=0.2, roa=0.1, debt_to_equity=0.5, current_ratio=2.0,
                fcf_yield=0.05, gross_margin_trend="Rising", debt_to_ebitda=1.0,
                interest_coverage=10, altman_z_score=5, earnings_growth_qoq=0.2, 
                revenue_growth_3y=0.2, inst_ownership=0.6, eps_surprise_pct=0.05
            ),
            technicals=Technicals(150.0, 100.0, 80.0, 60.0, 1.0, 0.05, "Bullish", "Rising"),
            projections=Projections(110.0, 130.0, 90.0, 100.0),
            sentiment=Sentiment("Positive", 0.8, 10, None)
        )
        
        mock_algo = MagicMock()
        mock_algo.score = 75.0
        
        # Build context simulating "BROKEN" status injection
        context = scorer._build_context(dummy_stock, "CFA", None, None, mock_algo, "BROKEN")
        
        # Verify Context Variables
        self.assertEqual(context["guardian_status"], "BROKEN")
        self.assertEqual(context["price_context"]["Offline Algo Baseline Score"], "75.0/100")
        
        # Verify Prompt Injection Matrix
        system_prompt = scorer._build_system_prompt(context)
        self.assertIn("GUARDIAN ALERT:", system_prompt)
        self.assertIn("The quantitative Guardian Agent has marked the thesis for this stock as BROKEN", system_prompt)
        
        # Test intact status doesn't pollute the prompt
        context_clean = scorer._build_context(dummy_stock, "CFA", None, None, mock_algo, "INTACT")
        system_prompt_clean = scorer._build_system_prompt(context_clean)
        self.assertNotIn("GUARDIAN ALERT:", system_prompt_clean)


if __name__ == '__main__':
    unittest.main()
