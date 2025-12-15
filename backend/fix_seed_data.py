from backend.database import SessionLocal
from backend.models import Watchlist

def fix_data():
    db = SessionLocal()
    try:
        print("--- Fixing Seed Data ---")
        
        # Energy Giants
        wl1 = db.query(Watchlist).filter(Watchlist.name == "Energy Giants").first()
        if wl1:
            wl1.stocks = "XOM,CVX,SHEL,TTE,COP,BP,EOG,PXD,MPC,PSX"
            print("Updated Energy Giants")

        # Tech Titans
        wl2 = db.query(Watchlist).filter(Watchlist.name == "Tech Titans").first()
        if wl2:
            wl2.stocks = "AAPL,MSFT,GOOGL,AMZN,NVDA,META,TSM,AVGO,ORCL,ADBE"
            print("Updated Tech Titans")

        # Pharma Leaders
        wl3 = db.query(Watchlist).filter(Watchlist.name == "Pharma Leaders").first()
        if wl3:
            wl3.stocks = "LLY,JNJ,MRK,ABBV,NVS,AZN,PFE,AMGN,BMY,GILD"
            print("Updated Pharma Leaders")

        # Chips & Semi
        wl4 = db.query(Watchlist).filter(Watchlist.name == "Chips & Semi").first()
        if wl4:
            wl4.stocks = "NVDA,TSM,AVGO,AMD,QCOM,INTC,TXN,MU,ADI,LRCX"
            print("Updated Chips & Semi")

        db.commit()
        print("Database commit successful.")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_data()
