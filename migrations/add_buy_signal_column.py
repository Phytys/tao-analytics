"""
Migration to add buy_signal column to metrics_snap table.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from config import DB_URL

def migrate():
    """Add buy_signal column to metrics_snap table."""
    engine = create_engine(DB_URL)
    
    with engine.connect() as conn:
        # Check if column already exists
        result = conn.execute(text("PRAGMA table_info(metrics_snap)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'buy_signal' not in columns:
            # Add buy_signal column
            conn.execute(text("ALTER TABLE metrics_snap ADD COLUMN buy_signal INTEGER"))
            conn.commit()
            print("Added buy_signal column to metrics_snap table")
        else:
            print("buy_signal column already exists in metrics_snap table")

if __name__ == "__main__":
    migrate() 