#!/usr/bin/env python
"""
Debug script to check emission fields on metagraph.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from services.bittensor.endpoints import MAIN_RPC
import bittensor as bt

def debug_emissions(netuid=64):
    """Debug emission fields on metagraph."""
    print(f"🔍 Debugging emissions for subnet {netuid}")
    print(f"🌐 Endpoint: {MAIN_RPC}")
    print("=" * 60)
    
    try:
        sub = bt.subtensor(MAIN_RPC)
        mg = sub.metagraph(netuid=netuid)
        
        print("📋 Checking emission-related attributes:")
        print("-" * 40)
        
        # Check for emission vectors
        emission_fields = ['owner_emission', 'miner_emission', 'validator_emission']
        for field in emission_fields:
            if hasattr(mg, field):
                value = getattr(mg, field)
                print(f"✅ {field}: {type(value)}, shape: {value.shape if hasattr(value, 'shape') else 'N/A'}")
                if hasattr(value, 'sum'):
                    total = value.sum().item()
                    print(f"   Total: {total}")
            else:
                print(f"❌ {field}: Not found")
        
        print("\n🔍 All attributes containing 'emission':")
        emission_attrs = [attr for attr in dir(mg) if 'emission' in attr.lower()]
        for attr in emission_attrs:
            try:
                value = getattr(mg, attr)
                print(f"  {attr}: {value}")
            except Exception as e:
                print(f"  {attr}: Error accessing - {e}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_emissions(64) 