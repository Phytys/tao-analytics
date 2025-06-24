#!/usr/bin/env python3
"""
Quick sanity-check: query current block height from a public main-net RPC
without running a local node.
"""
import bittensor as bt
import rich

CHAIN_ENDPOINT = "wss://entrypoint-finney.opentensor.ai:443"

sub = bt.subtensor(
    network="finney",          # name in bittensor's preset table
    chain_endpoint=CHAIN_ENDPOINT,
    timeout=12,                # seconds
)

info = {
    "network": sub.network,
    "chain_endpoint": CHAIN_ENDPOINT,
    "current_block": sub.get_current_block(),
    "finalized_block": sub.get_finalized_head(),
}
rich.print(info) 