"""
TAO.app Cache Service for TAO Analytics.
Provides cached access to TAO.app API endpoints with quota guard integration.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import requests

from .db import get_db
from .quota_guard import QuotaGuard
from models import AggregatedCache, HoldersCache, ValidatorsCache
from config import TAO_APP_BASE_URL

logger = logging.getLogger(__name__)

# Initialize quota guard
quota_guard = QuotaGuard()

def get_cached_aggregated(netuid: int) -> Optional[Dict[str, Any]]:
    """
    Get cached aggregated data for a subnet.
    
    Args:
        netuid: Subnet ID
        
    Returns:
        Cached data or None if not found/expired
    """
    try:
        with get_db() as session:
            # Check for fresh data (within 24 hours)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            cached_data = session.query(AggregatedCache).filter(
                AggregatedCache.netuid == netuid,
                AggregatedCache.fetched_at > cutoff_time
            ).first()
            
            if cached_data:
                logger.info(f"Using cached aggregated data for subnet {netuid}")
                return cached_data.data
            
            return None
            
    except Exception as e:
        logger.error(f"Error getting cached aggregated data for subnet {netuid}: {e}")
        return None

def save_aggregated_to_db(netuid: int, data: Dict[str, Any]) -> bool:
    """
    Save aggregated data to database with upsert logic.
    
    Args:
        netuid: Subnet ID
        data: API response data
        
    Returns:
        True if saved successfully
    """
    try:
        with get_db() as session:
            # Use upsert logic: INSERT ... ON CONFLICT DO UPDATE
            existing = session.query(AggregatedCache).filter_by(netuid=netuid).first()
            
            if existing:
                # Update existing record
                existing.data = data
                existing.fetched_at = datetime.utcnow()
            else:
                # Create new record
                new_cache = AggregatedCache(
                    netuid=netuid,
                    data=data,
                    fetched_at=datetime.utcnow()
                )
                session.add(new_cache)
            
            session.commit()
            logger.info(f"Saved aggregated data for subnet {netuid}")
            return True
            
    except Exception as e:
        logger.error(f"Error saving aggregated data for subnet {netuid}: {e}")
        return False

def fetch_aggregated_with_cache(netuid: int) -> Optional[Dict[str, Any]]:
    """
    Fetch aggregated data for a subnet with caching.
    
    Args:
        netuid: Subnet ID
        
    Returns:
        Aggregated data or None if failed
    """
    # First try to get from cache
    cached_data = get_cached_aggregated(netuid)
    if cached_data:
        return cached_data
    
    # Fetch from API with quota guard
    try:
        url = f"{TAO_APP_BASE_URL}/subnets/aggregated"
        params = {"netuid": netuid}
        
        # Check quota before making call
        if not quota_guard.check_quota("subnets_aggregated"):
            logger.error("Quota exceeded for subnets_aggregated")
            return None
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Increment quota count
        new_count = quota_guard.increment_call_count("subnets_aggregated")
        logger.info(f"Aggregated API call successful. Quota count: {new_count}")
        
        # Save to database
        save_aggregated_to_db(netuid, data)
        
        logger.info(f"Fetched and cached aggregated data for subnet {netuid}")
        return data
        
    except Exception as e:
        logger.error(f"Error fetching aggregated data for subnet {netuid}: {e}")
        return None

def get_cached_holders(netuid: int) -> Optional[Dict[str, Any]]:
    """
    Get cached holders data for a subnet.
    
    Args:
        netuid: Subnet ID
        
    Returns:
        Cached data or None if not found/expired
    """
    try:
        with get_db() as session:
            # Check for fresh data (within 24 hours)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            cached_data = session.query(HoldersCache).filter(
                HoldersCache.netuid == netuid,
                HoldersCache.fetched_at > cutoff_time
            ).first()
            
            if cached_data:
                logger.info(f"Using cached holders data for subnet {netuid}")
                return cached_data.data
            
            return None
            
    except Exception as e:
        logger.error(f"Error getting cached holders data for subnet {netuid}: {e}")
        return None

def save_holders_to_db(netuid: int, data: Dict[str, Any]) -> bool:
    """
    Save holders data to database with upsert logic.
    
    Args:
        netuid: Subnet ID
        data: API response data
        
    Returns:
        True if saved successfully
    """
    try:
        with get_db() as session:
            # Use upsert logic: INSERT ... ON CONFLICT DO UPDATE
            existing = session.query(HoldersCache).filter_by(netuid=netuid).first()
            
            if existing:
                # Update existing record
                existing.data = data
                existing.fetched_at = datetime.utcnow()
            else:
                # Create new record
                new_cache = HoldersCache(
                    netuid=netuid,
                    data=data,
                    fetched_at=datetime.utcnow()
                )
                session.add(new_cache)
            
            session.commit()
            logger.info(f"Saved holders data for subnet {netuid}")
            return True
            
    except Exception as e:
        logger.error(f"Error saving holders data for subnet {netuid}: {e}")
        return False

def fetch_holders_with_cache(netuid: int) -> Optional[Dict[str, Any]]:
    """
    Fetch holders data for a subnet with caching.
    
    Args:
        netuid: Subnet ID
        
    Returns:
        Holders data or None if failed
    """
    # First try to get from cache
    cached_data = get_cached_holders(netuid)
    if cached_data:
        return cached_data
    
    # Fetch from API with quota guard
    try:
        url = f"{TAO_APP_BASE_URL}/subnets/holders"
        params = {"netuid": netuid}
        
        # Check quota before making call
        if not quota_guard.check_quota("subnets_holders"):
            logger.error("Quota exceeded for subnets_holders")
            return None
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Increment quota count
        new_count = quota_guard.increment_call_count("subnets_holders")
        logger.info(f"Holders API call successful. Quota count: {new_count}")
        
        # Save to database
        save_holders_to_db(netuid, data)
        
        logger.info(f"Fetched and cached holders data for subnet {netuid}")
        return data
        
    except Exception as e:
        logger.error(f"Error fetching holders data for subnet {netuid}: {e}")
        return None

def get_cached_validators(netuid: int) -> Optional[Dict[str, Any]]:
    """
    Get cached validators data for a subnet.
    
    Args:
        netuid: Subnet ID
        
    Returns:
        Cached data or None if not found/expired
    """
    try:
        with get_db() as session:
            # Check for fresh data (within 24 hours)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            cached_data = session.query(ValidatorsCache).filter(
                ValidatorsCache.netuid == netuid,
                ValidatorsCache.fetched_at > cutoff_time
            ).first()
            
            if cached_data:
                logger.info(f"Using cached validators data for subnet {netuid}")
                return cached_data.data
            
            return None
            
    except Exception as e:
        logger.error(f"Error getting cached validators data for subnet {netuid}: {e}")
        return None

def save_validators_to_db(netuid: int, data: Dict[str, Any]) -> bool:
    """
    Save validators data to database with upsert logic.
    
    Args:
        netuid: Subnet ID
        data: Validators data
        
    Returns:
        True if saved successfully
    """
    try:
        with get_db() as session:
            # Use upsert logic: INSERT ... ON CONFLICT DO UPDATE
            existing = session.query(ValidatorsCache).filter_by(netuid=netuid).first()
            
            if existing:
                # Update existing record
                existing.data = data
                existing.fetched_at = datetime.utcnow()
            else:
                # Create new record
                new_cache = ValidatorsCache(
                    netuid=netuid,
                    data=data,
                    fetched_at=datetime.utcnow()
                )
                session.add(new_cache)
            
            session.commit()
            logger.info(f"Saved validators data for subnet {netuid}")
            return True
            
    except Exception as e:
        logger.error(f"Error saving validators data for subnet {netuid}: {e}")
        return False

def fetch_validators_with_cache(netuid: int) -> Optional[Dict[str, Any]]:
    """
    Fetch validators data for a subnet with caching.
    For now, this is a placeholder for future taostats integration.
    
    Args:
        netuid: Subnet ID
        
    Returns:
        Validators data or None if failed
    """
    # First try to get from cache
    cached_data = get_cached_validators(netuid)
    if cached_data:
        return cached_data
    
    # TODO: Implement taostats scrape or other validators data source
    # For now, return placeholder data
    placeholder_data = {
        "validators": [],
        "total_validators": 0,
        "active_validators": 0,
        "message": "Validators data not yet implemented"
    }
    
    # Save placeholder to database
    save_validators_to_db(netuid, placeholder_data)
    
    logger.info(f"Using placeholder validators data for subnet {netuid}")
    return placeholder_data

# Global instance for easy access
taoapp_cache_service = {
    'get_aggregated': get_cached_aggregated,
    'fetch_aggregated': fetch_aggregated_with_cache,
    'get_holders': get_cached_holders,
    'fetch_holders': fetch_holders_with_cache,
    'get_validators': get_cached_validators,
    'fetch_validators': fetch_validators_with_cache
} 