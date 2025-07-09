"""
Landing Page Insights Service for TAO Analytics.
Generates dynamic cards for the landing page based on correlation analysis data.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from services.db import get_db, load_screener_frame
from services.correlation_analysis import correlation_service
from models import SubnetMeta
import logging

logger = logging.getLogger(__name__)

class LandingPageInsightsService:
    """Service for generating dynamic landing page insights."""
    
    # Configuration for metric weights and thresholds
    METRIC_WEIGHTS = {
        "tao_score": 0.30,
        "stake_quality": 0.20,
        "price_7d_change": 0.20,
        "flow_turnover": 0.15,
        "validator_ratio": 0.05,  # Reduced from 0.15 due to low variance impact
    }
    
    # Emission farming detection configuration
    FARMER_WEIGHTS = {
        'emission_roi': 0.20,
        'stake_quality': 0.15,
        'validator_util_pct': 0.15,
        'flow_turnover': 0.15,
        'stake_hhi': 0.20,
        'price_30d_change': 0.15,
    }
    
    # Weights when emission ROI is not available
    FARMER_WEIGHTS_NO_ROI = {
        'stake_quality': 0.1875,
        'validator_util_pct': 0.1875,
        'flow_turnover': 0.1875,
        'stake_hhi': 0.25,
        'price_30d_change': 0.1875,
    }
    
    # Constants for synthetic emission calculation
    # Based on Bittensor's current 12-second block time
    AVG_BLOCK_TIME = 12  # seconds
    BLOCKS_PER_DAY = int(86400 / AVG_BLOCK_TIME)  # 7200 blocks per day
    
    # TODO: After first halving (~Nov 2025), fetch per-block emission from chain state
    # Current: 1 TAO per block total, split across all subnets
    # Post-halving: Will be 0.5 TAO per block, requiring dynamic adjustment
    
    # Outlier detection thresholds
    OUTLIER_THRESHOLD = 2.0  # Z-score threshold
    MAX_ROBUST_Z_SCORE = 8.0  # Cap extreme z-scores to prevent scaling issues (±8σ covers 99.999999% of normal dist.)
    MIN_SAMPLE_SIZE = 8  # Minimum samples for statistical calculations
    
    # Emission farming thresholds
    FARMER_WATCHLIST_THRESHOLD = 1.00  # Adjusted for current data distribution
    FARMER_REDFLAG_THRESHOLD = 1.30    # Adjusted for current data distribution
    
    def __init__(self):
        """Initialize the landing page insights service."""
        pass
    
    def get_landing_page_insights(self) -> Dict[str, Any]:
        """
        Get comprehensive insights for the landing page.
        
        Returns:
            Dictionary with landing page insights
        """
        try:
            # Get latest data
            df = load_screener_frame()
            if df.empty:
                return self._get_fallback_insights()
            
            # Preprocess and normalize data
            df = self._preprocess_data(df)
            
            # Get enrichment data
            enrichment_data = self._get_enrichment_data()
            
            # Generate insights
            insights = {
                'hot_subnets': self._get_hot_subnets(df),
                'outliers': self._get_outliers(df),
                'price_momentum': self._get_price_momentum(df),
                'hot_categories': self._get_hot_categories(df, enrichment_data),
                'farmer_watchlist': self._get_farmer_watchlist(df),
                'farmer_redflags': self._get_farmer_redflags(df),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M UTC'),
                'data_available': True
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating landing page insights: {e}")
            return self._get_fallback_insights()
    
    def _preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess and normalize data for analysis.
        
        Key transformations:
        1. Flow turnover calculation: flow_24h / market_cap_tao
        2. Log1p transform on flow_turnover to handle heavy-tailed distribution
        3. Validator ratio calculation: active_validators / max_validators
        4. Winsorization: Clip values at 1% and 99% percentiles
        5. Z-score normalization: (value - mean) / std
        """
        if df.empty:
            return df
        
        # Create a copy to avoid modifying original
        df = df.copy()
        
        # Calculate flow turnover (flow / market cap) for better scaling
        df['flow_turnover'] = np.where(
            (df['flow_24h'].notna()) & (df['market_cap_tao'].fillna(0) > 0),
            df['flow_24h'] / df['market_cap_tao'],
            0
        )
        
        # Apply log1p transform to flow_turnover to handle heavy-tailed distribution
        # This prevents extreme z-scores while preserving relative differences
        df['flow_turnover_log1p'] = np.log1p(np.abs(df['flow_turnover'])) * np.sign(df['flow_turnover'])
        
        # Calculate validator ratio
        df['validator_ratio'] = np.where(
            (df['active_validators'].notna()) & (df['max_validators'] > 0),
            df['active_validators'] / df['max_validators'],
            0
        )
        
        # Winsorize extreme values (1% and 99% percentiles)
        numeric_columns = ['tao_score', 'stake_quality', 'price_7d_change', 'flow_turnover_log1p', 'validator_ratio']
        
        for col in numeric_columns:
            if col in df.columns and df[col].notna().sum() >= self.MIN_SAMPLE_SIZE:
                # Winsorize at 1% and 99% percentiles
                lower_bound = df[col].quantile(0.01)
                upper_bound = df[col].quantile(0.99)
                df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)
        
        # Z-score normalization for each metric
        for col in numeric_columns:
            if col in df.columns and df[col].notna().sum() >= self.MIN_SAMPLE_SIZE:
                mean_val = df[col].mean()
                std_val = df[col].std()
                if std_val > 0:
                    df[f'{col}_z'] = (df[col] - mean_val) / std_val
                else:
                    df[f'{col}_z'] = 0
            else:
                df[f'{col}_z'] = 0
        
        # Map flow_turnover_log1p_z back to flow_turnover_z for compatibility
        df['flow_turnover_z'] = df['flow_turnover_log1p_z']
        
        # Calculate emission farming metrics
        df = self._calculate_farmer_metrics(df)
        
        return df
    
    def _calculate_farmer_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate emission farming detection metrics.
        
        Synthetic emission ROI calculation:
        - Assumes stable emission share per subnet across 7200 blocks per day
        - Uses tao_in_emission × BLOCKS_PER_DAY as daily emission estimate
        - Falls back to total_emission_tao if tao_in_emission unavailable
        """
        if df.empty:
            return df
        
        # Calculate synthetic emission ROI from single-block data
        if 'tao_in_emission' in df.columns and df['tao_in_emission'].notna().sum() > 0:
            # Synthetic daily emission = tao_in_emission × BLOCKS_PER_DAY
            # Assumes emission share per subnet is roughly stable intra-day
            df['daily_emission_tao'] = df['tao_in_emission'] * self.BLOCKS_PER_DAY
            # Handle division by zero and invalid values
            df['emission_roi'] = np.where(
                (df['total_stake_tao'] > 0) & (df['daily_emission_tao'] > 0),
                df['daily_emission_tao'] / df['total_stake_tao'],
                np.nan
            )
        elif 'total_emission_tao' in df.columns and df['total_emission_tao'].notna().sum() > 0:
            # Fallback: use total_emission_tao if tao_in_emission not available
            df['daily_emission_tao'] = df['total_emission_tao'] * self.BLOCKS_PER_DAY
            df['emission_roi'] = np.where(
                (df['total_stake_tao'] > 0) & (df['daily_emission_tao'] > 0),
                df['daily_emission_tao'] / df['total_stake_tao'],
                np.nan
            )
        else:
            # Fallback: use existing emission_roi if available, otherwise NaN
            df['emission_roi'] = df.get('emission_roi', np.nan)
        
        # Pre-process farmer metrics with winsorization
        farmer_metrics = [
            'emission_roi', 'stake_quality', 'validator_util_pct', 
            'flow_turnover', 'stake_hhi', 'price_30d_change'
        ]
        
        for metric in farmer_metrics:
            if metric in df.columns and df[metric].notna().sum() >= self.MIN_SAMPLE_SIZE:
                # Winsorize at 1% and 99% percentiles
                lower_bound = df[metric].quantile(0.01)
                upper_bound = df[metric].quantile(0.99)
                df[metric] = df[metric].clip(lower=lower_bound, upper=upper_bound)
        
        # Z-score normalization for farmer metrics
        for metric in farmer_metrics:
            if metric in df.columns and df[metric].notna().sum() >= self.MIN_SAMPLE_SIZE:
                mean_val = df[metric].mean()
                std_val = df[metric].std()
                if std_val > 0:
                    df[f'{metric}_z'] = (df[metric] - mean_val) / std_val
                else:
                    df[f'{metric}_z'] = 0
            else:
                df[f'{metric}_z'] = 0
        
        # Create negative z-scores for metrics where lower values indicate higher risk
        for metric in ['stake_quality', 'validator_util_pct', 'flow_turnover', 'price_30d_change']:
            if f'{metric}_z' in df.columns:
                df[f'{metric}_z_neg'] = -df[f'{metric}_z']
        
        # Calculate farmer score
        df = self._calculate_farmer_score(df)
        
        return df
    
    def _calculate_farmer_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate emission farming risk score."""
        if df.empty:
            return df
        
        # Check if emission ROI is available
        emission_roi_available = bool(df['emission_roi'].notna().sum() > 0)
        
        if emission_roi_available:
            weights = self.FARMER_WEIGHTS
            # Use 6-factor scoring with emission ROI
            df['farmer_score'] = (
                df['emission_roi_z'].fillna(0) * weights['emission_roi'] +
                df['stake_quality_z_neg'].fillna(0) * weights['stake_quality'] +
                df['validator_util_pct_z_neg'].fillna(0) * weights['validator_util_pct'] +
                df['flow_turnover_z_neg'].fillna(0) * weights['flow_turnover'] +
                df['stake_hhi_z'].fillna(0) * weights['stake_hhi'] +
                df['price_30d_change_z_neg'].fillna(0) * weights['price_30d_change']
            )
        else:
            weights = self.FARMER_WEIGHTS_NO_ROI
            # Use 5-factor scoring without emission ROI
            df['farmer_score'] = (
                df['stake_quality_z_neg'].fillna(0) * weights['stake_quality'] +
                df['validator_util_pct_z_neg'].fillna(0) * weights['validator_util_pct'] +
                df['flow_turnover_z_neg'].fillna(0) * weights['flow_turnover'] +
                df['stake_hhi_z'].fillna(0) * weights['stake_hhi'] +
                df['price_30d_change_z_neg'].fillna(0) * weights['price_30d_change']
            )
        
        return df
    
    def _get_farmer_watchlist(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Get subnets on emission farming watchlist (farmer_score > 1.50)."""
        if df.empty or 'farmer_score' not in df.columns:
            return []
        
        # Filter for watchlist threshold
        watchlist_df = df[df['farmer_score'] > self.FARMER_WATCHLIST_THRESHOLD].copy()
        
        if watchlist_df.empty:
            return []
        
        # Sort by farmer score and get top 3
        watchlist_df = watchlist_df.nlargest(3, 'farmer_score')
        
        watchlist = []
        for _, subnet in watchlist_df.iterrows():
            # Get the three worst-contributing metrics
            worst_metrics = self._get_worst_contributing_metrics(subnet)
            
            watchlist.append({
                'netuid': int(subnet['netuid']),
                'name': subnet['subnet_name'],
                'farmer_score': round(float(subnet['farmer_score']), 2),
                'worst_metrics': worst_metrics,
                'category': subnet.get('primary_category', 'Unknown')
            })
        
        return watchlist
    
    def _get_farmer_redflags(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Get subnets with red flag emission farming signals (farmer_score > 2.50)."""
        if df.empty or 'farmer_score' not in df.columns:
            return []
        
        # Filter for red flag threshold
        redflag_df = df[df['farmer_score'] > self.FARMER_REDFLAG_THRESHOLD].copy()
        
        if redflag_df.empty:
            return []
        
        # Sort by farmer score and get top 3
        redflag_df = redflag_df.nlargest(3, 'farmer_score', keep='first')
        
        redflags = []
        for _, subnet in redflag_df.iterrows():
            # Get the three worst-contributing metrics
            worst_metrics = self._get_worst_contributing_metrics(subnet)
            
            redflags.append({
                'netuid': int(subnet['netuid']),
                'name': subnet['subnet_name'],
                'farmer_score': round(float(subnet['farmer_score']), 2),
                'worst_metrics': worst_metrics,
                'category': subnet.get('primary_category', 'Unknown')
            })
        
        return redflags
    
    def _get_worst_contributing_metrics(self, subnet: pd.Series) -> List[Dict[str, Any]]:
        """Get the three worst-contributing metrics to the farmer score."""
        metric_contributions = []
        
        # Calculate individual metric contributions
        contributions = {
            'Emission ROI': subnet['emission_roi_z'] * self.FARMER_WEIGHTS['emission_roi'],
            'Stake Quality': subnet['stake_quality_z_neg'] * self.FARMER_WEIGHTS['stake_quality'],
            'Validator Util': subnet['validator_util_pct_z_neg'] * self.FARMER_WEIGHTS['validator_util_pct'],
            'Flow Turnover': subnet['flow_turnover_z_neg'] * self.FARMER_WEIGHTS['flow_turnover'],
            'Stake HHI': subnet['stake_hhi_z'] * self.FARMER_WEIGHTS['stake_hhi'],
            'Price 30d': subnet['price_30d_change_z_neg'] * self.FARMER_WEIGHTS['price_30d_change']
        }
        
        # Sort by contribution (highest = worst)
        sorted_contributions = sorted(contributions.items(), key=lambda x: x[1], reverse=True)
        
        # Return top 3 worst contributors
        for metric_name, contribution in sorted_contributions[:3]:
            metric_contributions.append({
                'metric': metric_name,
                'contribution': round(contribution, 2)
            })
        
        return metric_contributions
    
    def _get_hot_subnets(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Get top 3 hot subnets based on normalized metrics."""
        if df.empty:
            return []
        
        # Calculate hot score using z-scores
        z_score_columns = [f'{metric}_z' for metric in self.METRIC_WEIGHTS.keys()]
        
        # Check if we have enough data for z-scores
        if not all(col in df.columns for col in z_score_columns):
            return []
        
        # Calculate weighted hot score
        df['hot_score'] = sum(
            df[f'{metric}_z'] * weight 
            for metric, weight in self.METRIC_WEIGHTS.items()
        )
        
        # Get top 3
        top_subnets = df.nlargest(3, 'hot_score')
        
        hot_subnets = []
        for _, subnet in top_subnets.iterrows():
            hot_subnets.append({
                'netuid': int(subnet['netuid']),
                'name': subnet['subnet_name'],
                'tao_score': round(float(subnet['tao_score']), 1),
                'price_change_7d': round(float(subnet['price_7d_change']), 1) if pd.notna(subnet['price_7d_change']) else 0,
                'flow_24h': round(float(subnet['flow_24h']), 0) if pd.notna(subnet['flow_24h']) else 0,
                'hot_score': round(float(subnet['hot_score']), 1),
                'category': subnet.get('primary_category', 'Unknown')
            })
        
        return hot_subnets
    
    def _get_outliers(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Get top 3 outliers using robust MAD method."""
        if df.empty:
            return []
        
        outliers = []
        
        # Define outlier metrics
        outlier_metrics = [
            {'metric': 'tao_score', 'description': 'TAO Score'},
            {'metric': 'stake_quality', 'description': 'Stake Quality'},
            {'metric': 'market_cap_tao', 'description': 'Market Cap'},
            {'metric': 'flow_turnover', 'description': 'Flow Turnover'}
        ]
        
        for config in outlier_metrics:
            metric = config['metric']
            if metric not in df.columns:
                continue
            
            # Use MAD (Median Absolute Deviation) for robust outlier detection
            values = df[metric].dropna()
            if len(values) < self.MIN_SAMPLE_SIZE:
                continue
            
            median_val = values.median()
            mad = np.median(np.abs(values - median_val))
            
            if mad > 0:
                # Calculate robust z-scores using MAD
                robust_z_scores = 0.6745 * (values - median_val) / mad
                
                # Cap robust z-scores at MAX_ROBUST_Z_SCORE
                robust_z_scores = np.clip(robust_z_scores, -self.MAX_ROBUST_Z_SCORE, self.MAX_ROBUST_Z_SCORE)
                
                outlier_indices = robust_z_scores[abs(robust_z_scores) > self.OUTLIER_THRESHOLD].index
                
                for idx in outlier_indices:
                    subnet = df.loc[idx]
                    outliers.append({
                        'netuid': int(subnet['netuid']),
                        'name': subnet['subnet_name'],
                        'metric': config['description'],
                        'value': round(float(subnet[metric]), 2),
                        'z_score': round(float(robust_z_scores[idx]), 2),
                        'reason': self._get_outlier_reason(subnet, metric, robust_z_scores[idx]),
                        'category': subnet.get('primary_category', 'Unknown')
                    })
        
        # Sort by absolute z-score and return top 3
        outliers.sort(key=lambda x: abs(x['z_score']), reverse=True)
        return outliers[:3]
    
    def _get_outlier_reason(self, subnet: pd.Series, metric: str, z_score: float) -> str:
        """Generate human-readable reason for outlier."""
        reasons = {
            'tao_score': {
                'high': 'Exceptional performance across all metrics',
                'low': 'Underperforming in key network metrics'
            },
            'stake_quality': {
                'high': 'Excellent stake distribution quality',
                'low': 'Concentrated stake distribution'
            },
            'market_cap_tao': {
                'high': 'High market valuation',
                'low': 'Low market valuation'
            },
            'flow_turnover': {
                'high': 'High token turnover rate',
                'low': 'Low token turnover rate'
            }
        }
        
        direction = 'high' if z_score > 0 else 'low'
        return reasons.get(metric, {}).get(direction, 'Statistical outlier')
    
    def _get_price_momentum(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Get top 3 subnets by price momentum and net inflow."""
        if df.empty:
            return []
        
        # Filter for subnets with positive flow and price data
        momentum_df = df[
            (df['flow_24h'].notna()) & 
            (df['price_7d_change'].notna()) &
            (df['flow_24h'].fillna(0).astype(float) > 0)  # Positive flow only
        ].copy()
        
        if momentum_df.empty:
            return []
        
        # Use normalized metrics for momentum score
        if 'price_7d_change_z' in momentum_df.columns and 'flow_turnover_z' in momentum_df.columns:
            momentum_df['momentum_score'] = (
                (momentum_df['price_7d_change_z'] * 0.5) +
                (momentum_df['flow_turnover_z'] * 0.5)
            )
        else:
            # Fallback to raw values if z-scores not available
            momentum_df['momentum_score'] = (
                (momentum_df['price_7d_change'] * 0.5) +
                (momentum_df['flow_turnover'] * 0.5)
            )
        
        # Get top 3
        top_momentum = momentum_df.nlargest(3, 'momentum_score')
        
        momentum_subnets = []
        for _, subnet in top_momentum.iterrows():
            momentum_subnets.append({
                'netuid': int(subnet['netuid']),
                'name': subnet['subnet_name'],
                'price_change_7d': round(float(subnet['price_7d_change']), 1),
                'flow_24h': round(float(subnet['flow_24h']), 0),
                'momentum_score': round(float(subnet['momentum_score']), 1),
                'market_cap': round(float(subnet['market_cap_tao']), 0) if pd.notna(subnet['market_cap_tao']) else 0,
                'category': subnet.get('primary_category', 'Unknown')
            })
        
        return momentum_subnets
    
    def _get_hot_categories(self, df: pd.DataFrame, enrichment_data: Dict) -> List[Dict[str, Any]]:
        """Get top 3 hottest categories based on performance."""
        if df.empty:
            return []
        
        # Group by category and calculate performance metrics
        category_stats = df.groupby('primary_category').agg({
            'tao_score': ['mean', 'count'],
            'price_7d_change': 'mean',
            'flow_turnover': 'mean',  # Use average turnover instead of total flow
            'market_cap_tao': 'sum'
        }).round(2)
        
        # Flatten column names
        category_stats.columns = ['_'.join(col).strip() for col in category_stats.columns]
        category_stats = category_stats.reset_index()
        
        # Calculate category hot score with sqrt of count to reduce size bias
        category_stats['hot_score'] = (
            (category_stats['tao_score_mean'] * 0.3) +
            (category_stats['price_7d_change_mean'].fillna(0) * 0.3) +
            (category_stats['flow_turnover_mean'].fillna(0) * 0.2) +
            (np.sqrt(category_stats['tao_score_count']) * 0.2)  # Use sqrt to reduce size bias
        )
        
        # Get top 3
        top_categories = category_stats.nlargest(3, 'hot_score')
        
        hot_categories = []
        for _, category in top_categories.iterrows():
            hot_categories.append({
                'name': category['primary_category'],
                'subnet_count': int(category['tao_score_count']),
                'avg_tao_score': round(float(category['tao_score_mean']), 1),
                'avg_price_change_7d': round(float(category['price_7d_change_mean']), 1),
                'avg_flow_turnover': round(float(category['flow_turnover_mean']), 3),
                'hot_score': round(float(category['hot_score']), 1),
                'description': self._get_category_description(str(category['primary_category']), enrichment_data)
            })
        
        return hot_categories
    
    def _get_category_description(self, category: str, enrichment_data: Dict) -> str:
        """Get description for category."""
        descriptions = {
            'LLM-Inference': 'Large Language Model inference services',
            'LLM-Training / Fine-tune': 'Model training and fine-tuning',
            'AI-Verification & Trust': 'AI verification and trust mechanisms',
            'Confidential-Compute': 'Privacy-preserving computation',
            'Data-Feeds & Oracles': 'Data feeds and oracle services',
            'Media-Vision / 3-D': 'Computer vision and 3D processing',
            'Finance-Trading & Forecasting': 'Financial trading and forecasting',
            'Consumer-AI & Games': 'Consumer AI and gaming applications',
            'Dev-Tooling': 'Developer tools and infrastructure',
            'Privacy / Anonymity': 'Privacy and anonymity solutions',
            'Science-Research (Non-financial)': 'Scientific research applications',
            'Security & Auditing': 'Security and auditing services',
            'Serverless-Compute': 'Serverless computing platforms',
            'Hashrate-Mining (BTC / PoW)': 'Mining and proof-of-work',
            'Unknown': 'Uncategorized subnets'
        }
        
        return descriptions.get(category, f'{category} subnets')
    
    def _get_enrichment_data(self) -> Dict:
        """Get enrichment data for categories."""
        try:
            session = get_db()
            subnets = session.query(SubnetMeta).all()
            session.close()
            
            enrichment_data = {}
            for subnet in subnets:
                if subnet.primary_category:
                    if subnet.primary_category not in enrichment_data:
                        enrichment_data[subnet.primary_category] = []
                    enrichment_data[subnet.primary_category].append({
                        'netuid': subnet.netuid,
                        'name': subnet.subnet_name,
                        'description': subnet.what_it_does
                    })
            
            return enrichment_data
        except Exception as e:
            logger.error(f"Error getting enrichment data: {e}")
            return {}
    
    def _get_fallback_insights(self) -> Dict[str, Any]:
        """Get fallback insights when data is unavailable."""
        return {
            'hot_subnets': [],
            'outliers': [],
            'price_momentum': [],
            'hot_categories': [],
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M UTC'),
            'data_available': False
        }

# Global service instance
landing_page_insights_service = LandingPageInsightsService() 