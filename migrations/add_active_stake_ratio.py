#!/usr/bin/env python3
"""
Migration script to add active_stake_ratio column to metrics_snap table.
"""

import sqlite3
import os
from pathlib import Path

def migrate():
    """Add active_stake_ratio column to metrics_snap table."""
    
    # Get database path
    db_path = Path("tao.sqlite")
    
    if not db_path.exists():
        print(f"Database file {db_path} not found!")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(metrics_snap)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'active_stake_ratio' in columns:
            print("Column active_stake_ratio already exists in metrics_snap table.")
            return True
        
        # Add the column
        print("Adding active_stake_ratio column to metrics_snap table...")
        cursor.execute("ALTER TABLE metrics_snap ADD COLUMN active_stake_ratio FLOAT")
        
        # Commit changes
        conn.commit()
        print("Successfully added active_stake_ratio column to metrics_snap table.")
        
        return True
        
    except Exception as e:
        print(f"Error during migration: {e}")
        return False
    
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = migrate()
    if success:
        print("Migration completed successfully.")
    else:
        print("Migration failed.")
        exit(1) 