#!/usr/bin/env python3
"""
Migration: Add tao_score_v21 column to metrics_snap table
"""
import sqlite3
import os

def migrate():
    db_path = 'tao.sqlite'
    
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(metrics_snap)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'tao_score_v21' not in columns:
            print("Adding tao_score_v21 column to metrics_snap table...")
            cursor.execute("ALTER TABLE metrics_snap ADD COLUMN tao_score_v21 FLOAT")
            conn.commit()
            print("✓ Added tao_score_v21 column")
        else:
            print("✓ tao_score_v21 column already exists")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate() 