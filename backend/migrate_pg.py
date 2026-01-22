import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Add current directory to path to import from backend if needed
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    """
    Migration script to add 'position' column to 'watchlists' table in PostgreSQL.
    Uses environment variables for connection.
    """
    # 1. Get Connection URL (matching backend/database.py logic)
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        db_user = os.getenv("DB_USER")
        db_pass = os.getenv("DB_PASS")
        db_name = os.getenv("DB_NAME", "finance")
        cloud_sql_instance = os.getenv("CLOUDSQL_INSTANCE")
        
        if db_user and db_pass and cloud_sql_instance:
            # Check if we are running in a Cloud Run environment (Unix socket) 
            # or locally (requires Cloud SQL Proxy)
            if os.path.exists("/cloudsql"):
                db_url = f"postgresql+psycopg2://{db_user}:{db_pass}@/{db_name}?host=/cloudsql/{cloud_sql_instance}"
            else:
                # Local development via Cloud SQL Proxy (defaulting to localhost:5432)
                logger.info("Local environment detected. Using localhost:5432 for PostgreSQL connection.")
                db_url = f"postgresql+psycopg2://{db_user}:{db_pass}@127.0.0.1:5432/{db_name}"
        else:
            db_url = "sqlite:///./finance.db"
    
    logger.info(f"Connecting to database with URL type: {db_url.split(':')[0]}")
    
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # 2. Check if column exists
            logger.info("Checking for 'position' column in 'watchlists' table...")
            
            if "sqlite" in db_url:
                check_query = text("PRAGMA table_info(watchlists)")
                result = conn.execute(check_query)
                columns = [row[1] for row in result.fetchall()]
            else:
                # PostgreSQL check
                check_query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='watchlists' AND column_name='position';
                """)
                result = conn.execute(check_query)
                columns = [row[0] for row in result.fetchall()]
            
            if 'position' not in columns:
                logger.info("Adding 'position' column...")
                conn.execute(text("ALTER TABLE watchlists ADD COLUMN position INTEGER DEFAULT 0"))
                
                # 3. Initialize positions
                logger.info("Initializing positions for existing watchlists...")
                # Fetch all watchlists ordered by user and ID
                select_query = text("SELECT id, user_id FROM watchlists ORDER BY user_id, id")
                rows = conn.execute(select_query).fetchall()
                
                user_counts = {}
                for row in rows:
                    w_id, u_id = row[0], row[1]
                    if u_id not in user_counts:
                        user_counts[u_id] = 0
                    else:
                        user_counts[u_id] += 1
                    
                    update_query = text("UPDATE watchlists SET position = :pos WHERE id = :id")
                    conn.execute(update_query, {"pos": user_counts[u_id], "id": w_id})
                
                conn.commit()
                logger.info("Migration successful!")
            else:
                logger.info("Column 'position' already exists. Nothing to do.")
                
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()
