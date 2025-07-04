#!/usr/bin/env python3
"""
Batch enrichment script for multiple subnets.
Processes subnets efficiently with smart enrichment logic that automatically
handles both context-rich and model-only modes based on context availability.

USAGE EXAMPLES:
    # Process specific subnets
    python batch_enrich.py --netuids 1 2 3 64
    
    # Process a range of subnets
    python batch_enrich.py --range 1 10
    
    # Force re-enrichment even if context hasn't changed
    python batch_enrich.py --range 1 20 --force
    
    # Process with custom delay between API calls
    python batch_enrich.py --range 1 50 --delay 2.0
    
    # Limit number of subnets processed
    python batch_enrich.py --range 1 100 --max-subnets 10

OPTIONS:
    --netuids NETUID [NETUID ...]  List of specific NetUIDs to process
    --range START END              Range of NetUIDs (inclusive)
    --force                        Force enrichment even if context hasn't changed
    --delay SECONDS               Delay between API calls (default: 1.0)
    --max-subnets N               Maximum number of subnets to process
    --resume                       Resume from previous run
"""

import argparse
import sys
import json
import signal
from pathlib import Path
from typing import List
from enrich_with_openai import enrich_with_openai, save_enrichment
from prepare_context import prepare_context_with_fallback, format_context, SubnetContext, get_all_netuids, compute_context_hash
from models import SubnetMeta, ScreenerRaw
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from config import DB_URL
from datetime import datetime
import time
from parameter_settings import DEFAULT_API_DELAY, PROGRESS_SAVE_FREQUENCY, MIN_CONTEXT_TOKENS

# Global state for graceful shutdown
processed_netuids = set()
interrupted = False

# Create the engine once at the top
engine = create_engine(DB_URL)

def signal_handler(signum, frame):
    """Handle SIGINT gracefully."""
    global interrupted
    print(f"\n⚠️  Interrupted! Saving progress...")
    interrupted = True
    save_progress()
    sys.exit(0)

def save_progress():
    """Save processed netuids to file for potential resume."""
    progress_file = "processed_netuids.json"
    with open(progress_file, 'w') as f:
        json.dump(list(processed_netuids), f)
    print(f"Progress saved to {progress_file}")

def load_progress():
    """Load previously processed netuids."""
    progress_file = "processed_netuids.json"
    try:
        with open(progress_file, 'r') as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def process_subnet(netuid: int, force: bool = False) -> bool:
    """Process a single subnet with smart enrichment logic."""
    try:
        print(f"\n{'='*50}")
        print(f"Processing subnet {netuid}...")
        print(f"{'='*50}")
        
        # Get context (this handles fallback to model-only if no context available)
        context = prepare_context_with_fallback(netuid)
        if not context:
            print(f"Failed to prepare context for subnet {netuid}")
            return False
        
        # Check if context has changed (hash-based caching)
        with Session(engine) as session:
            meta = session.get(SubnetMeta, netuid)
            current_hash = compute_context_hash(context)
            print(f"Computed context hash: {current_hash}")
            if isinstance(meta, SubnetMeta) and meta.context_hash is not None:
                print(f"Stored context hash:   {meta.context_hash}")
                if current_hash == meta.context_hash and not force:
                    print(f"Context unchanged for subnet {netuid}, skipping enrichment")
                    return True
                print(f"Context changed for subnet {netuid}, proceeding with enrichment")
            else:
                print(f"No stored hash for subnet {netuid}, proceeding with enrichment")
        
        # Smart enrichment logic based on context availability
        if context.token_count >= MIN_CONTEXT_TOKENS:
            # Rich context available - use context + model knowledge
            print(f"Rich context available ({context.token_count} tokens) - using context + model knowledge")
            enrichment = enrich_with_openai(context, force_model_only=False)
        else:
            # No context or minimal context - use model-only mode
            print(f"Minimal context ({context.token_count} tokens) - using model-only mode")
            enrichment = enrich_with_openai(context, force_model_only=True)
        
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
    # Global state for graceful shutdown
    global processed_netuids, interrupted
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    parser = argparse.ArgumentParser(description="Batch enrich multiple subnets with smart enrichment logic")
    parser.add_argument("--netuids", nargs="+", type=int, help="List of NetUIDs to process")
    parser.add_argument("--range", nargs=2, type=int, help="Range of NetUIDs (start end)")
    parser.add_argument("--force", action="store_true", help="Force enrichment even if context hasn't changed")
    parser.add_argument("--delay", type=float, default=DEFAULT_API_DELAY, help="Delay between API calls (seconds)")
    parser.add_argument("--max-subnets", type=int, help="Maximum number of subnets to process")
    parser.add_argument("--resume", action="store_true", help="Resume from previous run")
    
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
    
    # Load progress if resuming
    if args.resume:
        processed_netuids = load_progress()
        print(f"Resuming from previous run. Already processed: {len(processed_netuids)} subnets")
        # Skip already processed subnets
        netuids = [n for n in netuids if n not in processed_netuids]
    
    # Limit number of subnets if specified
    if args.max_subnets:
        netuids = netuids[:args.max_subnets]
    
    print(f"Processing {len(netuids)} subnets: {netuids}")
    print(f"Delay between calls: {args.delay}s")
    print(f"Force mode: {args.force}")
    print("Smart enrichment: Will use context when available, model-only when not")
    
    # Process subnets
    successful = 0
    failed = 0
    skipped = 0
    
    for i, netuid in enumerate(netuids, 1):
        if interrupted:
            break
            
        print(f"\n[{i}/{len(netuids)}] Processing subnet {netuid}")
        
        result = process_subnet(netuid, force=args.force)
        
        if result:
            successful += 1
            processed_netuids.add(netuid)
        else:
            failed += 1
        
        # Save progress every PROGRESS_SAVE_FREQUENCY subnets
        if i % PROGRESS_SAVE_FREQUENCY == 0:
            save_progress()
        
        # Add delay between calls to avoid rate limiting
        if i < len(netuids) and not interrupted:
            print(f"Waiting {args.delay}s before next call...")
            time.sleep(args.delay)
    
    # Final progress save
    save_progress()
    
    # Summary
    print(f"\n{'='*50}")
    print("BATCH PROCESSING COMPLETE")
    print(f"{'='*50}")
    print(f"Total subnets: {len(netuids)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Success rate: {successful/len(netuids)*100:.1f}%")
    print(f"Total processed (including previous runs): {len(processed_netuids)}")
    


if __name__ == "__main__":
    main() 