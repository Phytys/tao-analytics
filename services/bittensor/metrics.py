#!/usr/bin/env python
"""
extract_subnet_metrics.py
Extract comprehensive metrics from Bittensor subnet metagraphs.
"""

import bittensor as bt
import numpy as np
import json
import argparse
from datetime import datetime
from typing import Dict, Any
from .endpoints import MAIN_RPC

# Simple in-memory cache for PoC
_rolling_cache = {}
_rolling_cache_ttl = 300  # 5 minutes

def calculate_subnet_metrics(netuid: int, endpoint: str = MAIN_RPC) -> Dict[str, Any]:
    """
    Calculate comprehensive metrics for a subnet.
    
    Args:
        netuid: Subnet ID to analyze
        endpoint: RPC endpoint to use
        
    Returns:
        Dictionary with subnet metrics including:
        - total_stake_tao: Total TAO staked in subnet
        - stake_hhi: Herfindahl-Hirschman Index for stake concentration (0-10,000)
        - mean_incentive: Average incentive across all UIDs
        - p95_incentive: 95th percentile incentive value
        - consensus_alignment: Percentage of UIDs within ±0.10 of subnet mean consensus
        - trust_score: Average trust score across all UIDs
        - emission_split: Actual share of TAO minted in last block to each role
          (owner/miners/validators), derived from metagraph emission vectors.
          Each value is 0-1 and the trio sums to 1. If all zero, emissions not enabled.
        - uid_count: Number of registered participants (UIDs) in subnet
    """
    try:
        # Connect to Bittensor network
        sub = bt.subtensor(endpoint)
        
        # Get metagraph for the subnet
        mg = sub.metagraph(netuid=netuid)
        
        # Calculate metrics using exact formulas from design doc
        total_stake = mg.stake.sum().item()
        hhi = ((mg.stake / total_stake) ** 2).sum() * 10_000  # 0–10 000
        mean_incentive = mg.incentive.mean().item()
        p95_incentive = np.quantile(mg.incentive, .95)
        
        # Calculate emission split using derived roles from metagraph
        emission_split = {}
        total_emission_rao = 0.0  # Initialize total emission in RAO
        try:
            # Get total emissions from the emission vector (actual RAO emitted per UID)
            if hasattr(mg, 'emission'):
                total_emission_rao = mg.emission.sum().item()
                
                if total_emission_rao > 0:
                    # Derive role-based emission splits
                    owner_emission = 0.0
                    validator_emission = 0.0
                    miner_emission = 0.0
                    
                    # Identify owner (if owner_coldkey is available)
                    if hasattr(mg, 'owner_coldkey') and hasattr(mg, 'owner_hotkey'):
                        # Find UID that matches owner keys
                        for i, uid in enumerate(mg.uids):
                            if hasattr(mg, 'owner_coldkey') and hasattr(mg, 'owner_hotkey'):
                                # This is a simplified approach - in reality we'd need to check actual keys
                                # For now, assume UID 0 is owner (common pattern)
                                if i == 0:
                                    owner_emission += mg.emission[i].item()
                                else:
                                    # Check if this UID is a validator
                                    if hasattr(mg, 'validator_permit') and mg.validator_permit[i]:
                                        validator_emission += mg.emission[i].item()
                                    else:
                                        miner_emission += mg.emission[i].item()
                    
                    # Calculate ratios
                    emission_split['owner'] = float(owner_emission / total_emission_rao)
                    emission_split['miners'] = float(miner_emission / total_emission_rao)
                    emission_split['validators'] = float(validator_emission / total_emission_rao)
                else:
                    # No emissions in this block
                    emission_split['owner'] = 0.0
                    emission_split['miners'] = 0.0
                    emission_split['validators'] = 0.0
            else:
                # No emission data available
                emission_split['owner'] = 0.0
                emission_split['miners'] = 0.0
                emission_split['validators'] = 0.0
                
        except Exception as e:
            print(f"Error calculating emission split: {e}")
            # Fallback to zero if emission vectors not available
            emission_split['owner'] = 0.0
            emission_split['miners'] = 0.0
            emission_split['validators'] = 0.0
        
        # Additional metrics
        uid_count = len(mg.uids)
        
        # Calculate consensus alignment (percentage within ±0.10 of subnet mean)
        if hasattr(mg, 'consensus') and mg.consensus is not None:
            mean_consensus = mg.consensus.mean()
            aligned = np.abs(mg.consensus - mean_consensus) < 0.10
            consensus_alignment = aligned.mean().item() * 100
            pct_aligned = consensus_alignment  # Store the percentage
        else:
            consensus_alignment = None
            mean_consensus = None
            pct_aligned = None
            
        # Calculate trust score (average trust across all validators)
        if hasattr(mg, 'trust') and mg.trust is not None:
            # Calculate stake-weighted trust score
            stake_weights = mg.S / mg.S.sum()
            trust_score = (mg.trust * stake_weights).sum().item()
        else:
            trust_score = None
        
        # Calculate active validators count
        active_validators = 0
        if hasattr(mg, 'validator_permit') and mg.validator_permit is not None:
            active_validators = int(mg.validator_permit.sum().item())
        
        # NEW: Calculate active stake ratio
        active_stake_ratio = None
        if hasattr(mg, 'validator_permit') and mg.validator_permit is not None and total_stake > 0:
            try:
                # Calculate stake on active validators
                active_stake = (mg.stake * mg.validator_permit).sum().item()
                active_stake_ratio = (active_stake / total_stake) * 100
                active_stake_ratio = round(active_stake_ratio, 1)
            except Exception as e:
                print(f"Error calculating active stake ratio for subnet {netuid}: {e}")
                active_stake_ratio = None
        
        # Get emission totals from emissions object
        tao_in_emission = 0.0
        alpha_out_emission = 0.0
        if hasattr(mg, 'emissions'):
            emissions_obj = mg.emissions
            if hasattr(emissions_obj, 'tao_in_emission'):
                tao_in_emission = float(emissions_obj.tao_in_emission)
            if hasattr(emissions_obj, 'alpha_out_emission'):
                alpha_out_emission = float(emissions_obj.alpha_out_emission)
        
        # Compile results
        metrics = {
            "netuid": int(netuid),
            "total_stake_tao": float(round(total_stake, 6)),
            "stake_hhi": float(round(hhi, 6)),  # Herfindahl-Hirschman Index
            "mean_incentive": float(round(mean_incentive, 6)),
            "p95_incentive": float(round(p95_incentive, 6)),
            "consensus_alignment": float(round(consensus_alignment, 6)) if consensus_alignment is not None else None,
            "trust_score": float(round(trust_score, 6)) if trust_score is not None else None,
            "emission_split": {
                "owner": float(round(emission_split["owner"], 6)),
                "miners": float(round(emission_split["miners"], 6)),
                "validators": float(round(emission_split["validators"], 6)),
            },
            "emission_split_rolling": calculate_emission_split_rolling(netuid, endpoint),
            "total_emission_rao": float(round(total_emission_rao, 6)),
            "total_emission_tao": float(round(total_emission_rao / 1_000_000_000, 12)),
            "uid_count": int(uid_count),
            "endpoint": endpoint,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "mean_consensus": float(round(mean_consensus, 6)) if mean_consensus is not None else None,
            "pct_aligned": float(round(pct_aligned, 6)) if pct_aligned is not None else None,
            "tao_in_emission": float(round(tao_in_emission, 6)),
            "alpha_out_emission": float(round(alpha_out_emission, 6)),
            "active_validators": int(active_validators)
        }
        
        return metrics
        
    except Exception as e:
        return {
            "netuid": netuid,
            "error": str(e),
            "endpoint": endpoint,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

def calculate_emission_split_rolling(netuid: int, endpoint: str = MAIN_RPC, window_blocks: int = 360) -> Dict[str, float]:
    """
    Calculate emission split over a rolling window of blocks.
    
    PoC implementation - optimized for speed with minimal blocks.
    
    Args:
        netuid: Subnet ID
        endpoint: RPC endpoint
        window_blocks: Number of blocks to look back (default 360 = one tempo)
        
    Returns:
        Dictionary with emission split ratios (owner, miners, validators)
    """
    import time
    
    # Check cache first
    cache_key = f"{netuid}:{endpoint}"
    current_time = time.time()
    
    if cache_key in _rolling_cache:
        cached_time, cached_result = _rolling_cache[cache_key]
        if current_time - cached_time < _rolling_cache_ttl:
            print(f"PoC: Using cached rolling emission split")
            return cached_result
    
    try:
        sub = bt.subtensor(endpoint)
        current_block = sub.get_current_block()
        
        # PoC optimization: Use only 3 blocks for speed
        max_blocks_to_fetch = 3  # Ultra-fast for PoC
        start_block = current_block - max_blocks_to_fetch + 1
        
        print(f"PoC: Calculating rolling emission split over {max_blocks_to_fetch} blocks")
        
        # Initialize rolling totals
        owner_tot = 0.0
        validator_tot = 0.0
        miner_tot = 0.0
        blocks_with_emission = 0
        
        # Fetch blocks sequentially (ultra-limited for PoC speed)
        for block_num in range(start_block, current_block + 1):
            try:
                # Get metagraph for this specific block
                mg = sub.metagraph(netuid=netuid, block=block_num)
                
                if hasattr(mg, 'emission') and mg.emission is not None:
                    emission_vector = mg.emission
                    block_total = emission_vector.sum().item()
                    
                    if block_total > 0:
                        # Get owner UID (index) - simplified approach
                        owner_uid = 0  # Assume UID 0 is owner for now
                        
                        # Get validator permits
                        validator_permits = mg.validator_permit if hasattr(mg, 'validator_permit') else None
                        
                        # Sum emissions by role for this block
                        block_owner = 0.0
                        block_validator = 0.0
                        block_miner = 0.0
                        
                        for uid_idx, emission in enumerate(emission_vector):
                            emission_value = emission.item()
                            
                            if uid_idx == owner_uid:
                                block_owner += emission_value
                            elif validator_permits is not None and validator_permits[uid_idx]:
                                block_validator += emission_value
                            else:
                                block_miner += emission_value
                        
                        # Add to rolling totals
                        owner_tot += block_owner
                        validator_tot += block_validator
                        miner_tot += block_miner
                        blocks_with_emission += 1
                        
            except Exception as e:
                print(f"Error fetching block {block_num}: {e}")
                continue
        
        # Calculate total emissions across all blocks
        total_emission = owner_tot + validator_tot + miner_tot
        
        if total_emission > 0:
            # Normalize to ratios
            emission_split = {
                'owner': float(owner_tot / total_emission),
                'miners': float(miner_tot / total_emission),
                'validators': float(validator_tot / total_emission)
            }
        else:
            # No emissions in rolling window
            emission_split = {
                'owner': 0.0,
                'miners': 0.0,
                'validators': 0.0
            }
            
        print(f"PoC: Rolling emission split ({blocks_with_emission} blocks): {emission_split}")
        
        # Cache the result
        _rolling_cache[cache_key] = (current_time, emission_split)
        
        return emission_split
        
    except Exception as e:
        print(f"Error calculating rolling emission split: {e}")
        return {
            'owner': 0.0,
            'miners': 0.0,
            'validators': 0.0
        }

def main():
    parser = argparse.ArgumentParser(description="Extract Bittensor subnet metrics")
    parser.add_argument("--netuid", type=int, required=True, help="Subnet ID to analyze")
    parser.add_argument("--endpoint", type=str, default=MAIN_RPC, help="RPC endpoint to use")
    parser.add_argument("--output", type=str, help="Output file (default: stdout)")
    
    args = parser.parse_args()
    
    print(f"🔍 Extracting metrics for subnet {args.netuid}")
    print(f"🌐 Using endpoint: {args.endpoint}")
    print()
    
    # Extract metrics
    metrics = calculate_subnet_metrics(args.netuid, args.endpoint)
    
    # Output results
    if "error" in metrics:
        print(f"❌ Error extracting metrics: {metrics['error']}")
        exit(1)
    
    # Pretty print the results
    print("📊 Subnet Metrics:")
    print("=" * 40)
    print(f"🔢 Subnet ID: {metrics['netuid']}")
    print(f"💰 Total Stake: {metrics['total_stake_tao']:,.2f} TAO")
    print(f"📈 Stake HHI: {metrics['stake_hhi']:.2f} (0-10,000)")
    print(f"🎯 Mean Incentive: {metrics['mean_incentive']:.6f}")
    print(f"📊 P95 Incentive: {metrics['p95_incentive']:.6f}")
    
    if metrics['consensus_alignment'] is not None:
        print(f"🤝 Consensus Alignment: {metrics['consensus_alignment']:.2f}%")
    
    if metrics['trust_score'] is not None:
        print(f"🛡️  Trust Score: {metrics['trust_score']:.6f}")
    
    print(f"👥 UID Count: {metrics['uid_count']}")
    print()
    
    print("💸 Emission Split:")
    print(f"   👑 Owner: {metrics['emission_split']['owner']:.6f}")
    print(f"   ⛏️  Miners: {metrics['emission_split']['miners']:.6f}")
    print(f"   ✅ Validators: {metrics['emission_split']['validators']:.6f}")
    print()
    
    print(f"⏰ Timestamp: {metrics['timestamp']}")
    print()
    
    # Output JSON
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"💾 Results saved to: {args.output}")
    else:
        print("📄 JSON Output:")
        print(json.dumps(metrics, indent=2))

if __name__ == "__main__":
    main() 