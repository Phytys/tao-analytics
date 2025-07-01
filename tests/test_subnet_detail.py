#!/usr/bin/env python3
"""
Test script for subnet detail page functionality.
Tests the new investor-focused layout and data sources.
"""

import sys
import os
# Add parent directory to path since we're now in tests/
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db import get_db
from models import MetricsSnap, SubnetMeta, CategoryStats, GptInsights, AggregatedCache, HoldersCache
from services.gpt_insight import gpt_insight_service
import pandas as pd
from datetime import datetime, timedelta

def test_subnet_data_completeness(netuid: int = 64):
    """Test data completeness for a specific subnet."""
    print(f"\n=== Testing Subnet {netuid} Data Completeness ===")
    
    with get_db() as session:
        # Get latest metrics
        latest_metrics = session.query(MetricsSnap).filter_by(netuid=netuid)\
            .order_by(MetricsSnap.timestamp.desc()).first()
        
        # Get subnet metadata
        subnet_meta = session.query(SubnetMeta).filter_by(netuid=netuid).first()
        
        # Get category stats
        category_stats = None
        if latest_metrics and latest_metrics.category:
            category_stats = session.query(CategoryStats).filter_by(category=latest_metrics.category).first()
        
        print(f"Subnet Name: {subnet_meta.subnet_name if subnet_meta else 'Unknown'}")
        print(f"Category: {subnet_meta.primary_category if subnet_meta else 'Unknown'}")
        print(f"Tagline: {subnet_meta.tagline if subnet_meta else 'None'}")
        
        if latest_metrics:
            print(f"\nMetrics Timestamp: {latest_metrics.timestamp}")
            
            # Test Overview Card Data
            print(f"\n--- Overview Card Data ---")
            print(f"Price (TAO): {latest_metrics.price_tao}")
            print(f"Market Cap (TAO): {latest_metrics.market_cap_tao}")
            print(f"Total Stake (TAO): {latest_metrics.total_stake_tao}")
            print(f"UID Count: {latest_metrics.uid_count}")
            print(f"Price 1d Change: {latest_metrics.price_1d_change}%")
            print(f"Price 7d Change: {latest_metrics.price_7d_change}%")
            print(f"Price 30d Change: {latest_metrics.price_30d_change}%")
            print(f"Buy Volume 24h: {latest_metrics.buy_volume_tao_1d} TAO")
            print(f"TAO Reserves: {latest_metrics.tao_in} TAO")
            
            # Test Key Metrics Grid Data
            print(f"\n--- Key Metrics Grid Data ---")
            print(f"Stake Quality: {latest_metrics.stake_quality}")
            print(f"Reserve Momentum: {latest_metrics.reserve_momentum}")
            print(f"Emission ROI: {latest_metrics.emission_roi}")
            print(f"Active Validators: {latest_metrics.active_validators}")
            
            # Test Peer Comparison Data
            print(f"\n--- Peer Comparison Data ---")
            if category_stats:
                print(f"Category Median Stake Quality: {category_stats.median_stake_quality}")
                print(f"Category Median Emission ROI: {category_stats.median_emission_roi}")
                print(f"Subnets in Category: {category_stats.subnet_count}")
            else:
                print("No category stats available")
            
            # Test Flow Data
            print(f"\n--- Flow Data ---")
            print(f"Alpha Circulating: {latest_metrics.alpha_circ}")
            print(f"Alpha Proportion: {latest_metrics.alpha_prop}")
            print(f"Root Proportion: {latest_metrics.root_prop}")
            
        else:
            print("No metrics data available")

def test_gpt_insight_functionality(netuid: int = 64):
    """Test GPT insight functionality."""
    print(f"\n=== Testing GPT Insight for Subnet {netuid} ===")
    
    try:
        insight = gpt_insight_service['get_insight'](netuid)
        print(f"GPT Insight: {insight}")
        print(f"Insight Length: {len(insight)} characters")
        
        # Check if insight follows the design brief format
        if "Compared with other" in insight or "demo insight" in insight:
            print("✅ GPT insight format looks correct")
        else:
            print("⚠️ GPT insight may not follow design brief format")
            
    except Exception as e:
        print(f"❌ Error getting GPT insight: {e}")

def test_all_subnets_data_quality():
    """Test data quality across all subnets."""
    print(f"\n=== Testing All Subnets Data Quality ===")
    
    with get_db() as session:
        # Get latest metrics for all subnets
        latest_timestamp = session.query(MetricsSnap.timestamp)\
            .order_by(MetricsSnap.timestamp.desc()).first()
        
        if not latest_timestamp:
            print("No metrics data available")
            return
        
        latest_timestamp = latest_timestamp[0]
        
        # Get all subnets with latest data
        subnets = session.query(MetricsSnap).filter(
            MetricsSnap.timestamp == latest_timestamp
        ).all()
        
        print(f"Testing {len(subnets)} subnets with data from {latest_timestamp}")
        
        # Check data completeness
        missing_price = 0
        missing_market_cap = 0
        missing_reserve_momentum = 0
        missing_stake_quality = 0
        missing_emission_roi = 0
        missing_active_validators = 0
        
        for subnet in subnets:
            if subnet.price_tao is None:
                missing_price += 1
            if subnet.market_cap_tao is None:
                missing_market_cap += 1
            if subnet.reserve_momentum is None:
                missing_reserve_momentum += 1
            if subnet.stake_quality is None:
                missing_stake_quality += 1
            if subnet.emission_roi is None:
                missing_emission_roi += 1
            if subnet.active_validators is None:
                missing_active_validators += 1
        
        total_subnets = len(subnets)
        print(f"\nData Completeness Report:")
        print(f"Price Data: {(total_subnets - missing_price) / total_subnets * 100:.1f}% complete")
        print(f"Market Cap Data: {(total_subnets - missing_market_cap) / total_subnets * 100:.1f}% complete")
        print(f"Reserve Momentum: {(total_subnets - missing_reserve_momentum) / total_subnets * 100:.1f}% complete")
        print(f"Stake Quality: {(total_subnets - missing_stake_quality) / total_subnets * 100:.1f}% complete")
        print(f"Emission ROI: {(total_subnets - missing_emission_roi) / total_subnets * 100:.1f}% complete")
        print(f"Active Validators: {(total_subnets - missing_active_validators) / total_subnets * 100:.1f}% complete")
        
        # Check category stats
        category_stats = session.query(CategoryStats).all()
        print(f"\nCategory Stats: {len(category_stats)} categories with peer comparison data")

def test_investor_metrics_calculation():
    """Test the calculation of investor-focused metrics."""
    print(f"\n=== Testing Investor Metrics Calculation ===")
    
    with get_db() as session:
        # Test subnet 64 specifically
        latest_metrics = session.query(MetricsSnap).filter_by(netuid=64)\
            .order_by(MetricsSnap.timestamp.desc()).first()
        
        if latest_metrics:
            print(f"Subnet 64 Latest Metrics:")
            print(f"Stake Quality (HHI-adjusted): {latest_metrics.stake_quality}")
            print(f"Reserve Momentum (Δ TAO-in 24h / supply): {latest_metrics.reserve_momentum}")
            print(f"Emission ROI (TAO-in/day ÷ stake): {latest_metrics.emission_roi}")
            print(f"Active Validators (validator_permit.sum()): {latest_metrics.active_validators}")
            
            # Check if calculations make sense
            if latest_metrics.stake_quality is not None and 0 <= latest_metrics.stake_quality <= 100:
                print("✅ Stake Quality calculation looks correct")
            else:
                print("⚠️ Stake Quality calculation may be incorrect")
                
            if latest_metrics.reserve_momentum is not None:
                print("✅ Reserve Momentum calculation available")
            else:
                print("⚠️ Reserve Momentum calculation missing")
                
            if latest_metrics.emission_roi is not None and latest_metrics.emission_roi >= 0:
                print("✅ Emission ROI calculation looks correct")
            else:
                print("⚠️ Emission ROI calculation may be incorrect")
                
            if latest_metrics.active_validators is not None and latest_metrics.active_validators >= 0:
                print("✅ Active Validators calculation looks correct")
            else:
                print("⚠️ Active Validators calculation may be incorrect")

def test_feedback_fixes():
    """Test the fixes for the feedback issues."""
    print(f"\n=== Testing Feedback Fixes ===")
    
    with get_db() as session:
        # Test subnet 64 specifically
        latest_metrics = session.query(MetricsSnap).filter_by(netuid=64)\
            .order_by(MetricsSnap.timestamp.desc()).first()
        
        if latest_metrics:
            print(f"Subnet 64 Latest Metrics:")
            
            # Test 1: Price and Market Cap should not be NULL
            print(f"\n--- Test 1: Price & Market Cap Data ---")
            print(f"Price (TAO): {latest_metrics.price_tao}")
            print(f"Market Cap (TAO): {latest_metrics.market_cap_tao}")
            
            if latest_metrics.price_tao is not None:
                print("✅ Price data is available")
            else:
                print("❌ Price data is NULL - needs fixing")
                
            if latest_metrics.market_cap_tao is not None:
                print("✅ Market cap data is available")
            else:
                print("❌ Market cap data is NULL - needs fixing")
            
            # Test 2: Reserve Momentum should not be "--"
            print(f"\n--- Test 2: Reserve Momentum ---")
            print(f"Reserve Momentum: {latest_metrics.reserve_momentum}")
            
            if latest_metrics.reserve_momentum is not None:
                print("✅ Reserve momentum is calculated")
            else:
                print("❌ Reserve momentum is NULL - needs historical data")
            
            # Test 3: Active Validators should be clear
            print(f"\n--- Test 3: Active Validators ---")
            print(f"Active Validators: {latest_metrics.active_validators}")
            print(f"UID Count: {latest_metrics.uid_count}")
            
            if latest_metrics.active_validators is not None:
                print("✅ Active validators count is available")
                print(f"   Note: Should show as 'Active Validators (of {latest_metrics.uid_count} UIDs)'")
            else:
                print("❌ Active validators count is NULL")
            
            # Test 4: Category Stats for Peer Comparison
            print(f"\n--- Test 4: Category Stats ---")
            if latest_metrics.category:
                category_stats = session.query(CategoryStats).filter_by(category=latest_metrics.category).first()
                if category_stats:
                    print(f"Category: {latest_metrics.category}")
                    print(f"Median Stake Quality: {category_stats.median_stake_quality}")
                    print(f"Median Emission ROI: {category_stats.median_emission_roi}")
                    print(f"Subnets in Category: {category_stats.subnet_count}")
                    print("✅ Category stats available for peer comparison")
                else:
                    print("❌ No category stats found - needs nightly computation")
            else:
                print("❌ No category assigned to subnet")
            
            # Test 5: GPT Insights Cache
            print(f"\n--- Test 5: GPT Insights Cache ---")
            gpt_insight = session.query(GptInsights).filter_by(netuid=64).first()
            if gpt_insight:
                print(f"GPT Insight: {gpt_insight.text[:100]}...")
                print(f"Cached at: {gpt_insight.ts}")
                print("✅ GPT insight is cached")
            else:
                print("❌ No GPT insight cached - will generate on first view")
            
            # Test 6: Cache Tables
            print(f"\n--- Test 6: Cache Tables ---")
            aggregated_cache = session.query(AggregatedCache).filter_by(netuid=64).first()
            holders_cache = session.query(HoldersCache).filter_by(netuid=64).first()
            
            if aggregated_cache:
                print("✅ Aggregated cache table exists")
            else:
                print("❌ No aggregated cache - will be created on first API call")
                
            if holders_cache:
                print("✅ Holders cache table exists")
            else:
                print("❌ No holders cache - will be created on first API call")
                
        else:
            print("❌ No metrics data available for subnet 64")

def main():
    """Run all tests."""
    print("🧪 Testing Subnet Detail Page - Investor-Focused Layout")
    print("=" * 60)
    
    # Test specific subnet
    test_subnet_data_completeness(64)
    
    # Test GPT insight
    test_gpt_insight_functionality(64)
    
    # Test all subnets data quality
    test_all_subnets_data_quality()
    
    # Test investor metrics calculation
    test_investor_metrics_calculation()
    
    # Test feedback fixes
    test_feedback_fixes()
    
    print(f"\n✅ Testing complete!")
    print("\nKey Issues to Check:")
    print("1. Active validators should use validator_permit.sum()")
    print("2. Market cap should display properly in overview")
    print("3. Reserve momentum should be calculated from historical data")
    print("4. GPT insights should include peer comparisons")
    print("5. All investor metrics should be populated")

if __name__ == "__main__":
    main() 