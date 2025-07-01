"""
Migration: Add rank percentage columns for expert-level GPT insights.

This adds percentage-based ranking fields that GPT can use for expert commentary
without needing to regurgitate raw numbers.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import get_db
from sqlalchemy import text

def migrate():
    """Add rank percentage columns to metrics_snap table."""
    print("Adding rank percentage columns to metrics_snap...")
    
    with get_db() as session:
        # Add new columns for rank percentages
        columns_to_add = [
            "stake_quality_rank_pct INTEGER",  # Top X% in category
            "momentum_rank_pct INTEGER",       # Top X% in category  
            "validator_util_pct INTEGER",      # 28/256 = 11%
            "buy_sell_ratio FLOAT"             # buy_vol / sell_vol
        ]
        
        for column_def in columns_to_add:
            try:
                column_name = column_def.split()[0]
                session.execute(text(f"ALTER TABLE metrics_snap ADD COLUMN {column_def}"))
                print(f"✓ Added {column_name}")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print(f"⚠ Column {column_name} already exists")
                else:
                    print(f"✗ Error adding {column_name}: {e}")
        
        session.commit()
        print("Migration completed!")

if __name__ == "__main__":
    migrate() 