import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))
from database import SessionLocal
from models import VerificationCode, EarningsAnalysis

db = SessionLocal()
print("Checking VerificationCode...")
codes = db.query(VerificationCode).all()
print(f"Found {len(codes)} codes.")
for c in codes:
    print(f"  {c.email}: {c.code}")

print("\nChecking EarningsAnalysis...")
earnings = db.query(EarningsAnalysis).all()
print(f"Found {len(earnings)} earnings.")
for e in earnings:
    print(f"  {e.ticker} {e.quarter} {e.year}")
