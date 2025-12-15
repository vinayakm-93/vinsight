from backend.database import SessionLocal
from backend.models import User, Watchlist
from sqlalchemy.orm import joinedload

def verify_data():
    db = SessionLocal()
    try:
        print("--- Verifying Database State ---")
        users = db.query(User).options(joinedload(User.watchlists)).all()
        for user in users:
            print(f"User: {user.email} (ID: {user.id})")
            if not user.watchlists:
                print("  -> No watchlists found!")
            for wl in user.watchlists:
                print(f"  -> Watchlist: {wl.name} (ID: {wl.id})")
                print(f"     Stocks: {wl.stocks}")
        
        if not users:
            print("No users found in database.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_data()
