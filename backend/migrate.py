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
    
    # Provide a connection timeout to prevent infinite hangs in Cloud Run
    connect_args = {"connect_timeout": 5} if "postgresql" in SQLALCHEMY_DATABASE_URL else {}
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)

    
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

                if 'thesis_limit' not in u_columns:
                    logger.info("Adding 'thesis_limit' to 'users'")
                    conn.execute(text("ALTER TABLE users ADD COLUMN thesis_limit INTEGER DEFAULT 10"))
                    conn.commit()

                if 'guardian_limit' not in u_columns:
                    logger.info("Adding 'guardian_limit' to 'users'")
                    conn.execute(text("ALTER TABLE users ADD COLUMN guardian_limit INTEGER DEFAULT 10"))
                    conn.commit()

                if 'theses_generated_this_month' not in u_columns:
                    logger.info("Adding 'theses_generated_this_month' to 'users'")
                    conn.execute(text("ALTER TABLE users ADD COLUMN theses_generated_this_month INTEGER DEFAULT 0"))
                    conn.commit()

                logger.info("Migration check complete.")

                # --- Guardian Theses Schema ---
                logger.info("Checking 'guardian_theses' schema...")
                if is_postgres:
                    result = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='guardian_theses')"))
                    gt_exists = result.scalar()
                else:
                    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='guardian_theses'"))
                    gt_exists = result.fetchone() is not None

                if gt_exists:
                    if is_postgres:
                        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='guardian_theses'"))
                    else:
                        result = conn.execute(text("PRAGMA table_info(guardian_theses)"))
                    gt_columns = [row[0] if is_postgres else row[1] for row in result.fetchall()]
                    logger.info(f"Guardian theses columns found: {gt_columns}")

                    if 'last_manual_scan_at' not in gt_columns:
                        logger.info("Adding 'last_manual_scan_at' to 'guardian_theses'")
                        conn.execute(text("ALTER TABLE guardian_theses ADD COLUMN last_manual_scan_at TIMESTAMP"))
                        conn.commit()
                        logger.info("Added 'last_manual_scan_at' column.")
                else:
                    logger.info("'guardian_theses' table does not exist yet, skipping.")

                # --- Guardian Alerts Schema ---
                logger.info("Checking 'guardian_alerts' schema...")
                if is_postgres:
                    result = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='guardian_alerts')"))
                    ga_exists = result.scalar()
                else:
                    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='guardian_alerts'"))
                    ga_exists = result.fetchone() is not None

                if ga_exists:
                    if is_postgres:
                        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='guardian_alerts'"))
                    else:
                        result = conn.execute(text("PRAGMA table_info(guardian_alerts)"))
                    ga_columns = [row[0] if is_postgres else row[1] for row in result.fetchall()]
                    
                    missing_ga = [
                        ('research_history', 'TEXT'),
                        ('thinking_log', 'TEXT'),
                        ('key_evidence', 'TEXT'),
                        ('events_detected', 'TEXT'),
                        ('is_read', 'BOOLEAN DEFAULT FALSE'),
                        ('email_sent', 'BOOLEAN DEFAULT FALSE')
                    ]
                    for col_name, col_type in missing_ga:
                        if col_name not in ga_columns:
                            logger.info(f"Adding '{col_name}' to 'guardian_alerts'")
                            conn.execute(text(f"ALTER TABLE guardian_alerts ADD COLUMN {col_name} {col_type}"))
                            conn.commit()
                else:
                    logger.info("Creating 'guardian_alerts' table...")
                    # Simplified creation, main columns
                    conn.execute(text("""
                        CREATE TABLE guardian_alerts (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER NOT NULL REFERENCES users(id),
                            symbol VARCHAR NOT NULL,
                            thesis_status VARCHAR NOT NULL,
                            confidence FLOAT,
                            reasoning TEXT,
                            recommended_action VARCHAR,
                            research_history TEXT,
                            thinking_log TEXT,
                            key_evidence TEXT,
                            events_detected TEXT,
                            is_read BOOLEAN DEFAULT FALSE,
                            email_sent BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """) if is_postgres else text("""
                        CREATE TABLE guardian_alerts (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL REFERENCES users(id),
                            symbol VARCHAR NOT NULL,
                            thesis_status VARCHAR NOT NULL,
                            confidence FLOAT,
                            reasoning TEXT,
                            recommended_action VARCHAR,
                            research_history TEXT,
                            thinking_log TEXT,
                            key_evidence TEXT,
                            events_detected TEXT,
                            is_read BOOLEAN DEFAULT FALSE,
                            email_sent BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    conn.commit()

                # --- Investment Theses Schema (Thesis Library) ---
                logger.info("Checking 'investment_theses' schema...")
                if is_postgres:
                    result = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='investment_theses')"))
                    it_exists = result.scalar()
                else:
                    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='investment_theses'"))
                    it_exists = result.fetchone() is not None

                if not it_exists:
                    logger.info("Creating 'investment_theses' table...")
                    conn.execute(text("""
                        CREATE TABLE investment_theses (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER NOT NULL REFERENCES users(id),
                            symbol VARCHAR NOT NULL,
                            stance VARCHAR,
                            one_liner TEXT,
                            key_drivers TEXT,
                            primary_risk TEXT,
                            confidence_score INTEGER,
                            content TEXT,
                            sources TEXT,
                            agent_log TEXT,
                            is_edited BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(user_id, symbol)
                        )
                    """) if is_postgres else text("""
                        CREATE TABLE investment_theses (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL REFERENCES users(id),
                            symbol VARCHAR NOT NULL,
                            stance VARCHAR,
                            one_liner TEXT,
                            key_drivers TEXT,
                            primary_risk TEXT,
                            confidence_score INTEGER,
                            content TEXT,
                            sources TEXT,
                            agent_log TEXT,
                            is_edited BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(user_id, symbol)
                        )
                    """))
                    conn.commit()
                else:
                    # Check for missing columns in investment_theses if needed
                    pass

                # --- Portfolio Schema ---
                logger.info("Checking 'portfolios' schema...")
                if is_postgres:
                    result = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='portfolios')"))
                    portfolios_exist = result.scalar()
                else:
                    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='portfolios'"))
                    portfolios_exist = result.fetchone() is not None

                if not portfolios_exist:
                    logger.info("Creating 'portfolios' table...")
                    conn.execute(text("""
                        CREATE TABLE portfolios (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER NOT NULL REFERENCES users(id),
                            name VARCHAR NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            last_summary_at TIMESTAMP,
                            last_summary_text TEXT,
                            last_summary_source VARCHAR,
                            UNIQUE(user_id, name)
                        )
                    """) if is_postgres else text("""
                        CREATE TABLE portfolios (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL REFERENCES users(id),
                            name VARCHAR NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            last_summary_at TIMESTAMP,
                            last_summary_text TEXT,
                            last_summary_source VARCHAR,
                            UNIQUE(user_id, name)
                        )
                    """))
                    conn.commit()
                    logger.info("'portfolios' table created.")

                if is_postgres:
                    result = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='portfolio_holdings')"))
                    holdings_exist = result.scalar()
                else:
                    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='portfolio_holdings'"))
                    holdings_exist = result.fetchone() is not None

                if not holdings_exist:
                    logger.info("Creating 'portfolio_holdings' table...")
                    conn.execute(text("""
                        CREATE TABLE portfolio_holdings (
                            id SERIAL PRIMARY KEY,
                            portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
                            symbol VARCHAR NOT NULL,
                            quantity FLOAT NOT NULL DEFAULT 0,
                            avg_cost FLOAT,
                            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(portfolio_id, symbol)
                        )
                    """) if is_postgres else text("""
                        CREATE TABLE portfolio_holdings (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
                            symbol VARCHAR NOT NULL,
                            quantity FLOAT NOT NULL DEFAULT 0,
                            avg_cost FLOAT,
                            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(portfolio_id, symbol)
                        )
                    """))
                    conn.commit()
                    logger.info("'portfolio_holdings' table created.")

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
