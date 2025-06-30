"""
Automated Data Collection for TAO Analytics.
Replaces manual scripts with scheduled collection.
"""

import argparse
import schedule
import time
import sys
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.quota_guard import QuotaGuard, QuotaExceededError
from scripts.data_collection.fetch_screener import main as fetch_subnet_screener
from scripts.data_collection.fetch_coingecko_data import main as fetch_coingecko_data
from services.db import get_db
from services.db_utils import get_database_type
from services.bittensor.metrics import calculate_subnet_metrics
from services.bittensor.async_metrics import collect_all_subnet_metrics_async, collect_all_subnet_metrics_sync
from models import MetricsSnap, SubnetMeta, ScreenerRaw

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/cron_fetch.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def log_data_collection(session, source: str, method: str, success: bool, details: str = ""):
    """Log data collection activity."""
    try:
        # Simple logging for now - can be enhanced with database logging later
        logger.info(f"Data collection: {source} via {method} - {'SUCCESS' if success else 'FAILED'} - {details}")
    except Exception as e:
        logger.error(f"Error logging data collection: {e}")

def safe_fetch_subnet_screener():
    """Safely call fetch_subnet_screener with error handling."""
    try:
        fetch_subnet_screener()
        return True
    except Exception as e:
        logger.error(f"Error in fetch_subnet_screener: {e}")
        return False

def safe_fetch_coingecko_data():
    """Safely call fetch_coingecko_data with error handling."""
    try:
        fetch_coingecko_data()
        return True
    except Exception as e:
        logger.error(f"Error in fetch_coingecko_data: {e}")
        return False

class CronFetch:
    """Automated data collection with quota management."""
    
    def __init__(self):
        """Initialize cron fetch system."""
        self.quota_guard = QuotaGuard()
        self.session = get_db()
        
        # Ensure logs directory exists
        Path('logs').mkdir(exist_ok=True)
    
    def fetch_subnet_data(self):
        """Fetch subnet screener data with quota enforcement."""
        try:
            logger.info("Starting subnet screener fetch...")
            
            # Check quota before making call
            if not self.quota_guard.check_quota('/subnet_screener'):
                logger.error("Quota exceeded for subnet screener")
                return False
            
            # Fetch data
            success = safe_fetch_subnet_screener()
            
            if success:
                # Increment quota count
                new_count = self.quota_guard.increment_call_count('/subnet_screener')
                logger.info(f"Subnet screener fetch successful. Quota count: {new_count}")
                
                # Log collection
                log_data_collection(
                    self.session,
                    'subnet_screener',
                    'automated',
                    success=True,
                    details=f"Quota count: {new_count}"
                )
                return True
            else:
                logger.error("Subnet screener fetch failed")
                log_data_collection(
                    self.session,
                    'subnet_screener', 
                    'automated',
                    success=False,
                    details="Fetch failed"
                )
                return False
                
        except QuotaExceededError as e:
            logger.error(f"Quota exceeded: {e}")
            return False
        except Exception as e:
            logger.error(f"Error in subnet screener fetch: {e}")
            log_data_collection(
                self.session,
                'subnet_screener',
                'automated', 
                success=False,
                details=f"Error: {str(e)}"
            )
            return False
    
    def fetch_coingecko_data(self):
        """Fetch CoinGecko data with quota enforcement."""
        try:
            logger.info("Starting CoinGecko data fetch...")
            
            # Check quota before making call
            if not self.quota_guard.check_quota('/analytics/macro/aggregated'):
                logger.error("Quota exceeded for CoinGecko analytics")
                return False
            
            # Fetch data
            success = safe_fetch_coingecko_data()
            
            if success:
                # Increment quota count
                new_count = self.quota_guard.increment_call_count('/analytics/macro/aggregated')
                logger.info(f"CoinGecko fetch successful. Quota count: {new_count}")
                
                # Log collection
                log_data_collection(
                    self.session,
                    'coingecko_data',
                    'automated',
                    success=True,
                    details=f"Quota count: {new_count}"
                )
                return True
            else:
                logger.error("CoinGecko fetch failed")
                log_data_collection(
                    self.session,
                    'coingecko_data',
                    'automated',
                    success=False,
                    details="Fetch failed"
                )
                return False
                
        except QuotaExceededError as e:
            logger.error(f"Quota exceeded: {e}")
            return False
        except Exception as e:
            logger.error(f"Error in CoinGecko fetch: {e}")
            log_data_collection(
                self.session,
                'coingecko_data',
                'automated',
                success=False,
                details=f"Error: {str(e)}"
            )
            return False
    
    def fetch_sdk_snapshot(self):
        """Fetch SDK metrics snapshot for all subnets with improved reliability."""
        try:
            logger.info("Starting SDK metrics snapshot...")
            
            # Get current timestamp for snapshot
            snapshot_time = datetime.utcnow()
            
            # Get list of all subnets from screener data
            with get_db() as session:
                screener_data = session.query(ScreenerRaw.netuid).distinct().all()
                
                subnet_ids = [row[0] for row in screener_data]
                
                if not subnet_ids:
                    logger.warning("No subnet data available for SDK snapshot")
                    return False
                
                logger.info(f"Collecting SDK metrics for {len(subnet_ids)} subnets...")
                
                # Try async collection first with reduced concurrency
                metrics_list = []
                success_rate = 0
                
                try:
                    import asyncio
                    logger.info("Attempting async SDK collection with 4 workers...")
                    metrics_list = asyncio.run(collect_all_subnet_metrics_async(subnet_ids, max_workers=4))
                    
                    # Calculate success rate
                    successful_metrics = [m for m in metrics_list if "error" not in m or not m["error"]]
                    success_rate = (len(successful_metrics) / len(subnet_ids)) * 100
                    
                    logger.info(f"Async collection completed with {success_rate:.1f}% success rate")
                    
                    # If success rate is too low, try sync fallback
                    if success_rate < 40:
                        logger.warning(f"Low async success rate ({success_rate:.1f}%), trying sync fallback...")
                        sync_metrics = collect_all_subnet_metrics_sync(subnet_ids)
                        sync_successful = [m for m in sync_metrics if "error" not in m or not m["error"]]
                        sync_success_rate = (len(sync_successful) / len(subnet_ids)) * 100
                        
                        if sync_success_rate > success_rate:
                            logger.info(f"Sync fallback improved success rate to {sync_success_rate:.1f}%")
                            metrics_list = sync_metrics
                            success_rate = sync_success_rate
                        else:
                            logger.info(f"Sync fallback didn't improve success rate ({sync_success_rate:.1f}%), keeping async results")
                    
                except Exception as e:
                    logger.warning(f"Async collection failed, falling back to sync: {e}")
                    metrics_list = collect_all_subnet_metrics_sync(subnet_ids)
                    successful_metrics = [m for m in metrics_list if "error" not in m or not m["error"]]
                    success_rate = (len(successful_metrics) / len(subnet_ids)) * 100
                    logger.info(f"Sync collection completed with {success_rate:.1f}% success rate")
                
                # Log overall success rate
                if success_rate < 30:
                    logger.error(f"Very low success rate ({success_rate:.1f}%). Network connectivity issues detected.")
                elif success_rate < 60:
                    logger.warning(f"Moderate success rate ({success_rate:.1f}%). Some subnets may be temporarily unavailable.")
                else:
                    logger.info(f"Good success rate ({success_rate:.1f}%). Collection proceeding normally.")
                
                successful_snapshots = 0
                failed_snapshots = 0
                
                for metrics in metrics_list:
                    try:
                        if "error" in metrics and metrics["error"]:
                            logger.debug(f"Error getting metrics for subnet {metrics['netuid']}: {metrics['error']}")
                            failed_snapshots += 1
                            continue
                        
                        netuid = metrics['netuid']
                        
                        # Get subnet metadata for reference
                        subnet_meta = session.query(SubnetMeta).filter_by(netuid=netuid).first()
                        
                        # Create metrics snapshot record with all new fields
                        snapshot = MetricsSnap(
                            timestamp=snapshot_time,
                            netuid=netuid,
                            
                            # Market metrics (will be filled from screener data later)
                            market_cap_tao=None,  # TODO: Join with screener data
                            flow_24h=None,        # TODO: Join with screener data
                            price_tao=None,       # TODO: Join with screener data
                            
                            # SDK metrics
                            total_stake_tao=metrics.get('total_stake_tao'),
                            stake_hhi=metrics.get('stake_hhi'),
                            uid_count=metrics.get('uid_count'),
                            mean_incentive=metrics.get('mean_incentive'),
                            p95_incentive=metrics.get('p95_incentive'),
                            consensus_alignment=metrics.get('consensus_alignment'),
                            trust_score=metrics.get('trust_score'),
                            mean_consensus=metrics.get('mean_consensus'),
                            pct_aligned=metrics.get('pct_aligned'),
                            
                            # Emission metrics
                            emission_owner=metrics.get('emission_split', {}).get('owner'),
                            emission_miners=metrics.get('emission_split', {}).get('miners'),
                            emission_validators=metrics.get('emission_split', {}).get('validators'),
                            total_emission_tao=metrics.get('total_emission_tao'),
                            tao_in_emission=metrics.get('tao_in_emission'),
                            alpha_out_emission=metrics.get('alpha_out_emission'),
                            
                            # Network activity metrics
                            active_validators=metrics.get('active_validators'),
                            
                            # Metadata
                            subnet_name=subnet_meta.subnet_name if subnet_meta else None,
                            category=subnet_meta.primary_category if subnet_meta else None,
                            confidence=subnet_meta.confidence if subnet_meta else None
                        )
                        
                        session.add(snapshot)
                        successful_snapshots += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing subnet {metrics.get('netuid', 'unknown')}: {e}")
                        failed_snapshots += 1
                        continue
                
                # Commit all snapshots
                session.commit()
                
                final_success_rate = (successful_snapshots / len(subnet_ids)) * 100
                logger.info(f"SDK snapshot complete: {successful_snapshots} successful, {failed_snapshots} failed ({final_success_rate:.1f}% final success rate)")
                
                # Log collection with success rate
                log_data_collection(
                    self.session,
                    'sdk_snapshot',
                    'automated',
                    success=successful_snapshots > 0,
                    details=f"Processed {successful_snapshots}/{len(subnet_ids)} subnets ({final_success_rate:.1f}% success)"
                )
                
                return successful_snapshots > 0
                
        except Exception as e:
            logger.error(f"Error in SDK snapshot: {e}")
            log_data_collection(
                self.session,
                'sdk_snapshot',
                'automated',
                success=False,
                details=f"Error: {str(e)}"
            )
            return False
    
    def nightly_collection(self):
        """Nightly data collection (all sources)."""
        logger.info("Starting nightly data collection...")
        
        results = {
            'subnet_screener': self.fetch_subnet_data(),
            'coingecko': self.fetch_coingecko_data(),
            'sdk_snapshot': self.fetch_sdk_snapshot()
        }
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        logger.info(f"Nightly collection complete: {success_count}/{total_count} successful")
        
        # Log overall collection
        log_data_collection(
            self.session,
            'nightly_collection',
            'automated',
            success=success_count > 0,
            details=f"Results: {results}"
        )
        
        return results
    
    def hourly_collection(self):
        """Hourly data collection (subnet screener only)."""
        logger.info("Starting hourly subnet data collection...")
        
        success = self.fetch_subnet_data()
        
        logger.info(f"Hourly collection complete: {'success' if success else 'failed'}")
        
        # Log overall collection
        log_data_collection(
            self.session,
            'hourly_collection',
            'automated',
            success=success,
            details="Subnet screener only"
        )
        
        return success
    
    def run_once(self, collection_type: str):
        """Run collection once."""
        logger.info(f"Running {collection_type} collection once...")
        
        if collection_type == 'nightly':
            return self.nightly_collection()
        elif collection_type == 'hourly':
            return self.hourly_collection()
        elif collection_type == 'subnet':
            return self.fetch_subnet_data()
        elif collection_type == 'coingecko':
            return self.fetch_coingecko_data()
        elif collection_type == 'sdk_snapshot':
            return self.fetch_sdk_snapshot()
        else:
            logger.error(f"Unknown collection type: {collection_type}")
            return False
    
    def start_scheduler(self):
        """Start the scheduled collection."""
        logger.info("Starting scheduled data collection...")
        
        # Schedule nightly collection at 2 AM
        schedule.every().day.at("02:00").do(self.nightly_collection)
        logger.info("Scheduled nightly collection at 02:00")
        
        # Schedule hourly collection every hour
        schedule.every().hour.do(self.hourly_collection)
        logger.info("Scheduled hourly collection every hour")
        
        # Run initial collection
        logger.info("Running initial collection...")
        self.nightly_collection()
        
        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

def main():
    """CLI interface for cron fetch."""
    parser = argparse.ArgumentParser(description="TAO Analytics Automated Data Collection")
    parser.add_argument("--once", type=str, choices=['nightly', 'hourly', 'subnet', 'coingecko', 'sdk_snapshot'],
                       help="Run collection once")
    parser.add_argument("--schedule", action="store_true", help="Start scheduled collection")
    parser.add_argument("--test", action="store_true", help="Test collection without quota enforcement")
    
    args = parser.parse_args()
    
    cron = CronFetch()
    
    if args.once:
        result = cron.run_once(args.once)
        print(f"Collection result: {result}")
        sys.exit(0 if result else 1)
    
    elif args.schedule:
        try:
            cron.start_scheduler()
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            sys.exit(0)
    
    elif args.test:
        logger.info("Running test collection...")
        # Test without quota enforcement
        try:
            subnet_result = safe_fetch_subnet_screener()
            coingecko_result = safe_fetch_coingecko_data()
            print(f"Test results - Subnet: {subnet_result}, CoinGecko: {coingecko_result}")
        except Exception as e:
            logger.error(f"Test failed: {e}")
            sys.exit(1)
    
    else:
        # Default: show help
        parser.print_help()

if __name__ == "__main__":
    main() 