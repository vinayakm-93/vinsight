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
    
    logger.info(f"Connecting to database...")
    
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    try:
        with engine.connect() as conn:
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
                # --- Watchlists Schema ---
                logger.info("Checking 'watchlists' schema...")
                if is_postgres:
                    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='watchlists'"))
                else:
                    result = conn.execute(text("PRAGMA table_info(watchlists)"))
                
                wl_columns = [row[0] if is_postgres else row[1] for row in result.fetchall()]
                logger.info(f"Watchlist columns found: {wl_columns}")
                
                if 'position' not in wl_columns:
                    logger.info("Adding 'position' to 'watchlists'")
                    conn.execute(text("ALTER TABLE watchlists ADD COLUMN position INTEGER DEFAULT 0"))
                    conn.commit()
                
                if 'last_summary_at' not in wl_columns:
                    logger.info("Adding 'last_summary_at' to 'watchlists'")
                    conn.execute(text("ALTER TABLE watchlists ADD COLUMN last_summary_at TIMESTAMP"))
                    conn.commit()
                
                if 'last_summary_text' not in wl_columns:
                    logger.info("Adding 'last_summary_text' to 'watchlists'")
                    conn.execute(text("ALTER TABLE watchlists ADD COLUMN last_summary_text TEXT"))
                    conn.commit()

                if 'last_summary_stocks' not in wl_columns:
                    logger.info("Adding 'last_summary_stocks' to 'watchlists'")
                    conn.execute(text("ALTER TABLE watchlists ADD COLUMN last_summary_stocks VARCHAR"))
                    conn.commit()

                # --- Users Schema ---
                logger.info("Checking 'users' schema...")
                if is_postgres:
                    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users'"))
                else:
                    result = conn.execute(text("PRAGMA table_info(users)"))
                
                u_columns = [row[0] if is_postgres else row[1] for row in result.fetchall()]
                logger.info(f"Users columns found: {u_columns}")
                
                # Granular checks to avoid partial failure
                if 'alerts_triggered_this_month' not in u_columns:
                    logger.info("Adding 'alerts_triggered_this_month' to 'users'")
                    conn.execute(text("ALTER TABLE users ADD COLUMN alerts_triggered_this_month INTEGER DEFAULT 0"))
                    conn.commit()
                
                if 'alert_limit' not in u_columns:
                    logger.info("Adding 'alert_limit' to 'users'")
                    conn.execute(text("ALTER TABLE users ADD COLUMN alert_limit INTEGER DEFAULT 30"))
                    conn.commit()
                
                if 'last_alert_reset' not in u_columns:
                    logger.info("Adding 'last_alert_reset' to 'users'")
                    if is_postgres:
                        conn.execute(text("ALTER TABLE users ADD COLUMN last_alert_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
                    else:
                        conn.execute(text("ALTER TABLE users ADD COLUMN last_alert_reset TIMESTAMP DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW'))"))
                    conn.commit()
                
                if 'is_vip' not in u_columns:
                    logger.info("Adding 'is_vip' to 'users'")
                    conn.execute(text("ALTER TABLE users ADD COLUMN is_vip BOOLEAN DEFAULT FALSE"))
                    conn.commit()

                logger.info("Migration check complete.")
                    
            except Exception as e:
                logger.error(f"Migration error: {e}")
                
            finally:
                if is_postgres and lock_acquired:
                    logger.info("Releasing advisory lock...")
                    conn.execute(text("SELECT pg_advisory_unlock(1234567890)"))
                    
    except Exception as e:
        logger.error(f"Failed to connect or migrate: {e}")

if __name__ == "__main__":
    migrate()
