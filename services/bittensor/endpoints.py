"""
Bittensor network endpoints and constants.
"""

# Main production network (what was confusingly called "finney")
MAIN_RPC = "wss://entrypoint-finney.opentensor.ai:443"

# Test network
TEST_RPC = "wss://test.finney.opentensor.ai:443"

# Archive network (optional)
ARCHIVE_RPC = "wss://archive.chain.opentensor.ai:443"

# Lite RPC (optional)
LITE_RPC = "wss://lite.chain.opentensor.ai:443"

# Stable RPC pool with fallbacks for SDK probe
RPC_POOL = [
    "wss://entrypoint-finney.opentensor.ai:443",  # canonical
    "wss://finney.opentensor.ai:443",             # alt DNS
    "wss://bittensor-api.dwellir.com:443",        # Dwellir public
    "wss://bittensor.publicnode.com:443",         # PublicNode
]

# Network aliases for bt.subtensor()
NETWORK_ALIASES = {
    "main": MAIN_RPC,      # Main production network
    "test": TEST_RPC,      # Test network
    "finney": MAIN_RPC,    # Legacy alias for main-net
} 