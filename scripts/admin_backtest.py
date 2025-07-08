#!/usr/bin/env python3
"""
Admin script for running TAO Score v2.1 backtests.
Provides easy interface for generating optimization reports.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.run_backtest import run_backtest
from datetime import datetime, timedelta
import argparse

def main():
    """Main admin interface for backtesting."""
    parser = argparse.ArgumentParser(
        description="TAO Score v2.1 Backtest - Admin Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run backtest for last 30 days, 7-day returns
  python scripts/admin_backtest.py --horizon 7d
  
  # Run backtest for specific date range, 1-day returns
  python scripts/admin_backtest.py --start-date 2025-06-01 --end-date 2025-07-01 --horizon 1d
  
  # Quick test with last 7 days
  python scripts/admin_backtest.py --days 7 --horizon 1d
        """
    )
    
    parser.add_argument("--start-date", type=str, 
                       help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, 
                       help="End date (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, 
                       help="Number of days to look back (alternative to start-date)")
    parser.add_argument("--horizon", choices=['1d', '7d', '30d'], default='7d',
                       help="Return horizon to optimize for (default: 7d - recommended for production)")
    parser.add_argument("--output-dir", type=str, default="backtest_reports",
                       help="Directory to save reports (default: backtest_reports)")
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Determine date range
    if args.days:
        end_date = datetime.utcnow() - timedelta(days=1)  # Yesterday
        start_date = end_date - timedelta(days=args.days)
        print(f"Using last {args.days} days: {start_date.date()} to {end_date.date()}")
    else:
        start_date = None
        end_date = None
        if args.start_date:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        if args.end_date:
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    
    print("=" * 60)
    print("TAO SCORE v2.1 BACKTEST - ADMIN INTERFACE")
    print("=" * 60)
    print(f"Date Range: {start_date.date() if start_date else 'Default'} to {end_date.date() if end_date else 'Default'}")
    print(f"Return Horizon: {args.horizon}")
    print(f"Output Directory: {args.output_dir}")
    print("=" * 60)
    print()
    
    # Run backtest
    try:
        result = run_backtest(start_date, end_date, args.horizon)
        
        if result and result['success']:
            print("\n" + "=" * 60)
            print("✅ BACKTEST COMPLETED SUCCESSFULLY")
            print("=" * 60)
            print(f"Best correlation: {result['correlation']:.4f}")
            print(f"Improvement: {result['correlation'] - 0.0063:.4f} (baseline: 0.0063)")
            print()
            print("📊 Reports generated in current directory:")
            print("   • Executive Summary: tao_score_backtest_executive_*.txt")
            print("   • Detailed Report: tao_score_backtest_detailed_*.txt")
            print("   • JSON Data: tao_score_backtest_data_*.json")
            print()
            print("🔍 Next Steps:")
            print("   1. Review the executive summary")
            print("   2. Check the detailed report for risk analysis")
            print("   3. Consider if weight changes make business sense")
            print("   4. Implement changes only after careful review")
        else:
            print("\n❌ BACKTEST FAILED")
            if result:
                print(f"Error: {result.get('message', 'Unknown error')}")
    
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("Check your database connection and data availability")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 