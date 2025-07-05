#!/usr/bin/env python3
"""
Migration to add buy_signal column to metrics_snap table.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db import get_db
from sqlalchemy import text

def migrate():
    """Add buy_signal column to metrics_snap table."""
    print("Adding buy_signal column to metrics_snap table...")
    
    try:
        with get_db() as session:
            # Check if column already exists (PostgreSQL syntax)
            result = session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'metrics_snap' 
                AND column_name = 'buy_signal'
            """))
            
            if result.fetchone():
                print("✓ buy_signal column already exists")
                return True
            
            # Add the column
            session.execute(text("""
                ALTER TABLE metrics_snap 
                ADD COLUMN buy_signal INTEGER
            """))
            
            session.commit()
            print("✓ Successfully added buy_signal column to metrics_snap table")
            return True
            
    except Exception as e:
        print(f"❌ Error adding buy_signal column: {e}")
        return False

if __name__ == "__main__":
    migrate() 