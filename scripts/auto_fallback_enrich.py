#!/usr/bin/env python3
"""
Automatic Fallback Enrichment Script for TAO Analytics.

This script automatically re-enriches subnets that have:
1. Low confidence scores (<70)
2. Zero context tokens
3. Missing or incomplete data
4. Model-only provenance with thin context

Usage:
    python scripts/auto_fallback_enrich.py [--dry-run] [--min-confidence 70] [--max-subnets 10]
"""

import argparse
import sys
import time
from pathlib import Path
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import get_db
from services.cache import clear_all_caches
from models import SubnetMeta, ScreenerRaw
from scripts.data_collection.enrich_with_openai import enrich_subnet


def get_subnets_needing_fallback(min_confidence=70, max_subnets=10):
    """
    Get subnets that need fallback enrichment.
    
    Args:
        min_confidence: Minimum confidence threshold
        max_subnets: Maximum number of subnets to process
        
    Returns:
        List of subnet records needing enrichment
    """
    db = get_db()
    
    try:
        # Query for subnets needing fallback enrichment
        subnets = db.query(SubnetMeta).filter(
            or_(
                # Low confidence
                SubnetMeta.confidence < min_confidence,
                # Zero context tokens
                SubnetMeta.context_tokens == 0,
                # Model-only with thin context
                and_(
                    SubnetMeta.provenance == 'model-only',
                    SubnetMeta.context_tokens < 100
                ),
                # Missing critical fields
                or_(
                    SubnetMeta.what_it_does.is_(None),
                    SubnetMeta.what_it_does == '',
                    SubnetMeta.primary_category.is_(None),
                    SubnetMeta.primary_category == ''
                )
            )
        ).limit(max_subnets).all()
        
        return subnets
    finally:
        db.close()


def enrich_with_fallback_strategy(subnet_record, dry_run=False):
    """
    Enrich subnet with aggressive fallback strategy.
    
    Args:
        subnet_record: Subnet record to enrich
        dry_run: If True, don't actually make API calls
        
    Returns:
        dict: Enrichment result
    """
    netuid = subnet_record.netuid
    
    print(f"Processing subnet {netuid} (confidence: {subnet_record.confidence}%)")
    
    if dry_run:
        print(f"  [DRY RUN] Would re-enrich subnet {netuid}")
        return {'success': True, 'dry_run': True}
    
    try:
        # Clear cache for this subnet to force fresh data
        clear_all_caches()
        
        # Enrich with fallback context enabled
        result = enrich_subnet(
            netuid=netuid,
            force_refresh=True,  # Force refresh of context
            use_fallback=True,   # Enable fallback context
            max_retries=3        # More retries for fallback
        )
        
        if result['success']:
            print(f"  ✅ Successfully re-enriched subnet {netuid}")
            print(f"     New confidence: {result.get('confidence_score', 'N/A')}%")
            print(f"     Context tokens: {result.get('context_tokens', 'N/A')}")
            print(f"     Provenance: {result.get('provenance', 'N/A')}")
        else:
            print(f"  ❌ Failed to re-enrich subnet {netuid}: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        print(f"  ❌ Exception during enrichment: {e}")
        return {'success': False, 'error': str(e)}


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Automatic fallback enrichment for low-confidence subnets")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually make API calls")
    parser.add_argument("--min-confidence", type=int, default=70, help="Minimum confidence threshold")
    parser.add_argument("--max-subnets", type=int, default=10, help="Maximum subnets to process")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between API calls (seconds)")
    
    args = parser.parse_args()
    
    print("🤖 TAO Analytics - Automatic Fallback Enrichment")
    print("=" * 50)
    print(f"Min confidence: {args.min_confidence}%")
    print(f"Max subnets: {args.max_subnets}")
    print(f"Delay: {args.delay}s")
    print(f"Dry run: {args.dry_run}")
    print()
    
    # Get subnets needing fallback
    subnets = get_subnets_needing_fallback(
        min_confidence=args.min_confidence,
        max_subnets=args.max_subnets
    )
    
    if not subnets:
        print("✅ No subnets need fallback enrichment!")
        return
    
    print(f"Found {len(subnets)} subnets needing fallback enrichment:")
    for subnet in subnets:
        print(f"  - Subnet {subnet.netuid}: {subnet.subnet_name} (confidence: {subnet.confidence}%)")
    print()
    
    # Process subnets
    results = {
        'total': len(subnets),
        'success': 0,
        'failed': 0,
        'dry_run': 0
    }
    
    for i, subnet in enumerate(subnets, 1):
        print(f"[{i}/{len(subnets)}] ", end="")
        
        result = enrich_with_fallback_strategy(subnet, dry_run=args.dry_run)
        
        if result.get('dry_run'):
            results['dry_run'] += 1
        elif result['success']:
            results['success'] += 1
        else:
            results['failed'] += 1
        
        # Delay between calls (except for last one)
        if i < len(subnets) and not args.dry_run:
            print(f"Waiting {args.delay}s...")
            time.sleep(args.delay)
        
        print()
    
    # Summary
    print("=" * 50)
    print("📊 Enrichment Summary:")
    print(f"  Total processed: {results['total']}")
    print(f"  Successful: {results['success']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Dry run: {results['dry_run']}")
    
    if results['success'] > 0:
        success_rate = (results['success'] / results['total']) * 100
        print(f"  Success rate: {success_rate:.1f}%")
    
    print("✅ Fallback enrichment complete!")


if __name__ == "__main__":
    main() 