import sys
import os

# Add backend directory to path so we can import models and database
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))

from database import engine
from models import Base

def create_new_tables():
    print("Creating new tables...")
    try:
        # This will create tables that don't exist yet
        # It won't affect existing tables (safe to run)
        Base.metadata.create_all(bind=engine)
        print("Successfully created 'verification_codes' and 'earnings_analysis' tables (if they didn't exist).")
    except Exception as e:
        print(f"Error creating tables: {e}")

if __name__ == "__main__":
    create_new_tables()
