#!/usr/bin/env python3
"""
Health check script to test Network Overview functionality.
Run this on Heroku to verify the PostgreSQL vs SQLite fixes work.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db import load_screener_frame
from dash_app.pages.insights import get_network_summary_stats, _clean_numeric
import pandas as pd
from decimal import Decimal

def test_data_loading():
    """Test basic data loading."""
    print("=== Testing Data Loading ===")
    try:
        df = load_screener_frame()
        print(f"✓ Data loaded successfully: {len(df)} rows")
        print(f"✓ Columns: {list(df.columns)}")
        
        # Check for mixed data types
        numeric_cols = ['tao_score', 'market_cap_tao', 'total_stake_tao', 'stake_quality', 
                       'flow_24h', 'buy_signal', 'active_validators', 'validator_util_pct']
        
        print("\n=== Data Types Before Cleaning ===")
        for col in numeric_cols:
            if col in df.columns:
                print(f"{col}: {df[col].dtype}")
                # Check for mixed types
                sample_values = df[col].dropna().head(5)
                print(f"  Sample values: {list(sample_values)}")
        
        return df
    except Exception as e:
        print(f"✗ Data loading failed: {e}")
        return None

def test_numeric_cleaning(df):
    """Test the numeric cleaning function."""
    print("\n=== Testing Numeric Cleaning ===")
    try:
        numeric_cols = ['tao_score', 'market_cap_tao', 'total_stake_tao', 'stake_quality', 
                       'flow_24h', 'buy_signal', 'active_validators', 'validator_util_pct']
        
        df_cleaned = _clean_numeric(df.copy(), numeric_cols)
        
        print("✓ Numeric cleaning completed")
        print("\n=== Data Types After Cleaning ===")
        for col in numeric_cols:
            if col in df_cleaned.columns:
                print(f"{col}: {df_cleaned[col].dtype}")
                # Check for any remaining non-numeric values
                non_numeric = df_cleaned[col].dropna()
                if len(non_numeric) > 0:
                    print(f"  Non-null values: {len(non_numeric)}")
                    print(f"  Sample values: {list(non_numeric.head(3))}")
        
        return df_cleaned
    except Exception as e:
        print(f"✗ Numeric cleaning failed: {e}")
        return None

def test_network_summary_stats():
    """Test the network summary stats function."""
    print("\n=== Testing Network Summary Stats ===")
    try:
        stats, df = get_network_summary_stats()
        print("✓ Network summary stats calculated successfully")
        print(f"✓ Stats: {stats}")
        
        # Check for non-zero values
        non_zero_stats = {k: v for k, v in stats.items() if isinstance(v, (int, float)) and v > 0}
        print(f"✓ Non-zero stats: {len(non_zero_stats)} out of {len(stats)}")
        
        return stats
    except Exception as e:
        print(f"✗ Network summary stats failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_comparison_operations(df):
    """Test comparison operations that were failing."""
    print("\n=== Testing Comparison Operations ===")
    try:
        numeric_cols = ['tao_score', 'market_cap_tao', 'total_stake_tao', 'stake_quality', 
                       'flow_24h', 'buy_signal', 'active_validators', 'validator_util_pct']
        
        df_cleaned = _clean_numeric(df.copy(), numeric_cols)
        
        # Test the specific operations that were failing
        if 'tao_score' in df_cleaned.columns:
            high_performers = (df_cleaned['tao_score'] >= 70).sum()
            print(f"✓ High performers (>=70): {high_performers}")
        
        if 'flow_24h' in df_cleaned.columns:
            improving = (df_cleaned['flow_24h'] > 0).sum()
            print(f"✓ Improving subnets (>0): {improving}")
        
        if 'buy_signal' in df_cleaned.columns:
            strong_buy = (df_cleaned['buy_signal'] >= 4).sum()
            print(f"✓ Strong buy signals (>=4): {strong_buy}")
        
        print("✓ All comparison operations completed successfully")
        return True
    except Exception as e:
        print(f"✗ Comparison operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all health checks."""
    print("🔍 TAO Analytics Health Check")
    print("=" * 50)
    
    # Test 1: Data loading
    df = test_data_loading()
    if df is None:
        print("\n❌ Health check failed at data loading stage")
        return False
    
    # Test 2: Numeric cleaning
    df_cleaned = test_numeric_cleaning(df)
    if df_cleaned is None:
        print("\n❌ Health check failed at numeric cleaning stage")
        return False
    
    # Test 3: Comparison operations
    comparison_ok = test_comparison_operations(df)
    if not comparison_ok:
        print("\n❌ Health check failed at comparison operations stage")
        return False
    
    # Test 4: Network summary stats
    stats = test_network_summary_stats()
    if stats is None:
        print("\n❌ Health check failed at network summary stats stage")
        return False
    
    print("\n" + "=" * 50)
    print("✅ All health checks passed!")
    print("✅ Network Overview should work correctly on Heroku")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 