import urllib.parse
from sqlalchemy import create_engine, text

# Get creds from gcloud output
db_user = "vinsight"
db_pass = "ZCBMK:#%\`KB>`H*"
db_host = "34.57.196.253"
db_name = "finance"

# Need to properly escape the password which contains special chars
encoded_pass = urllib.parse.quote_plus(db_pass)
url = f"postgresql://{db_user}:{encoded_pass}@{db_host}:5432/{db_name}"

engine = create_engine(url)

with engine.connect() as conn:
    print("Executing extension creation...")
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    print("Vector extension created successfully.")
    
    print("Creating sec_chunks table...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS sec_chunks (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            section VARCHAR(20),
            content TEXT NOT NULL,
            metadata JSONB,
            embedding vector(384),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    conn.commit()
    print("Table sec_chunks created successfully.")
