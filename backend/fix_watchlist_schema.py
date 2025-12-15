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
        print("Starting migration to remove UNIQUE constraint from watchlists.name...")

        # 1. Check if table exists
        cursor.execute("DROP TABLE IF EXISTS watchlists_old")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='watchlists'")
        if not cursor.fetchone():
            print("Table 'watchlists' does not exist.")
            return

        # 2. Rename existing table
        print("Renaming 'watchlists' to 'watchlists_old'...")
        cursor.execute("ALTER TABLE watchlists RENAME TO watchlists_old")
        
        # Drop indexes from old table to free up names
        print("Dropping old indexes...")
        cursor.execute("DROP INDEX IF EXISTS ix_watchlists_id")
        cursor.execute("DROP INDEX IF EXISTS ix_watchlists_name") # Might exist if unique=True created it
        cursor.execute("DROP INDEX IF EXISTS ix_watchlists_user_id")
        # Also drop the unique constraint index which might be auto-named like 'sqlite_autoindex_watchlists_1' 
        # but we can't easily drop autoindexes. 
        # However, named indexes from SQLAlchemy (ix_...) are the ones colliding.

        # 3. Create new table without UNIQUE constraint
        print("Creating new 'watchlists' table...")
        # Note: We must recreate the schema exactly as SQLAlchemy would, but WITHOUT UNIQUE on name.
        # Original Schema inferred:
        # id INTEGER PRIMARY KEY AUTOINCREMENT
        # name VARCHAR NOT NULL
        # stocks VARCHAR
        # user_id INTEGER REFERENCES users(id)
        cursor.execute("""
            CREATE TABLE watchlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR NOT NULL,
                stocks VARCHAR DEFAULT "",
                user_id INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        
        # Create index on user_id (optional but good practice as per SA model)
        cursor.execute("CREATE INDEX ix_watchlists_user_id ON watchlists (user_id)")
        cursor.execute("CREATE INDEX ix_watchlists_id ON watchlists (id)")
        # Note: We do NOT create unique index on name

        # 4. Copy data
        print("Copying data from old table...")
        cursor.execute("INSERT INTO watchlists (id, name, stocks, user_id) SELECT id, name, stocks, user_id FROM watchlists_old")

        # 5. Drop old table
        print("Dropping 'watchlists_old'...")
        cursor.execute("DROP TABLE watchlists_old")

        conn.commit()
        print("Migration successful: UNIQUE constraint removed.")

    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
