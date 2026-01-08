import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# Use DATABASE_URL if set, or construct from components (Secrets), otherwise local SQLite
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    # Check if we have Cloud SQL credentials (e.g. from Secrets)
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASS")
    db_name = os.getenv("DB_NAME", "finance")
    cloud_sql_instance = os.getenv("CLOUDSQL_INSTANCE")

    if db_user and db_pass and cloud_sql_instance:
         # URL-encode password to handle special characters
         encoded_pass = quote_plus(db_pass)
         SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg2://{db_user}:{encoded_pass}@/{db_name}?host=/cloudsql/{cloud_sql_instance}"
    else:
        # Fallback to local SQLite
        SQLALCHEMY_DATABASE_URL = "sqlite:///./finance.db"

check_same_thread = False
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    connect_args = {"check_same_thread": False}
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args=connect_args
    )
else:
    # Production / Cloud SQL (PostgreSQL)
    # Recommended pool settings for Cloud Run
    connect_args = {}
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Self-healing Migration: Ensure 'position' column exists
    # SQLAlchemy create_all does not add columns to existing tables
    try:
        with engine.connect() as conn:
            # For PostgreSQL, use advisory lock to prevent concurrent migrations
            is_postgres = "postgresql" in SQLALCHEMY_DATABASE_URL
            lock_acquired = False
            
            if is_postgres:
                # Try to acquire advisory lock (arbitrary lock ID: 1234567890)
                # pg_try_advisory_lock returns true if lock acquired, false if already held
                result = conn.execute(text("SELECT pg_try_advisory_lock(1234567890)"))
                lock_acquired = result.scalar()
                
                if not lock_acquired:
                    logger.info("Migration already in progress by another worker, skipping")
                    return
            
            try:
                if "sqlite" in SQLALCHEMY_DATABASE_URL:
                    # SQLite check
                    result = conn.execute(text("PRAGMA table_info(watchlists)"))
                    columns = [row[1] for row in result.fetchall()]
                else:
                    # PostgreSQL check
                    result = conn.execute(text("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name='watchlists' AND column_name='position';
                    """))
                    columns = [row[0] for row in result.fetchall()]
                
                if 'position' not in columns:
                    logger.info("Migrating database: Adding 'position' column to 'watchlists' table")
                    conn.execute(text("ALTER TABLE watchlists ADD COLUMN position INTEGER DEFAULT 0"))
                    conn.commit()
                    logger.info("Migration successful")
                else:
                    logger.info("Column 'position' already exists, no migration needed")
                    
            except Exception as e:
                # Check if error is "column already exists" (can happen in race condition)
                error_str = str(e).lower()
                if "already exists" in error_str or "duplicate column" in error_str:
                    logger.info("Column 'position' already exists (caught during migration attempt)")
                else:
                    raise  # Re-raise if it's a different error
                    
            finally:
                # Release advisory lock if we acquired it
                if is_postgres and lock_acquired:
                    conn.execute(text("SELECT pg_advisory_unlock(1234567890)"))
                    
    except Exception as e:
        logger.warning(f"Database migration (position column) skipped or failed: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
