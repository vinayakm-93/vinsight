import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import app AFTER sys.path update (to find modules)
from main import app
from services import finance, analysis, simulation

client = TestClient(app)

class TestAnalysisOptimization(unittest.TestCase):

    @patch('routes.data.finance.get_stock_history')
    @patch('routes.data.finance.get_stock_info')
    @patch('routes.data.finance.get_news')
    @patch('routes.data.finance.get_institutional_holders')
    @patch('routes.data.simulation.run_monte_carlo')
    def test_graceful_degradation_news_failure(self, mock_mc, mock_inst, mock_news, mock_info, mock_hist):
        """
        Test that if GET_NEWS fails, the endpoint still returns 200 and other data.
        """
        print("\nTesting Graceful Degradation: News Failure")
        
        # 1. Setup Mocks
        # History (Essential - must succeed)
        mock_hist.return_value = [
            {'Date': '2023-01-01', 'Open': 100, 'High': 110, 'Low': 90, 'Close': 105, 'Volume': 1000},
            {'Date': '2023-01-02', 'Open': 105, 'High': 115, 'Low': 100, 'Close': 110, 'Volume': 1200}
        ] * 10 # Need enough data for technicals
        
        # Info (Essential)
        mock_info.return_value = {
            'sector': 'Technology', 'trailingPE': 20, 'pegRatio': 1.5, 'beta': 1.2,
            'profitMargins': 0.2, 'debtToEquity': 50
        }
        
        # News (FAILING)
        mock_news.side_effect = Exception("API Timeout")
        
        # Institutional (Success)
        mock_inst.return_value = {'institutionsPercentHeld': 0.6, 'insider_transactions': []}
        
        # Simulation (Success)
        mock_mc.return_value = {'p50': [100, 110], 'p90': [100, 120], 'p10': [100, 90]}
        
        # 2. Execute Request
        response = client.get("/api/data/analysis/AAPL")
        
        # 3. Assertions
        # Should be 200 OK, not 500
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        
        # Verify Critical Data Present
        self.assertIn("ai_analysis", data)
        self.assertIn("simulation", data)
        self.assertIn("institutional", data)
        
        # Verify Failed Data handled gracefully
        # News should be empty list, not crash
        self.assertEqual(data["news"], [])
        
        print("✅ Graceful Degradation Confirmed: News API failure did not crash endpoint.")

    @patch('routes.data.finance.get_stock_history')
    def test_history_failure_fatal(self, mock_hist):
        """
        Test that if HISTORY fails, the endpoint DOES return error (essential data).
        """
        print("\nTesting Essential Failure: History")
        mock_hist.side_effect = Exception("Yahoo Down")
        
        response = client.get("/api/data/analysis/AAPL")
        
        # Should be 404 or 500 depending on handling, but definitely not 200 with partial data
        # Our code raises 404 if history is empty/failed
        self.assertNotEqual(response.status_code, 200)
        print("✅ Essential Failure Confirmed: History failure correctly returns error.")

if __name__ == '__main__':
    unittest.main()
