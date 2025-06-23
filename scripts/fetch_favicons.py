#!/usr/bin/env python3
"""
Fetch favicons for all subnets and update the database.
This script will download favicons from subnet websites and cache them locally.
"""

import sys
from pathlib import Path
import time
from typing import List, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import load_subnet_frame
from services.favicons import favicon_service
from models import SubnetMeta
from config import DB_URL
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

def fetch_favicons_for_subnets(delay: float = 1.0, max_subnets: Optional[int] = None) -> None:
    """
    Fetch favicons for all subnets with websites.
    
    Args:
        delay: Delay between requests in seconds
        max_subnets: Maximum number of subnets to process (for testing)
    """
    print("🔍 Loading subnet data...")
    df = load_subnet_frame()
    
    # Filter subnets with websites
    subnets_with_websites = df[df['website_url'].notna() & (df['website_url'] != '')]
    
    if max_subnets:
        subnets_with_websites = subnets_with_websites.head(max_subnets)
    
    total_subnets = len(subnets_with_websites)
    print(f"📊 Found {total_subnets} subnets with websites")
    
    if total_subnets == 0:
        print("❌ No subnets with websites found")
        return
    
    # Database connection
    engine = create_engine(DB_URL)
    session = Session(engine)
    
    successful = 0
    failed = 0
    skipped = 0
    
    print(f"\n🚀 Starting favicon fetch for {total_subnets} subnets...")
    print("=" * 60)
    
    for i, (_, row) in enumerate(subnets_with_websites.iterrows(), 1):
        netuid = row['netuid']
        website_url = row['website_url']
        subnet_name = row['subnet_name'] or f"Subnet {netuid}"
        
        print(f"[{i}/{total_subnets}] Processing {subnet_name} (NetUID {netuid})")
        print(f"   Website: {website_url}")
        
        try:
            # Check if favicon already exists in database
            meta = session.get(SubnetMeta, netuid)
            if meta and meta.favicon_url:
                print(f"   ✅ Favicon already cached: {meta.favicon_url}")
                skipped += 1
                continue
            
            # Fetch favicon
            favicon_url = favicon_service.get_favicon_url(website_url)
            
            if favicon_url:
                # Update database
                if not meta:
                    meta = SubnetMeta(netuid=netuid)
                    session.add(meta)
                
                meta.favicon_url = favicon_url
                session.commit()
                
                print(f"   ✅ Favicon fetched: {favicon_url}")
                successful += 1
            else:
                print(f"   ❌ No favicon found")
                failed += 1
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            failed += 1
            session.rollback()
        
        # Add delay between requests
        if i < total_subnets:
            print(f"   ⏳ Waiting {delay}s...")
            time.sleep(delay)
        
        print()
    
    session.close()
    
    # Summary
    print("=" * 60)
    print("📊 FAVICON FETCH SUMMARY")
    print("=" * 60)
    print(f"Total subnets processed: {total_subnets}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Skipped (already cached): {skipped}")
    print(f"Success rate: {(successful/total_subnets)*100:.1f}%")
    
    # Cache cleanup
    print(f"\n🧹 Cleaning up old favicons...")
    deleted_count = favicon_service.cleanup_old_favicons(max_age_days=30)
    print(f"Deleted {deleted_count} old favicon files")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch favicons for all subnets")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests (seconds)")
    parser.add_argument("--max-subnets", type=int, help="Maximum number of subnets to process (for testing)")
    parser.add_argument("--cleanup", action="store_true", help="Only cleanup old favicons")
    
    args = parser.parse_args()
    
    if args.cleanup:
        print("🧹 Cleaning up old favicons...")
        deleted_count = favicon_service.cleanup_old_favicons(max_age_days=30)
        print(f"Deleted {deleted_count} old favicon files")
        return
    
    fetch_favicons_for_subnets(delay=args.delay, max_subnets=args.max_subnets)

if __name__ == "__main__":
    main() 