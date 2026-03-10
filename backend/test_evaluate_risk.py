import sys
import os
import logging
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.guardian_agent import evaluate_risk_agentic
from services.guardian import gather_evidence

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_evaluate_risk")

def main():
    symbol = "CRWD"
    logger.info(f"--- Running Agentic Risk Evaluation for {symbol} ---")
    
    # 1. Gather Evidence
    logger.info("Gathering evidence...")
    evidence = gather_evidence(symbol)
    
    # 2. Define a strong, specific original thesis to defend
    thesis = "Long CRWD based on its dominant Falcon platform and network effects in endpoint security. Key risk is execution missteps or severe breaches impacting trust."
    
    # 3. Define the triggering events (simulating a recent news break or price drop)
    events = ["Recent earnings report showed slowing ARR growth.", "Lingering concerns over the July 19th outage fallout and pricing pressure."]
    
    scan_id = "test_scan_001"
    
    try:
        # Run the full agentic loop
        result = evaluate_risk_agentic(symbol, thesis, events, evidence, scan_id=scan_id)
        
        logger.info("\n==================================")
        logger.info("      AGENT EVALUATION RESULT")
        logger.info("==================================")
        print(json.dumps(result, indent=2))
            
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    main()
