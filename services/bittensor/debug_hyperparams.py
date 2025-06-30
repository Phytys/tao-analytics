#!/usr/bin/env python
"""
Debug script to inspect subnet hyperparameters.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from services.bittensor.endpoints import MAIN_RPC
import bittensor as bt

def inspect_hyperparams(netuid=64):
    """Inspect subnet hyperparameters."""
    print(f"🔍 Inspecting hyperparameters for subnet {netuid}")
    print(f"🌐 Endpoint: {MAIN_RPC}")
    print("=" * 60)
    
    try:
        sub = bt.subtensor(MAIN_RPC)
        hyperparams = sub.get_subnet_hyperparameters(netuid)
        
        print("📋 Hyperparameters object:")
        print(f"Type: {type(hyperparams)}")
        print(f"Dir: {dir(hyperparams)}")
        print()
        
        print("🎯 Emission-related attributes:")
        emission_attrs = [attr for attr in dir(hyperparams) if 'emission' in attr.lower()]
        for attr in emission_attrs:
            try:
                value = getattr(hyperparams, attr)
                print(f"  {attr}: {value}")
            except Exception as e:
                print(f"  {attr}: Error accessing - {e}")
        
        print("\n📊 All attributes:")
        for attr in dir(hyperparams):
            if not attr.startswith('_'):
                try:
                    value = getattr(hyperparams, attr)
                    print(f"  {attr}: {value}")
                except Exception as e:
                    print(f"  {attr}: Error accessing - {e}")
        
        print("\n🔍 Checking for emission methods on subtensor:")
        emission_methods = [method for method in dir(sub) if 'emission' in method.lower()]
        for method in emission_methods:
            print(f"  {method}")
        
        print("\n🔍 Checking for ratio methods on subtensor:")
        ratio_methods = [method for method in dir(sub) if 'ratio' in method.lower()]
        for method in ratio_methods:
            print(f"  {method}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    inspect_hyperparams(64) 