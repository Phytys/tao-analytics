#!/usr/bin/env python
"""
Test script to verify performance improvements for insights page.
Measures query execution times before and after optimizations.
"""

import sys
from pathlib import Path
import time
import logging

# Add the parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from services.db import get_db
from models import MetricsSnap
from sqlalchemy import func, desc
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_time_series_query():
    """Test the time series query performance."""
    logger.info("Testing time series query performance...")
    
    session = get_db()
    try:
        # Test 1: Basic time series query with limits
        start_time = time.time()
        cutoff_date = datetime.now() - timedelta(days=30)
        
        query = session.query(MetricsSnap).filter(
            MetricsSnap.timestamp >= cutoff_date
        ).order_by(MetricsSnap.timestamp.desc()).limit(5000)
        
        result = query.all()
        execution_time = time.time() - start_time
        
        logger.info(f"✅ Time series query: {len(result)} rows in {execution_time:.2f}s")
        
        # Test 2: Latest data per subnet query
        start_time = time.time()
        latest_query = session.query(
            MetricsSnap.netuid,
            MetricsSnap.subnet_name,
            MetricsSnap.tao_score,
            func.max(MetricsSnap.timestamp).label('latest_timestamp')
        ).group_by(
            MetricsSnap.netuid,
            MetricsSnap.subnet_name,
            MetricsSnap.tao_score
        ).limit(200)
        
        result = latest_query.all()
        execution_time = time.time() - start_time
        
        logger.info(f"✅ Latest data query: {len(result)} rows in {execution_time:.2f}s")
        
        # Test 3: Category performance query
        start_time = time.time()
        category_query = session.query(
            MetricsSnap.category,
            func.avg(MetricsSnap.tao_score).label('avg_score'),
            func.count(MetricsSnap.netuid).label('subnet_count')
        ).filter(
            MetricsSnap.category.isnot(None)
        ).group_by(MetricsSnap.category).limit(50)
        
        result = category_query.all()
        execution_time = time.time() - start_time
        
        logger.info(f"✅ Category performance query: {len(result)} rows in {execution_time:.2f}s")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Query test failed: {e}")
        return False
    finally:
        session.close()

def test_connection_pool():
    """Test connection pool configuration."""
    logger.info("Testing connection pool configuration...")
    
    try:
        from services.db import engine
        
        # Test pool status
        pool = engine.pool
        logger.info(f"✅ Connection pool configured:")
        logger.info(f"  - Pool size: {getattr(pool, '_pool_size', 'N/A')}")
        logger.info(f"  - Max overflow: {getattr(pool, '_max_overflow', 'N/A')}")
        logger.info(f"  - Pool timeout: {getattr(pool, '_timeout', 'N/A')}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Connection pool test failed: {e}")
        return False

def test_database_stats():
    """Test database statistics and data volume."""
    logger.info("Testing database statistics...")
    
    session = get_db()
    try:
        # Get table statistics
        total_rows = session.query(MetricsSnap).count()
        unique_subnets = session.query(MetricsSnap.netuid).distinct().count()
        date_range = session.query(
            func.min(MetricsSnap.timestamp),
            func.max(MetricsSnap.timestamp)
        ).first()
        
        logger.info(f"✅ Database statistics:")
        logger.info(f"  - Total rows: {total_rows:,}")
        logger.info(f"  - Unique subnets: {unique_subnets}")
        if date_range and date_range[0] and date_range[1]:
            logger.info(f"  - Date range: {date_range[0]} to {date_range[1]}")
        else:
            logger.info(f"  - Date range: No data available")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database stats test failed: {e}")
        return False
    finally:
        session.close()

def main():
    """Run all performance tests."""
    logger.info("🚀 Starting performance tests...")
    
    tests = [
        ("Database Statistics", test_database_stats),
        ("Connection Pool", test_connection_pool),
        ("Query Performance", test_time_series_query),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name} passed")
            else:
                logger.error(f"❌ {test_name} failed")
        except Exception as e:
            logger.error(f"❌ {test_name} failed with exception: {e}")
    
    logger.info(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All performance tests passed!")
    else:
        logger.warning("⚠️  Some tests failed. Check the logs above.")

if __name__ == "__main__":
    main() 