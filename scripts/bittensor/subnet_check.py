#!/usr/bin/env python
"""
subnet_check.py
Diagnostic script to check subnet sizes and verify correct subnet IDs.
"""

import bittensor as bt
import rich
from bt_endpoints import MAIN_RPC

def check_subnet(endpoint: str, netuid: int, label: str):
    """Check a specific subnet."""
    try:
        sub = bt.subtensor(endpoint)
        metagraph = sub.metagraph(netuid=netuid)
        
        rich.print(f"🔍 [blue]{label} (netuid={netuid}):[/blue]")
        rich.print(f"   Neurons: {metagraph.n}")
        rich.print(f"   Hotkeys: {len(metagraph.hotkeys)}")
        rich.print(f"   Stake: {metagraph.stake.sum():.2f} TAO")
        rich.print()
        
        return metagraph.n
        
    except Exception as e:
        rich.print(f"❌ [red]{label} (netuid={netuid}) failed:[/red] {e}")
        rich.print()
        return 0

def main():
    rich.print("🔍 [bold]Bittensor Subnet Diagnostic[/bold]")
    rich.print("=" * 50)
    rich.print()
    
    # Check different subnet IDs
    check_subnet(MAIN_RPC, 0, "Root Subnet")
    check_subnet(MAIN_RPC, 1, "Subnet 1")
    check_subnet(MAIN_RPC, 2, "Subnet 2")
    check_subnet(MAIN_RPC, 3, "Subnet 3")
    
    # Check block progression
    rich.print("⏱️ [yellow]Block Progression Check:[/yellow]")
    sub = bt.subtensor(MAIN_RPC)
    block1 = sub.get_current_block()
    rich.print(f"   Current block: {block1:,}")
    
    import time
    time.sleep(2)
    
    block2 = sub.get_current_block()
    rich.print(f"   After 2s: {block2:,}")
    rich.print(f"   Difference: {block2 - block1}")
    rich.print()

if __name__ == "__main__":
    main() 