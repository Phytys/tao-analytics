#!/usr/bin/env python3
"""
Sync categories between SubnetMeta and MetricsSnap tables.

This script ensures that the category field in MetricsSnap matches the 
primary_category field in SubnetMeta after enrichment updates.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from services.db import get_db
from models import SubnetMeta, MetricsSnap
from sqlalchemy import func
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_categories():
    """Sync categories between SubnetMeta and MetricsSnap tables."""
    try:
        with get_db() as session:
            # Get the latest timestamp for metrics
            latest_timestamp = session.query(func.max(MetricsSnap.timestamp)).scalar()
            
            if not latest_timestamp:
                logger.warning("No metrics data available")
                return False
            
            # Get all subnets with latest metrics
            latest_metrics = session.query(MetricsSnap).filter(
                MetricsSnap.timestamp == latest_timestamp
            ).all()
            
            updated_count = 0
            mismatched_count = 0
            
            for metrics in latest_metrics:
                # Get corresponding subnet metadata
                subnet_meta = session.query(SubnetMeta).filter_by(netuid=metrics.netuid).first()
                
                current_category = getattr(metrics, 'category', None)
                new_category = getattr(subnet_meta, 'primary_category', None) if subnet_meta else None
                
                if new_category is not None:
                    # Check if categories don't match
                    if current_category != new_category:
                        logger.info(f"Subnet {metrics.netuid}: '{current_category}' -> '{new_category}'")
                        setattr(metrics, 'category', new_category)
                        updated_count += 1
                        mismatched_count += 1
                    else:
                        updated_count += 1
                else:
                    # No metadata or no category, clear the metrics category
                    if current_category is not None:
                        logger.info(f"Subnet {metrics.netuid}: '{current_category}' -> None (no metadata)")
                        setattr(metrics, 'category', None)
                        updated_count += 1
            
            # Commit all changes
            session.commit()
            
            logger.info(f"Category sync complete: {updated_count} subnets processed, {mismatched_count} categories updated")
            
            # Clear GPT insights cache for updated subnets to force regeneration
            if mismatched_count > 0:
                from services.gpt_insight import clear_gpt_insights_cache
                clear_gpt_insights_cache()
                logger.info("Cleared GPT insights cache to force regeneration with updated categories")
            
            return True
            
    except Exception as e:
        logger.error(f"Error syncing categories: {e}")
        return False

def main():
    """Main function."""
    print("Syncing categories between SubnetMeta and MetricsSnap tables...")
    
    success = sync_categories()
    
    if success:
        print("✅ Category sync completed successfully")
    else:
        print("❌ Category sync failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 