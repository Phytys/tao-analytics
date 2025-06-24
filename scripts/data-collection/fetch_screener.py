#!/usr/bin/env python
import httpx
import json
import sys
from pathlib import Path
from datetime import datetime

# Add the parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import TAO_ENDPOINT, TAO_KEY
from models import Session, ScreenerRaw, SubnetMeta
from services.cache import clear_all_caches

def main():
    print("Fetching screener …")
    r = httpx.get(TAO_ENDPOINT, headers={"X-API-Key": TAO_KEY}, timeout=30)
    r.raise_for_status()
    screener = r.json()

    sess = Session()
    current_time = datetime.utcnow()
    
    for row in screener:
        netuid = row["netuid"]

        # upsert raw table with current timestamp
        screener_raw = ScreenerRaw(
            netuid=netuid,
            raw_json=row,
            fetched_at=current_time
        )
        sess.merge(screener_raw)

        # Update subnet_meta: always update subnet_name, reset LLM fields if name changes
        meta = sess.get(SubnetMeta, netuid)
        if meta is None:
            # New subnet: create a new row
            sess.add(SubnetMeta(netuid=netuid, subnet_name=row["subnet_name"]))
        else:
            # Existing subnet: update subnet_name
            if meta.subnet_name != row["subnet_name"]:
                # If name changed, reset LLM fields and last_enriched_at
                meta.subnet_name = row["subnet_name"]
                meta.tagline = None
                meta.what_it_does = None
                meta.category = None
                meta.tags = None
                meta.confidence = None
                meta.last_enriched_at = None
            else:
                # If name unchanged, just update subnet_name
                meta.subnet_name = row["subnet_name"]

    sess.commit()
    print(f"Saved {len(screener)} rows.")
    sess.close()
    
    # Clear cache to ensure new data is immediately visible
    clear_all_caches()
    print("✅ Cache cleared - new data is now visible in the app!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", e)
        sys.exit(1) 