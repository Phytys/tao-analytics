#!/usr/bin/env python3
"""
Migration: Add tao_score_v21 column to metrics_snap table (Postgres/Heroku compatible)
"""
import os
from sqlalchemy import create_engine, text

DB_URL = os.environ.get("DATABASE_URL")
if DB_URL and DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)
print(f"Using DB_URL: {DB_URL}")

def migrate():
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        # Check if column already exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'metrics_snap' 
            AND column_name = 'tao_score_v21'
        """))
        if result.fetchone():
            print("✓ tao_score_v21 column already exists")
            return
        # Add the column
        print("Adding tao_score_v21 column to metrics_snap table...")
        conn.execute(text("""
            ALTER TABLE metrics_snap ADD COLUMN tao_score_v21 FLOAT
        """))
        print("✓ Successfully added tao_score_v21 column to metrics_snap table")

if __name__ == "__main__":
    migrate() 