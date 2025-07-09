"""
Clean Correlation Analysis Service for TAO Analytics.
Focuses purely on statistical correlation analysis between metrics.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from scipy import stats
from services.db import get_db
from models import MetricsSnap

logger = logging.getLogger(__name__)

# Statistical thresholds
MIN_CORRELATION = 0.3
MAX_P_VALUE = 0.05
Z_SCORE_THRESHOLD = 2.0

class CorrelationAnalysisService:
    """Service for clean statistical correlation analysis."""
    
    def __init__(self):
        """Initialize the correlation analysis service."""
        pass
    
    def get_correlation_analysis(self, days_back: int = 2, selected_subnet: Optional[str] = None) -> Dict[str, Any]:
        """
        Get clean correlation analysis for metrics.
        
        Args:
            days_back: Number of days of data to analyze
            selected_subnet: Specific subnet to analyze, or None for network-wide
            
        Returns:
            Dictionary with correlation analysis results
        """
        try:
            # Get data
            df = self._get_analysis_data(days_back, selected_subnet)
            if df.empty:
                return {
                    'success': False,
                    'error': 'No data available for analysis',
                    'correlation_matrix': None,
                    'significant_correlations': [],
                    'outliers': [],
                    'summary_stats': {}
                }
            
            # Calculate correlations
            correlation_matrix = self._calculate_correlation_matrix(df)
            significant_correlations = self._find_significant_correlations(df)
            outliers = self._detect_outliers(df)
            summary_stats = self._calculate_summary_stats(df)
            
            return {
                'success': True,
                'correlation_matrix': correlation_matrix,
                'significant_correlations': significant_correlations,
                'outliers': outliers,
                'summary_stats': summary_stats,
                'data_points': len(df),
                'metrics_analyzed': len(correlation_matrix.columns) if correlation_matrix is not None else 0
            }
            
        except Exception as e:
            logger.error(f"Error in correlation analysis: {e}")
            return {
                'success': False,
                'error': f'Analysis error: {str(e)}',
                'correlation_matrix': None,
                'significant_correlations': [],
                'outliers': [],
                'summary_stats': {}
            }
    
    def _get_analysis_data(self, days_back: int, selected_subnet: Optional[str] = None) -> pd.DataFrame:
        """Get data for correlation analysis."""
        session = get_db()
        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            # Build query based on analysis type
            # Use database-agnostic approach to avoid PostgreSQL parameter binding issues
            from config import ACTIVE_DATABASE_URL
            
            if selected_subnet and selected_subnet != "all":
                # Per-subnet time-series analysis - get more data for meaningful correlations
                if 'postgresql' in ACTIVE_DATABASE_URL:
                    # PostgreSQL syntax with direct date arithmetic
                    sql = f"""
                        SELECT 
                            netuid, subnet_name, category, timestamp,
                            -- Core metrics
                            tao_score, stake_quality, buy_signal, emission_roi, trust_score,
                            -- Market metrics
                            market_cap_tao, fdv_tao, price_tao, price_1d_change, price_7d_change, 
                            price_30d_change, price_1h_change, flow_24h, ath_60d, atl_60d,
                            -- Volume metrics
                            buy_volume_tao_1d, sell_volume_tao_1d, total_volume_tao_1d,
                            buy_vol_tao_1d, sell_vol_tao_1d, buy_sell_ratio,
                            net_volume_tao_1h, net_volume_tao_7d, total_volume_pct_change,
                            -- Network metrics
                            active_validators, validators_active, validator_util_pct, 
                            total_stake_tao, max_validators, uid_count, active_stake_ratio,
                            -- Stake metrics
                            stake_hhi, gini_coeff_top_100, hhi, stake_quality_rank_pct,
                            -- Flow metrics
                            reserve_momentum, tao_in, alpha_circ, alpha_prop, root_prop,
                            alpha_in, alpha_out, emission_pct, alpha_emitted_pct,
                            -- Consensus metrics
                            consensus_alignment, mean_consensus, pct_aligned, confidence,
                            mean_incentive, p95_incentive,
                            -- Emission metrics
                            emission_owner, emission_miners, emission_validators,
                            total_emission_tao, tao_in_emission, alpha_out_emission,
                            realized_pnl_tao, unrealized_pnl_tao,
                            -- Performance metrics
                            momentum_rank_pct
                        FROM metrics_snap 
                        WHERE timestamp >= NOW() - INTERVAL '{days_back} days'
                        AND netuid = {int(selected_subnet)}
                        ORDER BY timestamp DESC
                        LIMIT 5000
                    """
                    df = pd.read_sql(sql, session.bind)
                else:
                    # SQLite syntax with parameters
                    sql = """
                        SELECT 
                            netuid, subnet_name, category, timestamp,
                            -- Core metrics
                            tao_score, stake_quality, buy_signal, emission_roi, trust_score,
                            -- Market metrics
                            market_cap_tao, fdv_tao, price_tao, price_1d_change, price_7d_change, 
                            price_30d_change, price_1h_change, flow_24h, ath_60d, atl_60d,
                            -- Volume metrics
                            buy_volume_tao_1d, sell_volume_tao_1d, total_volume_tao_1d,
                            buy_vol_tao_1d, sell_vol_tao_1d, buy_sell_ratio,
                            net_volume_tao_1h, net_volume_tao_7d, total_volume_pct_change,
                            -- Network metrics
                            active_validators, validators_active, validator_util_pct, 
                            total_stake_tao, max_validators, uid_count, active_stake_ratio,
                            -- Stake metrics
                            stake_hhi, gini_coeff_top_100, hhi, stake_quality_rank_pct,
                            -- Flow metrics
                            reserve_momentum, tao_in, alpha_circ, alpha_prop, root_prop,
                            alpha_in, alpha_out, emission_pct, alpha_emitted_pct,
                            -- Consensus metrics
                            consensus_alignment, mean_consensus, pct_aligned, confidence,
                            mean_incentive, p95_incentive,
                            -- Emission metrics
                            emission_owner, emission_miners, emission_validators,
                            total_emission_tao, tao_in_emission, alpha_out_emission,
                            realized_pnl_tao, unrealized_pnl_tao,
                            -- Performance metrics
                            momentum_rank_pct
                        FROM metrics_snap 
                        WHERE timestamp >= :cutoff_date
                        AND netuid = :netuid
                        ORDER BY timestamp DESC
                        LIMIT 5000
                    """
                    df = pd.read_sql(sql, session.bind, params={
                        'cutoff_date': cutoff_date,
                        'netuid': int(selected_subnet)
                    })
            else:
                # Network-wide analysis (latest data per subnet)
                if 'postgresql' in ACTIVE_DATABASE_URL:
                    # PostgreSQL syntax with direct date arithmetic
                    sql = f"""
                        SELECT m1.*
                        FROM metrics_snap m1
                        INNER JOIN (
                            SELECT netuid, MAX(timestamp) as max_timestamp
                            FROM metrics_snap
                            WHERE timestamp >= NOW() - INTERVAL '{days_back} days'
                            GROUP BY netuid
                        ) m2 ON m1.netuid = m2.netuid AND m1.timestamp = m2.max_timestamp
                        ORDER BY m1.netuid
                        LIMIT 200
                    """
                    df = pd.read_sql(sql, session.bind)
                else:
                    # SQLite syntax with parameters
                    sql = """
                        SELECT m1.*
                        FROM metrics_snap m1
                        INNER JOIN (
                            SELECT netuid, MAX(timestamp) as max_timestamp
                            FROM metrics_snap
                            WHERE timestamp >= :cutoff_date
                            GROUP BY netuid
                        ) m2 ON m1.netuid = m2.netuid AND m1.timestamp = m2.max_timestamp
                        ORDER BY m1.netuid
                        LIMIT 200
                    """
                    df = pd.read_sql(sql, session.bind, params={
                        'cutoff_date': cutoff_date
                    })
            
            # Ensure timestamp is properly converted
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            return df
            
        finally:
            session.close()
    
    def _calculate_correlation_matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate correlation matrix for available metrics."""
        # Define comprehensive metric categories
        core_metrics = ['tao_score', 'stake_quality', 'buy_signal', 'emission_roi', 'trust_score']
        
        # Market & Price metrics
        market_metrics = [
            'market_cap_tao', 'fdv_tao', 'price_tao', 'price_1d_change', 'price_7d_change', 
            'price_30d_change', 'price_1h_change', 'flow_24h', 'ath_60d', 'atl_60d'
        ]
        
        # Volume & Trading metrics
        volume_metrics = [
            'buy_volume_tao_1d', 'sell_volume_tao_1d', 'total_volume_tao_1d',
            'buy_vol_tao_1d', 'sell_vol_tao_1d', 'buy_sell_ratio',
            'net_volume_tao_1h', 'net_volume_tao_7d', 'total_volume_pct_change'
        ]
        
        # Network & Validator metrics
        network_metrics = [
            'active_validators', 'validators_active', 'validator_util_pct', 
            'total_stake_tao', 'max_validators', 'uid_count', 'active_stake_ratio'
        ]
        
        # Stake distribution metrics
        stake_metrics = [
            'stake_hhi', 'gini_coeff_top_100', 'hhi', 'stake_quality_rank_pct'
        ]
        
        # Token flow & Emission metrics
        flow_metrics = [
            'reserve_momentum', 'tao_in', 'alpha_circ', 'alpha_prop', 'root_prop',
            'alpha_in', 'alpha_out', 'emission_pct', 'alpha_emitted_pct'
        ]
        
        # Consensus & Incentive metrics
        consensus_metrics = [
            'consensus_alignment', 'mean_consensus', 'pct_aligned', 'confidence',
            'mean_incentive', 'p95_incentive'
        ]
        
        # Emission & PnL metrics
        emission_metrics = [
            'emission_owner', 'emission_miners', 'emission_validators',
            'total_emission_tao', 'tao_in_emission', 'alpha_out_emission',
            'realized_pnl_tao', 'unrealized_pnl_tao'
        ]
        
        # Performance & Momentum metrics
        performance_metrics = [
            'momentum_rank_pct'
        ]
        
        all_metrics = (core_metrics + market_metrics + volume_metrics + network_metrics + 
                      stake_metrics + flow_metrics + consensus_metrics + emission_metrics + 
                      performance_metrics)
        
        # Filter to available columns
        available_cols = [col for col in all_metrics if col in df.columns]
        
        if len(available_cols) < 2:
            return pd.DataFrame()
        
        # Calculate correlation matrix
        corr_matrix = df[available_cols].corr()
        
        return corr_matrix
    
    def _find_significant_correlations(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Find statistically significant correlations."""
        corr_matrix = self._calculate_correlation_matrix(df)
        if corr_matrix.empty:
            return []
        
        significant_pairs = []
        
        # Get upper triangle of correlation matrix
        upper_triangle = np.triu(np.ones(corr_matrix.shape), k=1)
        
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                metric1 = corr_matrix.columns[i]
                metric2 = corr_matrix.columns[j]
                correlation = corr_matrix.iloc[i, j]
                
                # Skip if correlation is NaN
                if pd.isna(correlation):
                    continue
                
                # Calculate p-value using scipy
                try:
                    # Get non-null values for both metrics
                    valid_data = df[[metric1, metric2]].dropna()
                    if len(valid_data) < 3:  # Need at least 3 data points
                        continue
                    
                    # Calculate correlation and p-value
                    corr_coef, p_value = stats.pearsonr(valid_data[metric1], valid_data[metric2])
                    
                    # Check if correlation is significant
                    if abs(corr_coef) >= MIN_CORRELATION and p_value <= MAX_P_VALUE:
                        significant_pairs.append({
                            'metric1': metric1,
                            'metric2': metric2,
                            'correlation': round(corr_coef, 3),
                            'p_value': round(p_value, 4),
                            'sample_size': len(valid_data),
                            'strength': 'Strong' if abs(corr_coef) >= 0.7 else 'Moderate' if abs(corr_coef) >= 0.5 else 'Weak'
                        })
                except Exception as e:
                    logger.warning(f"Error calculating p-value for {metric1} vs {metric2}: {e}")
                    continue
        
        # Sort by absolute correlation value
        significant_pairs.sort(key=lambda x: abs(x['correlation']), reverse=True)
        
        return significant_pairs[:20]  # Return top 20 significant correlations
    
    def _detect_outliers(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect statistical outliers in the data."""
        outliers = []
        
        # Define metrics to check for outliers
        outlier_metrics = ['tao_score', 'stake_quality', 'market_cap_tao', 'total_stake_tao', 'active_validators']
        
        for metric in outlier_metrics:
            if metric not in df.columns:
                continue
            
            # Get non-null values
            values = df[metric].dropna()
            if len(values) < 3:
                continue
            
            # Calculate z-scores
            z_scores = np.abs(stats.zscore(values))
            
            # Find outliers
            outlier_indices = np.where(z_scores > Z_SCORE_THRESHOLD)[0]
            
            for idx in outlier_indices:
                original_idx = values.index[idx]
                row = df.loc[original_idx]
                
                outliers.append({
                    'subnet_name': row.get('subnet_name', 'Unknown'),
                    'netuid': row.get('netuid', 'Unknown'),
                    'metric': metric,
                    'value': round(float(values.iloc[idx]), 2),
                    'z_score': round(float(z_scores[idx]), 2),
                    'mean': round(float(values.mean()), 2),
                    'std': round(float(values.std()), 2)
                })
        
        # Sort by z-score
        outliers.sort(key=lambda x: x['z_score'], reverse=True)
        
        return outliers[:15]  # Return top 15 outliers
    
    def _calculate_summary_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate summary statistics for the dataset."""
        summary = {
            'total_subnets': len(df),
            'unique_subnets': df['netuid'].nunique() if 'netuid' in df.columns else 0,
            'date_range': {
                'start': df['timestamp'].min().isoformat() if 'timestamp' in df.columns else None,
                'end': df['timestamp'].max().isoformat() if 'timestamp' in df.columns else None
            }
        }
        
        # Add metric-specific statistics
        key_metrics = ['tao_score', 'stake_quality', 'market_cap_tao', 'total_stake_tao']
        
        for metric in key_metrics:
            if metric in df.columns:
                values = df[metric].dropna()
                if len(values) > 0:
                    summary[metric] = {
                        'mean': round(float(values.mean()), 2),
                        'median': round(float(values.median()), 2),
                        'std': round(float(values.std()), 2),
                        'min': round(float(values.min()), 2),
                        'max': round(float(values.max()), 2),
                        'count': len(values)
                    }
        
        return summary

# Global service instance
correlation_service = CorrelationAnalysisService() 