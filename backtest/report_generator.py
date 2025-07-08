#!/usr/bin/env python3
"""
Report generator for TAO Score v2.1 backtest results.
Produces detailed analysis and executive summary for admin review.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import json

class BacktestReportGenerator:
    """Generates detailed backtest reports for admin review."""
    
    def __init__(self, data: pd.DataFrame, optimization_result: Dict, 
                 comparison: Dict, data_summary: Dict):
        """
        Initialize report generator.
        
        Args:
            data: Historical data used for backtesting
            optimization_result: Results from weight optimization
            comparison: Performance comparison between weights
            data_summary: Summary of data used
        """
        self.data = data
        self.optimization_result = optimization_result
        self.comparison = comparison
        self.data_summary = data_summary
        
    def generate_executive_summary(self) -> str:
        """Generate executive summary for admin review."""
        summary = []
        summary.append("=" * 80)
        summary.append("TAO SCORE v2.1 BACKTEST - EXECUTIVE SUMMARY")
        summary.append("=" * 80)
        summary.append(f"Report Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        summary.append("")
        
        # Key Findings
        summary.append("KEY FINDINGS:")
        summary.append("-" * 40)
        
        if self.optimization_result['success']:
            current_corr = self.comparison['weights1_correlation']
            optimized_corr = self.comparison['weights2_correlation']
            improvement = self.comparison['improvement']
            improvement_pct = self.comparison['improvement_pct']
            
            summary.append(f"• Current weights correlation: {current_corr:.4f}")
            summary.append(f"• Optimized weights correlation: {optimized_corr:.4f}")
            summary.append(f"• Improvement: {improvement:.4f} ({improvement_pct:.1f}%)")
            
            if improvement > 0.02:
                summary.append("• RECOMMENDATION: Consider implementing optimized weights")
            elif improvement > 0.01:
                summary.append("• RECOMMENDATION: Monitor for further improvements")
            else:
                summary.append("• RECOMMENDATION: Current weights performing adequately")
        else:
            summary.append("• Optimization failed - current weights recommended")
        
        summary.append("")
        
        # Data Quality
        summary.append("DATA QUALITY:")
        summary.append("-" * 40)
        summary.append(f"• Total records: {self.data_summary['total_records']:,}")
        summary.append(f"• Unique subnets: {self.data_summary['unique_subnets']}")
        summary.append(f"• Date range: {self.data_summary['date_range']}")
        summary.append(f"• Valid return data points: {self.data_summary['valid_returns_1d']}")
        
        if self.data_summary['valid_returns_1d'] < 100:
            summary.append("• WARNING: Limited data may affect reliability")
        
        summary.append("")
        
        # Weight Changes Summary
        if self.optimization_result['success']:
            summary.append("MAJOR WEIGHT CHANGES:")
            summary.append("-" * 40)
            
            current_weights = {
                'sq': 0.18, 'av': 0.10, 'hhi': 0.07, 'mcap': 0.15,
                'eff': 0.10, 'fvel': 0.08, 'rpd': 0.07, 'sharpe': 0.15, 'vol': 0.10
            }
            optimized_weights = self.optimization_result['weights']
            
            changes = []
            for metric, new_weight in optimized_weights.items():
                old_weight = current_weights[metric]
                change = new_weight - old_weight
                change_pct = (change / old_weight) * 100 if old_weight > 0 else 0
                changes.append((metric, old_weight, new_weight, change, change_pct))
            
            # Sort by absolute change
            changes.sort(key=lambda x: abs(x[3]), reverse=True)
            
            for metric, old_w, new_w, change, change_pct in changes[:5]:
                metric_name = self._get_metric_name(metric)
                summary.append(f"• {metric_name}: {old_w:.3f} → {new_w:.3f} ({change:+.3f}, {change_pct:+.1f}%)")
        
        summary.append("")
        summary.append("=" * 80)
        
        return "\n".join(summary)
    
    def generate_detailed_report(self) -> str:
        """Generate detailed technical report."""
        report = []
        report.append("=" * 80)
        report.append("TAO SCORE v2.1 BACKTEST - DETAILED REPORT")
        report.append("=" * 80)
        report.append(f"Report Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        report.append("")
        
        # Data Analysis
        report.append("1. DATA ANALYSIS")
        report.append("-" * 40)
        report.append(f"Total records: {self.data_summary['total_records']:,}")
        report.append(f"Unique subnets: {self.data_summary['unique_subnets']}")
        report.append(f"Date range: {self.data_summary['date_range']}")
        report.append(f"Valid 1-day returns: {self.data_summary['valid_returns_1d']}")
        report.append(f"Valid 7-day returns: {self.data_summary['valid_returns_7d']}")
        report.append(f"Valid 30-day returns: {self.data_summary['valid_returns_30d']}")
        report.append("")
        
        # Return Distribution Analysis
        report.append("2. RETURN DISTRIBUTION ANALYSIS")
        report.append("-" * 40)
        if 'return_1d' in self.data.columns:
            returns = self.data['return_1d'].dropna()
            report.append(f"1-day returns statistics:")
            report.append(f"  Mean: {returns.mean():.4f}%")
            report.append(f"  Std Dev: {returns.std():.4f}%")
            report.append(f"  Min: {returns.min():.4f}%")
            report.append(f"  Max: {returns.max():.4f}%")
            report.append(f"  Median: {returns.median():.4f}%")
        report.append("")
        
        # Current vs Optimized Weights
        report.append("3. WEIGHT COMPARISON")
        report.append("-" * 40)
        
        current_weights = {
            'sq': 0.18, 'av': 0.10, 'hhi': 0.07, 'mcap': 0.15,
            'eff': 0.10, 'fvel': 0.08, 'rpd': 0.07, 'sharpe': 0.15, 'vol': 0.10
        }
        
        if self.optimization_result['success']:
            optimized_weights = self.optimization_result['weights']
            
            report.append("Metric Name                    Current    Optimized   Change     % Change")
            report.append("-" * 70)
            
            for metric in current_weights.keys():
                old_weight = current_weights[metric]
                new_weight = optimized_weights[metric]
                change = new_weight - old_weight
                change_pct = (change / old_weight) * 100 if old_weight > 0 else 0
                metric_name = self._get_metric_name(metric)
                
                report.append(f"{metric_name:<30} {old_weight:>8.3f} {new_weight:>10.3f} {change:>8.3f} {change_pct:>8.1f}%")
        else:
            report.append("Optimization failed - no weight changes available")
        
        report.append("")
        
        # Performance Metrics
        report.append("4. PERFORMANCE METRICS")
        report.append("-" * 40)
        report.append(f"Current weights correlation: {self.comparison['weights1_correlation']:.6f}")
        report.append(f"Optimized weights correlation: {self.comparison['weights2_correlation']:.6f}")
        report.append(f"Absolute improvement: {self.comparison['improvement']:.6f}")
        report.append(f"Percentage improvement: {self.comparison['improvement_pct']:.2f}%")
        
        if self.optimization_result['success']:
            report.append(f"Optimization iterations: {self.optimization_result['iterations']}")
        
        report.append("")
        
        # Risk Analysis
        report.append("5. RISK ANALYSIS")
        report.append("-" * 40)
        
        if self.optimization_result['success']:
            optimized_weights = self.optimization_result['weights']
            
            # Check for extreme weight changes
            extreme_changes = []
            for metric, new_weight in optimized_weights.items():
                old_weight = current_weights[metric]
                change_pct = abs((new_weight - old_weight) / old_weight) * 100
                if change_pct > 100:  # More than 100% change
                    extreme_changes.append((metric, change_pct))
            
            if extreme_changes:
                report.append("⚠️  EXTREME WEIGHT CHANGES DETECTED:")
                for metric, change_pct in extreme_changes:
                    metric_name = self._get_metric_name(metric)
                    report.append(f"  • {metric_name}: {change_pct:.1f}% change")
                report.append("  RECOMMENDATION: Review these changes carefully")
            else:
                report.append("✅ No extreme weight changes detected")
            
            # Check weight distribution
            max_weight = max(optimized_weights.values())
            min_weight = min(optimized_weights.values())
            
            if max_weight > 0.4:
                report.append(f"⚠️  High concentration in single metric: {max_weight:.3f}")
            if min_weight < 0.01:
                report.append(f"⚠️  Very low weight for some metrics: {min_weight:.3f}")
        
        report.append("")
        
        # Recommendations
        report.append("6. RECOMMENDATIONS")
        report.append("-" * 40)
        
        if self.optimization_result['success']:
            improvement = self.comparison['improvement']
            
            if improvement > 0.05:
                report.append("✅ STRONG RECOMMENDATION: Implement optimized weights")
                report.append("   Rationale: Significant improvement in predictive power")
            elif improvement > 0.02:
                report.append("✅ MODERATE RECOMMENDATION: Consider implementing optimized weights")
                report.append("   Rationale: Moderate improvement, low risk")
            elif improvement > 0.01:
                report.append("⚠️  WEAK RECOMMENDATION: Monitor for further improvements")
                report.append("   Rationale: Small improvement, may not justify change")
            else:
                report.append("❌ NO RECOMMENDATION: Keep current weights")
                report.append("   Rationale: No significant improvement detected")
        else:
            report.append("❌ NO RECOMMENDATION: Optimization failed")
            report.append("   Rationale: Technical issues prevented optimization")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def _get_metric_name(self, metric_code: str) -> str:
        """Get human-readable metric name."""
        names = {
            'sq': 'Stake Quality',
            'av': 'Active Validators', 
            'hhi': 'Stake HHI (Inverted)',
            'mcap': 'Market Cap',
            'eff': 'Emission Efficiency (Inverted)',
            'fvel': 'Flow Velocity',
            'rpd': 'Root Prop Delta (Inverted)',
            'sharpe': 'Sharpe Ratio (30d)',
            'vol': 'Volume (1d)'
        }
        return names.get(metric_code, metric_code.upper())
    
    def save_reports(self, output_dir: str = ".") -> Dict[str, str]:
        """Save both executive summary and detailed report to files."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # Generate reports
        exec_summary = self.generate_executive_summary()
        detailed_report = self.generate_detailed_report()
        
        # Save files
        exec_file = f"{output_dir}/tao_score_backtest_executive_{timestamp}.txt"
        detailed_file = f"{output_dir}/tao_score_backtest_detailed_{timestamp}.txt"
        
        with open(exec_file, 'w') as f:
            f.write(exec_summary)
        
        with open(detailed_file, 'w') as f:
            f.write(detailed_report)
        
        # Save JSON data for programmatic access
        json_file = f"{output_dir}/tao_score_backtest_data_{timestamp}.json"
        data = {
            'timestamp': timestamp,
            'optimization_result': self.optimization_result,
            'comparison': self.comparison,
            'data_summary': self.data_summary
        }
        
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        return {
            'executive_summary': exec_file,
            'detailed_report': detailed_file,
            'json_data': json_file
        } 