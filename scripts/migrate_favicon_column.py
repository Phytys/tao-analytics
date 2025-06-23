#!/usr/bin/env python3
"""
Database migration to add favicon_url column to subnet_meta table.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import DB_URL
from sqlalchemy import create_engine, text

def migrate_favicon_column():
    """Add favicon_url column to subnet_meta table."""
    print("🔧 Starting database migration...")
    
    engine = create_engine(DB_URL)
    
    try:
        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("PRAGMA table_info(subnet_meta)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'favicon_url' in columns:
                print("✅ favicon_url column already exists")
                return
            
            # Add the column
            print("📝 Adding favicon_url column...")
            conn.execute(text("ALTER TABLE subnet_meta ADD COLUMN favicon_url TEXT"))
            conn.commit()
            
            print("✅ Migration completed successfully!")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate_favicon_column() 