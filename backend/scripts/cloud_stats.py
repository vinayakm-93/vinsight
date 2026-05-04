import sys
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus

# Read creds
with open('../db_user.txt') as f: db_user = f.read().strip()
with open('../db_pass.txt') as f: db_pass = f.read().strip()

encoded_pass = quote_plus(db_pass)
SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg2://{db_user}:{encoded_pass}@127.0.0.1:5433/finance"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# To import models, add backend to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import GuardianAlert, InvestmentThesis

def main():
    db = SessionLocal()
    try:
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        mails = db.query(GuardianAlert).filter(GuardianAlert.created_at >= seven_days_ago, GuardianAlert.email_sent == True).count()
        alerts = db.query(GuardianAlert).filter(GuardianAlert.created_at >= seven_days_ago).count()
        theses = db.query(InvestmentThesis).filter(InvestmentThesis.created_at >= seven_days_ago).count()

        print("\n=== CLOUD PRODUCTION ACTIVITY (LAST 7 DAYS) ===")
        print(f"Mails Successfully Sent: {mails}")
        print(f"Total Guardian Agent Evaluations (Alerts Recorded): {alerts}")
        print(f"New Investment Theses Generated: {theses}")
        print("=================================================\n")
    except Exception as e:
        print(f"Error querying cloud db: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
