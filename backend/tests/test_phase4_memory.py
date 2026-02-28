import unittest
from unittest.mock import patch, MagicMock
from services.score_memory import save_score, get_history
from datetime import datetime, timedelta

class TestPhase4Memory(unittest.TestCase):

    @patch('services.score_memory.SessionLocal')
    def test_save_score_first_time(self, mock_session):
        """Test saving a score when no previous history exists."""
        db = MagicMock()
        mock_session.return_value = db
        
        # Mock no existing record
        mock_query = db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_order = mock_filter.order_by.return_value
        mock_order.first.return_value = None
        
        saved = save_score("AAPL", 85.0, "High Conviction", 150.0)
        
        self.assertTrue(saved)
        db.add.assert_called_once()
        db.commit.assert_called_once()

    @patch('services.score_memory.SessionLocal')
    def test_save_score_throttle_24h(self, mock_session):
        """Test that a save is skipped if <24h have passed and price is stable."""
        db = MagicMock()
        mock_session.return_value = db
        
        # Mock recent record (2 hours ago)
        mock_record = MagicMock()
        mock_record.created_at = datetime.utcnow() - timedelta(hours=2)
        mock_record.price = 150.0
        
        mock_query = db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_order = mock_filter.order_by.return_value
        mock_order.first.return_value = mock_record
        
        # Current price unchanged
        saved = save_score("AAPL", 85.0, "High Conviction", 150.0)
        
        self.assertFalse(saved)
        db.add.assert_not_called()

    @patch('services.score_memory.SessionLocal')
    def test_save_score_volatility_bypass(self, mock_session):
        """Test that the 24h throttle is bypassed if price swings >3%."""
        db = MagicMock()
        mock_session.return_value = db
        
        # Mock recent record (2 hours ago) at $100
        mock_record = MagicMock()
        mock_record.created_at = datetime.utcnow() - timedelta(hours=2)
        mock_record.price = 100.0
        
        mock_query = db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_order = mock_filter.order_by.return_value
        mock_order.first.return_value = mock_record
        
        # Current price $90 (10% drop - highly volatile)
        saved = save_score("AAPL", 40.0, "Underperform", 90.0)
        
        self.assertTrue(saved)
        db.add.assert_called_once()
        db.commit.assert_called_once()

    @patch('services.score_memory.SessionLocal')
    def test_get_history_formatting(self, mock_session):
        """Test that history fetches correctly format the output list."""
        db = MagicMock()
        mock_session.return_value = db
        
        m1 = MagicMock(score=80.0, rating="Buy", price=145.0, created_at=datetime(2026, 1, 1))
        m2 = MagicMock(score=75.0, rating="Watchlist", price=140.0, created_at=datetime(2026, 1, 2))
        
        mock_query = db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_order = mock_filter.order_by.return_value
        mock_limit = mock_order.limit.return_value
        mock_limit.all.return_value = [m1, m2]
        
        history = get_history("AAPL", 2)
        
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['score'], 80.0)
        self.assertEqual(history[0]['date'], "2026-01-01")

if __name__ == '__main__':
    unittest.main()
