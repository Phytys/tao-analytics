#!/usr/bin/env python
"""
sdk_probe.py
Comprehensive Bittensor SDK connectivity and latency probe.
Tests multiple RPC endpoints with detailed metrics collection.
"""

import bittensor as bt
import rich
import json
import time
import statistics
from datetime import datetime
from typing import Dict, List, Tuple
from .endpoints import MAIN_RPC, TEST_RPC

# Stable RPC pool with fallbacks
RPC_POOL = [
    "wss://entrypoint-finney.opentensor.ai:443",  # canonical
    "wss://finney.opentensor.ai:443",             # alt DNS
    "wss://bittensor-api.dwellir.com:443",        # Dwellir public
    "wss://bittensor.publicnode.com:443",         # PublicNode
]

def time_rpc_call(func, *args, **kwargs) -> Tuple[float, bool]:
    """Time a single RPC call and return (latency_ms, success)."""
    start_time = time.time()
    try:
        result = func(*args, **kwargs)
        latency_ms = (time.time() - start_time) * 1000
        return latency_ms, True
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        rich.print(f"    ❌ RPC call failed: {e.__class__.__name__}: {e}")
        return latency_ms, False

def probe_endpoint(endpoint: str, label: str) -> Dict:
    """Probe a single endpoint with comprehensive metrics."""
    rich.print(f"🔍 [bold]Probing {label}[/bold]")
    rich.print(f"🌐 Endpoint: {endpoint}")
    
    try:
        # Connect to endpoint
        sub = bt.subtensor(endpoint)
        
        # Test calls: 3 block calls + 7 metagraph calls = 10 total
        latencies = []
        successes = 0
        total_calls = 10
        
        # Test 1-3: Block calls
        for i in range(3):
            rich.print(f"    📦 Testing block call {i+1}/3...")
            latency, success = time_rpc_call(sub.get_current_block)
            latencies.append(latency)
            if success:
                successes += 1
        
        # Test 4-10: Metagraph calls
        for i in range(7):
            rich.print(f"    🧠 Testing metagraph call {i+1}/7...")
            latency, success = time_rpc_call(sub.metagraph, netuid=0)
            latencies.append(latency)
            if success:
                successes += 1
        
        # Calculate metrics
        failure_rate = (total_calls - successes) / total_calls
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
        
        # Determine safety status
        is_safe = failure_rate <= 0.30
        
        # Get network info for successful connections
        network_info = {}
        if successes > 0:
            try:
                current_block = sub.get_current_block()
                neurons = sub.metagraph(netuid=0).n
                network_info = {
                    "current_block": int(current_block),
                    "root_neurons": int(neurons)
                }
            except Exception as e:
                network_info = {"error": str(e)}
        
        result = {
            "endpoint": endpoint,
            "label": label,
            "total_calls": total_calls,
            "successful_calls": successes,
            "failed_calls": total_calls - successes,
            "failure_rate": round(failure_rate, 3),
            "avg_latency_ms": round(avg_latency, 2),
            "p95_latency_ms": round(p95_latency, 2),
            "is_safe": is_safe,
            "network_info": network_info,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Display results
        status_color = "green" if is_safe else "red"
        status_icon = "✅" if is_safe else "❌"
        
        rich.print(f"    {status_icon} [bold]{label} Results:[/bold]")
        rich.print(f"    📊 Success Rate: {successes}/{total_calls} ({successes/total_calls*100:.1f}%)")
        rich.print(f"    ⏱️  Avg Latency: {avg_latency:.2f}ms")
        rich.print(f"    📈 P95 Latency: {p95_latency:.2f}ms")
        rich.print(f"    🛡️  Status: [{status_color}]{'SAFE' if is_safe else 'UNSAFE'}[/{status_color}]")
        if network_info:
            rich.print(f"    📦 Current Block: {network_info.get('current_block', 'N/A'):,}")
            rich.print(f"    🧠 Root Neurons: {network_info.get('root_neurons', 'N/A')}")
        rich.print()
        
        return result
        
    except Exception as e:
        rich.print(f"    ❌ [red]Connection failed:[/red] {e.__class__.__name__}: {e}")
        rich.print()
        
        return {
            "endpoint": endpoint,
            "label": label,
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "failure_rate": 1.0,
            "avg_latency_ms": 0,
            "p95_latency_ms": 0,
            "is_safe": False,
            "network_info": {"error": str(e)},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

def main():
    rich.print("🚀 [bold]Bittensor SDK Connectivity & Latency Probe[/bold]")
    rich.print("=" * 70)
    rich.print()
    
    # Probe all endpoints in the pool
    results = []
    
    for i, endpoint in enumerate(RPC_POOL, 1):
        label = f"RPC-{i}"
        result = probe_endpoint(endpoint, label)
        results.append(result)
    
    # Calculate summary statistics
    safe_endpoints = [r for r in results if r["is_safe"]]
    unsafe_endpoints = [r for r in results if not r["is_safe"]]
    
    if safe_endpoints:
        avg_latencies = [r["avg_latency_ms"] for r in safe_endpoints]
        p95_latencies = [r["p95_latency_ms"] for r in safe_endpoints]
        
        summary = {
            "total_endpoints": len(results),
            "safe_endpoints": len(safe_endpoints),
            "unsafe_endpoints": len(unsafe_endpoints),
            "overall_avg_latency_ms": round(statistics.mean(avg_latencies), 2),
            "overall_p95_latency_ms": round(statistics.mean(p95_latencies), 2),
            "best_endpoint": min(safe_endpoints, key=lambda x: x["avg_latency_ms"])["endpoint"],
            "worst_safe_endpoint": max(safe_endpoints, key=lambda x: x["avg_latency_ms"])["endpoint"],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    else:
        summary = {
            "total_endpoints": len(results),
            "safe_endpoints": 0,
            "unsafe_endpoints": len(results),
            "overall_avg_latency_ms": 0,
            "overall_p95_latency_ms": 0,
            "best_endpoint": "N/A",
            "worst_safe_endpoint": "N/A",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    # Display summary
    rich.print("📊 [bold]Probe Summary[/bold]")
    rich.print("=" * 40)
    rich.print(f"🔍 Total Endpoints Tested: {summary['total_endpoints']}")
    rich.print(f"✅ Safe Endpoints: {summary['safe_endpoints']}")
    rich.print(f"❌ Unsafe Endpoints: {summary['unsafe_endpoints']}")
    
    if safe_endpoints:
        rich.print(f"⏱️  Overall Avg Latency: {summary['overall_avg_latency_ms']}ms")
        rich.print(f"📈 Overall P95 Latency: {summary['overall_p95_latency_ms']}ms")
        rich.print(f"🏆 Best Endpoint: {summary['best_endpoint']}")
        rich.print(f"🐌 Worst Safe Endpoint: {summary['worst_safe_endpoint']}")
    else:
        rich.print("⚠️  [red]No safe endpoints found![/red]")
    
    rich.print()
    
    # Save results to JSON
    output_data = {
        "summary": summary,
        "endpoint_results": results,
        "probe_config": {
            "rpc_pool": RPC_POOL,
            "calls_per_endpoint": 10,
            "failure_threshold": 0.30
        }
    }
    
    with open("sdk_probe_results.json", "w") as f:
        json.dump(output_data, f, indent=2)
    
    rich.print(f"💾 Results saved to: [blue]sdk_probe_results.json[/blue]")
    rich.print()
    
    # Final verdict
    if summary["safe_endpoints"] >= 2:
        rich.print("🎉 [bold green]Probe Result: GREEN[/bold green] - Multiple safe endpoints available")
    elif summary["safe_endpoints"] == 1:
        rich.print("⚠️  [bold yellow]Probe Result: YELLOW[/bold yellow] - Single safe endpoint available")
    else:
        rich.print("🚨 [bold red]Probe Result: RED[/bold red] - No safe endpoints found")

if __name__ == "__main__":
    main() 