"""
Automated Data Collection for TAO Analytics.
Replaces manual scripts with scheduled collection.
"""

import argparse
import schedule
import time
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Optional
import asyncio

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
from models import MetricsSnap, SubnetMeta, ScreenerRaw, DailyEmissionStats, ApiQuota, GptInsightsNew
from services.calc_metrics import calculate_all_metrics, validate_metrics, calculate_reserve_momentum, calculate_emission_roi
import numpy as np
from services.bittensor.async_utils import run_blocking

# Configure logging
import os
# Ensure logs directory exists
Path('logs').mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/cron_fetch.log') if os.path.exists('logs') else logging.NullHandler(),
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
        
        # Ensure logs directory exists (only if we can write to it)
        try:
            Path('logs').mkdir(exist_ok=True)
        except Exception:
            pass  # Ignore if we can't create logs directory
    
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
    
    def fetch_daily_emission_stats(self, netuid: int, session) -> Optional[float]:
        """
        Fetch daily emission stats using the efficient diff method.
        
        Args:
            netuid: Subnet ID
            session: Database session
            
        Returns:
            Daily emission in TAO, or None if failed
        """
        try:
            import bittensor as bt
            
            # Get current block
            sub = bt.subtensor()
            head = sub.get_current_block()
            
            # Try native RPC first (SDK ≥9.8)
            delta = None
            method = None
            
            if hasattr(sub, "emission_since"):
                try:
                    tao_prev = sub.emission_since(block=head-199, netuid=netuid)  # 200 blocks ago
                    tao_now = sub.emission_since(block=head, netuid=netuid)
                    delta = tao_now - tao_prev
                    method = "native"
                    logger.debug(f"Subnet {netuid}: Using native emission_since RPC")
                except Exception as e:
                    logger.debug(f"Subnet {netuid}: Native emission_since failed: {e}")
                    delta = None
                    method = None
            
            # Fallback to two-metagraph diff
            if delta is None:
                try:
                    import asyncio
                    from services.bittensor.async_utils import run_blocking
                    import bittensor as bt

                    async def fetch_metagraphs():
                        mg_prev, mg_now = await asyncio.gather(
                            run_blocking(lambda: bt.subtensor().metagraph(netuid=netuid, block=head-199, lite=True)),
                            run_blocking(lambda: bt.subtensor().metagraph(netuid=netuid, block=head, lite=True)),
                        )
                        return mg_prev, mg_now

                    # Run async function
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    mg_prev, mg_now = loop.run_until_complete(fetch_metagraphs())
                    loop.close()

                    delta = mg_now.tao_in_emission.sum() - mg_prev.tao_in_emission.sum()
                    method = "diff-200-unweighted"
                    logger.info(f"Subnet {netuid}: Using metagraph diff method (diff-200-unweighted)")

                except Exception as e:
                    logger.error(f"Subnet {netuid}: Both emission methods failed: {e}")
                    return None
            
            # Convert and store (only if method is not unweighted)
            if delta is not None and "unweighted" not in method:
                daily_emission_tao = delta / 1e9  # RAO → TAO
                
                # Store in daily_emission_stats
                today = datetime.utcnow().date()
                emission_stat = DailyEmissionStats(
                    netuid=netuid,
                    date=today,
                    tao_emission=daily_emission_tao,
                    method=method
                )
                session.add(emission_stat)
                session.commit()
                logger.info(f"daily_emission_stats insert ok method={method} netuid={netuid} value={daily_emission_tao}")
                
                return daily_emission_tao
            elif delta is not None and "unweighted" in method:
                logger.debug(f"Subnet {netuid}: Skipping emission stats (unweighted method)")
                return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching daily emission for subnet {netuid}: {e}")
            return None

    def fetch_sdk_snapshot(self, limit: int = None):
        """Fetch SDK metrics snapshot for all subnets with optimized performance."""
        try:
            logger.info("Starting SDK metrics snapshot...")
            
            # Check for test mode
            fast_test_mode = os.getenv("FAST_METRICS_TEST", "0").lower() in ("1", "true", "yes")
            
            # Get current timestamp for snapshot
            snapshot_time = datetime.utcnow()
            
            # Get list of subnets from screener data
            with get_db() as session:
                screener_data = session.query(ScreenerRaw.netuid).distinct().all()
                
                all_subnet_ids = [row[0] for row in screener_data]
                
                # Apply test mode or limit
                if fast_test_mode:
                    # Sample subnets for fast testing
                    sample_subnets = [1, 3, 4, 11, 64, 100]
                    subnet_ids = [netuid for netuid in sample_subnets if netuid in all_subnet_ids]
                    logger.info(f"FAST_METRICS_TEST mode: Processing {len(subnet_ids)} sample subnets: {subnet_ids}")
                elif limit:
                    subnet_ids = all_subnet_ids[:limit]
                    logger.info(f"Limited to {len(subnet_ids)} subnets for testing: {subnet_ids}")
                else:
                    # Process in batches to avoid memory issues on Heroku
                    batch_size = 32  # Process 32 subnets at a time
                    subnet_ids = all_subnet_ids[:batch_size]
                    logger.info(f"Processing {len(subnet_ids)} subnets in batch (total available: {len(all_subnet_ids)})")
                
                logger.info(f"Total subnets available: {len(all_subnet_ids)}")
                
                # OPTIMIZATION: Pre-fetch yesterday's TAO-in data for all subnets in a single query
                logger.info("Pre-fetching yesterday's TAO-in data for all subnets...")
                yesterday = snapshot_time - timedelta(days=1)
                yesterday_data = session.query(MetricsSnap.netuid, MetricsSnap.tao_in)\
                    .filter(MetricsSnap.netuid.in_(subnet_ids))\
                    .filter(MetricsSnap.timestamp >= yesterday)\
                    .order_by(MetricsSnap.netuid, MetricsSnap.timestamp.desc())\
                    .all()
                
                # Create lookup dictionary for yesterday's TAO-in data
                yesterday_tao_in_lookup = {}
                for netuid, tao_in in yesterday_data:
                    if netuid not in yesterday_tao_in_lookup:  # Keep only the most recent
                        yesterday_tao_in_lookup[netuid] = tao_in
                
                logger.info(f"Pre-fetched yesterday's data for {len(yesterday_tao_in_lookup)} subnets")
            
            # OPTIMIZATION: Pre-fetch all subnet metadata in a single query
            logger.info("Pre-fetching subnet metadata for all subnets...")
            subnet_metadata = session.query(SubnetMeta).filter(SubnetMeta.netuid.in_(subnet_ids)).all()
            subnet_meta_lookup = {meta.netuid: meta for meta in subnet_metadata}
            logger.info(f"Pre-fetched metadata for {len(subnet_meta_lookup)} subnets")
            
            # OPTIMIZATION: Pre-fetch all latest screener data in a single query
            logger.info("Pre-fetching latest screener data for all subnets...")
            from sqlalchemy import func
            latest_screener_subquery = session.query(
                ScreenerRaw.netuid,
                func.max(ScreenerRaw.fetched_at).label('max_fetched_at')
            ).filter(ScreenerRaw.netuid.in_(subnet_ids)).group_by(ScreenerRaw.netuid).subquery()
            
            latest_screeners = session.query(ScreenerRaw).join(
                latest_screener_subquery,
                (ScreenerRaw.netuid == latest_screener_subquery.c.netuid) &
                (ScreenerRaw.fetched_at == latest_screener_subquery.c.max_fetched_at)
            ).all()
            
            screener_lookup = {screener.netuid: screener for screener in latest_screeners}
            logger.info(f"Pre-fetched screener data for {len(screener_lookup)} subnets")
            
            # OPTIMIZATION: Pre-fetch max_validators for all subnets in bulk
            logger.info("Pre-fetching max_validators for all subnets...")
            max_validators_lookup = {}
            try:
                import bittensor as bt
                sub = bt.subtensor()
                for netuid in subnet_ids:
                    try:
                        subnet_info = sub.get_subnet_info(netuid)
                        max_validators_lookup[netuid] = subnet_info.max_allowed_validators
                    except Exception as e:
                        logger.warning(f"Failed to get max_validators for subnet {netuid}: {e}")
                        max_validators_lookup[netuid] = None
                logger.info(f"Pre-fetched max_validators for {len(max_validators_lookup)} subnets")
            except Exception as e:
                logger.warning(f"Failed to pre-fetch max_validators: {e}")
            
            if not subnet_ids:
                logger.warning("No subnet data available for SDK snapshot")
                return False
            
            logger.info(f"Collecting SDK metrics for {len(subnet_ids)} subnets...")
            
            # Try async collection with optimized settings
            metrics_list = []
            success_rate = 0
            
            # Determine worker count and collection mode
            if fast_test_mode:
                max_workers = 4
                logger.info("FAST_METRICS_TEST mode: Using 4 workers with lite metagraphs")
            else:
                max_workers = 4  # Reduced from 16 to avoid memory issues on Heroku
                logger.info(f"Production mode: Using {max_workers} workers with full metagraphs")
            
            try:
                logger.info(f"Attempting async SDK collection with {max_workers} workers...")
                metrics_list = asyncio.run(collect_all_subnet_metrics_async(subnet_ids, max_workers=max_workers, lite_mode=fast_test_mode))
                
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
            
            logger.info(f"Processing {len(metrics_list)} subnet metrics...")
            
            for i, metrics in enumerate(metrics_list):
                try:
                    if "error" in metrics and metrics["error"]:
                        logger.debug(f"Error getting metrics for subnet {metrics['netuid']}: {metrics['error']}")
                        failed_snapshots += 1
                        continue
                    
                    netuid = metrics['netuid']
                    
                    # Get subnet metadata for reference
                    subnet_meta = subnet_meta_lookup.get(netuid)
                    
                    # Get latest screener data for price/flow metrics
                    latest_screener = screener_lookup.get(netuid)
                    
                    # OPTIMIZATION: Use pre-fetched yesterday's data instead of individual query
                    yesterday_tao_in = yesterday_tao_in_lookup.get(netuid)
                    
                    # Skip emission ROI until SDK 9.8+ is available
                    daily_emission_tao = None
                    
                    # Fetch max_validators from SDK for validator utilization calculation
                    max_validators = max_validators_lookup.get(netuid)
                    
                    # Calculate validator utilization percentage
                    active_validators = metrics.get('active_validators')
                    validator_util_pct = None
                    if max_validators is not None and active_validators is not None:
                        validator_util_pct = round((active_validators / max_validators) * 100, 1)
                    
                    # Extract screener data for time series - include all available fields
                    screener_metrics = {}
                    if latest_screener is not None and latest_screener.raw_json is not None:
                        screener_data = latest_screener.raw_json
                        screener_metrics = {
                            # Core market metrics
                            'price_tao': screener_data.get('price'),
                            'market_cap_tao': screener_data.get('market_cap_tao'),
                            'fdv_tao': screener_data.get('fdv_tao'),
                            
                            # Volume metrics
                            'buy_volume_tao_1d': screener_data.get('buy_volume_tao_1d'),
                            'sell_volume_tao_1d': screener_data.get('sell_volume_tao_1d'),
                            'total_volume_tao_1d': screener_data.get('total_volume_tao_1d'),
                            'net_volume_tao_1h': screener_data.get('net_volume_tao_1h'),
                            'flow_24h': screener_data.get('net_volume_tao_24h'),
                            'net_volume_tao_7d': screener_data.get('net_volume_tao_7d'),
                            
                            # Price action metrics
                            'price_1h_change': screener_data.get('price_1h_pct_change'),
                            'price_1d_change': screener_data.get('price_1d_pct_change'),
                            'price_7d_change': screener_data.get('price_7d_pct_change'),
                            'price_30d_change': screener_data.get('price_1m_pct_change'),
                            'buy_volume_pct_change': screener_data.get('buy_volume_pct_change'),
                            'sell_volume_pct_change': screener_data.get('sell_volume_pct_change'),
                            'total_volume_pct_change': screener_data.get('total_volume_pct_change'),
                            
                            # Flow metrics
                            'tao_in': screener_data.get('tao_in'),
                            'alpha_in': screener_data.get('alpha_in'),
                            'alpha_out': screener_data.get('alpha_out'),
                            'alpha_circ': screener_data.get('alpha_circ'),
                            'alpha_prop': screener_data.get('alpha_prop'),
                            'root_prop': screener_data.get('root_prop'),
                            
                            # Emission metrics
                            'emission_pct': screener_data.get('emission_pct'),
                            'alpha_emitted_pct': screener_data.get('alpha_emitted_pct'),
                            
                            # PnL metrics
                            'realized_pnl_tao': screener_data.get('realized_pnl_tao'),
                            'unrealized_pnl_tao': screener_data.get('unrealized_pnl_tao'),
                            
                            # Price extremes
                            'ath_60d': screener_data.get('ath_60d'),
                            'atl_60d': screener_data.get('atl_60d'),
                            
                            # Distribution metrics
                            'gini_coeff_top_100': screener_data.get('gini_coeff_top_100'),
                            'hhi': screener_data.get('hhi'),
                            
                            # Metadata
                            'symbol': screener_data.get('symbol'),
                            'github_repo': screener_data.get('github_repo'),
                            'subnet_contact': screener_data.get('subnet_contact'),
                            'subnet_url': screener_data.get('subnet_url'),
                            'subnet_website': screener_data.get('subnet_website'),
                            'discord': screener_data.get('discord'),
                            'additional': screener_data.get('additional'),
                            'owner_coldkey': screener_data.get('owner_coldkey'),
                            'owner_hotkey': screener_data.get('owner_hotkey')
                        }
                    
                    # Calculate all metrics using the new calculation service
                    # Use SDK metrics directly (they're already calculated correctly)
                    # Only calculate reserve momentum and emission ROI which need additional data
                    calculated_metrics = {
                        # Market data from screener (use as-is)
                        'price_tao': screener_metrics.get('price_tao'),
                        'market_cap_tao': screener_metrics.get('market_cap_tao'),
                        'fdv_tao': screener_metrics.get('fdv_tao'),
                        'buy_vol_tao_1d': screener_metrics.get('buy_volume_tao_1d'),
                        'sell_vol_tao_1d': screener_metrics.get('sell_volume_tao_1d'),
                        'tao_in': screener_metrics.get('tao_in'),
                        
                        # Additional screener fields (use as-is)
                        'total_volume_tao_1d': screener_metrics.get('total_volume_tao_1d'),
                        'net_volume_tao_1h': screener_metrics.get('net_volume_tao_1h'),
                        'net_volume_tao_24h': screener_metrics.get('flow_24h'),
                        'net_volume_tao_7d': screener_metrics.get('net_volume_tao_7d'),
                        'price_1h_change': screener_metrics.get('price_1h_change'),
                        'price_1d_change': screener_metrics.get('price_1d_change'),
                        'price_7d_change': screener_metrics.get('price_7d_change'),
                        'price_30d_change': screener_metrics.get('price_30d_change'),
                        'buy_volume_pct_change': screener_metrics.get('buy_volume_pct_change'),
                        'sell_volume_pct_change': screener_metrics.get('sell_volume_pct_change'),
                        'total_volume_pct_change': screener_metrics.get('total_volume_pct_change'),
                        'alpha_in': screener_metrics.get('alpha_in'),
                        'alpha_out': screener_metrics.get('alpha_out'),
                        'alpha_circ': screener_metrics.get('alpha_circ'),
                        'alpha_prop': screener_metrics.get('alpha_prop'),
                        'root_prop': screener_metrics.get('root_prop'),
                        'emission_pct': screener_metrics.get('emission_pct'),
                        'alpha_emitted_pct': screener_metrics.get('alpha_emitted_pct'),
                        'realized_pnl_tao': screener_metrics.get('realized_pnl_tao'),
                        'unrealized_pnl_tao': screener_metrics.get('unrealized_pnl_tao'),
                        'ath_60d': screener_metrics.get('ath_60d'),
                        'atl_60d': screener_metrics.get('atl_60d'),
                        'gini_coeff_top_100': screener_metrics.get('gini_coeff_top_100'),
                        'hhi': screener_metrics.get('hhi'),
                        'symbol': screener_metrics.get('symbol'),
                        'github_repo': screener_metrics.get('github_repo'),
                        'subnet_contact': screener_metrics.get('subnet_contact'),
                        'subnet_url': screener_metrics.get('subnet_url'),
                        'subnet_website': screener_metrics.get('subnet_website'),
                        'discord': screener_metrics.get('discord'),
                        'additional': screener_metrics.get('additional'),
                        'owner_coldkey': screener_metrics.get('owner_coldkey'),
                        'owner_hotkey': screener_metrics.get('owner_hotkey'),
                        
                        # SDK metrics (use as-is from SDK collection)
                        'total_stake_tao': metrics.get('total_stake_tao'),
                        'stake_hhi': metrics.get('stake_hhi'),
                        'stake_quality': metrics.get('stake_quality'),
                        'consensus_alignment': metrics.get('consensus_alignment'),
                        # Trust score only for trust-based subnets
                        'trust_score': metrics.get('trust_score') if subnet_meta and subnet_meta.primary_category in ("AI-Verification & Trust", "Validator", "Root") else None,
                        'active_stake_ratio': metrics.get('active_stake_ratio'),
                        'active_validators': metrics.get('active_validators'),
                        'validators_active': metrics.get('validators_active'),
                        'uid_count': metrics.get('uid_count'),
                        'mean_incentive': metrics.get('mean_incentive'),
                        'p95_incentive': metrics.get('p95_incentive'),
                        'mean_consensus': metrics.get('mean_consensus'),
                        'pct_aligned': metrics.get('pct_aligned'),
                        
                        # Emission metrics (use as-is from SDK collection)
                        'emission_owner': metrics.get('emission_split', {}).get('owner'),
                        'emission_miners': metrics.get('emission_split', {}).get('miners'),
                        'emission_validators': metrics.get('emission_split', {}).get('validators'),
                        'total_emission_tao': metrics.get('total_emission_tao'),
                        'tao_in_emission': metrics.get('tao_in_emission'),
                        'alpha_out_emission': metrics.get('alpha_out_emission'),
                        
                        # Validator utilization metrics
                        'validator_util_pct': validator_util_pct,
                        'max_validators': max_validators,
                    }
                    
                    # Calculate reserve momentum using yesterday's data
                    tao_in_today = screener_metrics.get('tao_in')
                    tao_in_yesterday_val = yesterday_tao_in
                    market_cap = screener_metrics.get('market_cap_tao')
                    
                    if tao_in_today is not None and tao_in_yesterday_val is not None and market_cap is not None:
                        calculated_metrics['reserve_momentum'] = calculate_reserve_momentum(
                            float(tao_in_today),
                            float(tao_in_yesterday_val),
                            float(market_cap)
                        )
                    else:
                        calculated_metrics['reserve_momentum'] = None
                    
                    # Calculate emission ROI using daily emission data
                    if daily_emission_tao is not None and metrics.get('total_stake_tao') is not None:
                        calculated_metrics['emission_roi'] = calculate_emission_roi(
                            daily_emission_tao,
                            metrics.get('total_stake_tao')
                        )
                    else:
                        calculated_metrics['emission_roi'] = None
                    
                    # Calculate TAO-Score using all available metrics
                    from services.calc_metrics import calculate_tao_score
                    calculated_metrics['tao_score'] = calculate_tao_score(
                        stake_quality=calculated_metrics.get('stake_quality'),
                        consensus_alignment=calculated_metrics.get('consensus_alignment'),
                        active_stake_ratio=calculated_metrics.get('active_stake_ratio'),
                        emission_roi=calculated_metrics.get('emission_roi'),
                        reserve_momentum=calculated_metrics.get('reserve_momentum'),
                        validator_util_pct=calculated_metrics.get('validator_util_pct'),
                        inflation_pct=calculated_metrics.get('emission_pct'),  # Use emission_pct as inflation proxy
                        price_7d_change=screener_metrics.get('price_7d_change'),  # Use 7-day price change for momentum
                        session=session
                    )
                    
                    # Validate metrics before storing
                    is_valid, error_msg = validate_metrics(calculated_metrics)
                    if not is_valid:
                        logger.error(f"Validation failed for subnet {netuid}: {error_msg}")
                        failed_snapshots += 1
                        continue
                    
                    # Set data quality flag
                    data_quality_flag = 'complete' if daily_emission_tao is not None else 'partial'
                    
                    # Create metrics snapshot record with calculated metrics
                    snapshot = MetricsSnap(
                        timestamp=snapshot_time,
                        netuid=netuid,
                        
                        # Market metrics from screener
                        market_cap_tao=calculated_metrics.get('market_cap_tao'),
                        flow_24h=screener_metrics.get('flow_24h'),
                        price_tao=calculated_metrics.get('price_tao'),
                        
                        # Price action metrics from screener
                        price_1d_change=screener_metrics.get('price_1d_change'),
                        price_7d_change=screener_metrics.get('price_7d_change'),
                        price_30d_change=screener_metrics.get('price_30d_change'),
                        buy_volume_tao_1d=calculated_metrics.get('buy_vol_tao_1d'),
                        sell_volume_tao_1d=calculated_metrics.get('sell_vol_tao_1d'),
                        
                        # Flow metrics from screener
                        tao_in=calculated_metrics.get('tao_in'),
                        alpha_circ=screener_metrics.get('alpha_circ'),
                        alpha_prop=screener_metrics.get('alpha_prop'),
                        root_prop=screener_metrics.get('root_prop'),
                        
                        # SDK metrics
                        total_stake_tao=calculated_metrics.get('total_stake_tao'),
                        stake_hhi=calculated_metrics.get('stake_hhi'),
                        uid_count=calculated_metrics.get('uid_count'),
                        mean_incentive=metrics.get('mean_incentive'),
                        p95_incentive=metrics.get('p95_incentive'),
                        consensus_alignment=calculated_metrics.get('consensus_alignment'),
                        trust_score=calculated_metrics.get('trust_score'),
                        active_stake_ratio=calculated_metrics.get('active_stake_ratio'),
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
                        max_validators=calculated_metrics.get('max_validators'),
                        
                        # Calculated metrics using new formulas
                        stake_quality=calculated_metrics.get('stake_quality'),
                        reserve_momentum=calculated_metrics.get('reserve_momentum'),
                        emission_roi=calculated_metrics.get('emission_roi'),
                        validators_active=calculated_metrics.get('validators_active'),
                        tao_score=calculated_metrics.get('tao_score'),
                        
                        # NEW: Investor-focused fields
                        fdv_tao=calculated_metrics.get('fdv_tao'),
                        buy_vol_tao_1d=calculated_metrics.get('buy_vol_tao_1d'),
                        sell_vol_tao_1d=calculated_metrics.get('sell_vol_tao_1d'),
                        data_quality_flag=data_quality_flag,
                        last_screener_update=latest_screener.fetched_at if latest_screener else None,
                        
                        # Additional screener fields
                        total_volume_tao_1d=calculated_metrics.get('total_volume_tao_1d'),
                        net_volume_tao_1h=calculated_metrics.get('net_volume_tao_1h'),
                        net_volume_tao_7d=calculated_metrics.get('net_volume_tao_7d'),
                        price_1h_change=calculated_metrics.get('price_1h_change'),
                        buy_volume_pct_change=calculated_metrics.get('buy_volume_pct_change'),
                        sell_volume_pct_change=calculated_metrics.get('sell_volume_pct_change'),
                        total_volume_pct_change=calculated_metrics.get('total_volume_pct_change'),
                        alpha_in=calculated_metrics.get('alpha_in'),
                        alpha_out=calculated_metrics.get('alpha_out'),
                        emission_pct=calculated_metrics.get('emission_pct'),
                        alpha_emitted_pct=calculated_metrics.get('alpha_emitted_pct'),
                        realized_pnl_tao=calculated_metrics.get('realized_pnl_tao'),
                        unrealized_pnl_tao=calculated_metrics.get('unrealized_pnl_tao'),
                        ath_60d=calculated_metrics.get('ath_60d'),
                        atl_60d=calculated_metrics.get('atl_60d'),
                        gini_coeff_top_100=calculated_metrics.get('gini_coeff_top_100'),
                        hhi=calculated_metrics.get('hhi'),
                        symbol=calculated_metrics.get('symbol'),
                        github_repo=calculated_metrics.get('github_repo'),
                        subnet_contact=calculated_metrics.get('subnet_contact'),
                        subnet_url=calculated_metrics.get('subnet_url'),
                        subnet_website=calculated_metrics.get('subnet_website'),
                        discord=calculated_metrics.get('discord'),
                        additional=calculated_metrics.get('additional'),
                        owner_coldkey=calculated_metrics.get('owner_coldkey'),
                        owner_hotkey=calculated_metrics.get('owner_hotkey'),
                        
                        # Metadata
                        subnet_name=subnet_meta.subnet_name if subnet_meta else None,
                        category=subnet_meta.primary_category if subnet_meta else None,
                        confidence=subnet_meta.confidence if subnet_meta else None
                    )
                    
                    session.add(snapshot)
                    successful_snapshots += 1
                    
                    # Log progress every 10 subnets or at the end
                    if (i + 1) % 10 == 0 or (i + 1) == len(metrics_list):
                        progress = (i + 1) / len(metrics_list) * 100
                        logger.info(f"Database progress: {i + 1}/{len(metrics_list)} subnets ({progress:.1f}%) - {successful_snapshots} successful, {failed_snapshots} failed")
                    
                except Exception as e:
                    logger.error(f"Error processing subnet {metrics.get('netuid', 'unknown')}: {e}")
                    failed_snapshots += 1
                    continue
            
            # Commit all snapshots
            session.commit()
            
            # Compute category statistics for peer comparisons
            self.compute_category_stats(session)
            
            # Compute rank percentages for expert-level GPT insights
            self.compute_rank_percentages(session)
            
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
    
    def compute_category_stats(self, session):
        """Compute category-level statistics for peer comparisons."""
        try:
            logger.info("Computing category statistics...")
            
            # Get latest metrics for each subnet
            from models import CategoryStats
            from sqlalchemy import func
            
            # Get the latest timestamp
            latest_timestamp = session.query(func.max(MetricsSnap.timestamp)).scalar()
            
            if not latest_timestamp:
                logger.warning("No metrics data available for category stats")
                return
            
            # Compute median stats by category
            category_stats = session.query(
                MetricsSnap.category,
                func.avg(MetricsSnap.stake_quality).label('median_stake_quality'),
                func.avg(MetricsSnap.emission_roi).label('median_emission_roi'),
                func.count(MetricsSnap.netuid).label('subnet_count')
            ).filter(
                MetricsSnap.timestamp == latest_timestamp,
                MetricsSnap.category.isnot(None)
            ).group_by(MetricsSnap.category).all()
            
            # Clear existing stats
            session.query(CategoryStats).delete()
            
            # Insert new stats
            for stat in category_stats:
                category_stat = CategoryStats(
                    category=stat.category,
                    median_stake_quality=stat.median_stake_quality,
                    median_emission_roi=stat.median_emission_roi,
                    subnet_count=stat.subnet_count,
                    timestamp=datetime.utcnow()
                )
                session.add(category_stat)
            
            session.commit()
            logger.info(f"Computed stats for {len(category_stats)} categories")
            
        except Exception as e:
            logger.error(f"Error computing category stats: {e}")
            session.rollback()
    
    def compute_rank_percentages(self, session):
        """Compute rank percentages for expert-level GPT insights."""
        try:
            logger.info("Computing rank percentages...")
            
            from sqlalchemy import func
            from services.calc_metrics import calculate_rank_percentage, calculate_validator_utilization, calculate_buy_sell_ratio
            
            # Get the latest timestamp
            latest_timestamp = session.query(func.max(MetricsSnap.timestamp)).scalar()
            
            if not latest_timestamp:
                logger.warning("No metrics data available for rank percentages")
                return
            
            # Get all subnets with latest metrics
            latest_metrics = session.query(MetricsSnap).filter(
                MetricsSnap.timestamp == latest_timestamp
            ).all()
            
            # Group by category for ranking
            categories = {}
            for metric in latest_metrics:
                if metric.category:
                    if metric.category not in categories:
                        categories[metric.category] = []
                    categories[metric.category].append(metric)
            
            # Compute rank percentages for each subnet
            for metric in latest_metrics:
                if metric.category and metric.category in categories:
                    category_metrics = categories[metric.category]
                    
                    # Stake quality rank (higher is better)
                    if metric.stake_quality is not None:
                        category_qualities = [m.stake_quality for m in category_metrics if m.stake_quality is not None]
                        metric.stake_quality_rank_pct = calculate_rank_percentage(metric.stake_quality, category_qualities)
                    
                    # Momentum rank (higher is better)
                    if metric.reserve_momentum is not None:
                        category_momentums = [m.reserve_momentum for m in category_metrics if m.reserve_momentum is not None]
                        metric.momentum_rank_pct = calculate_rank_percentage(metric.reserve_momentum, category_momentums)
                    
                    # Validator utilization
                    metric.validator_util_pct = calculate_validator_utilization(metric.active_validators)
                    
                    # Buy/sell ratio
                    metric.buy_sell_ratio = calculate_buy_sell_ratio(metric.buy_volume_tao_1d, metric.sell_volume_tao_1d)
            
            session.commit()
            logger.info(f"Computed rank percentages for {len(latest_metrics)} subnets")
            
        except Exception as e:
            logger.error(f"Error computing rank percentages: {e}")
            session.rollback()
    
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
    parser.add_argument("--limit", type=int, help="Limit number of subnets for SDK snapshot (for testing)")
    
    args = parser.parse_args()
    
    cron = CronFetch()
    
    if args.once:
        if args.once == 'sdk_snapshot' and args.limit:
            result = cron.fetch_sdk_snapshot(limit=args.limit)
        else:
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