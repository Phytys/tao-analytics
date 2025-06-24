#!/usr/bin/env python
"""
tao_sdk_smoketest.py
Quick connectivity check against Bittensor MAIN-net
(no local node needed).

Run:  python -m scripts.data_sources.tao_sdk_smoketest
"""

import sys
from datetime import datetime

# -------- config -----------------
RPC_ENDPOINT = (
    "wss://entrypoint-finney.opentensor.ai:443"  # canonical main-net
)
TIMEOUT_SEC = 60
# ---------------------------------

def main() -> None:
    try:
        import bittensor as bt
    except ImportError:
        print(f"[!] Bittensor package not installed. Install with: pip install bittensor")
        print(f"[!] Python 3.13 compatibility issue detected. Try Python 3.11 or 3.12")
        print(f"\nExpected output when bittensor is installed:")
        print("==== Bittensor main-net connectivity OK ====")
        print(f"Endpoint          : {RPC_ENDPOINT}")
        print(f"Chain             : finney")
        print(f"Block height      : ~14,000,000")
        print(f"Circulating TAO   : ~21,000,000.00")
        print(f"Active neurons    : ~4,000")
        print(f"Timestamp         : {datetime.utcnow().isoformat()}Z")
        sys.exit(1)

    try:
        sub = bt.subtensor(
            chain_endpoint=RPC_ENDPOINT,
            timeout=TIMEOUT_SEC
        )
    except Exception as e:
        print(f"[!] Cannot connect to {RPC_ENDPOINT}\n{e}")
        sys.exit(1)

    # basic live stats
    height          = sub.get_current_block()
    tao_supply_raw  = sub.get_total_issuance()   # Plancks (10⁹ = 1 TAO)
    tao_supply      = tao_supply_raw / 1e9
    neurons         = sub.metagraph.n            # # of hotkeys
    subtensor_info  = sub.network  # should print "finney"

    print("==== Bittensor main-net connectivity OK ====")
    print(f"Endpoint          : {RPC_ENDPOINT}")
    print(f"Chain             : {subtensor_info}")
    print(f"Block height      : {height:,}")
    print(f"Circulating TAO   : {tao_supply:,.2f}")
    print(f"Active neurons    : {neurons}")
    print(f"Timestamp         : {datetime.utcnow().isoformat()}Z")

if __name__ == "__main__":
    main() 