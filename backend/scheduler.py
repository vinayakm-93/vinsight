import asyncio
import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
from services import alert_checker

class MarketWatcher:
    _instance = None
    _task = None
    _running = False

    @staticmethod
    def start():
        if MarketWatcher._task is None:
            MarketWatcher._running = True
            MarketWatcher._task = asyncio.create_task(MarketWatcher._loop())
            print("Alert Agent: STARTED")

    @staticmethod
    def stop():
        MarketWatcher._running = False
        if MarketWatcher._task:
            MarketWatcher._task.cancel()

    @staticmethod
    async def _loop():
        print("Alert Agent: Entring Watch Loop")
        while MarketWatcher._running:
            try:
                # 1. Market Hours Check (Can be disabled for testing/crypto)
                now = datetime.datetime.now()
                # Assuming crypto/24h for MVP simplicity or check config
                # if now.weekday() < 5 and 9 <= now.hour <= 16:
                
                # 2. Check Alerts
                db = SessionLocal()
                try:
                    await alert_checker.check_alerts(db)
                finally:
                    db.close()

                # 3. Sleep
                await asyncio.sleep(60) # Check every 60s
            except asyncio.CancelledError:
                print("Alert Agent: STOPPING")
                break
            except Exception as e:
                print(f"Alert Agent Error: {e}")
                await asyncio.sleep(60) # Backoff on error
