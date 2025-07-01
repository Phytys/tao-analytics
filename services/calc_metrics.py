"""
Calculation service for investor-focused metrics.
Implements the exact formulas specified in the feedback.
"""

import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, Union

logger = logging.getLogger(__name__)

def calculate_stake_quality(stake_hhi: Optional[float]) -> Optional[float]:
    """
    Calculate stake quality using the exact formula from feedback.
    
    Formula: normalized_hhi = stake_hhi / 10000, stake_quality = round(max(0, 100 - normalized_hhi*100), 1)
    
    Args:
        stake_hhi: Herfindahl-Hirschman Index (0-10,000)
        
    Returns:
        Stake quality score (0-100)
    """
    if stake_hhi is None:
        return None
    
    normalized_hhi = stake_hhi / 10000  # 0-1
    stake_quality = max(0, 100 - normalized_hhi * 100)
    return round(stake_quality, 1)

def calculate_daily_emission_tao(tao_prev: float, tao_now: float) -> Optional[float]:
    """
    Calculate daily TAO emission using the efficient diff method.
    
    Formula: daily_emission_tao = (tao_now - tao_prev) / 1e9
    
    Args:
        tao_prev: Emission since block (head-359)
        tao_now: Emission since block (head)
        
    Returns:
        Daily TAO emission
    """
    if tao_prev is None or tao_now is None:
        return None
    
    delta = tao_now - tao_prev
    daily_emission_tao = delta / 1e9  # RAO → TAO
    return daily_emission_tao

def calculate_emission_roi(daily_emission_tao: Optional[float], total_stake_tao: Optional[float]) -> Optional[float]:
    """
    Calculate emission ROI.
    
    Formula: emission_roi = daily_emission_tao / total_stake_tao
    
    Args:
        daily_emission_tao: Daily TAO emission
        total_stake_tao: Total stake in TAO
        
    Returns:
        Emission ROI
    """
    if daily_emission_tao is None or total_stake_tao is None or total_stake_tao <= 0:
        return None
    
    return daily_emission_tao / total_stake_tao

def calculate_reserve_momentum(tao_in_today: float, tao_in_yesterday: float, market_cap_tao: float) -> float:
    """
    Calculate reserve momentum.
    
    Formula: tao_in_change = today.tao_in - yesterday.tao_in
             reserve_momentum = tao_in_change / market_cap_tao
    
    Args:
        tao_in_today: TAO-in reserves today
        tao_in_yesterday: TAO-in reserves yesterday
        market_cap_tao: Market cap in TAO
        
    Returns:
        Reserve momentum
    """
    if tao_in_today is None or tao_in_yesterday is None or market_cap_tao is None or market_cap_tao <= 0:
        return None
    
    tao_in_change = tao_in_today - tao_in_yesterday
    return tao_in_change / market_cap_tao

def calculate_consensus_alignment(consensus: np.ndarray, stakes: np.ndarray) -> float:
    """
    Calculate consensus alignment using stake-weighted ±2σ rule.
    
    Formula: mean = np.average(mg.consensus, weights=mg.S)
             sigma = np.sqrt(np.average((mg.consensus-mean)**2, weights=mg.S))
             aligned = np.abs(mg.consensus-mean) < 2*sigma
             consensus_alignment = np.average(aligned, weights=mg.S) * 100
    
    Args:
        consensus: Consensus values array
        stakes: Stake weights array
        
    Returns:
        Consensus alignment percentage (0-100)
    """
    if consensus is None or stakes is None or len(consensus) == 0 or len(stakes) == 0:
        return None
    
    try:
        # Convert to numpy arrays if needed
        consensus = np.array(consensus)
        stakes = np.array(stakes)
        
        # Calculate stake-weighted mean
        mean = np.average(consensus, weights=stakes)
        
        # Calculate stake-weighted standard deviation
        variance = np.average((consensus - mean) ** 2, weights=stakes)
        sigma = np.sqrt(variance)
        
        # Find UIDs within ±2σ
        aligned = np.abs(consensus - mean) < 2 * sigma
        
        # Calculate stake-weighted percentage
        consensus_alignment = np.average(aligned, weights=stakes) * 100
        
        return float(consensus_alignment)
        
    except Exception as e:
        logger.error(f"Error calculating consensus alignment: {e}")
        return None

def calculate_trust_score(trust: np.ndarray, stakes: np.ndarray) -> float:
    """
    Calculate stake-weighted trust score.
    
    Formula: trust_score = np.average(mg.trust, weights=mg.S)
    
    Args:
        trust: Trust values array
        stakes: Stake weights array
        
    Returns:
        Trust score
    """
    if trust is None or stakes is None or len(trust) == 0 or len(stakes) == 0:
        return None
    
    try:
        # Convert to numpy arrays if needed
        trust = np.array(trust)
        stakes = np.array(stakes)
        
        # Calculate stake-weighted mean
        trust_score = np.average(trust, weights=stakes)
        
        return float(trust_score)
        
    except Exception as e:
        logger.error(f"Error calculating trust score: {e}")
        return None

def calculate_stake_hhi(stakes: np.ndarray) -> float:
    """
    Calculate Herfindahl-Hirschman Index for stake concentration.
    
    Formula: ((S / S.sum())**2).sum()*10_000
    
    Args:
        stakes: Stake values array
        
    Returns:
        HHI (0-10,000)
    """
    if stakes is None or len(stakes) == 0:
        return None
    
    try:
        # Convert to numpy array if needed
        stakes = np.array(stakes)
        
        # Calculate total stake
        total_stake = stakes.sum()
        
        if total_stake <= 0:
            return None
        
        # Calculate market shares
        market_shares = stakes / total_stake
        
        # Calculate HHI
        hhi = (market_shares ** 2).sum() * 10000
        
        return float(hhi)
        
    except Exception as e:
        logger.error(f"Error calculating stake HHI: {e}")
        return None

def calculate_rank_percentage(value: float, category_values: list) -> Optional[int]:
    """
    Calculate rank percentage within a category.
    
    Formula: rank_pct = round((position / total_count) * 100)
    
    Args:
        value: The value to rank
        category_values: List of all values in the category
        
    Returns:
        Rank percentage (0-100), where 0 = bottom, 100 = top
    """
    if value is None or category_values is None or len(category_values) == 0:
        return None
    
    try:
        # Filter out None values
        valid_values = [v for v in category_values if v is not None]
        
        if len(valid_values) == 0:
            return None
        
        # Sort values (ascending for stake_quality, descending for momentum)
        sorted_values = sorted(valid_values)
        
        # Find position (0-indexed)
        position = sorted_values.index(value)
        
        # Calculate percentage
        rank_pct = round((position / len(sorted_values)) * 100)
        
        return rank_pct
        
    except Exception as e:
        logger.error(f"Error calculating rank percentage: {e}")
        return None

def calculate_validator_utilization(active_validators: int, total_possible: int = 256) -> Optional[int]:
    """
    Calculate validator utilization percentage.
    
    Formula: util_pct = round((active_validators / total_possible) * 100)
    
    Args:
        active_validators: Number of active validators
        total_possible: Total possible validators (default 256)
        
    Returns:
        Utilization percentage (0-100)
    """
    if active_validators is None or active_validators < 0:
        return None
    
    try:
        util_pct = round((active_validators / total_possible) * 100)
        return min(util_pct, 100)  # Cap at 100%
        
    except Exception as e:
        logger.error(f"Error calculating validator utilization: {e}")
        return None

def calculate_buy_sell_ratio(buy_volume: float, sell_volume: float) -> Optional[float]:
    """
    Calculate buy/sell volume ratio.
    
    Formula: ratio = buy_volume / max(1, sell_volume)
    
    Args:
        buy_volume: Buy volume in TAO
        sell_volume: Sell volume in TAO
        
    Returns:
        Buy/sell ratio (rounded to 2 decimal places)
    """
    if buy_volume is None or sell_volume is None:
        return None
    
    try:
        # Avoid division by zero
        denominator = max(1, sell_volume)
        ratio = buy_volume / denominator
        
        return round(ratio, 2)
        
    except Exception as e:
        logger.error(f"Error calculating buy/sell ratio: {e}")
        return None

def validate_metrics(metrics: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate metrics using the exact validation rules from feedback.
    
    Args:
        metrics: Dictionary of metrics to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Price validation
        if metrics.get('price_tao') is not None:
            if not (0 < metrics['price_tao'] < 10):
                return False, f"price outlier: {metrics['price_tao']}"
        
        # Stake quality validation
        if metrics.get('stake_quality') is not None:
            if not (0 < metrics['stake_quality'] <= 100):
                return False, f"stake_quality out of range: {metrics['stake_quality']}"
        
        # Emission ROI validation
        if metrics.get('emission_roi') is not None:
            if metrics['emission_roi'] < 0:
                return False, f"emission_roi cannot be negative: {metrics['emission_roi']}"
        
        # Consensus alignment validation
        if metrics.get('consensus_alignment') is not None:
            if not (0 <= metrics['consensus_alignment'] <= 100):
                return False, f"consensus_alignment out of range: {metrics['consensus_alignment']}"
        
        return True, "All validations passed"
        
    except Exception as e:
        return False, f"Validation error: {e}"

def calculate_all_metrics(
    # Market data from screener
    price_tao: float = None,
    market_cap_tao: float = None,
    fdv_tao: float = None,
    buy_vol_tao_1d: float = None,
    sell_vol_tao_1d: float = None,
    tao_in: float = None,
    tao_in_yesterday: float = None,
    
    # Additional screener fields
    total_volume_tao_1d: float = None,
    net_volume_tao_1h: float = None,
    net_volume_tao_24h: float = None,
    net_volume_tao_7d: float = None,
    price_1h_change: float = None,
    price_1d_change: float = None,
    price_7d_change: float = None,
    price_30d_change: float = None,
    buy_volume_pct_change: float = None,
    sell_volume_pct_change: float = None,
    total_volume_pct_change: float = None,
    alpha_in: float = None,
    alpha_out: float = None,
    alpha_circ: float = None,
    alpha_prop: float = None,
    root_prop: float = None,
    emission_pct: float = None,
    alpha_emitted_pct: float = None,
    realized_pnl_tao: float = None,
    unrealized_pnl_tao: float = None,
    ath_60d: float = None,
    atl_60d: float = None,
    gini_coeff_top_100: float = None,
    hhi: float = None,
    symbol: str = None,
    github_repo: str = None,
    subnet_contact: str = None,
    subnet_url: str = None,
    subnet_website: str = None,
    discord: str = None,
    additional: str = None,
    owner_coldkey: str = None,
    owner_hotkey: str = None,
    
    # SDK data
    stakes: np.ndarray = None,
    consensus: np.ndarray = None,
    trust: np.ndarray = None,
    validator_permit: np.ndarray = None,
    daily_emission_tao: float = None,
    total_stake_tao: float = None,
    
    # Additional data
    uid_count: int = None
) -> Dict[str, Any]:
    """
    Calculate all investor-focused metrics using the exact formulas.
    
    Returns:
        Dictionary with all calculated metrics
    """
    results = {}
    
    # Calculate stake metrics
    if stakes is not None:
        results['stake_hhi'] = calculate_stake_hhi(stakes)
        results['stake_quality'] = calculate_stake_quality(results['stake_hhi'])
    
    # Calculate emission metrics
    if daily_emission_tao is not None and total_stake_tao is not None:
        results['emission_roi'] = calculate_emission_roi(daily_emission_tao, total_stake_tao)
    
    # Calculate reserve momentum
    if tao_in is not None and tao_in_yesterday is not None and market_cap_tao is not None:
        results['reserve_momentum'] = calculate_reserve_momentum(tao_in, tao_in_yesterday, market_cap_tao)
    
    # Calculate consensus alignment
    if consensus is not None and stakes is not None:
        results['consensus_alignment'] = calculate_consensus_alignment(consensus, stakes)
    
    # Calculate trust score
    if trust is not None and stakes is not None:
        results['trust_score'] = calculate_trust_score(trust, stakes)
    
    # Calculate active validators
    if validator_permit is not None:
        results['validators_active'] = int(validator_permit.sum()) if hasattr(validator_permit, 'sum') else len([v for v in validator_permit if v])
    
    # Store raw values
    results.update({
        'price_tao': price_tao,
        'market_cap_tao': market_cap_tao,
        'fdv_tao': fdv_tao,
        'buy_vol_tao_1d': buy_vol_tao_1d,
        'sell_vol_tao_1d': sell_vol_tao_1d,
        'tao_in': tao_in,
        'total_stake_tao': total_stake_tao,
        'daily_emission_tao': daily_emission_tao,
        'uid_count': uid_count,
        
        # Additional screener fields
        'total_volume_tao_1d': total_volume_tao_1d,
        'net_volume_tao_1h': net_volume_tao_1h,
        'net_volume_tao_24h': net_volume_tao_24h,
        'net_volume_tao_7d': net_volume_tao_7d,
        'price_1h_change': price_1h_change,
        'price_1d_change': price_1d_change,
        'price_7d_change': price_7d_change,
        'price_30d_change': price_30d_change,
        'buy_volume_pct_change': buy_volume_pct_change,
        'sell_volume_pct_change': sell_volume_pct_change,
        'total_volume_pct_change': total_volume_pct_change,
        'alpha_in': alpha_in,
        'alpha_out': alpha_out,
        'alpha_circ': alpha_circ,
        'alpha_prop': alpha_prop,
        'root_prop': root_prop,
        'emission_pct': emission_pct,
        'alpha_emitted_pct': alpha_emitted_pct,
        'realized_pnl_tao': realized_pnl_tao,
        'unrealized_pnl_tao': unrealized_pnl_tao,
        'ath_60d': ath_60d,
        'atl_60d': atl_60d,
        'gini_coeff_top_100': gini_coeff_top_100,
        'hhi': hhi,
        'symbol': symbol,
        'github_repo': github_repo,
        'subnet_contact': subnet_contact,
        'subnet_url': subnet_url,
        'subnet_website': subnet_website,
        'discord': discord,
        'additional': additional,
        'owner_coldkey': owner_coldkey,
        'owner_hotkey': owner_hotkey
    })
    
    return results 