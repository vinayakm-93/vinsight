import logging
import os
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_guardian")

from database import engine, SQLALCHEMY_DATABASE_URL

def migrate_guardian():
    url = SQLALCHEMY_DATABASE_URL
    # engine is already created in database.py, but we can reuse it or create new one.
    # To be safe with pool settings, let's just use the imported engine.
    
    logger.info(f"Starting Guardian migration on {url.split('@')[-1] if '@' in url else 'sqlite'}")

    try:
        with engine.connect() as conn:
            # Check if using PostgreSQL for locking
            is_postgres = "postgresql" in url
            if is_postgres:
                conn.execute(text("SELECT pg_advisory_lock(1234567890)")) # Arbitrary lock ID
            
            inspector = inspect(engine)
            
            # --- 1. User Table Updates ---
            columns = [c['name'] for c in inspector.get_columns("users")]
            if "guardian_limit" not in columns:
                logger.info("Adding 'guardian_limit' to 'users' table")
                conn.execute(text("ALTER TABLE users ADD COLUMN guardian_limit INTEGER DEFAULT 10"))
                conn.commit()
            else:
                logger.info("'guardian_limit' already exists in 'users'")

            # --- 2. Create Guardian Tables ---
            existing_tables = inspector.get_table_names()
                        
            # guardian_theses
            if "guardian_theses" not in existing_tables:
                logger.info("Creating 'guardian_theses' table")
                create_theses_sql = """
                CREATE TABLE guardian_theses (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    symbol VARCHAR NOT NULL,
                    thesis TEXT NOT NULL,
                    auto_generated BOOLEAN DEFAULT TRUE,
                    is_active BOOLEAN DEFAULT TRUE,
                    last_checked_at TIMESTAMP,
                    last_price FLOAT,
                    check_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    CONSTRAINT uq_user_guardian_thesis UNIQUE (user_id, symbol)
                );
                """
                # Adjust for SQLite if needed (SERIAL -> INTEGER PRIMARY KEY AUTOINCREMENT)
                if not is_postgres:
                     create_theses_sql = create_theses_sql.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
                     create_theses_sql = create_theses_sql.replace("TIMESTAMP DEFAULT NOW()", "DATETIME DEFAULT CURRENT_TIMESTAMP")
                
                conn.execute(text(create_theses_sql))
                conn.commit()
            else:
                logger.info("'guardian_theses' table already exists")

            # guardian_alerts
            if "guardian_alerts" not in existing_tables:
                logger.info("Creating 'guardian_alerts' table")
                create_alerts_sql = """
                CREATE TABLE guardian_alerts (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    symbol VARCHAR NOT NULL,
                    thesis_status VARCHAR NOT NULL,
                    confidence FLOAT,
                    reasoning TEXT,
                    recommended_action VARCHAR,
                    key_evidence TEXT,
                    events_detected TEXT,
                    is_read BOOLEAN DEFAULT FALSE,
                    email_sent BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                """
                if not is_postgres:
                     create_alerts_sql = create_alerts_sql.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
                     create_alerts_sql = create_alerts_sql.replace("TIMESTAMP DEFAULT NOW()", "DATETIME DEFAULT CURRENT_TIMESTAMP")

                conn.execute(text(create_alerts_sql))
                conn.commit()
            else:
                logger.info("'guardian_alerts' table already exists")

            if is_postgres:
                conn.execute(text("SELECT pg_advisory_unlock(1234567890)"))

            logger.info("Guardian migration completed successfully.")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate_guardian()
