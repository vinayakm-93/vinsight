import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
from models import GuardianAlert
import json

db = SessionLocal()
try:
    alert = db.query(GuardianAlert).order_by(GuardianAlert.id.desc()).first()
    if alert:
        print(json.dumps({
            "status": alert.thesis_status,
            "confidence": alert.confidence,
            "reasoning": alert.reasoning,
            "key_evidence": alert.key_evidence,
            "events": alert.events_detected
        }, indent=2))
    else:
        print("No alerts found.")
finally:
    db.close()
