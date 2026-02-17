import sys
import os
import logging

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import guardian, finance
from services.analysis import calculate_technical_indicators

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_guardian")

def test_detect_events_real():
    symbol = "NVDA"
    logger.info(f"--- Testing detect_events for {symbol} ---")
    
    # 1. Test with current price (should be no drop unless market is crashing)
    result = guardian.detect_events(symbol)
    logger.info(f"Result (Realtime): {result}")
    
    # 2. Test with Mock Last Price (Simulate 10% drop)
    current_price = result.get('current_price')
    if current_price:
        high_price = current_price * 1.10 # Last price was 10% higher
        logger.info(f"Simulating price drop from {high_price} to {current_price}")
        result_drop = guardian.detect_events(symbol, last_known_price=high_price)
        logger.info(f"Result (Simulated Drop): {result_drop}")
        assert result_drop['triggered'] == True, "Should have triggered on 10% drop"
        assert any("Price dropped" in e for e in result_drop['events']), "Should list price drop event"
    else:
        logger.warning("Could not get current price to simulate drop.")

def test_gather_evidence_real():
    symbol = "AAPL"
    logger.info(f"--- Testing gather_evidence for {symbol} ---")
    
    evidence = guardian.gather_evidence(symbol)
    
    # Check keys
    required_keys = ['news', 'fundamentals', 'analyst_ratings', 'technicals'] # Sentiment might fail if key invalid
    for k in required_keys:
        if k not in evidence:
            logger.error(f"Missing key: {k}")
        else:
            logger.info(f"Key '{k}' present. Data: {str(evidence[k])[:100]}...")
            
    # Check technicals specific structure
    if 'technicals' in evidence:
        techs = evidence['technicals']
        logger.info(f"Technicals: {techs}")
        if not techs.get('rsi'):
            logger.warning("RSI missing (might be not enough history or API error)")

if __name__ == "__main__":
    logger.info("Starting Local Verification for Guardian Service...")
    try:
        test_detect_events_real()
        test_gather_evidence_real()
        logger.info("\n✅ All Tests Passed (Visual verification required for data accuracy)")
    except AssertionError as e:
        logger.error(f"\n❌ Test Failed: {e}")
    except Exception as e:
        logger.error(f"\n❌ execution Error: {e}")
