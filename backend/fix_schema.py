import sys
import os
from sqlalchemy import create_engine, text, inspect
from database import SQLALCHEMY_DATABASE_URL

def fix_schema():
    print(f"Checking schema for database: {SQLALCHEMY_DATABASE_URL}")
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    with engine.connect() as conn:
        inspector = inspect(engine)
        columns = [c['name'] for c in inspector.get_columns('users')]
        
        print(f"Current 'users' columns: {columns}")
        
        if 'guardian_limit' not in columns:
            print("⚠️ 'guardian_limit' missing from 'users'. Adding it...")
            try:
                # SQLite ALTER TABLE ADD COLUMN
                conn.execute(text("ALTER TABLE users ADD COLUMN guardian_limit INTEGER DEFAULT 10"))
                conn.commit()
                print("✅ Added 'guardian_limit' column.")
            except Exception as e:
                print(f"❌ Failed to add column: {e}")
        else:
            print("✅ 'guardian_limit' already exists.")
            
    # Create missing tables
    from models import Base, GuardianThesis, GuardianAlert
    print("Checking for missing tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Schema update complete (Tables created if missing).")

if __name__ == "__main__":
    fix_schema()
