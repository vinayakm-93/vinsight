import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "finance.db")

def migrate():
    print(f"Connecting to database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Add new columns to users table
        print("Checking users table columns...")
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'thesis_limit' not in columns:
            print("Adding thesis_limit to users...")
            cursor.execute("ALTER TABLE users ADD COLUMN thesis_limit INTEGER DEFAULT 10")
            
        if 'theses_generated_this_month' not in columns:
            print("Adding theses_generated_this_month to users...")
            cursor.execute("ALTER TABLE users ADD COLUMN theses_generated_this_month INTEGER DEFAULT 0")
        
        # Create investment_theses table
        print("Creating investment_theses table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS investment_theses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol VARCHAR NOT NULL,
                stance VARCHAR,
                one_liner VARCHAR,
                key_drivers TEXT,
                primary_risk TEXT,
                confidence_score FLOAT,
                content TEXT,
                sources TEXT,
                agent_log TEXT,
                is_edited BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # Add indices
        print("Creating indices...")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_investment_theses_symbol ON investment_theses (symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_investment_theses_user_id ON investment_theses (user_id)")
        
        conn.commit()
        print("Migration complete!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
