
import pytest
from unittest.mock import MagicMock, patch
import os
import sys

# Ensure backend path is in sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.analyst_service import AnalystService

class TestAnalystService:
    @patch('services.analyst_service.Groq')
    def test_chat_mock(self, MockGroq):
        # 1. Setup Mock
        mock_client = MagicMock()
        MockGroq.return_value = mock_client
        
        # Mock response structure
        mock_completion = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "VinSight: Your portfolio is heavily concentrated in Crypto."
        mock_completion.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_completion
        
        # 2. Init Service
        service = AnalystService(api_key="fake_key")
        assert service.is_available()
        
        # 3. Call Chat
        context = {
            "total_value": 10000,
            "positions": [
                {"ticker": "BTC", "weight": 0.8},
                {"ticker": "AAPL", "weight": 0.2}
            ],
            "modifications": ["CONCENTRATION RISK: BTC > 20%"]
        }
        response = service.chat("Is my portfolio risky?", context)
        
        # 4. Verify
        assert "VinSight" in response
        mock_client.chat.completions.create.assert_called_once()
        
        # Verify prompt contained context
        args, kwargs = mock_client.chat.completions.create.call_args
        messages = kwargs['messages']
        assert "CONCENTRATION RISK" in messages[0]['content']

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
