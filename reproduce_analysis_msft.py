import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load env
load_dotenv('backend/.env')

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.earnings import analyze_earnings
from database import SessionLocal
import json

ticker = "MSFT"
print(f"Testing FULL earnings analysis for {ticker}...")

db = SessionLocal()
try:
    from models import EarningsAnalysis
    db.query(EarningsAnalysis).filter(EarningsAnalysis.ticker == ticker).delete()
    db.commit()
    print("Deleted cache entry for MSFT.")

    result = analyze_earnings(ticker, db)
    
    if "error" in result:
        print(f"FAILURE: {result['error']}")
    else:
        print("SUCCESS: Analysis complete.")
        print(json.dumps(result['metadata'], indent=2))
finally:
    db.close()
