import sys
import os
import time

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))

from database import engine, init_db
from sqlalchemy import text

def init_cloud_db():
    print("Initializing Cloud SQL Database...")
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable is not set.")
        print("Usage: DATABASE_URL='postgresql+psycopg2://...' python3 scripts/init_cloud_db.py")
        sys.exit(1)
    
    print(f"Target Database: {db_url}")
    
    try:
        # Try to connect
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("Connection successful!")
            
        print("Creating tables...")
        init_db()
        print("Tables created successfully!")
        
    except Exception as e:
        print(f"\nCRITICAL ERROR: Could not connect to database.")
        print(f"Details: {e}")
        print("\nTroubleshooting:")
        print("1. If running locally, are you using Cloud SQL Auth Proxy?")
        print("2. Is the DB user/pass correct?")
        print("3. Does the database 'finance' exist associated with the user?")

if __name__ == "__main__":
    init_cloud_db()
