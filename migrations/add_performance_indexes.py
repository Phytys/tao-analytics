#!/usr/bin/env python
"""
Migration: Add Performance Indexes for Insights Page
Adds critical indexes to improve query performance on Heroku PostgreSQL.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text, Index
from models import Base, MetricsSnap
from config import DB_URL, ACTIVE_DATABASE_URL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_performance_indexes():
    """Add critical indexes for performance optimization."""
    
    # Create engine
    engine = create_engine(DB_URL, echo=False)
    
    try:
        with engine.connect() as conn:
            logger.info("Adding performance indexes...")
            
            # 1. Composite index for time-series queries by subnet (most critical)
            logger.info("Adding composite index on (netuid, timestamp)...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_metrics_snap_netuid_timestamp 
                ON metrics_snap (netuid, timestamp DESC)
            """))
            
            # 2. Index on timestamp for date range queries
            logger.info("Adding index on timestamp...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_metrics_snap_timestamp 
                ON metrics_snap (timestamp DESC)
            """))
            
            # 3. Index on subnet_name for search queries
            logger.info("Adding index on subnet_name...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_metrics_snap_subnet_name 
                ON metrics_snap (subnet_name)
            """))
            
            # 4. Index on category for filtering
            logger.info("Adding index on category...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_metrics_snap_category 
                ON metrics_snap (category)
            """))
            
            # 5. Index on tao_score for ranking queries
            logger.info("Adding index on tao_score...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_metrics_snap_tao_score 
                ON metrics_snap (tao_score DESC)
            """))
            
            # 6. Index on price_7d_change for improvement tracking
            logger.info("Adding index on price_7d_change...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_metrics_snap_price_7d_change 
                ON metrics_snap (price_7d_change DESC)
            """))
            
            # 7. Index on buy_signal for signal analysis
            logger.info("Adding index on buy_signal...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_metrics_snap_buy_signal 
                ON metrics_snap (buy_signal DESC)
            """))
            
            # Commit the changes
            conn.commit()
            logger.info("✅ All performance indexes added successfully!")
            
            # Verify indexes were created (database-agnostic)
            try:
                if ACTIVE_DATABASE_URL.startswith("postgresql://"):
                    # PostgreSQL verification
                    result = conn.execute(text("""
                        SELECT indexname, tablename 
                        FROM pg_indexes 
                        WHERE tablename = 'metrics_snap' 
                        AND indexname LIKE 'idx_metrics_snap_%'
                        ORDER BY indexname
                    """))
                else:
                    # SQLite verification
                    result = conn.execute(text("""
                        SELECT name as indexname, tbl_name as tablename
                        FROM sqlite_master 
                        WHERE type = 'index' 
                        AND tbl_name = 'metrics_snap' 
                        AND name LIKE 'idx_metrics_snap_%'
                        ORDER BY name
                    """))
                
                indexes = result.fetchall()
                logger.info(f"Created {len(indexes)} indexes:")
                for index in indexes:
                    logger.info(f"  - {index[0]}")
            except Exception as e:
                logger.warning(f"Could not verify indexes: {e}")
                logger.info("Indexes were created successfully (verification skipped)")
                
    except Exception as e:
        logger.error(f"❌ Error adding indexes: {e}")
        raise
    finally:
        engine.dispose()

if __name__ == "__main__":
    add_performance_indexes() 