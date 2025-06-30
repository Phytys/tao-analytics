#!/usr/bin/env python
"""
Debug script to inspect metagraph fields for subnet 64.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from services.bittensor.endpoints import MAIN_RPC
import bittensor as bt

def inspect_metagraph(netuid=64):
    """Inspect all available fields on the metagraph object."""
    print(f"🔍 Inspecting metagraph for subnet {netuid}")
    print(f"🌐 Endpoint: {MAIN_RPC}")
    print("=" * 60)
    
    try:
        sub = bt.subtensor(MAIN_RPC)
        mg = sub.metagraph(netuid=netuid)
        
        print("📋 Available attributes on metagraph object:")
        print("-" * 40)
        
        # Get all attributes
        attrs = [attr for attr in dir(mg) if not attr.startswith('_')]
        
        # Filter for emission-related attributes
        emission_attrs = [attr for attr in attrs if 'emission' in attr.lower()]
        print("🎯 Emission-related attributes:")
        for attr in emission_attrs:
            try:
                value = getattr(mg, attr)
                print(f"  {attr}: {value}")
            except Exception as e:
                print(f"  {attr}: Error accessing - {e}")
        
        print("\n📊 Other key attributes:")
        key_attrs = ['uids', 'stake', 'incentive', 'consensus', 'trust', 'weights', 'bonds']
        for attr in key_attrs:
            if attr in attrs:
                try:
                    value = getattr(mg, attr)
                    if hasattr(value, 'shape'):
                        print(f"  {attr}: shape {value.shape}, type {type(value)}")
                    else:
                        print(f"  {attr}: {value}")
                except Exception as e:
                    print(f"  {attr}: Error accessing - {e}")
        
        print("\n🔍 All attributes (first 20):")
        for i, attr in enumerate(attrs[:20]):
            print(f"  {attr}")
        if len(attrs) > 20:
            print(f"  ... and {len(attrs) - 20} more")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    inspect_metagraph(64) 