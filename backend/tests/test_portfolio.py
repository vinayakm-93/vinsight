
import pytest
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from services.vinsight_scorer import PortfolioScorer, Portfolio, Position, StockData, Fundamentals, Technicals, Sentiment, Projections
from services.importer import load_portfolio_from_csv

# Helper to create a dummy CSV file
def create_dummy_csv(path):
    with open(path, 'w') as f:
        f.write("Ticker,Type,Shares,AvgCost\n")
        f.write("AAPL,Equity,10,150.0\n")
        f.write("BTC,Crypto,0.1,60000.0\n")
        f.write("VOO,ETF,5,400.0\n")
        f.write("USD,Cash,1000,1.0\n")

class TestPortfolioScorer:
    def setup_method(self):
        self.scorer = PortfolioScorer()
        self.csv_path = "dummy_portfolio.csv"
        create_dummy_csv(self.csv_path)
        
    def teardown_method(self):
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)
            
    def test_load_and_score(self):
        # 1. Load Data
        portfolio = load_portfolio_from_csv(self.csv_path)
        assert len(portfolio.positions) == 3
        # Cash check
        assert portfolio.cash == 1000.0
        
        # 2. Score
        result = self.scorer.evaluate(portfolio)
        
        # 3. Verify
        print(f"\nPortfolio Score: {result.total_score}")
        print(f"Rating: {result.rating}")
        print(f"Modifications: {result.modifications}")
        
        assert result.total_score > 0
        assert len(result.holdings_summary) == 3
        
        # Check weighted Score math roughly
        # Total Value approx: (10*157.5) + (0.1*63000) + (5*420) + 1000 = 1575 + 6300 + 2100 + 1000 = ~11000
        # Weights: Apple ~14%, BTC ~57%, VOO ~19%
        # BTC Scorer (Mock Data) -> High Score (Rising Hash, High Vol) -> Probably > 70
        # If BTC is 57% and high score, total should be decent.
        
        # Check Concentration Penalty
        # BTC is > 50% of portfolio value. Should trigger penalty.
        assert "CONCENTRATION RISK" in result.modifications[0]

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
