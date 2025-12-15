import sqlite3
import os

DB_PATH = "finance.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("Adding composite unique constraint (user_id, name) to watchlists...")

        # Check if constraint already exists
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='uq_user_watchlist_name'")
        if cursor.fetchone():
            print("Constraint already exists.")
            return

        # SQLite doesn't support adding constraints to existing tables directly
        # We need to recreate the table
        
        # 1. Create new table with constraint
        print("Creating new table with constraint...")
        cursor.execute("""
            CREATE TABLE watchlists_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR NOT NULL,
                stocks VARCHAR DEFAULT "",
                user_id INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id),
                UNIQUE(user_id, name)
            )
        """)
        
        # 2. Copy data from old table
        print("Copying data...")
        cursor.execute("INSERT INTO watchlists_new (id, name, stocks, user_id) SELECT id, name, stocks, user_id FROM watchlists")
        
        # 3. Drop old table
        print("Dropping old table...")
        cursor.execute("DROP TABLE watchlists")
        
        # 4. Rename new table
        print("Renaming new table...")
        cursor.execute("ALTER TABLE watchlists_new RENAME TO watchlists")
        
        # 5. Recreate indexes
        print("Recreating indexes...")
        cursor.execute("CREATE INDEX ix_watchlists_id ON watchlists (id)")
        cursor.execute("CREATE INDEX ix_watchlists_user_id ON watchlists (user_id)")

        conn.commit()
        print("Migration successful: Composite unique constraint added.")

    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
