"""
Data Migration Script for TAO Analytics.
Handles transition from manual to automated data collection.
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import get_db
from services.quota_guard import QuotaGuard
from sqlalchemy import text, func
from models import ScreenerRaw, CoinGeckoPrice, SubnetMeta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/data_migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataMigration:
    """Handles data migration and validation for automated collection."""
    
    def __init__(self):
        """Initialize data migration system."""
        self.session = get_db()
        self.quota_guard = QuotaGuard()
        
        # Ensure logs directory exists
        Path('logs').mkdir(exist_ok=True)
    
    def analyze_data_freshness(self):
        """Analyze data freshness across all tables."""
        logger.info("Analyzing data freshness...")
        
        analysis = {}
        
        # Check ScreenerRaw data
        try:
            latest_screener = self.session.execute(
                text("SELECT MAX(fetched_at) as latest FROM screener_raw")
            ).fetchone()
            
            if latest_screener and latest_screener[0]:
                latest_screener_time = latest_screener[0]
                if isinstance(latest_screener_time, str):
                    latest_screener_time = datetime.fromisoformat(latest_screener_time.replace('Z', '+00:00'))
                age_hours = (datetime.utcnow() - latest_screener_time).total_seconds() / 3600
                
                analysis['screener_raw'] = {
                    'latest': latest_screener_time,
                    'age_hours': age_hours,
                    'fresh': age_hours < 24,  # Consider fresh if less than 24 hours
                    'count': self.session.execute(text("SELECT COUNT(*) FROM screener_raw")).fetchone()[0]
                }
            else:
                analysis['screener_raw'] = {
                    'latest': None,
                    'age_hours': None,
                    'fresh': False,
                    'count': 0
                }
        except Exception as e:
            logger.error(f"Error analyzing screener_raw: {e}")
            analysis['screener_raw'] = {'error': str(e)}
        
        # Check CoinGecko data (table name is 'coingecko')
        try:
            latest_coingecko = self.session.execute(
                text("SELECT MAX(fetched_at) as latest FROM coingecko")
            ).fetchone()
            
            if latest_coingecko and latest_coingecko[0]:
                latest_coingecko_time = latest_coingecko[0]
                if isinstance(latest_coingecko_time, str):
                    latest_coingecko_time = datetime.fromisoformat(latest_coingecko_time.replace('Z', '+00:00'))
                age_hours = (datetime.utcnow() - latest_coingecko_time).total_seconds() / 3600
                
                analysis['coingecko'] = {
                    'latest': latest_coingecko_time,
                    'age_hours': age_hours,
                    'fresh': age_hours < 24,  # Consider fresh if less than 24 hours
                    'count': self.session.execute(text("SELECT COUNT(*) FROM coingecko")).fetchone()[0]
                }
            else:
                analysis['coingecko'] = {
                    'latest': None,
                    'age_hours': None,
                    'fresh': False,
                    'count': 0
                }
        except Exception as e:
            logger.error(f"Error analyzing coingecko: {e}")
            analysis['coingecko'] = {'error': str(e)}
        
        # Check SubnetMeta data
        try:
            analysis['subnet_meta'] = {
                'count': self.session.execute(text("SELECT COUNT(*) FROM subnet_meta")).fetchone()[0],
                'enriched_count': self.session.execute(
                    text("SELECT COUNT(*) FROM subnet_meta WHERE tagline IS NOT NULL")
                ).fetchone()[0]
            }
        except Exception as e:
            logger.error(f"Error analyzing subnet_meta: {e}")
            analysis['subnet_meta'] = {'error': str(e)}
        
        return analysis
    
    def validate_data_integrity(self):
        """Validate data integrity across tables."""
        logger.info("Validating data integrity...")
        
        issues = []
        
        # Check for orphaned records
        try:
            # Check for screener_raw records without corresponding subnet_meta
            orphaned_screener = self.session.execute(text("""
                SELECT COUNT(*) FROM screener_raw sr
                LEFT JOIN subnet_meta sm ON sr.netuid = sm.netuid
                WHERE sm.netuid IS NULL
            """)).fetchone()[0]
            
            if orphaned_screener > 0:
                issues.append(f"Found {orphaned_screener} orphaned screener_raw records")
        except Exception as e:
            issues.append(f"Error checking orphaned screener records: {e}")
        
        # Check for duplicate netuids in screener_raw
        try:
            duplicates = self.session.execute(text("""
                SELECT netuid, COUNT(*) as count
                FROM screener_raw
                GROUP BY netuid
                HAVING COUNT(*) > 1
            """)).fetchall()
            
            if duplicates:
                issues.append(f"Found {len(duplicates)} netuids with duplicate screener records")
        except Exception as e:
            issues.append(f"Error checking duplicate screener records: {e}")
        
        # Check for recent data gaps
        try:
            # Check if we have data from the last 7 days
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_screener = self.session.execute(
                text("SELECT COUNT(*) FROM screener_raw WHERE fetched_at >= :week_ago"),
                {"week_ago": week_ago}
            ).fetchone()[0]
            
            if recent_screener == 0:
                issues.append("No screener data from the last 7 days")
            
            # Check coingecko table if it exists
            try:
                recent_coingecko = self.session.execute(
                    text("SELECT COUNT(*) FROM coingecko WHERE fetched_at >= :week_ago"),
                    {"week_ago": week_ago}
                ).fetchone()[0]
                
                if recent_coingecko == 0:
                    issues.append("No CoinGecko data from the last 7 days")
            except Exception:
                issues.append("CoinGecko table does not exist")
        except Exception as e:
            issues.append(f"Error checking recent data: {e}")
        
        return issues
    
    def backup_manual_data(self):
        """Create backup of current manual data."""
        logger.info("Creating backup of manual data...")
        
        try:
            # Create backup tables with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Backup screener_raw
            self.session.execute(text(f"""
                CREATE TABLE screener_raw_backup_{timestamp} AS 
                SELECT * FROM screener_raw
            """))
            
            # Backup coingecko (if table exists)
            try:
                self.session.execute(text(f"""
                    CREATE TABLE coingecko_backup_{timestamp} AS 
                    SELECT * FROM coingecko
                """))
            except Exception:
                logger.warning("CoinGecko table does not exist, skipping backup")
            
            # Backup subnet_meta
            self.session.execute(text(f"""
                CREATE TABLE subnet_meta_backup_{timestamp} AS 
                SELECT * FROM subnet_meta
            """))
            
            self.session.commit()
            logger.info(f"Backup created with timestamp: {timestamp}")
            return timestamp
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            self.session.rollback()
            return None
    
    def cleanup_old_data(self, days_to_keep=30):
        """Clean up old data to prevent database bloat."""
        logger.info(f"Cleaning up data older than {days_to_keep} days...")
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        try:
            # Clean up old screener_raw data
            screener_result = self.session.execute(
                text("DELETE FROM screener_raw WHERE fetched_at < :cutoff"),
                {"cutoff": cutoff_date}
            )
            screener_deleted = screener_result.rowcount if hasattr(screener_result, 'rowcount') else 0
            
            # Clean up old coingecko data (if table exists)
            coingecko_deleted = 0
            try:
                coingecko_result = self.session.execute(
                    text("DELETE FROM coingecko WHERE fetched_at < :cutoff"),
                    {"cutoff": cutoff_date}
                )
                coingecko_deleted = coingecko_result.rowcount if hasattr(coingecko_result, 'rowcount') else 0
            except Exception:
                logger.warning("CoinGecko table does not exist, skipping cleanup")
            
            self.session.commit()
            
            logger.info(f"Cleaned up {screener_deleted} screener records and {coingecko_deleted} coingecko records")
            return {'screener_deleted': screener_deleted, 'coingecko_deleted': coingecko_deleted}
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            self.session.rollback()
            return None
    
    def migrate_to_automated(self, dry_run=True, force=False):
        """Migrate from manual to automated data collection."""
        logger.info(f"Starting migration to automated collection (dry_run={dry_run}, force={force})")
        
        # Analyze current state
        analysis = self.analyze_data_freshness()
        issues = self.validate_data_integrity()
        
        print("\n📊 Data Analysis:")
        print("=" * 50)
        
        for table, data in analysis.items():
            if 'error' in data:
                print(f"❌ {table}: ERROR - {data['error']}")
            else:
                if table == 'screener_raw':
                    status = "✅" if data['fresh'] else "⚠️"
                    print(f"{status} {table}: {data['count']} records, latest: {data['latest']} ({data['age_hours']:.1f}h ago)")
                elif table == 'coingecko':
                    status = "✅" if data['fresh'] else "⚠️"
                    print(f"{status} {table}: {data['count']} records, latest: {data['latest']} ({data['age_hours']:.1f}h ago)")
                elif table == 'subnet_meta':
                    print(f"📋 {table}: {data['count']} total, {data['enriched_count']} enriched")
        
        if issues:
            print(f"\n⚠️ Data Integrity Issues ({len(issues)}):")
            for issue in issues:
                print(f"  - {issue}")
        
        # Check if migration is safe
        can_migrate = True
        if not force:
            if issues:
                print(f"\n❌ Migration blocked: {len(issues)} data integrity issues found")
                can_migrate = False
            
            if not analysis.get('screener_raw', {}).get('fresh', False):
                print("\n❌ Migration blocked: Screener data is not fresh (< 24h)")
                can_migrate = False
            
            if not analysis.get('coingecko', {}).get('fresh', False):
                print("\n❌ Migration blocked: CoinGecko data is not fresh (< 24h)")
                can_migrate = False
        
        if not can_migrate and not force:
            print("\n💡 Use --force to override these checks")
            return False
        
        if dry_run:
            print(f"\n🔍 DRY RUN - Migration would proceed:")
            print("  - Create backup of current data")
            print("  - Clean up old data (>30 days)")
            print("  - Initialize quota tracking")
            print("  - Ready for automated collection")
            return True
        
        # Perform actual migration
        print(f"\n🚀 Performing migration...")
        
        # Create backup
        backup_timestamp = self.backup_manual_data()
        if not backup_timestamp:
            print("❌ Migration failed: Could not create backup")
            return False
        
        # Clean up old data
        cleanup_result = self.cleanup_old_data()
        if cleanup_result is None:
            print("❌ Migration failed: Could not clean up old data")
            return False
        
        # Initialize quota tracking (already done by quota_guard)
        print("✅ Quota tracking initialized")
        
        print(f"\n✅ Migration completed successfully!")
        print(f"  - Backup created: {backup_timestamp}")
        print(f"  - Cleaned up: {cleanup_result['screener_deleted']} screener, {cleanup_result['coingecko_deleted']} coingecko records")
        print(f"  - Ready for automated collection")
        
        return True

def main():
    """CLI interface for data migration."""
    parser = argparse.ArgumentParser(description="TAO Analytics Data Migration")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--force", action="store_true", help="Force migration even if issues are found")
    parser.add_argument("--analyze", action="store_true", help="Only analyze data, don't migrate")
    parser.add_argument("--backup", action="store_true", help="Only create backup")
    parser.add_argument("--cleanup", action="store_true", help="Only clean up old data")
    
    args = parser.parse_args()
    
    migration = DataMigration()
    
    if args.analyze:
        analysis = migration.analyze_data_freshness()
        issues = migration.validate_data_integrity()
        
        print("\n📊 Data Analysis:")
        print("=" * 50)
        
        for table, data in analysis.items():
            if 'error' in data:
                print(f"❌ {table}: ERROR - {data['error']}")
            else:
                if table == 'screener_raw':
                    status = "✅" if data['fresh'] else "⚠️"
                    print(f"{status} {table}: {data['count']} records, latest: {data['latest']} ({data['age_hours']:.1f}h ago)")
                elif table == 'coingecko':
                    status = "✅" if data['fresh'] else "⚠️"
                    print(f"{status} {table}: {data['count']} records, latest: {data['latest']} ({data['age_hours']:.1f}h ago)")
                elif table == 'subnet_meta':
                    print(f"📋 {table}: {data['count']} total, {data['enriched_count']} enriched")
        
        if issues:
            print(f"\n⚠️ Data Integrity Issues ({len(issues)}):")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\n✅ No data integrity issues found")
    
    elif args.backup:
        timestamp = migration.backup_manual_data()
        if timestamp:
            print(f"✅ Backup created: {timestamp}")
        else:
            print("❌ Backup failed")
            sys.exit(1)
    
    elif args.cleanup:
        result = migration.cleanup_old_data()
        if result:
            print(f"✅ Cleanup completed: {result['screener_deleted']} screener, {result['coingecko_deleted']} coingecko records")
        else:
            print("❌ Cleanup failed")
            sys.exit(1)
    
    else:
        # Default: migrate
        success = migration.migrate_to_automated(dry_run=args.dry_run, force=args.force)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 