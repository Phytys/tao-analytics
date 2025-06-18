#!/usr/bin/env python3
"""
Batch enrichment script for multiple subnets.
Processes subnets efficiently with cost control and progress tracking.
"""

import argparse
import sys
from typing import List
from enrich_with_openai import enrich_with_openai, save_enrichment
from prepare_context import prepare_context, format_context, SubnetContext, get_all_netuids, compute_context_hash
from models import SubnetMeta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from config import DB_URL
from datetime import datetime
import time

def process_subnet(netuid: int, force: bool = False) -> bool:
    """Process a single subnet and return success status."""
    try:
        print(f"\n{'='*50}")
        print(f"Processing subnet {netuid}...")
        print(f"{'='*50}")
        
        # Get context
        context = prepare_context(netuid)
        if not context:
            print(f"Failed to prepare context for subnet {netuid}")
            return False
        
        # Check if context has changed
        engine = create_engine(DB_URL)
        with Session(engine) as session:
            meta = session.get(SubnetMeta, netuid)
            current_hash = compute_context_hash(context)
            print(f"Computed context hash: {current_hash}")
            if meta and meta.context_hash:
                print(f"Stored context hash:   {meta.context_hash}")
                if current_hash == meta.context_hash and not force:
                    print(f"Context unchanged for subnet {netuid}, skipping enrichment")
                    return True
                print(f"Context changed for subnet {netuid}, proceeding with enrichment")
            else:
                print(f"No stored hash for subnet {netuid}, proceeding with enrichment")
        
        # Enrich with OpenAI
        enrichment = enrich_with_openai(context)
        if enrichment:
            print(f"\nEnrichment successful for subnet {netuid}")
            save_enrichment(netuid, enrichment, context)
            return True
        else:
            print(f"Enrichment failed for subnet {netuid}")
            return False
            
    except Exception as e:
        print(f"Error processing subnet {netuid}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Batch enrich multiple subnets")
    parser.add_argument("--netuids", nargs="+", type=int, help="List of NetUIDs to process")
    parser.add_argument("--range", nargs=2, type=int, help="Range of NetUIDs (start end)")
    parser.add_argument("--force", action="store_true", help="Force enrichment even if context hasn't changed")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between API calls (seconds)")
    parser.add_argument("--max-subnets", type=int, help="Maximum number of subnets to process")
    
    args = parser.parse_args()
    
    # Determine which subnets to process
    if args.netuids:
        netuids = args.netuids
    elif args.range:
        start, end = args.range
        netuids = list(range(start, end + 1))
    else:
        print("Please specify either --netuids or --range")
        sys.exit(1)
    
    # Limit number of subnets if specified
    if args.max_subnets:
        netuids = netuids[:args.max_subnets]
    
    print(f"Processing {len(netuids)} subnets: {netuids}")
    print(f"Delay between calls: {args.delay}s")
    print(f"Force mode: {args.force}")
    
    # Process subnets
    successful = 0
    failed = 0
    skipped = 0
    
    for i, netuid in enumerate(netuids, 1):
        print(f"\n[{i}/{len(netuids)}] Processing subnet {netuid}")
        
        result = process_subnet(netuid, force=args.force)
        
        if result:
            successful += 1
        else:
            failed += 1
        
        # Add delay between calls to avoid rate limiting
        if i < len(netuids):
            print(f"Waiting {args.delay}s before next call...")
            time.sleep(args.delay)
    
    # Summary
    print(f"\n{'='*50}")
    print("BATCH PROCESSING COMPLETE")
    print(f"{'='*50}")
    print(f"Total subnets: {len(netuids)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Success rate: {successful/len(netuids)*100:.1f}%")

if __name__ == "__main__":
    main() 