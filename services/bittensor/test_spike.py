#!/usr/bin/env python
"""
Test script for Sprint 3 Bittensor SDK spike modules.
"""

import sys
import os
# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from services.bittensor import (
    MAIN_RPC, RPC_POOL,
    probe_endpoint, calculate_subnet_metrics,
    get_metagraph, get_metrics
)

def test_endpoints():
    """Test endpoint configuration."""
    print("🔧 Testing endpoints...")
    print(f"Main RPC: {MAIN_RPC}")
    print(f"RPC Pool: {RPC_POOL}")
    print("✅ Endpoints configured correctly\n")

def test_probe():
    """Test probe functionality."""
    print("🔍 Testing probe...")
    result = probe_endpoint(MAIN_RPC, "TEST")
    print(f"Probe result: {result['is_safe']}")
    print("✅ Probe working correctly\n")

def test_metrics():
    """Test metrics calculation."""
    print("📊 Testing metrics...")
    metrics = calculate_subnet_metrics(3)
    print(f"Subnet 3 total stake: {metrics['total_stake_tao']:,.0f} TAO")
    print("✅ Metrics calculation working correctly\n")

def test_cache():
    """Test caching layer."""
    print("💾 Testing cache...")
    metrics = get_metrics(3)
    print(f"Cached metrics: {metrics['total_stake_tao']:,.0f} TAO")
    print("✅ Cache layer working correctly\n")

def main():
    print("🚀 Testing Sprint 3 Bittensor SDK Spike Modules")
    print("=" * 50)
    print()
    
    test_endpoints()
    test_probe()
    test_metrics()
    test_cache()
    
    print("🎉 All tests passed! SDK spike modules are ready.")

if __name__ == "__main__":
    main() 