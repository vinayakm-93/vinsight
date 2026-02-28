import os
from sqlalchemy import create_engine, text
from database import SQLALCHEMY_DATABASE_URL

def migrate_score_history():
    print(f"Connecting to DB: {SQLALCHEMY_DATABASE_URL}")
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    with engine.connect() as conn:
        print("Creating score_history table if it doesn't exist...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS score_history (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR NOT NULL,
                score DOUBLE PRECISION NOT NULL,
                rating VARCHAR NOT NULL,
                price DOUBLE PRECISION NOT NULL,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_score_history_symbol 
            ON score_history (symbol);
        """))
        conn.commit()
        print("Migration complete.")

if __name__ == "__main__":
    migrate_score_history()
