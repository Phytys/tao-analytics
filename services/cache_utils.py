"""
Safe caching utilities for handling Redis connection errors and serialization issues.
"""

from flask import current_app
import pickle
import redis
import logging
import sys
import gc

log = logging.getLogger(__name__)

# In-memory cache for fallback (when Redis is unavailable)
_memory_cache = {}
_cache_sizes = {}

def _get_memory_usage():
    """Get current memory usage in MB."""
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024  # Convert to MB
    except ImportError:
        return 0

def _cleanup_memory_cache(max_size_mb=100):
    """Clean up memory cache if it gets too large."""
    if not _memory_cache:
        return
    
    current_memory = _get_memory_usage()
    if current_memory > max_size_mb:
        log.warning(f"Memory usage high ({current_memory:.1f}MB), clearing cache")
        _memory_cache.clear()
        _cache_sizes.clear()
        gc.collect()  # Force garbage collection

def cache_get(key):
    """Safely get a value from cache, handling connection and serialization errors."""
    cache = getattr(current_app, "cache", None)
    if cache is None:
        # Fallback to in-memory cache
        return _memory_cache.get(key)
    
    try:
        obj = cache.get(key)
        # Flask-Caching with Redis returns the object *unpickled* if you use
        # the default serializer, but will return bytes if SERIALIZER=None.
        if isinstance(obj, (bytes, bytearray)):
            obj = pickle.loads(obj)
        return obj
    except Exception as e:
        # Handle Redis, SSL certificate, and deserialization errors
        if "certificate verify failed" in str(e) or "Redis" in str(e):
            log.warning("Redis/SSL error → bypass cache (%s)", e)
        else:
            log.warning("Cache deserialisation failed → bypass (%s)", e)
            try:
                cache.delete(key)  # purge corrupt entry
            except:
                pass
        
        # Fallback to in-memory cache
        return _memory_cache.get(key)

def cache_set(key, value, timeout=300):
    """Safely set a value in cache, handling connection errors silently."""
    cache = getattr(current_app, "cache", None)
    if cache is None:
        # Fallback to in-memory cache
        _memory_cache[key] = value
        _cache_sizes[key] = sys.getsizeof(value) if hasattr(value, '__sizeof__') else 0
        _cleanup_memory_cache(max_size_mb=100)  # Cleanup if memory usage is high
        return
    
    try:
        cache.set(key, value, timeout=timeout)
    except Exception as e:
        # Handle Redis, SSL certificate, and other cache errors silently
        if "certificate verify failed" in str(e) or "Redis" in str(e):
            log.debug("Redis/SSL error → fallback to memory cache (%s)", e)
            # Fallback to in-memory cache
            _memory_cache[key] = value
            _cache_sizes[key] = sys.getsizeof(value) if hasattr(value, '__sizeof__') else 0
            _cleanup_memory_cache(max_size_mb=100)  # Cleanup if memory usage is high
        else:
            log.warning("Cache set failed (%s)", e)
        pass  # silently ignore – app must keep working 