"""
Migration script to add PasswordReset table
"""
import os
import sys
from sqlalchemy import create_engine

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import Base, PasswordReset

def migrate():
    # Use DATABASE_URL if set, otherwise local SQLite
    SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./backend/finance.db")
    
    connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
    
    # Create only the PasswordReset table
    PasswordReset.__table__.create(bind=engine, checkfirst=True)
    print("✅ PasswordReset table created successfully")

if __name__ == "__main__":
    migrate()
