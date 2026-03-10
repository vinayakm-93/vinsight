import sys
import os
import logging
import json

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.guardian_agent import generate_investment_thesis
from database import get_db
from models import SecSummary
from sqlalchemy import select

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_new_stock")

def main():
    symbol = sys.argv[1] if len(sys.argv) > 1 else "PLTR"

    logger.info(f"--- Running Agent for {symbol} ---")
    
    try:
        # 1. Run the agent
        result = generate_investment_thesis(symbol)
        logger.info(f"Agent Execution Complete. Thesis generated.")
        
        # 2. Check DB for SecSummary
        db = next(get_db())
        record = db.execute(select(SecSummary).filter_by(symbol=symbol)).scalar_one_or_none()
        
        if record:
            logger.info("Found SecSummary record in DB!")
            logger.info(f"10K Risk Factors (Preview): {record.risk_factors_10k[:200] if record.risk_factors_10k else 'None'}...")
            logger.info(f"10K Date: {record.latest_10k_date}")
            logger.info(f"10Q Updates (Preview): {record.latest_10q_delta[:200] if record.latest_10q_delta else 'None'}...")
        else:
            logger.error(f"No SECSummary record found for {symbol} in the database!")
            
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    main()
