#!/usr/bin/env python
import json
import sys
from pathlib import Path
import sqlite3
from tabulate import tabulate
import argparse

# Add the parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))
from models import Session, ScreenerRaw

def inspect_raw_data(netuid: int = None):
    """Inspect raw data from screener_raw table."""
    sess = Session()
    
    if netuid:
        # Get specific subnet
        raw = sess.get(ScreenerRaw, netuid)
        if not raw:
            print(f"No data found for netuid {netuid}")
            return
        
        data = raw.raw_json
        print(f"\n=== Raw Data for netuid {netuid} ===")
        print("\nBasic Info:")
        basic_info = {
            'netuid': data.get('netuid'),
            'subnet_name': data.get('subnet_name'),
            'price': data.get('price'),
            'market_cap_tao': data.get('market_cap_tao'),
            'emission_pct': data.get('emission_pct'),
            'github_repo': data.get('github_repo'),
            'subnet_website': data.get('subnet_website'),
            'discord': data.get('discord'),
            'owner_coldkey': data.get('owner_coldkey'),
            'owner_hotkey': data.get('owner_hotkey')
        }
        print(tabulate([basic_info.items()], tablefmt='grid'))
        
        print("\nFull JSON Data:")
        print(json.dumps(data, indent=2))
        
    else:
        # List all subnets with basic info
        rows = sess.query(ScreenerRaw).all()
        print("\n=== All Subnets ===")
        table_data = []
        for row in rows:
            data = row.raw_json
            table_data.append([
                data.get('netuid'),
                data.get('subnet_name'),
                data.get('price'),
                data.get('market_cap_tao'),
                data.get('github_repo'),
                data.get('subnet_website')
            ])
        
        print(tabulate(
            table_data,
            headers=['netuid', 'name', 'price', 'market_cap', 'github', 'website'],
            tablefmt='grid'
        ))
    
    sess.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect raw data from TAO.app API")
    parser.add_argument("--netuid", type=int, help="netuid to inspect (optional)")
    args = parser.parse_args()
    
    inspect_raw_data(args.netuid) 