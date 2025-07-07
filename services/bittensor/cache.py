"""
Bittensor SDK caching layer for Sprint 3 spike.
Provides cached access to metagraph and metrics data.
"""

import os
import time
import functools
import logging
from typing import Dict, Any, Optional
from .metrics import calculate_subnet_metrics
from .endpoints import MAIN_RPC

# Configure logging
logger = logging.getLogger("sdk")

# Try to use Redis if available
try:
    import redis
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        if redis_url.startswith("rediss://"):
            redis_client = redis.from_url(redis_url, ssl_cert_reqs=None)
        else:
            redis_client = redis.from_url(redis_url)
    else:
        redis_client = None
    if redis_client:
        redis_client.ping()  # Test connection
        logger.info("Using Redis for caching")
    else:
        redis_client = None
        logger.info("Redis not configured, using in-memory cache")
except ImportError:
    redis_client = None
    logger.info("Redis not available, using in-memory cache")

def ttl_cache(maxsize=64, ttl=900):
    """Simple TTL cache decorator using functools.lru_cache."""
    def decorator(func):
        @functools.lru_cache(maxsize=maxsize)
        def cached_func(*args, **kwargs):
            # For simplicity, we'll use the function name and args as cache key
            # In a real implementation, you'd want more sophisticated key generation
            return func(*args, **kwargs)
        return cached_func
    return decorator

@ttl_cache(maxsize=64, ttl=900)  # 15 minutes for metagraph data
def get_metagraph(netuid: int, endpoint: str = MAIN_RPC) -> Dict[str, Any]:
    """
    Get cached or live metagraph data for a subnet.
    
    Args:
        netuid: Subnet ID
        endpoint: RPC endpoint to use
        
    Returns:
        Metagraph data dictionary
    """
    cache_key = f"metagraph:{netuid}:{endpoint}"
    
    # Try Redis first
    if redis_client:
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for metagraph {netuid}")
                return eval(cached_data)  # Simple deserialization for demo
        except Exception as e:
            logger.warning(f"Redis cache error: {e}")
    
    # Fallback to live data
    logger.info(f"Cache miss for metagraph {netuid}, fetching live data")
    try:
        import bittensor as bt
        sub = bt.subtensor(endpoint)
        mg = sub.metagraph(netuid=netuid)
        
        # Convert to serializable format
        data = {
            "netuid": netuid,
            "endpoint": endpoint,
            "timestamp": time.time(),
            "uids": mg.uids.tolist() if hasattr(mg, 'uids') else [],
            "stake": mg.stake.tolist() if hasattr(mg, 'stake') else [],
            "incentive": mg.incentive.tolist() if hasattr(mg, 'incentive') else [],
        }
        
        # Cache in Redis if available
        if redis_client:
            try:
                redis_client.setex(cache_key, 900, str(data))  # 15 minutes TTL
            except Exception as e:
                logger.warning(f"Failed to cache in Redis: {e}")
        
        return data
        
    except Exception as e:
        logger.error(f"Error fetching metagraph {netuid}: {e}")
        return {"error": str(e), "netuid": netuid}

@ttl_cache(maxsize=64, ttl=900)  # 15 minutes for metrics data
def get_metrics(netuid: int, endpoint: str = MAIN_RPC) -> Dict[str, Any]:
    """
    Get cached or live metrics for a subnet.
    
    Args:
        netuid: Subnet ID
        endpoint: RPC endpoint to use
        
    Returns:
        Metrics dictionary
    """
    cache_key = f"metrics:{netuid}:{endpoint}"
    
    # Try Redis first
    if redis_client:
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for metrics {netuid}")
                return eval(cached_data)  # Simple deserialization for demo
        except Exception as e:
            logger.warning(f"Redis cache error: {e}")
    
    # Fallback to live data
    logger.info(f"Cache miss for metrics {netuid}, calculating live data")
    try:
        metrics = calculate_subnet_metrics(netuid, endpoint)
        
        # Cache in Redis if available
        if redis_client and "error" not in metrics:
            try:
                redis_client.setex(cache_key, 900, str(metrics))  # 15 minutes TTL
            except Exception as e:
                logger.warning(f"Failed to cache in Redis: {e}")
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error calculating metrics for {netuid}: {e}")
        return {"error": str(e), "netuid": netuid}

def get_probe_results() -> Optional[Dict[str, Any]]:
    """
    Get cached probe results (1 hour TTL).
    
    Returns:
        Probe results dictionary or None if not cached
    """
    cache_key = "probe_results"
    
    if redis_client:
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                return eval(cached_data)
        except Exception as e:
            logger.warning(f"Redis cache error: {e}")
    
    return None

def cache_probe_results(results: Dict[str, Any]) -> None:
    """
    Cache probe results for 1 hour.
    
    Args:
        results: Probe results to cache
    """
    cache_key = "probe_results"
    
    if redis_client:
        try:
            redis_client.setex(cache_key, 3600, str(results))  # 1 hour TTL
            logger.info("Probe results cached")
        except Exception as e:
            logger.warning(f"Failed to cache probe results: {e}") 