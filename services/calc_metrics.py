"""
Calculation service for investor-focused metrics.
Implements the exact formulas specified in the feedback.
"""

import numpy as np
import logging
import os
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

def calculate_consensus_alignment(consensus: np.ndarray, stakes: np.ndarray) -> Optional[float]:
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

def calculate_trust_score(trust: np.ndarray, stakes: np.ndarray) -> Optional[float]:
    """
    Calculate stake-weighted trust score.
    
    Formula: weights = stakes / stakes.sum()
             trust_score = (trust * weights).sum()
    
    Args:
        trust: Trust values array
        stakes: Stake weights array
        
    Returns:
        Stake-weighted trust score (0-1)
    """
    if trust is None or stakes is None or len(trust) == 0 or len(stakes) == 0:
        return None
    
    try:
        # Convert to numpy arrays if needed
        trust = np.array(trust)
        stakes = np.array(stakes)
        
        # Calculate total stake
        total_stake = stakes.sum()
        
        if total_stake <= 0:
            return None
        
        # Calculate stake weights
        weights = stakes / total_stake
        
        # Calculate stake-weighted trust score
        trust_score = (trust * weights).sum()
        
        return float(trust_score)
        
    except Exception as e:
        logger.error(f"Error calculating trust score: {e}")
        return None

def calculate_tao_score(
    stake_quality: Optional[float],
    consensus_alignment: Optional[float], 
    active_stake_ratio: Optional[float],
    emission_roi: Optional[float],
    reserve_momentum: Optional[float],
    validator_util_pct: Optional[float],
    inflation_pct: Optional[float] = None,
    price_7d_change: Optional[float] = None,
    session = None
) -> Optional[float]:
    """
    Calculate TAO-Score v1.1 using updated weights and scaling.
    
    Core metrics (required): stake_quality, consensus_alignment, active_stake_ratio
    Optional metrics: validator_util_pct, inflation_pct, price_7d_change
    
    Args:
        stake_quality: Stake quality score (0-100)
        consensus_alignment: Consensus alignment percentage (0-100)
        active_stake_ratio: Active stake ratio percentage (0-100)
        emission_roi: Emission ROI (deprecated, kept for backward compatibility)
        reserve_momentum: Reserve momentum (deprecated, replaced with price_7d_change)
        validator_util_pct: Validator utilization percentage (0-100)
        inflation_pct: Annual inflation percentage
        price_7d_change: 7-day price change percentage
        session: Database session for momentum z-score calculation
        
    Returns:
        TAO-Score (0-100) or None if core metrics are missing
    """
    # Core metrics are required
    if any(metric is None for metric in [stake_quality, consensus_alignment, active_stake_ratio]):
        return None
    
    try:
        # Pre-scale all inputs to 0-100 range
        sq = max(0, min(100, stake_quality or 0))  # Stake quality (0-100)
        cons = max(0, min(100, consensus_alignment or 0))  # Consensus alignment (0-100)
        active_stake = max(0, min(100, active_stake_ratio or 0))  # Active stake ratio (0-100)
        
        # Optional metrics with scaling
        util = max(0, min(100, validator_util_pct or 0)) if validator_util_pct is not None else None
        
        # Inflation sanity check (penalize deviation from 8% target)
        target_inflation = float(os.getenv('TAO_INF_TARGET', '8'))
        infl = None
        if inflation_pct is not None:
            infl = max(0, 100 - abs((inflation_pct or 0) - target_inflation) * 4)
        
        # Momentum scaling: z-score of 7-day price change clipped to ±2 → 0-100
        mom = None
        if price_7d_change is not None:
            # Simple z-score approximation: assume normal distribution with ±20% range
            # Clip to ±2 standard deviations, then scale to 0-100
            z_score = max(-2, min(2, price_7d_change / 10))  # Assume 10% = 1 std dev
            mom = max(0, min(100, (z_score + 2) * 25))  # Scale -2 to +2 → 0 to 100
        
        # Updated base weights per v1.1 spec
        base_w = {
            'sq': 0.35, 'util': 0.20, 'cons': 0.15,
            'active_stake': 0.15, 'infl': 0.10, 'mom': 0.05
        }
        
        # Check which optional metrics are missing
        missing = []
        if util is None:
            missing.append('util')
        if infl is None:
            missing.append('infl')
        if mom is None:
            missing.append('mom')
        
        # Redistribute missing weights ONLY to core metrics (sq, cons, active_stake)
        if missing:
            redist = sum(base_w[m] for m in missing)
            core_metrics = ['sq', 'cons', 'active_stake']
            core_weight_sum = sum(base_w[c] for c in core_metrics)
            
            # Zero out missing weights
            for m in missing:
                base_w[m] = 0
            
            # Redistribute to core metrics proportionally
            for c in core_metrics:
                base_w[c] += redist * (base_w[c] / core_weight_sum)
        
        # Calculate final score
        tao_score = (
            sq * base_w['sq'] +
            (util if util is not None else 0) * base_w['util'] +
            cons * base_w['cons'] +
            active_stake * base_w['active_stake'] +
            (infl if infl is not None else 0) * base_w['infl'] +
            (mom if mom is not None else 0) * base_w['mom']
        )
        
        # Apply hard caps and round
        tao_score = max(0, min(tao_score, 100))
        return round(tao_score, 1)
        
    except Exception as e:
        logger.error(f"Error calculating TAO-Score: {e}")
        return None

def calculate_stake_hhi(stakes: np.ndarray) -> Optional[float]:
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

def calculate_active_stake_ratio(stakes: np.ndarray, validator_permit: np.ndarray) -> Optional[float]:
    """
    Calculate active stake ratio.
    
    Formula: (stake on permitted validators / total stake) * 100
    
    Args:
        stakes: Array of stake amounts
        validator_permit: Array of validator permit flags (True/False)
        
    Returns:
        Active stake ratio as percentage (0-100)
    """
    if stakes is None or validator_permit is None:
        return None
    
    try:
        total_stake = stakes.sum()
        if total_stake == 0:
            return 0.0
        
        active_stake = stakes[validator_permit].sum()
        ratio = (active_stake / total_stake) * 100
        
        return round(ratio, 1)
        
    except Exception as e:
        logger.error(f"Error calculating active stake ratio: {e}")
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
    
    # Calculate active stake ratio
    if stakes is not None and validator_permit is not None:
        results['active_stake_ratio'] = calculate_active_stake_ratio(stakes, validator_permit)
    
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

def calculate_tao_score_v21(
    # Core metrics
    stake_quality: Optional[float],
    active_validators: Optional[int],
    stake_hhi: Optional[float],
    market_cap_tao: Optional[float],
    emission_pct: Optional[float],
    flow_24h: Optional[float],
    root_prop: Optional[float],
    price_30d_change: Optional[float],
    total_volume_tao_1d: Optional[float],
    
    # Additional dependencies for calculated metrics
    fdv_tao: Optional[float] = None,
    total_emission_tao: Optional[float] = None,
    alpha_circ: Optional[float] = None,
    price_tao: Optional[float] = None,
    
    # Historical data for delta calculations
    root_prop_prev: Optional[float] = None,
    
    # Scaling parameters
    session = None
) -> Optional[float]:
    """
    Calculate TAO-Score v2.1 using expert-recommended factor investing approach.
    
    Expert-recommended formula with forward-looking, risk-aware metrics:
    - Network Health (35%): stake_quality, active_validators, stake_hhi
    - Economic Health (40%): market_cap_tao, emission_efficiency, flow_velocity, root_prop_delta
    - Market Performance (25%): sharpe_30d, total_volume_tao_1d
    
    Args:
        stake_quality: Stake quality score (0-100)
        active_validators: Number of active validators
        stake_hhi: Herfindahl-Hirschman Index for stake concentration
        market_cap_tao: Market capitalization in TAO
        emission_pct: Emission percentage
        flow_24h: 24-hour net volume flow
        root_prop: Root proportion of total tokens
        price_30d_change: 30-day price change percentage
        total_volume_tao_1d: 24-hour total volume in TAO
        fdv_tao: Fully diluted valuation in TAO
        total_emission_tao: Total daily emission in TAO
        alpha_circ: Circulating Alpha tokens
        price_tao: Current price in TAO
        root_prop_prev: Previous root proportion for delta calculation
        
    Returns:
        TAO-Score v2.1 (0-100) or None if core metrics are missing
    """
    try:
        # Core metrics are required
        if any(metric is None for metric in [stake_quality, active_validators, stake_hhi, market_cap_tao]):
            return None
        
        # Calculate expert-recommended derived metrics
        
        # 1. Emission Efficiency: TAO/Alpha emitted per $1 FDV (inverted for scoring)
        emission_efficiency = None
        if emission_pct is not None and fdv_tao is not None and fdv_tao > 0:
            # Lower emission efficiency = better (stronger token sink)
            emission_efficiency = emission_pct / fdv_tao if emission_pct > 0 else 0
        
        # 2. Flow Velocity: (24h Flow / Circulating Alpha)
        flow_velocity = None
        if flow_24h is not None and alpha_circ is not None and alpha_circ > 0:
            # Higher flow velocity = better (more real user demand)
            flow_velocity = abs(flow_24h) / alpha_circ
        
        # 3. Root Prop Delta: Month-over-month change in root proportion
        root_prop_delta = None
        if root_prop is not None and root_prop_prev is not None:
            # Lower root prop delta = better (less concentration)
            root_prop_delta = root_prop - root_prop_prev
        
        # 4. Sharpe-adjusted 30d Return: Risk-adjusted return
        sharpe_30d = None
        if price_30d_change is not None and price_tao is not None:
            # Simple Sharpe approximation: return / volatility proxy
            # For now, use price_30d_change as proxy (can be enhanced with actual volatility)
            sharpe_30d = price_30d_change / 100  # Normalize to reasonable range
        
        # Apply expert-recommended scaling and normalization
        
        # Heavy-tailed metrics: log(1 + x) transformation
        def log_transform(x):
            if x is None or x <= 0:
                return 0
            return np.log(1 + abs(x))
        
        # Z-score normalization (simplified for now)
        def z_score(x, mean=0, std=1):
            if x is None:
                return 0
            return (x - mean) / std if std > 0 else 0
        
        # Apply gentler transformations for better scaling
        sq = max(0, min(100, stake_quality or 0))  # Already 0-100
        av = max(0, min(100, (active_validators or 0) / 256 * 100))  # Scale 0-256 to 0-100
        
        # Gentler transformations for heavy-tailed metrics
        def sqrt_transform(x):
            if x is None or x <= 0:
                return 0
            return np.sqrt(abs(x))
        
        # Normalized z-scores with reasonable ranges
        def normalized_z_score(x, mean=0, std=1, min_val=-3, max_val=3):
            if x is None:
                return 0
            z = (x - mean) / std if std > 0 else 0
            # Clip to reasonable range and scale to 0-100
            z_clipped = max(min_val, min(max_val, z))
            return (z_clipped - min_val) / (max_val - min_val) * 100
        
        # Apply improved transformations
        hhi = normalized_z_score(stake_hhi or 0, mean=5000, std=2000)  # HHI to 0-100
        mcap = sqrt_transform(market_cap_tao or 0)  # Square root for heavy-tailed data
        eff = sqrt_transform(emission_efficiency or 0)  # Square root for efficiency
        fvel = sqrt_transform(flow_velocity or 0)  # Square root for velocity
        rpd = normalized_z_score(root_prop_delta or 0, mean=0, std=0.1)  # Delta to 0-100
        sharpe = normalized_z_score(sharpe_30d or 0, mean=0, std=0.2)  # Sharpe to 0-100
        vol = sqrt_transform(total_volume_tao_1d or 0)  # Square root for volume
        
        # Normalize market cap, efficiency, velocity, and volume to 0-100 range
        # Use reasonable maximums based on typical values
        mcap_norm = min(100, (mcap / 1000) * 100) if mcap > 0 else 0  # Scale by 1000 TAO
        eff_norm = min(100, (eff / 0.1) * 100) if eff > 0 else 0  # Scale by 0.1 efficiency
        fvel_norm = min(100, (fvel / 0.5) * 100) if fvel > 0 else 0  # Scale by 0.5 velocity
        vol_norm = min(100, (vol / 10000) * 100) if vol > 0 else 0  # Scale by 10k TAO volume
        
        # Expert-recommended v2.1 weights
        weights = {
            'sq': 0.18,      # stake_quality
            'av': 0.10,      # active_validators
            'hhi': 0.07,     # stake_hhi (inverted)
            'mcap': 0.15,    # market_cap_tao
            'eff': 0.10,     # emission_efficiency (inverted)
            'fvel': 0.08,    # flow_velocity
            'rpd': 0.07,     # root_prop_delta (inverted)
            'sharpe': 0.15,  # sharpe_30d
            'vol': 0.10      # total_volume_tao_1d
        }
        
        # Calculate weighted score with proper scaling
        tao_score_v21 = (
            sq * weights['sq'] +
            av * weights['av'] +
            (100 - hhi) * weights['hhi'] +  # Invert: lower HHI = better
            mcap_norm * weights['mcap'] +
            (100 - eff_norm) * weights['eff'] +  # Invert: lower emission efficiency = better
            fvel_norm * weights['fvel'] +
            (100 - rpd) * weights['rpd'] +  # Invert: lower root prop delta = better
            sharpe * weights['sharpe'] +
            vol_norm * weights['vol']
        )
        
        # Ensure final score is in 0-100 range
        tao_score_v21 = max(0, min(100, tao_score_v21))
        return round(tao_score_v21, 1)
        
    except Exception as e:
        logger.error(f"Error calculating TAO-Score v2.1: {e}")
        return None

def calculate_tao_scores_comparison(
    # Core metrics for v1.1
    stake_quality: Optional[float],
    consensus_alignment: Optional[float],
    active_stake_ratio: Optional[float],
    validator_util_pct: Optional[float],
    emission_pct: Optional[float],
    price_7d_change: Optional[float],
    
    # Additional metrics for v2.1
    active_validators: Optional[int] = None,
    stake_hhi: Optional[float] = None,
    market_cap_tao: Optional[float] = None,
    flow_24h: Optional[float] = None,
    root_prop: Optional[float] = None,
    price_30d_change: Optional[float] = None,
    total_volume_tao_1d: Optional[float] = None,
    fdv_tao: Optional[float] = None,
    total_emission_tao: Optional[float] = None,
    alpha_circ: Optional[float] = None,
    price_tao: Optional[float] = None,
    root_prop_prev: Optional[float] = None,
    
    session = None
) -> Dict[str, Optional[float]]:
    """
    Calculate both TAO Score v1.1 and v2.1 for comparison.
    
    Returns:
        Dictionary with 'tao_score_v11' and 'tao_score_v21' scores
    """
    try:
        # Calculate v1.1 score
        tao_score_v11 = calculate_tao_score(
            stake_quality=stake_quality,
            consensus_alignment=consensus_alignment,
            active_stake_ratio=active_stake_ratio,
            emission_roi=None,  # Not used in v1.1
            reserve_momentum=None,  # Not used in v1.1
            validator_util_pct=validator_util_pct,
            inflation_pct=None,  # Not used in v1.1
            price_7d_change=price_7d_change,
            session=session
        )
        
        # Calculate v2.1 score
        tao_score_v21 = calculate_tao_score_v21(
            stake_quality=stake_quality,
            active_validators=active_validators,
            stake_hhi=stake_hhi,
            market_cap_tao=market_cap_tao,
            emission_pct=emission_pct,
            flow_24h=flow_24h,
            root_prop=root_prop,
            price_30d_change=price_30d_change,
            total_volume_tao_1d=total_volume_tao_1d,
            fdv_tao=fdv_tao,
            total_emission_tao=total_emission_tao,
            alpha_circ=alpha_circ,
            price_tao=price_tao,
            root_prop_prev=root_prop_prev,
            session=session
        )
        
        return {
            'tao_score_v11': tao_score_v11,
            'tao_score_v21': tao_score_v21
        }
        
    except Exception as e:
        logger.error(f"Error calculating TAO scores comparison: {e}")
        return {
            'tao_score_v11': None,
            'tao_score_v21': None
        } 