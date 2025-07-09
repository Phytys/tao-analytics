"""
Cache utilities with Redis fallback to in-memory caching.
Handles Redis connection issues gracefully.
"""

import os
import time
import json
import logging
from typing import Any, Optional
import redis
from flask_caching import Cache
from flask import current_app

logger = logging.getLogger(__name__)

# Global in-memory cache fallback
_memory_cache = {}
_cache_timestamps = {}
_max_cache_size = 1000  # Maximum number of items in memory cache
_max_memory_mb = 100    # Maximum memory usage in MB

def _cleanup_memory_cache():
    """Clean up old cache entries to prevent memory bloat."""
    current_time = time.time()
    items_to_remove = []
    
    # Remove expired items
    for key, timestamp in _cache_timestamps.items():
        if current_time - timestamp > 300:  # 5 minutes
            items_to_remove.append(key)
    
    # Remove oldest items if we're over the limit
    if len(_memory_cache) > _max_cache_size:
        sorted_items = sorted(_cache_timestamps.items(), key=lambda x: x[1])
        items_to_remove.extend([key for key, _ in sorted_items[:len(_memory_cache) - _max_cache_size]])
    
    # Remove items
    for key in items_to_remove:
        _memory_cache.pop(key, None)
        _cache_timestamps.pop(key, None)

def _get_memory_usage_mb():
    """Get current memory cache usage in MB."""
    total_size = 0
    for key, value in _memory_cache.items():
        try:
            if isinstance(value, str):
                total_size += len(value.encode('utf-8'))
            else:
                total_size += len(json.dumps(value).encode('utf-8'))
        except:
            total_size += 100  # Estimate for complex objects
    return total_size / (1024 * 1024)

def init_cache(app):
    """Initialize cache with Redis SSL bypass for Heroku."""
    try:
        # Get Redis URL from environment
        redis_url = os.getenv("REDIS_TLS_URL") or os.getenv("REDIS_URL")
        
        if redis_url:
            # Build Redis client that ignores TLS verification (fixes Heroku SSL issue)
            redis_client = redis.from_url(
                redis_url,
                ssl_cert_reqs=None,          # Bypass CA check for self-signed certs
                socket_timeout=3,
                socket_connect_timeout=3,
                decode_responses=True
            )
            
            # Test the connection
            try:
                redis_client.ping()
                logger.info("Redis connection successful - using Redis cache")
                
                app.config['CACHE_TYPE'] = 'RedisCache'
                app.config['CACHE_REDIS_CLIENT'] = redis_client
                app.config['CACHE_DEFAULT_TIMEOUT'] = 300
                
                cache = Cache(app)
                return cache
                
            except Exception as e:
                logger.warning(f"Redis connection failed: {e} - falling back to in-memory cache")
                _use_memory_cache = True
        else:
            logger.info("No Redis URL found - using in-memory cache")
            _use_memory_cache = True
            
    except Exception as e:
        logger.warning(f"Redis initialization failed: {e} - falling back to in-memory cache")
        _use_memory_cache = True
    
    # Fallback to in-memory cache
    app.config['CACHE_TYPE'] = 'SimpleCache'
    cache = Cache(app)
    return cache

def cache_get(key: str) -> Optional[Any]:
    """Get value from cache with memory fallback."""
    try:
        # Try Redis first
        cache = current_app.extensions['cache']
        if cache.config['CACHE_TYPE'] == 'RedisCache':
            return cache.get(key)
    except Exception as e:
        logger.debug(f"Redis get failed for {key}: {e}")
    
    # Fallback to memory cache
    try:
        if key in _memory_cache:
            # Check if expired (5 minute TTL)
            if time.time() - _cache_timestamps.get(key, 0) < 300:
                return _memory_cache[key]
            else:
                # Remove expired item
                _memory_cache.pop(key, None)
                _cache_timestamps.pop(key, None)
    except Exception as e:
        logger.debug(f"Memory cache get failed for {key}: {e}")
    
    return None

def cache_set(key: str, value: Any, timeout: int = 300) -> bool:
    """Set value in cache with memory fallback."""
    try:
        # Try Redis first
        cache = current_app.extensions['cache']
        if cache.config['CACHE_TYPE'] == 'RedisCache':
            cache.set(key, value, timeout=timeout)
            return True
    except Exception as e:
        logger.debug(f"Redis set failed for {key}: {e}")
    
    # Fallback to memory cache
    try:
        # Cleanup before adding new item
        _cleanup_memory_cache()
        
        # Check memory usage
        current_memory = _get_memory_usage_mb()
        if current_memory > _max_memory_mb:
            logger.warning(f"Memory cache usage {current_memory:.1f}MB exceeds limit {_max_memory_mb}MB - cleaning up")
            _cleanup_memory_cache()
        
        _memory_cache[key] = value
        _cache_timestamps[key] = time.time()
        return True
        
    except Exception as e:
        logger.debug(f"Memory cache set failed for {key}: {e}")
    
    return False

def get_cache_stats():
    """Get cache statistics for monitoring."""
    try:
        cache = current_app.extensions['cache']
        if cache.config['CACHE_TYPE'] == 'RedisCache':
            try:
                redis_client = cache.config['CACHE_REDIS_CLIENT']
                info = redis_client.info()
                return {
                    'type': 'redis',
                    'status': 'connected',
                    'memory_usage_mb': info.get('used_memory_human', 'N/A'),
                    'cache_entries': info.get('db0', {}).get('keys', 'N/A'),
                    'hit_rate': 'N/A'  # Redis doesn't provide this by default
                }
            except Exception as e:
                return {
                    'type': 'redis',
                    'status': f'error: {str(e)}',
                    'memory_usage_mb': 'N/A',
                    'cache_entries': 'N/A',
                    'hit_rate': 'N/A'
                }
    except:
        pass
    
    # Memory cache stats
    memory_usage = _get_memory_usage_mb()
    return {
        'type': 'memory',
        'status': 'active',
        'memory_usage_mb': f"{memory_usage:.1f}MB",
        'cache_entries': len(_memory_cache),
        'hit_rate': 'N/A'
    } 