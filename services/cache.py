"""
Caching service for TAO Analytics.
Provides LRU cache for API responses and database queries.
"""

import hashlib
import json
import time
from functools import wraps
from typing import Any, Dict, Optional, Callable
from collections import OrderedDict


class LRUCache:
    """Simple LRU cache implementation."""
    
    def __init__(self, max_size: int = 100, ttl: int = 3600):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of items in cache
            ttl: Time to live in seconds (default: 1 hour)
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict = OrderedDict()
        self.timestamps: Dict[str, float] = {}
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from function arguments."""
        # Create a hash of the arguments, handling non-serializable objects
        key_data = {
            'args': [str(arg) if not isinstance(arg, (int, float, str, bool, type(None))) else arg for arg in args],
            'kwargs': {k: str(v) if not isinstance(v, (int, float, str, bool, type(None))) else v for k, v in sorted(kwargs.items())}
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self.cache:
            # Check if expired
            if time.time() - self.timestamps[key] > self.ttl:
                self.delete(key)
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache with timestamp."""
        if key in self.cache:
            # Move to end if already exists
            self.cache.move_to_end(key)
        else:
            # Check if cache is full
            if len(self.cache) >= self.max_size:
                # Remove least recently used item
                oldest_key = next(iter(self.cache))
                self.delete(oldest_key)
        
        self.cache[key] = value
        self.timestamps[key] = time.time()
    
    def delete(self, key: str) -> None:
        """Delete key from cache."""
        if key in self.cache:
            del self.cache[key]
            del self.timestamps[key]
    
    def clear(self) -> None:
        """Clear all items from cache."""
        self.cache.clear()
        self.timestamps.clear()
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self.cache)
    
    def cleanup_expired(self) -> int:
        """Remove expired items and return count of removed items."""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.timestamps.items()
            if current_time - timestamp > self.ttl
        ]
        
        for key in expired_keys:
            self.delete(key)
        
        return len(expired_keys)


# Global cache instances
api_cache = LRUCache(max_size=200, ttl=3600)  # 1 hour TTL for API responses
db_cache = LRUCache(max_size=100, ttl=1800)   # 30 min TTL for DB queries


def cached(cache_instance: LRUCache = None):
    """
    Decorator to cache function results.
    
    Args:
        cache_instance: LRUCache instance to use (defaults to api_cache)
    """
    def decorator(func: Callable) -> Callable:
        cache = cache_instance or api_cache
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key = cache._generate_key(func.__name__, *args, **kwargs)
            
            # Try to get from cache
            cached_result = cache.get(key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result
        
        return wrapper
    return decorator


def cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    return {
        'api_cache': {
            'size': api_cache.size(),
            'max_size': api_cache.max_size,
            'ttl': api_cache.ttl
        },
        'db_cache': {
            'size': db_cache.size(),
            'max_size': db_cache.max_size,
            'ttl': db_cache.ttl
        }
    }


def clear_all_caches() -> None:
    """Clear all cache instances."""
    api_cache.clear()
    db_cache.clear()


def cleanup_all_caches() -> Dict[str, int]:
    """Clean up expired items from all caches."""
    return {
        'api_cache_expired': api_cache.cleanup_expired(),
        'db_cache_expired': db_cache.cleanup_expired()
    } 