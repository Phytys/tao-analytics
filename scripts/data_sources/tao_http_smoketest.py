#!/usr/bin/env python
"""
tao_http_smoketest.py
Alternative connectivity check against Bittensor MAIN-net
using HTTP requests (no bittensor package needed).

Run:  python -m scripts.data_sources.tao_http_smoketest
"""

import requests
import json
import sys
from datetime import datetime, timezone

# -------- config -----------------
RPC_ENDPOINT = "https://entrypoint-finney.opentensor.ai:443"
HTTP_ENDPOINT = "https://entrypoint-finney.opentensor.ai"
TIMEOUT_SEC = 30
# ---------------------------------

def test_http_connectivity():
    """Test basic HTTP connectivity to Bittensor endpoints."""
    try:
        # Test basic HTTP connectivity
        response = requests.get(f"{HTTP_ENDPOINT}/health", timeout=TIMEOUT_SEC)
        if response.status_code == 200:
            return True, "HTTP endpoint accessible"
        else:
            return False, f"HTTP endpoint returned status {response.status_code}"
    except requests.exceptions.RequestException as e:
        return False, f"HTTP connection failed: {e}"

def test_rpc_connectivity():
    """Test RPC connectivity using a simple JSON-RPC call."""
    try:
        # Simple JSON-RPC call to get chain head
        payload = {
            "jsonrpc": "2.0",
            "method": "chain_getHeader",
            "params": [],
            "id": 1
        }
        
        headers = {
            "Content-Type": "application/json",
        }
        
        response = requests.post(
            f"{RPC_ENDPOINT}/json-rpc",
            json=payload,
            headers=headers,
            timeout=TIMEOUT_SEC
        )
        
        if response.status_code == 200:
            data = response.json()
            if "result" in data:
                return True, f"RPC endpoint accessible, block number: {data['result'].get('number', 'unknown')}"
            else:
                return False, f"RPC endpoint responded but no result: {data}"
        else:
            return False, f"RPC endpoint returned status {response.status_code}"
            
    except requests.exceptions.RequestException as e:
        return False, f"RPC connection failed: {e}"
    except json.JSONDecodeError as e:
        return False, f"RPC response not valid JSON: {e}"

def main() -> None:
    print("==== Bittensor HTTP connectivity test ====")
    print(f"HTTP Endpoint: {HTTP_ENDPOINT}")
    print(f"RPC Endpoint:  {RPC_ENDPOINT}")
    print(f"Timeout:       {TIMEOUT_SEC}s")
    print(f"Timestamp:     {datetime.now(timezone.utc).isoformat()}Z")
    print()
    
    # Test HTTP connectivity
    http_ok, http_msg = test_http_connectivity()
    print(f"HTTP Test:     {'✓' if http_ok else '✗'} {http_msg}")
    
    # Test RPC connectivity
    rpc_ok, rpc_msg = test_rpc_connectivity()
    print(f"RPC Test:      {'✓' if rpc_ok else '✗'} {rpc_msg}")
    
    print()
    if http_ok or rpc_ok:
        print("✓ At least one endpoint is accessible")
        print("  Note: Full SDK functionality requires bittensor package")
        print("  Install with: pip install bittensor (Python 3.11/3.12 recommended)")
    else:
        print("✗ No endpoints accessible")
        sys.exit(1)

if __name__ == "__main__":
    main() 