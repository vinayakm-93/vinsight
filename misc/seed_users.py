from backend.database import SessionLocal, init_db
from backend.models import User, Watchlist

def seed_existing_users():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            # Check if has watchlist
            wl = db.query(Watchlist).filter(Watchlist.user_id == user.id).first()
            if not wl:
                print(f"Adding watchlist for {user.email}")
                new_wl = Watchlist(
                    name="My First List",
                    user_id=user.id,
                    stocks="AAPL,NVDA,GOOGL,MSFT,TSLA"
                )
                db.add(new_wl)
            else:
                print(f"User {user.email} already has watchlist: {wl.name}")
        
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    seed_existing_users()
