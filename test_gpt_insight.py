#!/usr/bin/env python3
"""
Test script for enhanced GPT insights.
Clears cache and regenerates insights to test the new prompt.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.gpt_insight import gpt_insight_service
from services.db import get_db

def test_gpt_insight(netuid: int):
    """Test GPT insight generation for a specific subnet."""
    print(f"Testing GPT insight for subnet {netuid}...")
    
    # Clear cache for this subnet
    gpt_insight_service['clear_subnet_insight_cache'](netuid)
    print("✓ Cache cleared")
    
    # Generate new insight
    insight = gpt_insight_service['get_insight'](netuid)
    print("\n" + "="*50)
    print("GENERATED INSIGHT:")
    print("="*50)
    print(insight)
    print("="*50)
    
    return insight

def test_multiple_subnets():
    """Test multiple subnets to see different insights."""
    test_subnets = [1, 76, 21]  # Safe Scan, another subnet, etc.
    
    for netuid in test_subnets:
        print(f"\n{'='*60}")
        print(f"TESTING SUBNET {netuid}")
        print(f"{'='*60}")
        test_gpt_insight(netuid)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test specific subnet
        netuid = int(sys.argv[1])
        test_gpt_insight(netuid)
    else:
        # Test multiple subnets
        test_multiple_subnets() 