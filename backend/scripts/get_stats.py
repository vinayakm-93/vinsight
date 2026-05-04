import sys
import os
from datetime import datetime, timedelta

# Ensure we can import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import GuardianAlert, InvestmentThesis

def main():
    db = SessionLocal()
    try:
        seven_days_ago = datetime.utcnow() - timedelta(days=7)

        # Mails sent (GuardianAlerts where email_sent = True)
        mails_sent = db.query(GuardianAlert).filter(
            GuardianAlert.created_at >= seven_days_ago,
            GuardianAlert.email_sent == True
        ).count()
        
        # Total Guardian Alerts
        total_alerts = db.query(GuardianAlert).filter(
            GuardianAlert.created_at >= seven_days_ago
        ).count()

        # Investment Theses generated
        theses_generated = db.query(InvestmentThesis).filter(
            InvestmentThesis.created_at >= seven_days_ago
        ).count()

        print("\n=== SYSTEM ACTIVITY (LAST 7 DAYS) ===")
        print(f"Mails Successfully Sent: {mails_sent}")
        print(f"Total Guardian Agent Evaluations (Alerts Recorded): {total_alerts}")
        print(f"New Investment Theses Generated: {theses_generated}")
        print("======================================\n")
    except Exception as e:
        print(f"Error fetching stats: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
