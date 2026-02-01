import os
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load env vars
load_dotenv()

def migrate():
    # Construct DB URL (similar to database.py)
    SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
    
    if not SQLALCHEMY_DATABASE_URL:
        db_user = os.getenv("DB_USER")
        db_pass = os.getenv("DB_PASS")
        db_name = os.getenv("DB_NAME", "finance")
        cloud_sql_instance = os.getenv("CLOUDSQL_INSTANCE")

        if db_user and db_pass and cloud_sql_instance:
             encoded_pass = quote_plus(db_pass)
             SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg2://{db_user}:{encoded_pass}@/{db_name}?host=/cloudsql/{cloud_sql_instance}"
        else:
            SQLALCHEMY_DATABASE_URL = "sqlite:///./finance.db"
    
    logger.info(f"Connecting to database (Type: {'SQLite' if 'sqlite' in SQLALCHEMY_DATABASE_URL else 'Postgres'})...")
    
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # For PostgreSQL, use advisory lock
            is_postgres = "postgresql" in SQLALCHEMY_DATABASE_URL
            lock_acquired = False
            
            if is_postgres:
                logger.info("Acquiring advisory lock...")
                result = conn.execute(text("SELECT pg_try_advisory_lock(1234567890)"))
                lock_acquired = result.scalar()
                
                if not lock_acquired:
                    logger.info("Migration already in progress by another worker, skipping")
                    return
            
            try:
                # Check for 'position' column in 'watchlists'
                logger.info("Checking schema...")
                if "sqlite" in SQLALCHEMY_DATABASE_URL:
                    result = conn.execute(text("PRAGMA table_info(watchlists)"))
                    columns = [row[1] for row in result.fetchall()]
                else:
                    result = conn.execute(text("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name='watchlists' AND column_name='position';
                    """))
                    columns = [row[0] for row in result.fetchall()]
                
                if 'position' not in columns:
                    logger.info("Migrating: Adding 'position' column to 'watchlists' table")
                    conn.execute(text("ALTER TABLE watchlists ADD COLUMN position INTEGER DEFAULT 0"))
                    conn.commit()
                    logger.info("Migration successful")
                else:
                    logger.info("Column 'position' already exists, no migration needed")
                    
            except Exception as e:
                logger.error(f"Migration error: {e}")
                # Don't re-raise, checking other things
                
            finally:
                if is_postgres and lock_acquired:
                    logger.info("Releasing advisory lock...")
                    conn.execute(text("SELECT pg_advisory_unlock(1234567890)"))
                    
    except Exception as e:
        logger.error(f"Failed to connect or migrate: {e}")

if __name__ == "__main__":
    migrate()
