#!/usr/bin/env python
"""
Async SDK Metrics Collector for TAO Analytics.
Provides fast concurrent collection of subnet metrics for nightly snapshots.
"""

import asyncio
import aiohttp
import bittensor as bt
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional
import random
from concurrent.futures import ThreadPoolExecutor
import logging
import time

from .endpoints import MAIN_RPC, RPC_POOL

logger = logging.getLogger(__name__)

# RPC endpoint rotation for load balancing
RPC_ENDPOINTS = [MAIN_RPC] + RPC_POOL

def get_random_rpc() -> str:
    """Get a random RPC endpoint to avoid thundering herd."""
    return random.choice(RPC_ENDPOINTS)

def get_endpoint_priority() -> List[str]:
    """Get RPC endpoints in priority order (most reliable first)."""
    # Prioritize main endpoint and known reliable endpoints
    priority_endpoints = [
        MAIN_RPC,  # Main production endpoint
        "wss://finney.opentensor.ai:443",  # Alt DNS for main
        "wss://bittensor-api.dwellir.com:443",  # Dwellir public
        "wss://bittensor.publicnode.com:443",  # PublicNode
    ]
    return priority_endpoints

async def calculate_subnet_metrics_async(netuid: int, endpoint: Optional[str] = None, max_retries: int = 3, lite_mode: bool = False) -> Dict[str, Any]:
    """
    Calculate subnet metrics asynchronously with retry logic.
    
    Args:
        netuid: Subnet ID to analyze
        endpoint: RPC endpoint to use (random if None)
        max_retries: Maximum retry attempts
        lite_mode: Use lite metagraphs for faster collection
        
    Returns:
        Dictionary with subnet metrics
    """
    if endpoint is None:
        endpoint = get_random_rpc()
    
    # Try multiple endpoints if the first one fails
    endpoints_to_try = [endpoint] + [ep for ep in get_endpoint_priority() if ep != endpoint]
    
    for attempt in range(max_retries):
        for try_endpoint in endpoints_to_try:
            try:
                # Use ThreadPoolExecutor for bittensor calls (they're blocking)
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    metrics = await loop.run_in_executor(
                        executor, 
                        calculate_subnet_metrics_sync, 
                        netuid, 
                        try_endpoint,
                        lite_mode
                    )
                
                # Check if we got valid metrics (not just an error response)
                if "error" not in metrics or not metrics["error"]:
                    return metrics
                    
            except Exception as e:
                logger.debug(f"Attempt {attempt + 1} failed for subnet {netuid} with endpoint {try_endpoint}: {e}")
                continue
        
        # If all endpoints failed, wait before retry
        if attempt < max_retries - 1:
            await asyncio.sleep(1 + attempt * 2)  # Exponential backoff
    
    # All attempts failed
    logger.warning(f"All attempts failed for subnet {netuid}")
    return {
        "netuid": netuid,
        "error": "All endpoints failed after retries",
        "endpoint": endpoint,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

def calculate_subnet_metrics_sync(netuid: int, endpoint: str, lite_mode: bool = False) -> Dict[str, Any]:
    """
    Synchronous version of subnet metrics calculation with improved error handling.
    This is the same as the original function but optimized for async calls.
    
    Args:
        netuid: Subnet ID to analyze
        endpoint: RPC endpoint to use
        lite_mode: Use lite metagraphs for faster collection
    """
    try:
        # Connect to Bittensor network with timeout
        sub = bt.subtensor(endpoint)
        
        # Get metagraph for the subnet (lite mode for faster collection)
        mg = sub.metagraph(netuid=netuid, lite=lite_mode)
        
        # Validate metagraph data
        if mg is None or len(mg.uids) == 0:
            return {
                "netuid": netuid,
                "error": "Empty or invalid metagraph",
                "endpoint": endpoint,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        
        # Calculate metrics using exact formulas from design doc
        total_stake = mg.stake.sum().item()
        
        # Handle division by zero for HHI calculation
        if total_stake > 0:
            hhi = ((mg.stake / total_stake) ** 2).sum() * 10_000  # 0–10 000
        else:
            hhi = 0.0
            
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
            logger.warning(f"Error calculating emission split for subnet {netuid}: {e}")
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
            trust_score = mg.trust.mean().item()
        else:
            trust_score = None
        
        # Calculate active validators count
        active_validators = 0
        if hasattr(mg, 'validator_permit') and mg.validator_permit is not None:
            active_validators = int(mg.validator_permit.sum().item())
        
        # NEW: Sprint 5 computed metrics
        # Stake Quality: HHI-adjusted score (0-100)
        stake_quality = max(0, 100 - (hhi / 100)) if hhi is not None else None
        
        # Reserve Momentum: Δ TAO-in 24h / supply (placeholder - needs historical data)
        reserve_momentum = None  # TODO: Calculate from historical emission data
        
        # Emission ROI: Will be calculated from daily emission diff in cron_fetch.py
        emission_roi = None  # Calculated from daily_emission_tao / total_stake_tao in main collection
        
        # Validators Active: Same as active_validators but renamed for clarity
        validators_active = active_validators
        
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
            "total_emission_rao": float(round(total_emission_rao, 6)),
            "total_emission_tao": float(round(total_emission_rao / 1_000_000_000, 12)),
            "uid_count": int(uid_count),
            "endpoint": endpoint,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "mean_consensus": float(round(mean_consensus, 6)) if mean_consensus is not None else None,
            "pct_aligned": float(round(pct_aligned, 6)) if pct_aligned is not None else None,
            "tao_in_emission": float(round(tao_in_emission, 6)),
            "alpha_out_emission": float(round(alpha_out_emission, 6)),
            "active_validators": int(active_validators),
            "stake_quality": float(round(stake_quality, 6)) if stake_quality is not None else None,
            "reserve_momentum": float(round(reserve_momentum, 6)) if reserve_momentum is not None else None,
            "emission_roi": float(round(emission_roi, 6)) if emission_roi is not None else None,
            "validators_active": int(validators_active)
        }
        
        return metrics
        
    except Exception as e:
        return {
            "netuid": netuid,
            "error": str(e),
            "endpoint": endpoint,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

async def collect_all_subnet_metrics_async(subnet_ids: List[int], max_workers: int = 4, lite_mode: bool = False) -> List[Dict[str, Any]]:
    """
    Collect metrics for all subnets concurrently with improved reliability.
    
    Args:
        subnet_ids: List of subnet IDs to collect
        max_workers: Maximum concurrent workers
        lite_mode: Use lite metagraphs for faster collection (skips consensus/trust)
        
    Returns:
        List of metrics dictionaries
    """
    logger.info(f"Starting async collection for {len(subnet_ids)} subnets with {max_workers} workers")
    
    # Create semaphore to limit concurrent connections
    semaphore = asyncio.Semaphore(max_workers)
    
    async def collect_with_semaphore(netuid: int) -> Dict[str, Any]:
        async with semaphore:
            return await calculate_subnet_metrics_async(netuid, max_retries=2, lite_mode=lite_mode)
    
    # Create tasks for all subnets
    tasks = [collect_with_semaphore(netuid) for netuid in subnet_ids]
    
    # Execute all tasks concurrently with progress tracking
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out exceptions and log them
    valid_results = []
    failed_count = 0
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Exception for subnet {subnet_ids[i]}: {result}")
            failed_count += 1
        else:
            valid_results.append(result)
        
        # Log progress every 10 subnets or at the end
        if (i + 1) % 10 == 0 or (i + 1) == len(subnet_ids):
            progress = (i + 1) / len(subnet_ids) * 100
            success_rate = (len(valid_results) / (i + 1)) * 100
            logger.info(f"Progress: {i + 1}/{len(subnet_ids)} subnets ({progress:.1f}%) - {success_rate:.1f}% success")
    
    success_rate = (len(valid_results) / len(subnet_ids)) * 100
    logger.info(f"Completed async collection: {len(valid_results)}/{len(subnet_ids)} successful ({success_rate:.1f}%)")
    
    if success_rate < 50:
        logger.warning(f"Low success rate ({success_rate:.1f}%). Consider reducing concurrency or checking network connectivity.")
    
    return valid_results

def collect_all_subnet_metrics_sync(subnet_ids: List[int]) -> List[Dict[str, Any]]:
    """
    Synchronous fallback for collecting all subnet metrics.
    Use this when async is not available or for testing.
    """
    logger.info(f"Starting sync collection for {len(subnet_ids)} subnets")
    
    results = []
    successful = 0
    
    for i, netuid in enumerate(subnet_ids):
        try:
            # Try multiple endpoints for each subnet
            for endpoint in get_endpoint_priority():
                try:
                    metrics = calculate_subnet_metrics_sync(netuid, endpoint)
                    if "error" not in metrics or not metrics["error"]:
                        results.append(metrics)
                        successful += 1
                        break
                    else:
                        continue
                except Exception as e:
                    continue
            else:
                # All endpoints failed for this subnet
                results.append({
                    "netuid": netuid,
                    "error": "All endpoints failed",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
            
            # Log progress every 10 subnets
            if (i + 1) % 10 == 0:
                success_rate = (successful / (i + 1)) * 100
                logger.info(f"Processed {i + 1}/{len(subnet_ids)} subnets... ({success_rate:.1f}% success)")
                
        except Exception as e:
            logger.error(f"Error processing subnet {netuid}: {e}")
            results.append({
                "netuid": netuid,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
    
    final_success_rate = (successful / len(subnet_ids)) * 100
    logger.info(f"Completed sync collection: {successful}/{len(subnet_ids)} successful ({final_success_rate:.1f}%)")
    return results 