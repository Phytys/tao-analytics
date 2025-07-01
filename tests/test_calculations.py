#!/usr/bin/env python3
"""
Test script to verify TAO Analytics calculations and show actual values.
Run this to validate the calculations documented in CALCULATIONS_DOCUMENTATION.md
"""

import sys
import os
# Add parent directory to path since we're now in tests/
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.bittensor.metrics import calculate_subnet_metrics
from services.db import get_db
from models import MetricsSnap, CategoryStats
from sqlalchemy import func
import json

def test_emission_calculations():
    """Test emission calculations for subnet 1."""
    print("=== EMISSION CALCULATIONS TEST ===")
    
    metrics = calculate_subnet_metrics(1)
    
    print(f"Subnet 1 Metrics:")
    print(f"  tao_in_emission (per block): {metrics['tao_in_emission']}")
    print(f"  total_emission_tao (per block): {metrics['total_emission_tao']}")
    print(f"  alpha_out_emission: {metrics['alpha_out_emission']}")
    
    # Test daily estimation
    blocks_per_day = 7200
    daily_tao_emission = metrics['tao_in_emission'] * blocks_per_day
    daily_emission_roi = daily_tao_emission / metrics['total_stake_tao']
    
    print(f"\nDaily Estimation:")
    print(f"  Estimated daily tao_in_emission: {daily_tao_emission:.2f} TAO")
    print(f"  Daily emission ROI: {daily_emission_roi:.6f}")
    
    # Test emission split
    print(f"\nEmission Split:")
    print(f"  Owner: {metrics['emission_split']['owner']:.1%}")
    print(f"  Miners: {metrics['emission_split']['miners']:.1%}")
    print(f"  Validators: {metrics['emission_split']['validators']:.1%}")
    
    print(f"\nRolling Emission Split (3 blocks):")
    print(f"  Owner: {metrics['emission_split_rolling']['owner']:.1%}")
    print(f"  Miners: {metrics['emission_split_rolling']['miners']:.1%}")
    print(f"  Validators: {metrics['emission_split_rolling']['validators']:.1%}")

def test_stake_quality_calculation():
    """Test stake quality calculation."""
    print("\n=== STAKE QUALITY CALCULATION TEST ===")
    
    metrics = calculate_subnet_metrics(1)
    
    print(f"Subnet 1 Stake Metrics:")
    print(f"  HHI: {metrics['stake_hhi']}")
    print(f"  Current stake quality: {metrics.get('stake_quality', 'Not calculated')}")
    
    # Test the formula
    hhi = metrics['stake_hhi']
    current_quality = max(0, 100 - (hhi / 100))
    normalized_quality = max(0, 100 - ((hhi / 10000) * 100))
    
    print(f"\nStake Quality Calculations:")
    print(f"  Current formula: {current_quality:.1f}")
    print(f"  Normalized formula: {normalized_quality:.1f}")
    print(f"  HHI normalized to 0-1: {hhi/10000:.4f}")

def test_category_statistics():
    """Test category statistics calculation."""
    print("\n=== CATEGORY STATISTICS TEST ===")
    
    with get_db() as session:
        # Get latest timestamp
        latest_timestamp = session.query(func.max(MetricsSnap.timestamp)).scalar()
        
        if not latest_timestamp:
            print("No metrics data available")
            return
        
        # Test current calculation (using avg but labeled as median)
        current_stats = session.query(
            MetricsSnap.category,
            func.avg(MetricsSnap.stake_quality).label('avg_stake_quality'),
            func.avg(MetricsSnap.emission_roi).label('avg_emission_roi'),
            func.count(MetricsSnap.netuid).label('subnet_count')
        ).filter(
            MetricsSnap.timestamp == latest_timestamp,
            MetricsSnap.category.isnot(None)
        ).group_by(MetricsSnap.category).all()
        
        print("Current Category Statistics (using AVG):")
        for stat in current_stats:
            print(f"  {stat.category}: {stat.subnet_count} subnets")
            print(f"    Avg Stake Quality: {stat.avg_stake_quality:.1f}")
            print(f"    Avg Emission ROI: {stat.avg_emission_roi:.6f}")
        
        # Test proper median calculation (if supported)
        try:
            median_stats = session.query(
                MetricsSnap.category,
                func.percentile_cont(0.5).within_group(MetricsSnap.stake_quality.asc()).label('median_stake_quality'),
                func.percentile_cont(0.5).within_group(MetricsSnap.emission_roi.asc()).label('median_emission_roi'),
                func.count(MetricsSnap.netuid).label('subnet_count')
            ).filter(
                MetricsSnap.timestamp == latest_timestamp,
                MetricsSnap.category.isnot(None)
            ).group_by(MetricsSnap.category).all()
            
            print("\nProper Median Statistics:")
            for stat in median_stats:
                print(f"  {stat.category}: {stat.subnet_count} subnets")
                print(f"    Median Stake Quality: {stat.median_stake_quality:.1f}")
                print(f"    Median Emission ROI: {stat.median_emission_roi:.6f}")
        except Exception as e:
            print(f"Median calculation not supported: {e}")

def test_consensus_alignment():
    """Test consensus alignment calculation."""
    print("\n=== CONSENSUS ALIGNMENT TEST ===")
    
    metrics = calculate_subnet_metrics(1)
    
    print(f"Subnet 1 Consensus Metrics:")
    print(f"  Consensus Alignment: {metrics['consensus_alignment']:.1f}%")
    print(f"  Mean Consensus: {metrics['mean_consensus']:.6f}")
    print(f"  Trust Score: {metrics['trust_score']:.6f}")
    
    # Test the tolerance calculation
    tolerance = 0.10
    print(f"\nConsensus Tolerance Analysis:")
    print(f"  Current tolerance: ±{tolerance}")
    print(f"  This means UIDs within ±{tolerance} of mean are considered 'aligned'")

def test_gpt_context_data():
    """Test what data is available for GPT context."""
    print("\n=== GPT CONTEXT DATA TEST ===")
    
    with get_db() as session:
        # Get latest metrics for subnet 1
        latest_metrics = session.query(MetricsSnap).filter(
            MetricsSnap.netuid == 1
        ).order_by(MetricsSnap.timestamp.desc()).first()
        
        if not latest_metrics:
            print("No metrics data for subnet 1")
            return
        
        print("Available Data for GPT Context:")
        print(f"  Basic: netuid={latest_metrics.netuid}, stake={latest_metrics.total_stake_tao:,.0f}")
        print(f"  Stake Quality: {latest_metrics.stake_quality:.1f}/100")
        print(f"  Emission ROI: {latest_metrics.emission_roi:.6f}")
        print(f"  Reserve Momentum: {latest_metrics.reserve_momentum:.6f}")
        print(f"  Active Validators: {latest_metrics.active_validators}/256")
        
        # Check market data
        if latest_metrics.market_cap_tao:
            print(f"  Market Cap: {latest_metrics.market_cap_tao:,.0f} TAO")
        if latest_metrics.price_tao:
            print(f"  Price: {latest_metrics.price_tao:.6f} TAO")
        if latest_metrics.flow_24h:
            print(f"  24h Volume: {latest_metrics.flow_24h:,.0f} TAO")
        
        # Check emission data
        if latest_metrics.tao_in_emission:
            print(f"  TAO In Emission: {latest_metrics.tao_in_emission:.6f}")
        if latest_metrics.alpha_out_emission:
            print(f"  Alpha Out Emission: {latest_metrics.alpha_out_emission:.6f}")
        
        # Check network health
        if latest_metrics.consensus_alignment:
            print(f"  Consensus Alignment: {latest_metrics.consensus_alignment:.1f}%")
        if latest_metrics.trust_score:
            print(f"  Trust Score: {latest_metrics.trust_score:.6f}")
        if latest_metrics.mean_incentive:
            print(f"  Mean Incentive: {latest_metrics.mean_incentive:.6f}")

def main():
    """Run all tests."""
    print("TAO Analytics Calculations Test Suite")
    print("=" * 50)
    
    try:
        test_emission_calculations()
        test_stake_quality_calculation()
        test_category_statistics()
        test_consensus_alignment()
        test_gpt_context_data()
        
        print("\n" + "=" * 50)
        print("Test suite completed. Check CALCULATIONS_DOCUMENTATION.md for analysis.")
        
    except Exception as e:
        print(f"Error running tests: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 