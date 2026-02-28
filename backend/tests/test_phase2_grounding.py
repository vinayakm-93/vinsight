import unittest
from unittest.mock import MagicMock
from services.grounding_validator import GroundingValidator
from services.reasoning_scorer import ReasoningScorer, AIResponseSchema
from services.vinsight_scorer import StockData, Fundamentals, Technicals, Sentiment, Projections

class TestPhase2GroundingVerification(unittest.TestCase):
    
    def setUp(self):
        self.validator = GroundingValidator(tolerance_pct=0.05)
        self.scorer = ReasoningScorer()
        
        # Simulating the context that gets passed to check_hallucinations
        # Let's say the PE is 20.0, FCF is 5.5, Price is 150.0
        self.mock_context = {
            "metrics": [20.0, 5.5, 150.0, "Bullish", "10.0%"]
        }

    def test_numeric_extraction(self):
        """Test the validator's ability to pull numbers from messy text."""
        text = "The P/E of 20.5 is high, but revenue grew 5,000% to $150.00."
        extracted = self.validator._extract_numbers(text)
        self.assertIn(20.5, extracted)
        self.assertIn(5000.0, extracted)
        self.assertIn(150.0, extracted)

    def test_fuzzy_matching_success(self):
        """Test that numbers within the 5% tolerance are accepted."""
        valid_numbers = [100.0]
        
        # Exact match
        self.assertTrue(self.validator._fuzzy_match(100.0, valid_numbers))
        
        # Within +5% (104.9)
        self.assertTrue(self.validator._fuzzy_match(104.9, valid_numbers))
        
        # Within -5% (95.1)
        self.assertTrue(self.validator._fuzzy_match(95.1, valid_numbers))

    def test_fuzzy_matching_failure(self):
        """Test that numbers outside 5% tolerance are rejected."""
        valid_numbers = [100.0]
        
        # Outside +5% (106)
        self.assertFalse(self.validator._fuzzy_match(106.0, valid_numbers))
        
        # Outside -5% (94)
        self.assertFalse(self.validator._fuzzy_match(94.0, valid_numbers))

    def test_safe_numbers_ignored(self):
        """Test that conversational numbers (1, 10, 100) don't trigger hallucinations."""
        # Context has no numbers
        empty_context = {"metrics": []}
        
        # These are in the `safe_numbers` list
        text = "This is 1 of the Top 10 stocks. I give it 100 percent."
        hallucinations = self.validator.check_hallucinations(text, empty_context)
        
        self.assertEqual(hallucinations, 0)

    def test_hallucination_detection(self):
        """Test identifying missing numbers."""
        # 150 is in context. 80.5 and 999 are completely made up.
        text = "Price is 150, but PE is 80.5 and growth is 999."
        
        count = self.validator.check_hallucinations(text, self.mock_context)
        self.assertEqual(count, 2) # 80.5 and 999 should be flagged

    def test_reasoning_scorer_suppression(self):
        """Test that ReasoningScorer suppresses the text if >2 hallucinations exist."""
        # Setup dummy LLM response with 3 massive hallucinations
        bad_response = {
            "thought_process": "...",
            "confidence_score": 80,
            "primary_driver": "Growth",
            "summary": {
                "verdict": "Buy.",
                "bull_case": "PE is 800, Debt is 900, Price target is 1000.", # 3 Hallucinations
                "bear_case": "Nothing.",
                "fundamental_analysis": "",
                "technical_analysis": ""
            },
            "component_scores": {"valuation": 5, "growth": 5, "profitability": 5, "health": 5, "technicals": 5, "momentum": 5, "volume": 5},
            "risk_factors": [],
            "opportunities": []
        }
        
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
        
        # Mock the algo result so the context dict has NO 800, 900, or 1000
        mock_algo = MagicMock()
        mock_algo.details = [{"value": 20.0}, {"value": 150.0}] 
        mock_algo.breakdown = {}
        
        result = self.scorer._parse_response(bad_response, dummy_stock, "CFA", "Mock", mock_algo)
        
        # Verify the suppression matrix triggered
        self.assertEqual(result["structured_summary"]["bull_case"], "AI narrative suppressed due to data grounding mismatch.")
        self.assertEqual(result["structured_summary"]["bear_case"], "Please refer to the raw mathematical scoring breakdowns.")

if __name__ == '__main__':
    unittest.main()
