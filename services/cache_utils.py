"""
Safe caching utilities for handling Redis connection errors and serialization issues.
"""

from flask import current_app
import pickle
import redis
import logging

log = logging.getLogger(__name__)

def cache_get(key):
    """Safely get a value from cache, handling connection and serialization errors."""
    cache = getattr(current_app, "cache", None)
    if cache is None:
        return None  # caching disabled
    
    try:
        obj = cache.get(key)
        # Flask-Caching with Redis returns the object *unpickled* if you use
        # the default serializer, but will return bytes if SERIALIZER=None.
        if isinstance(obj, (bytes, bytearray)):
            obj = pickle.loads(obj)
        return obj
    except redis.exceptions.RedisError as e:
        log.warning("Redis down → bypass cache (%s)", e)
        return None
    except Exception as e:
        log.warning("Cache deserialisation failed → bypass (%s)", e)
        try:
            cache.delete(key)  # purge corrupt entry
        except:
            pass
        return None

def cache_set(key, value, timeout=300):
    """Safely set a value in cache, handling connection errors silently."""
    cache = getattr(current_app, "cache", None)
    if cache is None:
        return
    
    try:
        cache.set(key, value, timeout=timeout)
    except redis.exceptions.RedisError:
        pass  # silently ignore – app must keep working
    except Exception as e:
        log.warning("Cache set failed (%s)", e) 