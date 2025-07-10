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

def process_subnet(netuid: int, force: bool = False) -> dict:
    """Process a single subnet with smart enrichment logic.
    
    Returns:
        dict: Result with keys: 'status', 'reason', 'context_tokens', 'mode'
    """
    try:
        print(f"\n{'='*50}")
        print(f"Processing subnet {netuid}...")
        print(f"{'='*50}")
        
        # Get context (this handles fallback to model-only if no context available)
        context = prepare_context_with_fallback(netuid)
        if not context:
            print(f"Failed to prepare context for subnet {netuid}")
            return {'status': 'failed', 'reason': 'no_context', 'context_tokens': 0, 'mode': 'none'}
        
        # Check if context has changed (hash-based caching) with retry for connection issues
        max_db_retries = 3
        for db_attempt in range(max_db_retries):
            try:
                with Session(engine) as session:
                    meta = session.get(SubnetMeta, netuid)
                    current_hash = compute_context_hash(context)
                    print(f"Computed context hash: {current_hash}")
                    if isinstance(meta, SubnetMeta) and meta.context_hash is not None:
                        print(f"Stored context hash:   {meta.context_hash}")
                        if current_hash == meta.context_hash and not force:
                            print(f"Context unchanged for subnet {netuid}, skipping enrichment")
                            return {
                                'status': 'skipped', 
                                'reason': 'context_unchanged', 
                                'context_tokens': context.token_count,
                                'mode': 'none'
                            }
                        print(f"Context changed for subnet {netuid}, proceeding with enrichment")
                    else:
                        print(f"No stored hash for subnet {netuid}, proceeding with enrichment")
                    break  # Success, exit retry loop
            except Exception as e:
                if "too many connections" in str(e).lower() and db_attempt < max_db_retries - 1:
                    wait_time = (db_attempt + 1) * 10  # 10, 20, 30 seconds
                    print(f"Database connection limit reached, waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    # Connection failure - return special status
                    if "too many connections" in str(e).lower():
                        print(f"Database connection limit reached for subnet {netuid}")
                        return {
                            'status': 'failed', 
                            'reason': 'connection_limit', 
                            'context_tokens': context.token_count,
                            'mode': 'none',
                            'error': str(e)
                        }
                    else:
                        raise e  # Re-raise if it's not a connection issue
        
        # Smart enrichment logic based on context availability
        if context.token_count >= MIN_CONTEXT_TOKENS:
            # Rich context available - use context + model knowledge
            print(f"Rich context available ({context.token_count} tokens) - using context + model knowledge")
            enrichment = enrich_with_openai(context, force_model_only=False)
            mode = 'context_rich'
        else:
            # No context or minimal context - use model-only mode
            print(f"Minimal context ({context.token_count} tokens) - using model-only mode")
            enrichment = enrich_with_openai(context, force_model_only=True)
            mode = 'model_only'
        
        if enrichment:
            print(f"\nEnrichment successful for subnet {netuid}")
            save_enrichment(netuid, enrichment, context)
            return {
                'status': 'success', 
                'reason': 'enriched', 
                'context_tokens': context.token_count,
                'mode': mode
            }
        else:
            print(f"Enrichment failed for subnet {netuid}")
            return {
                'status': 'failed', 
                'reason': 'enrichment_failed', 
                'context_tokens': context.token_count,
                'mode': mode
            }
            
    except Exception as e:
        print(f"Error processing subnet {netuid}: {e}")
        return {
            'status': 'failed', 
            'reason': 'exception', 
            'context_tokens': 0,
            'mode': 'none',
            'error': str(e)
        }

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
    
    # Process subnets with detailed tracking
    results = {
        'successful': {'context_rich': [], 'model_only': []},
        'skipped': [],
        'failed': {'no_context': [], 'enrichment_failed': [], 'connection_limit': [], 'exception': []}
    }
    
    # Add pause on connection failure option
    parser.add_argument("--pause-on-connection-failure", action="store_true", 
                       help="Pause processing when hitting database connection limits")
    
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
    print(f"Pause on connection failure: {args.pause_on_connection_failure}")
    print("Smart enrichment: Will use context when available, model-only when not")
    
    for i, netuid in enumerate(netuids, 1):
        if interrupted:
            break
            
        print(f"\n[{i}/{len(netuids)}] Processing subnet {netuid}")
        
        result = process_subnet(netuid, force=args.force)
        
        # Track detailed results
        if result['status'] == 'success':
            results['successful'][result['mode']].append({
                'netuid': netuid,
                'context_tokens': result['context_tokens']
            })
            processed_netuids.add(netuid)
        elif result['status'] == 'skipped':
            results['skipped'].append({
                'netuid': netuid,
                'context_tokens': result['context_tokens']
            })
        else:  # failed
            results['failed'][result['reason']].append({
                'netuid': netuid,
                'context_tokens': result['context_tokens'],
                'error': result.get('error', 'Unknown error')
            })
            
            # Pause on connection failure if requested
            if result['reason'] == 'connection_limit' and args.pause_on_connection_failure:
                print(f"\n⚠️  CONNECTION LIMIT REACHED at subnet {netuid}")
                print("Processing paused due to database connection limits.")
                print("You can resume later with: --resume")
                break
        
        # Save progress every PROGRESS_SAVE_FREQUENCY subnets
        if i % PROGRESS_SAVE_FREQUENCY == 0:
            save_progress()
        
        # Add delay between calls to avoid rate limiting
        if i < len(netuids) and not interrupted:
            print(f"Waiting {args.delay}s before next call...")
            time.sleep(args.delay)
    
    # Final progress save
    save_progress()
    
    # Comprehensive Summary
    print(f"\n{'='*60}")
    print("🎯 BATCH ENRICHMENT COMPLETE - DETAILED SUMMARY")
    print(f"{'='*60}")
    
    # Overall stats
    total_processed = len(netuids)
    total_successful = len(results['successful']['context_rich']) + len(results['successful']['model_only'])
    total_skipped = len(results['skipped'])
    total_failed = sum(len(v) for v in results['failed'].values())
    
    print(f"📊 OVERALL STATISTICS:")
    print(f"   Total subnets processed: {total_processed}")
    print(f"   Successfully enriched: {total_successful}")
    print(f"   Skipped (no changes): {total_skipped}")
    print(f"   Failed: {total_failed}")
    print(f"   Success rate: {total_successful/total_processed*100:.1f}%")
    print(f"   Skip rate: {total_skipped/total_processed*100:.1f}%")
    print(f"   Total processed (including previous runs): {len(processed_netuids)}")
    
    # Successful enrichments
    if total_successful > 0:
        print(f"\n✅ SUCCESSFULLY ENRICHED ({total_successful} subnets):")
        
        if results['successful']['context_rich']:
            context_rich_netuids = [r['netuid'] for r in results['successful']['context_rich']]
            avg_tokens = sum(r['context_tokens'] for r in results['successful']['context_rich']) / len(results['successful']['context_rich'])
            print(f"   📚 Context-rich mode ({len(context_rich_netuids)}): {context_rich_netuids}")
            print(f"      Average context tokens: {avg_tokens:.0f}")
        
        if results['successful']['model_only']:
            model_only_netuids = [r['netuid'] for r in results['successful']['model_only']]
            avg_tokens = sum(r['context_tokens'] for r in results['successful']['model_only']) / len(results['successful']['model_only'])
            print(f"   🤖 Model-only mode ({len(model_only_netuids)}): {model_only_netuids}")
            print(f"      Average context tokens: {avg_tokens:.0f}")
    
    # Skipped subnets
    if total_skipped > 0:
        print(f"\n⏭️  SKIPPED - NO CHANGES ({total_skipped} subnets):")
        skipped_netuids = [r['netuid'] for r in results['skipped']]
        print(f"   Subnets: {skipped_netuids}")
        print(f"   (Context hash unchanged - no OpenAI API calls made)")
    
    # Failed subnets
    if total_failed > 0:
        print(f"\n❌ FAILED ({total_failed} subnets):")
        
        if results['failed']['no_context']:
            no_context_netuids = [r['netuid'] for r in results['failed']['no_context']]
            print(f"   🔍 No context available: {no_context_netuids}")
        
        if results['failed']['enrichment_failed']:
            enrichment_failed_netuids = [r['netuid'] for r in results['failed']['enrichment_failed']]
            print(f"   🤖 OpenAI enrichment failed: {enrichment_failed_netuids}")
        
        if results['failed']['connection_limit']:
            connection_failed_netuids = [r['netuid'] for r in results['failed']['connection_limit']]
            print(f"   🔌 Database connection limit: {connection_failed_netuids}")
            print(f"      ⚠️  These subnets need to be re-run when database connections are available")
        
        if results['failed']['exception']:
            exception_netuids = [r['netuid'] for r in results['failed']['exception']]
            print(f"   💥 Exceptions occurred: {exception_netuids}")
            for result in results['failed']['exception']:
                print(f"      Subnet {result['netuid']}: {result['error']}")
    
    # Cost implications
    print(f"\n💰 COST IMPLICATIONS:")
    print(f"   OpenAI API calls made: {total_successful}")
    print(f"   API calls saved (skipped): {total_skipped}")
    print(f"   Total potential cost savings: ${total_skipped * 0.01:.2f} (estimated)")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    if results['failed']['connection_limit']:
        print(f"   🔌 {len(results['failed']['connection_limit'])} subnets failed due to connection limits")
        print(f"      Re-run these subnets: {[r['netuid'] for r in results['failed']['connection_limit']]}")
    if results['failed']['enrichment_failed']:
        print(f"   ⚠️  {len(results['failed']['enrichment_failed'])} subnets failed enrichment - consider running with --force")
    if total_skipped > 0:
        print(f"   ✅ {total_skipped} subnets skipped (context unchanged) - this is normal and saves costs")
    if total_successful > 0:
        print(f"   🎉 {total_successful} subnets successfully enriched!")
    
    print(f"\n{'='*60}")
    print("🏁 Enrichment process complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main() 