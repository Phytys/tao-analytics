#!/usr/bin/env python
"""
sdk_smoketest.py
Robust connectivity check against Bittensor networks using explicit endpoints.
"""

import bittensor as bt
import rich
from datetime import datetime
from bt_endpoints import MAIN_RPC, TEST_RPC

def check_network(endpoint: str, label: str):
    """Test connectivity to a specific Bittensor network endpoint."""
    try:
        # Connect using explicit endpoint
        sub = bt.subtensor(endpoint)
        
        # Get basic network info
        current_block = sub.get_current_block()
        neurons = sub.metagraph(netuid=0).n  # Root subnet neurons
        
        # Pretty print the results
        rich.print(f"✅ [green]{label} connectivity successful![/green]")
        rich.print(f"🌐 Endpoint: {endpoint}")
        rich.print(f"📦 Current Block: {current_block:,}")
        rich.print(f"🧠 Root Subnet Neurons: {neurons}")
        rich.print(f"⏰ Timestamp: {datetime.utcnow().isoformat()}Z")
        rich.print()
        
        return True
        
    except Exception as e:
        rich.print(f"❌ [red]{label} connectivity failed:[/red] {e.__class__.__name__}: {e}")
        rich.print()
        return False

def main():
    rich.print("🚀 [bold]Bittensor Network Connectivity Test[/bold]")
    rich.print("=" * 60)
    rich.print()
    
    # Test both networks using explicit endpoints
    check_network(MAIN_RPC, "MAIN-NET (Production)")
    check_network(TEST_RPC, "TEST-NET (Development)")
    
    rich.print("📝 [yellow]Network Clarification:[/yellow]")
    rich.print("   • MAIN-NET: Production network (entrypoint-finney.opentensor.ai)")
    rich.print("   • TEST-NET: Development network (test.finney.opentensor.ai)")
    rich.print("   • 'finney' alias = MAIN-NET (not a test network!)")
    rich.print()

if __name__ == "__main__":
    main() 