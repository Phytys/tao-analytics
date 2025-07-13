#!/usr/bin/env python3
"""
Enhanced Validator Analysis Script for TAO Analytics
Uses existing SDK data collection to provide accurate validator business case analysis.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from services.db import get_db
from models import MetricsSnap, SubnetMeta, CategoryStats
from sqlalchemy import func, desc, and_, text

class EnhancedValidatorAnalysis:
    """Enhanced validator analysis using existing SDK data collection."""
    
    def __init__(self):
        self.db = get_db()
        self.current_tao_price_usd = 300  # Approximate current price
        self.blocks_per_day = 7200
        
    def get_latest_subnet_data(self) -> pd.DataFrame:
        """Get latest metrics for all subnets from existing SDK collection."""
        with self.db as session:
            # Get latest metrics for each subnet using subquery approach
            subquery = session.query(
                MetricsSnap.netuid,
                func.max(MetricsSnap.timestamp).label('max_timestamp')
            ).group_by(MetricsSnap.netuid).subquery()
            
            latest_metrics = session.query(MetricsSnap).join(
                subquery,
                and_(
                    MetricsSnap.netuid == subquery.c.netuid,
                    MetricsSnap.timestamp == subquery.c.max_timestamp
                )
            ).all()
            
            # Convert to DataFrame
            data = []
            for metric in latest_metrics:
                data.append({
                    'netuid': metric.netuid,
                    'subnet_name': metric.subnet_name,
                    'category': metric.category,
                    'price_tao': metric.price_tao,
                    'market_cap_tao': metric.market_cap_tao,
                    'total_stake_tao': metric.total_stake_tao,
                    'active_validators': metric.active_validators,
                    'max_validators': metric.max_validators,
                    'validator_util_pct': metric.validator_util_pct,
                    'emission_roi': metric.emission_roi,
                    'emission_validators': metric.emission_validators,
                    'tao_in_emission': metric.tao_in_emission,
                    'stake_quality': metric.stake_quality,
                    'consensus_alignment': metric.consensus_alignment,
                    'trust_score': metric.trust_score,
                    'tao_score': metric.tao_score,
                    'buy_signal': metric.buy_signal,
                    'stake_hhi': metric.stake_hhi,
                    'mean_incentive': metric.mean_incentive,
                    'p95_incentive': metric.p95_incentive,
                    'timestamp': metric.timestamp
                })
            
            return pd.DataFrame(data)
    
    def get_historical_validator_data(self, netuid: int, days_back: int = 30) -> pd.DataFrame:
        """Get historical validator performance data for trend analysis."""
        with self.db as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            historical_data = session.query(MetricsSnap).filter(
                MetricsSnap.netuid == netuid,
                MetricsSnap.timestamp >= cutoff_date
            ).order_by(MetricsSnap.timestamp).all()
            
            data = []
            for record in historical_data:
                data.append({
                    'timestamp': record.timestamp,
                    'active_validators': record.active_validators,
                    'validator_util_pct': record.validator_util_pct,
                    'emission_validators': record.emission_validators,
                    'tao_in_emission': record.tao_in_emission,
                    'consensus_alignment': record.consensus_alignment,
                    'stake_quality': record.stake_quality,
                    'mean_incentive': record.mean_incentive,
                    'stake_hhi': record.stake_hhi
                })
            
            return pd.DataFrame(data)
    
    def analyze_validator_trends(self, netuid: int) -> Dict[str, Any]:
        """Analyze historical trends for validator performance."""
        df = self.get_historical_validator_data(netuid, days_back=30)
        
        if df.empty:
            return {'trend_analysis': 'insufficient_data'}
        
        # Calculate trends
        trends = {}
        
        # Validator count trend
        if 'active_validators' in df.columns and df['active_validators'].notna().sum() > 1:
            validator_trend = np.polyfit(range(len(df)), df['active_validators'].fillna(0), 1)[0]
            trends['validator_growth_rate'] = validator_trend  # per day
        
        # Consensus alignment trend
        if 'consensus_alignment' in df.columns and df['consensus_alignment'].notna().sum() > 1:
            consensus_trend = np.polyfit(range(len(df)), df['consensus_alignment'].fillna(0), 1)[0]
            trends['consensus_trend'] = consensus_trend  # per day
        
        # Stake quality trend
        if 'stake_quality' in df.columns and df['stake_quality'].notna().sum() > 1:
            stake_trend = np.polyfit(range(len(df)), df['stake_quality'].fillna(0), 1)[0]
            trends['stake_quality_trend'] = stake_trend  # per day
        
        # Volatility analysis
        if 'active_validators' in df.columns:
            validator_volatility = df['active_validators'].std() if len(df) > 1 else 0
            trends['validator_volatility'] = validator_volatility
        
        # Stability score (inverse of volatility)
        trends['stability_score'] = max(0, 100 - (trends.get('validator_volatility', 0) * 10))
        
        return trends
    
    def calculate_realistic_earnings(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate realistic validator earnings based on historical data."""
        # Calculate daily validator emissions
        df['daily_validator_emission_tao'] = df['tao_in_emission'] * self.blocks_per_day * df['emission_validators']
        
        # Calculate earnings per validator (assuming equal distribution)
        df['daily_earnings_per_validator_tao'] = np.where(
            df['active_validators'] > 0,
            df['daily_validator_emission_tao'] / df['active_validators'],
            0
        )
        
        # Calculate annual earnings
        df['annual_earnings_per_validator_tao'] = df['daily_earnings_per_validator_tao'] * 365
        
        # Calculate USD earnings
        df['daily_earnings_per_validator_usd'] = df['daily_earnings_per_validator_tao'] * self.current_tao_price_usd
        df['annual_earnings_per_validator_usd'] = df['annual_earnings_per_validator_tao'] * self.current_tao_price_usd
        
        # Calculate ROI based on minimum stake requirements
        # Use stake quality to estimate minimum stake requirements
        df['estimated_min_stake'] = np.where(
            df['stake_quality'] > 80,
            1.0,  # High quality = low minimum stake
            np.where(
                df['stake_quality'] > 60,
                2.0,  # Medium quality = medium minimum stake
                5.0   # Low quality = high minimum stake
            )
        )
        
        df['validator_roi_annual'] = (df['annual_earnings_per_validator_tao'] / df['estimated_min_stake']) * 100
        
        return df
    
    def calculate_competition_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate competition and barrier-to-entry metrics."""
        # Validator utilization (lower = more room for new validators)
        df['validator_competition'] = 100 - df['validator_util_pct']
        
        # Stake concentration (HHI-based competition)
        df['stake_competition'] = 100 - df['stake_quality']
        
        # Incentive competition (based on incentive distribution)
        df['incentive_competition'] = np.where(
            df['p95_incentive'] > 0,
            (df['p95_incentive'] - df['mean_incentive']) / df['p95_incentive'] * 100,
            0
        )
        
        # Overall competition score (weighted average)
        df['competition_score'] = (
            df['validator_competition'] * 0.5 + 
            df['stake_competition'] * 0.3 +
            df['incentive_competition'] * 0.2
        )
        
        return df
    
    def calculate_risk_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate risk metrics for validator operation."""
        # Network health risk (consensus alignment)
        df['consensus_risk'] = 100 - df['consensus_alignment']
        
        # Stake quality risk (concentration)
        df['stake_risk'] = 100 - df['stake_quality']
        
        # Market risk (price volatility proxy)
        df['market_risk'] = np.where(
            df['buy_signal'] <= 2,
            50,  # High risk if buy signal is low
            np.where(
                df['buy_signal'] >= 4,
                10,  # Low risk if buy signal is high
                30   # Medium risk
            )
        )
        
        # Validator stability risk (based on utilization volatility)
        df['stability_risk'] = np.where(
            df['validator_util_pct'] > 90,
            40,  # High utilization = higher risk of being replaced
            np.where(
                df['validator_util_pct'] > 70,
                20,  # Medium utilization = moderate risk
                10   # Low utilization = low risk
            )
        )
        
        # Overall risk score
        df['risk_score'] = (
            df['consensus_risk'] * 0.25 +
            df['stake_risk'] * 0.25 +
            df['market_risk'] * 0.25 +
            df['stability_risk'] * 0.25
        )
        
        return df
    
    def calculate_opportunity_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate overall opportunity score for validators."""
        # Normalize metrics to 0-100 scale
        df['earnings_score'] = np.where(
            df['annual_earnings_per_validator_usd'] > 0,
            np.minimum(df['annual_earnings_per_validator_usd'] / 1000 * 100, 100),  # Cap at $1000/day
            0
        )
        
        df['growth_score'] = np.where(
            df['buy_signal'] >= 4,
            100,  # High growth potential
            np.where(
                df['buy_signal'] >= 3,
                70,  # Medium growth potential
                30   # Low growth potential
            )
        )
        
        df['stability_score'] = np.where(
            df['consensus_alignment'] >= 90,
            100,  # Very stable
            np.where(
                df['consensus_alignment'] >= 80,
                80,  # Stable
                np.where(
                    df['consensus_alignment'] >= 70,
                    60,  # Somewhat stable
                    40   # Unstable
                )
            )
        )
        
        # Expansion potential (room for new validators)
        df['expansion_potential'] = 100 - df['validator_util_pct']
        
        # Overall opportunity score
        df['opportunity_score'] = (
            df['earnings_score'] * 0.35 +
            df['growth_score'] * 0.25 +
            df['stability_score'] * 0.20 +
            df['expansion_potential'] * 0.20
        )
        
        return df
    
    def get_top_validator_opportunities(self, limit: int = 10) -> pd.DataFrame:
        """Get top validator opportunities ranked by opportunity score."""
        df = self.get_latest_subnet_data()
        
        if df.empty:
            print("No subnet data available")
            return pd.DataFrame()
        
        # Calculate all metrics
        df = self.calculate_realistic_earnings(df)
        df = self.calculate_competition_metrics(df)
        df = self.calculate_risk_metrics(df)
        df = self.calculate_opportunity_score(df)
        
        # Filter out subnets with no emissions or invalidators
        df = df[
            (df['emission_validators'] > 0) & 
            (df['active_validators'] > 0) &
            (df['daily_earnings_per_validator_tao'] > 0)
        ].copy()
        
        # Sort by opportunity score
        df = df.sort_values(by='opportunity_score', ascending=False).head(limit)
        
        return df
    
    def get_subnet_details(self, netuid: int) -> Dict[str, Any]:
        """Get detailed analysis for a specific subnet."""
        df = self.get_latest_subnet_data()
        subnet_data = df[df['netuid'] == netuid]
        
        if subnet_data.empty:
            return {"error": f"No data found for subnet {netuid}"}
        
        subnet = subnet_data.iloc[0]
        
        # Calculate detailed metrics
        df = self.calculate_realistic_earnings(df)
        df = self.calculate_competition_metrics(df)
        df = self.calculate_risk_metrics(df)
        df = self.calculate_opportunity_score(df)
        
        subnet_detailed = df[df['netuid'] == netuid].iloc[0]
        
        # Get historical trends
        trends = self.analyze_validator_trends(netuid)
        
        return {
            "netuid": int(netuid),
            "subnet_name": subnet['subnet_name'],
            "category": subnet['category'],
            "current_price_tao": subnet['price_tao'],
            "market_cap_tao": subnet['market_cap_tao'],
            "total_stake_tao": subnet['total_stake_tao'],
            
            # Validator metrics
            "active_validators": subnet['active_validators'],
            "max_validators": subnet['max_validators'],
            "validator_utilization_pct": subnet['validator_util_pct'],
            "room_for_new_validators": 100 - subnet['validator_util_pct'],
            
            # Earnings potential
            "daily_earnings_per_validator_tao": subnet_detailed['daily_earnings_per_validator_tao'],
            "annual_earnings_per_validator_tao": subnet_detailed['annual_earnings_per_validator_tao'],
            "daily_earnings_per_validator_usd": subnet_detailed['daily_earnings_per_validator_usd'],
            "annual_earnings_per_validator_usd": subnet_detailed['annual_earnings_per_validator_usd'],
            "validator_roi_annual_pct": subnet_detailed['validator_roi_annual'],
            "estimated_min_stake": subnet_detailed['estimated_min_stake'],
            
            # Competition analysis
            "competition_score": subnet_detailed['competition_score'],
            "validator_competition": subnet_detailed['validator_competition'],
            "stake_competition": subnet_detailed['stake_competition'],
            "incentive_competition": subnet_detailed['incentive_competition'],
            
            # Risk assessment
            "risk_score": subnet_detailed['risk_score'],
            "consensus_risk": subnet_detailed['consensus_risk'],
            "stake_risk": subnet_detailed['stake_risk'],
            "market_risk": subnet_detailed['market_risk'],
            "stability_risk": subnet_detailed['stability_risk'],
            
            # Quality metrics
            "stake_quality": subnet['stake_quality'],
            "consensus_alignment": subnet['consensus_alignment'],
            "trust_score": subnet['trust_score'],
            "tao_score": subnet['tao_score'],
            "buy_signal": subnet['buy_signal'],
            
            # Opportunity score
            "opportunity_score": subnet_detailed['opportunity_score'],
            "earnings_score": subnet_detailed['earnings_score'],
            "growth_score": subnet_detailed['growth_score'],
            "stability_score": subnet_detailed['stability_score'],
            "expansion_potential": subnet_detailed['expansion_potential'],
            
            # Historical trends
            "trends": trends,
            
            "last_updated": subnet['timestamp'].isoformat() if subnet['timestamp'] else None
        }
    
    def generate_enhanced_report(self) -> str:
        """Generate a comprehensive business case report using SDK data."""
        top_opportunities = self.get_top_validator_opportunities(10)
        
        if top_opportunities.empty:
            return "No validator opportunities found in current data."
        
        report = []
        report.append("# Enhanced Bittensor Validator Business Case Analysis")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Data Source: Existing SDK collection from database")
        report.append(f"Current TAO Price: ${self.current_tao_price_usd}")
        report.append("")
        
        # Executive Summary
        report.append("## Executive Summary")
        report.append("")
        report.append("This analysis uses real SDK data collected from the Bittensor network to identify")
        report.append("the top 10 subnets for running validators. The analysis includes:")
        report.append("- Real earnings potential based on actual emission data")
        report.append("- Competition analysis using stake distribution and incentive patterns")
        report.append("- Risk assessment based on network health metrics")
        report.append("- Historical trends and stability analysis")
        report.append("- Entry barrier assessment")
        report.append("")
        
        # Top Opportunities Table
        report.append("## Top 10 Validator Opportunities (Based on SDK Data)")
        report.append("")
        report.append("| Rank | Subnet | Name | Category | Annual Earnings | ROI | Competition | Risk | Score |")
        report.append("|------|--------|------|----------|-----------------|-----|-------------|------|-------|")
        
        for i, (idx, row) in enumerate(top_opportunities.iterrows(), 1):
            report.append(
                f"| {i} | {row['netuid']} | {row['subnet_name']} | {row['category']} | "
                f"${row['annual_earnings_per_validator_usd']:.0f} | {row['validator_roi_annual']:.1f}% | "
                f"{row['competition_score']:.0f} | {row['risk_score']:.0f} | {row['opportunity_score']:.0f} |"
            )
        
        report.append("")
        
        # Detailed Analysis
        report.append("## Detailed Analysis")
        report.append("")
        
        for i, (idx, row) in enumerate(top_opportunities.iterrows(), 1):
            report.append(f"### {i}. Subnet {row['netuid']}: {row['subnet_name']}")
            report.append("")
            report.append(f"**Category:** {row['category']}")
            report.append(f"**Current Price:** {row['price_tao']:.3f} TAO")
            report.append(f"**Market Cap:** {row['market_cap_tao']:,.0f} TAO")
            report.append("")
            
            report.append("**Earnings Potential (Based on SDK Data):**")
            report.append(f"- Daily earnings per validator: {row['daily_earnings_per_validator_tao']:.6f} TAO (${row['daily_earnings_per_validator_usd']:.2f})")
            report.append(f"- Annual earnings per validator: {row['annual_earnings_per_validator_tao']:.2f} TAO (${row['annual_earnings_per_validator_usd']:.0f})")
            report.append(f"- Annual ROI: {row['validator_roi_annual']:.1f}%")
            report.append(f"- Estimated minimum stake: {row['estimated_min_stake']:.1f} TAO")
            report.append("")
            
            report.append("**Competition Analysis:**")
            report.append(f"- Active validators: {row['active_validators']}/{row['max_validators']}")
            report.append(f"- Validator utilization: {row['validator_util_pct']:.1f}%")
            report.append(f"- Room for new validators: {100 - row['validator_util_pct']:.1f}%")
            report.append(f"- Competition score: {row['competition_score']:.0f}/100")
            report.append(f"- Stake concentration (HHI): {row['stake_hhi']:.0f}")
            report.append("")
            
            report.append("**Risk Assessment:**")
            report.append(f"- Consensus alignment: {row['consensus_alignment']:.1f}%")
            report.append(f"- Stake quality: {row['stake_quality']:.1f}/100")
            report.append(f"- Buy signal: {row['buy_signal']}/5")
            report.append(f"- Risk score: {row['risk_score']:.0f}/100")
            report.append("")
            
            report.append("**Opportunity Score Breakdown:**")
            report.append(f"- Earnings score: {row['earnings_score']:.0f}/100")
            report.append(f"- Growth score: {row['growth_score']:.0f}/100")
            report.append(f"- Stability score: {row['stability_score']:.0f}/100")
            report.append(f"- Expansion potential: {row['expansion_potential']:.0f}/100")
            report.append(f"- Overall opportunity: {row['opportunity_score']:.0f}/100")
            report.append("")
            
            report.append("**Business Case:**")
            if row['competition_score'] < 30:
                report.append("- Low competition makes this an excellent entry point for new validators.")
            elif row['competition_score'] < 60:
                report.append("- Moderate competition with good earnings potential.")
            else:
                report.append("- High competition but still profitable for skilled validators.")
            
            if row['risk_score'] < 20:
                report.append("- Low risk subnet with stable network conditions.")
            elif row['risk_score'] < 40:
                report.append("- Moderate risk with good potential returns.")
            else:
                report.append("- Higher risk subnet requiring careful monitoring.")
            
            report.append("")
            report.append("---")
            report.append("")
        
        # Investment Requirements
        report.append("## Investment Requirements")
        report.append("")
        report.append("**Minimum Requirements:**")
        report.append("- Hardware: Raspberry Pi 4 or equivalent (~$50-100)")
        report.append("- Internet: Stable broadband connection")
        report.append("- Stake: Varies by subnet (see analysis above)")
        report.append("- Technical knowledge: Basic Linux/command line")
        report.append("")
        
        report.append("**Recommended Setup:**")
        report.append("- Hardware: Dedicated server or high-end Pi 4")
        report.append("- Stake: 5-10 TAO for better earnings")
        report.append("- Monitoring: Automated alerts and backup")
        report.append("- Security: Cold storage for keys, secure validator setup")
        report.append("")
        
        # Risk Factors
        report.append("## Risk Factors")
        report.append("")
        report.append("**Technical Risks:**")
        report.append("- Network downtime or validator slashing")
        report.append("- Hardware failures")
        report.append("- Software bugs or updates")
        report.append("")
        
        report.append("**Market Risks:**")
        report.append("- TAO price volatility")
        report.append("- Subnet performance changes")
        report.append("- Competition increases")
        report.append("")
        
        report.append("**Network Risks:**")
        report.append("- Consensus alignment changes")
        report.append("- Stake quality degradation")
        report.append("- Emission split modifications")
        report.append("")
        
        # Recommendations
        report.append("## Recommendations")
        report.append("")
        report.append("**For Beginners:**")
        report.append("1. Start with subnets having low competition scores (< 30)")
        report.append("2. Use estimated minimum stake requirements")
        report.append("3. Focus on subnets with high consensus alignment (> 80%)")
        report.append("4. Monitor performance and adjust strategy")
        report.append("")
        
        report.append("**For Experienced Users:**")
        report.append("1. Target subnets with high earnings potential and moderate risk")
        report.append("2. Diversify across multiple subnets")
        report.append("3. Optimize for highest ROI opportunities")
        report.append("4. Consider running multiple validators")
        report.append("")
        
        report.append("**For Institutional Investors:**")
        report.append("1. Focus on subnets with high stake quality and stability")
        report.append("2. Implement robust monitoring and security")
        report.append("3. Consider staking larger amounts for economies of scale")
        report.append("4. Monitor regulatory developments")
        report.append("")
        
        return "\n".join(report)

def main():
    """Main function to run the enhanced validator analysis."""
    analyzer = EnhancedValidatorAnalysis()
    
    print("🔍 Enhanced Bittensor Validator Analysis")
    print("=" * 50)
    print("Using existing SDK data collection for accurate business case analysis")
    print("")
    
    # Get top opportunities
    print("\n📊 Top 10 Validator Opportunities (Based on SDK Data):")
    print("-" * 50)
    
    opportunities = analyzer.get_top_validator_opportunities(10)
    
    if opportunities.empty:
        print("No validator opportunities found in current data.")
        return
    
    # Display summary table
    print(f"{'Rank':<4} {'Subnet':<6} {'Name':<20} {'Annual $':<10} {'ROI %':<6} {'Competition':<12} {'Risk':<6} {'Score':<6}")
    print("-" * 80)
    
    for i, (idx, row) in enumerate(opportunities.iterrows(), 1):
        print(f"{i:<4} {row['netuid']:<6} {row['subnet_name'][:18]:<20} "
              f"${row['annual_earnings_per_validator_usd']:<9.0f} {row['validator_roi_annual']:<5.1f} "
              f"{row['competition_score']:<11.0f} {row['risk_score']:<5.0f} {row['opportunity_score']:<5.0f}")
    
    # Generate detailed report
    print("\n📋 Generating enhanced business case report...")
    report = analyzer.generate_enhanced_report()
    
    # Save report to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"enhanced_validator_analysis_{timestamp}.md"
    
    with open(filename, 'w') as f:
        f.write(report)
    
    print(f"✅ Enhanced report saved to: {filename}")
    
    # Show top 3 detailed analysis
    print("\n🔍 Detailed Analysis - Top 3 Opportunities:")
    print("=" * 60)
    
    for i in range(min(3, len(opportunities))):
        netuid = opportunities.iloc[i]['netuid']
        details = analyzer.get_subnet_details(netuid)
        
        print(f"\n{i+1}. Subnet {netuid}: {details['subnet_name']}")
        print(f"   Category: {details['category']}")
        print(f"   Annual Earnings: ${details['annual_earnings_per_validator_usd']:.0f} ({details['validator_roi_annual_pct']:.1f}% ROI)")
        print(f"   Min Stake Required: {details['estimated_min_stake']:.1f} TAO")
        print(f"   Competition: {details['competition_score']:.0f}/100 (Room for {details['room_for_new_validators']:.1f}% more validators)")
        print(f"   Risk: {details['risk_score']:.0f}/100 (Consensus: {details['consensus_alignment']:.1f}%, Stake Quality: {details['stake_quality']:.1f})")
        print(f"   Opportunity Score: {details['opportunity_score']:.0f}/100")

if __name__ == "__main__":
    main() 