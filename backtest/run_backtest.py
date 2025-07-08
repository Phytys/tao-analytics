#!/usr/bin/env python3
"""
Main backtest runner for TAO Score v2.1 optimization.
Loads data, runs optimization, and reports results.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.data_loader import BacktestDataLoader
from backtest.optimizer import TAOScoreOptimizer
from backtest.report_generator import BacktestReportGenerator
from datetime import datetime, timedelta
import pandas as pd
import json

def run_backtest(start_date=None, end_date=None, return_horizon='7d'):
    """
    Run complete backtest for TAO Score v2.1 optimization.
    
    Args:
        start_date: Start date for data (default: 30 days ago)
        end_date: End date for data (default: yesterday)
        return_horizon: Return horizon to optimize for ('1d', '7d', '30d')
    """
    print("=== TAO Score v2.1 Backtest Runner ===\n")
    
    # Set default dates if not provided
    if start_date is None:
        start_date = datetime.utcnow() - timedelta(days=30)
    if end_date is None:
        end_date = datetime.utcnow() - timedelta(days=1)
    
    print(f"Backtest period: {start_date.date()} to {end_date.date()}")
    print(f"Optimizing for: {return_horizon} returns\n")
    
    # Load data
    loader = BacktestDataLoader()
    data = loader.load_historical_data(start_date, end_date)
    
    if data.empty:
        print("No data available for backtesting")
        return
    
    # Show data summary
    summary = loader.get_data_summary(data)
    print("\n=== Data Summary ===")
    for key, value in summary.items():
        print(f"{key}: {value}")
    
    # Check if we have enough data
    return_column = f'return_{return_horizon}'
    valid_returns = data[return_column].notna().sum()
    
    if valid_returns < 20:
        print(f"\n⚠️  Warning: Only {valid_returns} valid return data points")
        print("This may not be enough for reliable optimization")
        print("Consider using a longer date range or shorter return horizon")
    
    print(f"\n=== Starting Optimization ===")
    
    # Create optimizer
    optimizer = TAOScoreOptimizer(data)
    
    # Test current weights
    print("\n1. Testing current weights...")
    current_correlation = -optimizer.calculate_correlation(optimizer.default_weights, return_column)
    print(f"Current correlation: {current_correlation:.4f}")
    
    # Optimize weights
    print("\n2. Optimizing weights...")
    result = optimizer.optimize_weights(return_column)
    
    if result['success']:
        print(f"\n✅ Optimization completed successfully!")
        print(f"Optimized correlation: {result['correlation']:.4f}")
        print(f"Iterations: {result['iterations']}")
        
        # Compare with current weights
        comparison = optimizer.compare_weights(
            optimizer.default_weights, 
            result['weights'], 
            return_column
        )
        
        print(f"\n=== Performance Comparison ===")
        print(f"Current weights correlation: {comparison['weights1_correlation']:.4f}")
        print(f"Optimized weights correlation: {comparison['weights2_correlation']:.4f}")
        print(f"Improvement: {comparison['improvement']:.4f} ({comparison['improvement_pct']:.1f}%)")
        
        # Generate and save reports
        report_generator = BacktestReportGenerator(data, result, comparison, summary)
        report_files = report_generator.save_reports("backtest_reports")
        
        print(f"\n=== Reports Generated ===")
        print(f"Executive Summary: {report_files['executive_summary']}")
        print(f"Detailed Report: {report_files['detailed_report']}")
        print(f"JSON Data: {report_files['json_data']}")
        
        # Also save simple results
        save_results(result, comparison, summary, return_horizon)
        print(f"Simple results: backtest_results_{return_horizon}_*.json")
        
    else:
        print(f"\n❌ Optimization failed: {result['message']}")
    
    return result

def save_results(optimization_result, comparison, data_summary, return_horizon):
    """Save optimization results to file."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"backtest_results_{return_horizon}_{timestamp}.json"
    
    results = {
        'timestamp': timestamp,
        'return_horizon': return_horizon,
        'optimization_result': optimization_result,
        'comparison': comparison,
        'data_summary': data_summary
    }
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {filename}")

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="TAO Score v2.1 Backtest Runner")
    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--horizon", choices=['1d', '7d', '30d'], default='7d',
                       help="Return horizon to optimize for")
    
    args = parser.parse_args()
    
    # Parse dates
    start_date = None
    end_date = None
    
    if args.start_date:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    if args.end_date:
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    
    # Run backtest
    result = run_backtest(start_date, end_date, args.horizon)
    
    if result and result['success']:
        print(f"\n🎉 Backtest completed successfully!")
        print(f"Best correlation: {result['correlation']:.4f}")
    else:
        print(f"\n❌ Backtest failed")

if __name__ == "__main__":
    main() 