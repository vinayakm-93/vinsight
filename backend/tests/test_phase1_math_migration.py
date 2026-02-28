import unittest
from unittest.mock import patch, MagicMock
from pydantic import ValidationError
from services.reasoning_scorer import ReasoningScorer, AIResponseSchema
from services.vinsight_scorer import StockData, Fundamentals, Technicals, Sentiment, Projections

class TestPhase1MathMigration(unittest.TestCase):
    
    def setUp(self):
        self.scorer = ReasoningScorer()
        
        # Standard valid LLM output matching the new Pydantic schema
        self.valid_llm_response = {
            "thought_process": "Text reasoning.",
            "confidence_score": 80,
            "primary_driver": "Growth",
            "summary": {
                "verdict": "Buy this stock.",
                "bull_case": "Bull",
                "bear_case": "Bear",
                "fundamental_analysis": "Fund",
                "technical_analysis": "Tech"
            },
            "component_scores": {
                "valuation": 8,
                "growth": 9,
                "profitability": 7,
                "health": 6,
                "technicals": 8,
                "momentum": 8,
                "volume": 7
            },
            "risk_factors": ["Market risk"],
            "opportunities": ["Expansion"]
        }
        
        # Dummy StockData matching good conditions (No kill switches)
        self.good_stock = StockData(
            ticker="TEST", beta=1.0, dividend_yield=0.0, market_bull_regime=True,
            fundamentals=Fundamentals(
                pe_ratio=20, forward_pe=15, peg_ratio=1, fcf_yield=0.05,
                profit_margin=0.2, operating_margin=0.2, gross_margin_trend="Rising",
                roe=0.2, roa=0.1, debt_to_equity=0.5, debt_to_ebitda=1.0,
                interest_coverage=10, current_ratio=2.0, altman_z_score=5,
                earnings_growth_qoq=0.2, revenue_growth_3y=0.2,
                inst_ownership=0.6, eps_surprise_pct=0.05
            ),
            technicals=Technicals(100.0, 90.0, 80.0, 60.0, 1.0, 0.05, "Bullish", "Rising"),
            projections=Projections(110.0, 130.0, 90.0, 100.0),
            sentiment=Sentiment("Positive", 0.8, 10, None)
        )

    def test_pydantic_validation_success(self):
        """Test that a compliant LLM dict passes Pydantic validation."""
        try:
            parsed = AIResponseSchema.model_validate(self.valid_llm_response)
            self.assertEqual(parsed.confidence_score, 80)
            self.assertEqual(parsed.component_scores.valuation, 8)
        except Exception as e:
            self.fail(f"Pydantic validation failed unexpectedly: {e}")

    def test_pydantic_validation_failure(self):
        """Test that missing required fields throws ValidationError."""
        invalid_response = self.valid_llm_response.copy()
        del invalid_response["component_scores"] # Missing required field
        
        with self.assertRaises(ValidationError):
            AIResponseSchema.model_validate(invalid_response)

    @patch('services.reasoning_scorer.VinSightScorer.evaluate')
    def test_fallback_on_schema_error(self, mock_algo_eval):
        """Test that investigate gracefully falls back to VinSightScorer on bad schema."""
        # Setup Algo mock
        mock_result = MagicMock()
        mock_result.total_score = 65
        mock_result.rating = "Speculative Hold"
        mock_result.verdict_narrative = "Fallback"
        mock_result.breakdown = {}
        mock_result.details = []
        mock_algo_eval.return_value = mock_result
        
        # Force the LLM to return bad JSON
        self.scorer._call_groq = MagicMock(return_value={"bad": "json"})
        self.scorer.provider = "groq"
        
        result = self.scorer.evaluate(self.good_stock, "CFA", None)
        
        # It should catch the ValidationError in evaluate and return the fallback formula
        self.assertEqual(result["score"], 65)
        self.assertEqual(result["meta"]["source"], "Formula Fallback (AI OFFLINE)")

    def test_persona_base_score_math(self):
        """Test that the python logic correctly multiplies AI components by Persona weights."""
        # CFA Weights: Valuation=30, Profitability=30, Growth=20, Health=20, Technicals=0
        # AI Output: Val=8 (80*0.3=24), Prof=7 (70*0.3=21), Growth=9 (90*0.2=18), Health=6 (60*0.2=12)
        # Base Score should be: 24 + 21 + 18 + 12 = 75
        
        mock_algo = MagicMock()
        mock_algo.breakdown = {}
        mock_algo.details = []
        
        result = self.scorer._parse_response(self.valid_llm_response, self.good_stock, "CFA", "Mock", mock_algo)
        
        # Confidence is 80, discount factor is 0.8 + 0.2*(0.8) = 0.96
        # 75 * 0.96 = 72
        self.assertEqual(result["score"], 72)

    def test_solvency_kill_switch(self):
        """Test that Debt/Equity > 2.0 triggers a 20 point penalty."""
        bad_stock = self.good_stock
        bad_stock.fundamentals.debt_to_equity = 2.5 # Trigger Solvency penalty
        bad_stock.fundamentals.revenue_growth_3y = 0.1 # Ensure it doesn't get the 'Growth' persona exemption
        
        mock_algo = MagicMock()
        mock_algo.breakdown = {}
        mock_algo.details = []
        
        # 1. Base Score = 75 (from CFA weights)
        # 2. Kill Switch = -20 (Solvency)
        # 3. Penalized Score = 55
        # 4. Confidence Discount = 55 * 0.96 = 53
        
        result = self.scorer._parse_response(self.valid_llm_response, bad_stock, "CFA", "Mock", mock_algo)
        self.assertEqual(result["score"], 53)
        
        # Ensure the kill switch was explicitly logged in risk factors
        risk_str = " ".join(result["score_explanation"]["factors"])
        self.assertIn("Solvency Risk (-20 pts): Debt/Equity > 2.0", risk_str)

    def test_valuation_trap_kill_switch(self):
        """Test that P/E > 50 and Growth < 10% triggers a 15 point penalty."""
        bad_stock = self.good_stock
        bad_stock.fundamentals.pe_ratio = 60 # Trigger trap
        bad_stock.fundamentals.revenue_growth_3y = 0.05 # low growth
        
        mock_algo = MagicMock()
        
        # Base = 75, Penalty = 15, Penalized = 60, Discounted = 60 * 0.96 = 58
        result = self.scorer._parse_response(self.valid_llm_response, bad_stock, "CFA", "Mock", mock_algo)
        self.assertEqual(result["score"], 58)
        
        risk_str = " ".join(result["score_explanation"]["factors"])
        self.assertIn("Valuation Trap (-15 pts): P/E > 50", risk_str)

if __name__ == '__main__':
    unittest.main()
