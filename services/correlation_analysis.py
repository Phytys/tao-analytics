"""
Correlation Analysis Service for TAO Analytics.
Provides AI-powered correlation matrix analysis with 24-hour database caching.
"""

import os
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from scipy import stats
from openai import OpenAI

from .db import get_db
from models import MetricsSnap, CorrelationAnalysis
from config import OPENAI_KEY

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

# GPT Configuration
MODEL_NAME = "gpt-4o-2024-05-13"
MAX_TOKENS = 2000
CACHE_DURATION_HOURS = 24

# Rate limiting
MAX_REQUESTS_PER_DAY = 10
MAX_REQUESTS_PER_HOUR = 2

# Statistical thresholds
MIN_CORRELATION = 0.5  # Minimum correlation to consider
MAX_P_VALUE = 0.05     # Maximum p-value for significance
Z_SCORE_THRESHOLD = 3  # Z-score threshold for outlier detection

class CorrelationAnalysisService:
    """Service for analyzing correlation matrices with GPT-4o."""
    
    def __init__(self):
        """Initialize the correlation analysis service."""
        pass
        
    def _load_cache(self) -> Optional[Dict[str, Any]]:
        """Load cached analysis from database."""
        try:
            with get_db() as session:
                cached = session.query(CorrelationAnalysis).order_by(CorrelationAnalysis.ts.desc()).first()
                if cached:
                    return {
                        'timestamp': cached.ts.isoformat(),
                        'analysis': cached.analysis_text,
                        'status': cached.status
                    }
        except Exception as e:
            logger.error(f"Error loading correlation analysis cache: {e}")
        return None
    
    def _save_cache(self, analysis: str, status: str = 'generated') -> bool:
        """Save analysis to database cache."""
        try:
            with get_db() as session:
                # Create new cache entry
                new_cache = CorrelationAnalysis(
                    analysis_text=analysis,
                    status=status,
                    ts=datetime.utcnow()
                )
                session.add(new_cache)
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving correlation analysis cache: {e}")
            return False
    
    def _load_rate_limit(self) -> Dict[str, Any]:
        """Load rate limit data from database."""
        try:
            with get_db() as session:
                cached = session.query(CorrelationAnalysis).order_by(CorrelationAnalysis.ts.desc()).first()
                if cached is not None:
                    return {
                        'daily_requests': cached.daily_requests_used or 0,
                        'hourly_requests': cached.hourly_requests_used or 0,
                        'last_request': cached.last_request_time.isoformat() if cached.last_request_time else None
                    }
        except Exception as e:
            logger.error(f"Error loading rate limit data: {e}")
        return {'daily_requests': 0, 'hourly_requests': 0, 'last_request': None}
    
    def _save_rate_limit(self, rate_data: Dict[str, Any]) -> bool:
        """Save rate limit data to database."""
        try:
            with get_db() as session:
                cached = session.query(CorrelationAnalysis).order_by(CorrelationAnalysis.ts.desc()).first()
                if cached is not None:
                    cached.daily_requests_used = rate_data.get('daily_requests', 0)
                    cached.hourly_requests_used = rate_data.get('hourly_requests', 0)
                    if rate_data.get('last_request'):
                        cached.last_request_time = datetime.fromisoformat(rate_data['last_request'])
                    session.commit()
                    return True
        except Exception as e:
            logger.error(f"Error saving rate limit data: {e}")
        return False
    
    def _check_rate_limit(self) -> bool:
        """Check if request is within rate limits."""
        rate_data = self._load_rate_limit()
        now = datetime.now()
        
        # Reset daily counter if it's a new day
        if rate_data.get('last_request'):
            last_request = datetime.fromisoformat(rate_data['last_request'])
            if (now - last_request).days >= 1:
                rate_data['daily_requests'] = 0
        
        # Reset hourly counter if it's been more than an hour
        if rate_data.get('last_request'):
            last_request = datetime.fromisoformat(rate_data['last_request'])
            if (now - last_request).total_seconds() >= 3600:
                rate_data['hourly_requests'] = 0
        
        # Check limits
        if rate_data.get('daily_requests', 0) >= MAX_REQUESTS_PER_DAY:
            logger.warning("Daily rate limit exceeded for correlation analysis")
            return False
        
        if rate_data.get('hourly_requests', 0) >= MAX_REQUESTS_PER_HOUR:
            logger.warning("Hourly rate limit exceeded for correlation analysis")
            return False
        
        return True
    
    def _update_rate_limit(self) -> bool:
        """Update rate limit counters."""
        rate_data = self._load_rate_limit()
        now = datetime.now()
        
        # Reset counters if needed
        if rate_data.get('last_request'):
            last_request = datetime.fromisoformat(rate_data['last_request'])
            if (now - last_request).days >= 1:
                rate_data['daily_requests'] = 0
            if (now - last_request).total_seconds() >= 3600:
                rate_data['hourly_requests'] = 0
        
        # Increment counters
        rate_data['daily_requests'] = rate_data.get('daily_requests', 0) + 1
        rate_data['hourly_requests'] = rate_data.get('hourly_requests', 0) + 1
        rate_data['last_request'] = now.isoformat()
        
        return self._save_rate_limit(rate_data)
    
    def _is_cache_valid(self) -> bool:
        """Check if cached analysis is still valid."""
        cache_data = self._load_cache()
        if not cache_data:
            return False
        
        try:
            last_update = datetime.fromisoformat(cache_data.get('timestamp', '2000-01-01'))
            return (datetime.now() - last_update) < timedelta(hours=CACHE_DURATION_HOURS)
        except Exception as e:
            logger.error(f"Error checking cache validity: {e}")
            return False
    
    def _calculate_significant_correlations(self, df: pd.DataFrame, available_cols: List[str]) -> List[Dict[str, Any]]:
        """Calculate correlations with p-value filtering to remove spurious correlations."""
        if len(available_cols) < 2:
            return []
        
        significant_pairs = []
        
        for i, col1 in enumerate(available_cols):
            for col2 in available_cols[i+1:]:
                # Remove rows with missing data for this pair
                pair_data = df[[col1, col2]].dropna()
                
                if len(pair_data) < 10:  # Need at least 10 data points
                    continue
                
                # Calculate correlation and p-value
                try:
                    correlation, p_value = stats.pearsonr(pair_data[col1], pair_data[col2])
                    
                    # Filter by correlation strength and statistical significance
                    if abs(correlation) >= MIN_CORRELATION and p_value < MAX_P_VALUE:
                        significant_pairs.append({
                            'metric1': col1,
                            'metric2': col2,
                            'correlation': correlation,
                            'p_value': p_value,
                            'sample_size': len(pair_data)
                        })
                except Exception as e:
                    logger.debug(f"Error calculating correlation for {col1} vs {col2}: {e}")
                    continue
        
        # Sort by absolute correlation value
        significant_pairs.sort(key=lambda x: abs(x['correlation']), reverse=True)
        return significant_pairs

    def _detect_outliers(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect subnets that are statistical outliers on key metrics."""
        outliers = []
        key_metrics = ['tao_score', 'stake_quality', 'market_cap_tao']
        
        for metric in key_metrics:
            if metric not in df.columns:
                continue
            
            # Remove missing values
            metric_data = df[metric].dropna()
            if len(metric_data) < 5:  # Need at least 5 data points
                continue
            
            # Calculate Z-scores
            mean_val = metric_data.mean()
            std_val = metric_data.std()
            
            if std_val == 0:  # Skip if no variation
                continue
            
            z_scores = (metric_data - mean_val) / std_val
            
            # Find outliers (beyond 3 standard deviations)
            outlier_indices = np.where(np.abs(z_scores) > Z_SCORE_THRESHOLD)[0]
            
            for idx in outlier_indices:
                subnet_idx = metric_data.index[idx]
                subnet_data = df.loc[subnet_idx]
                
                outliers.append({
                    'netuid': subnet_data.get('netuid', 'Unknown'),
                    'subnet_name': subnet_data.get('subnet_name', 'Unknown'),
                    'metric': metric,
                    'value': metric_data.iloc[idx],
                    'z_score': z_scores.iloc[idx],
                    'mean': mean_val,
                    'std': std_val
                })
        
        return outliers

    def _build_statistical_digest(self, df: pd.DataFrame, available_cols: List[str], 
                                 significant_pairs: List[Dict[str, Any]], 
                                 outliers: List[Dict[str, Any]]) -> str:
        """Build a statistical digest for the GPT prompt."""
        digest_lines = []
        
        # Basic statistics
        digest_lines.append(f"**Dataset Statistics:**")
        digest_lines.append(f"- Total subnets: {len(df)}")
        digest_lines.append(f"- Metrics analyzed: {len(available_cols)}")
        digest_lines.append(f"- Significant correlations (|r|≥{MIN_CORRELATION}, p<{MAX_P_VALUE}): {len(significant_pairs)}")
        digest_lines.append(f"- Statistical outliers detected: {len(outliers)}")
        
        # Key metric statistics
        key_metrics = ['tao_score', 'stake_quality', 'market_cap_tao']
        for metric in key_metrics:
            if metric in df.columns:
                metric_data = df[metric].dropna()
                if len(metric_data) > 0:
                    digest_lines.append(f"- {metric}: μ={metric_data.mean():.2f}, σ={metric_data.std():.2f}, range=[{metric_data.min():.2f}, {metric_data.max():.2f}]")
        
        # Sample size information
        if significant_pairs:
            sample_sizes = [pair['sample_size'] for pair in significant_pairs]
            digest_lines.append(f"- Correlation sample sizes: min={min(sample_sizes)}, max={max(sample_sizes)}, median={np.median(sample_sizes):.0f}")
        
        # Outlier summary
        if outliers:
            outlier_metrics = {}
            for outlier in outliers:
                metric = outlier['metric']
                if metric not in outlier_metrics:
                    outlier_metrics[metric] = []
                outlier_metrics[metric].append(outlier['subnet_name'])
            
            digest_lines.append(f"- Outliers by metric:")
            for metric, subnet_names in outlier_metrics.items():
                digest_lines.append(f"  • {metric}: {', '.join(subnet_names[:3])}{'...' if len(subnet_names) > 3 else ''}")
        
        return "\n".join(digest_lines)

    def _get_correlation_data(self) -> Optional[Dict[str, Any]]:
        """Get correlation data from database with enhanced statistical analysis."""
        try:
            with get_db() as session:
                # Get latest data for each subnet (SQLite compatible)
                latest_sql = """
                    SELECT m1.*
                    FROM metrics_snap m1
                    INNER JOIN (
                        SELECT netuid, MAX(timestamp) as max_timestamp
                        FROM metrics_snap
                        GROUP BY netuid
                    ) m2 ON m1.netuid = m2.netuid AND m1.timestamp = m2.max_timestamp
                    ORDER BY m1.netuid
                    LIMIT 200
                """
                
                df = pd.read_sql(latest_sql, session.bind)
                
                if df.empty:
                    return None
                
                # Define metric categories
                core_metrics = ['tao_score', 'stake_quality', 'buy_signal', 'emission_roi']
                market_metrics = ['market_cap_tao', 'price_7d_change', 'price_1d_change', 'flow_24h', 
                                'buy_sell_ratio', 'total_volume_tao_1d', 'fdv_tao']
                network_metrics = ['active_validators', 'validator_util_pct', 'consensus_alignment', 
                                 'active_stake_ratio', 'uid_count', 'max_validators']
                stake_metrics = ['total_stake_tao', 'stake_hhi', 'gini_coeff_top_100', 'hhi']
                flow_metrics = ['reserve_momentum', 'tao_in', 'alpha_circ', 'alpha_prop', 'root_prop']
                performance_metrics = ['stake_quality_rank_pct', 'momentum_rank_pct', 
                                     'realized_pnl_tao', 'unrealized_pnl_tao']
                
                all_metrics = (core_metrics + market_metrics + network_metrics + 
                             stake_metrics + flow_metrics + performance_metrics)
                
                # Filter to available columns
                available_cols = [col for col in all_metrics if col in df.columns]
                
                if len(available_cols) < 2:
                    return None
                
                # Calculate significant correlations with p-value filtering
                significant_pairs = self._calculate_significant_correlations(df, available_cols)
                
                # Detect outliers
                outliers = self._detect_outliers(df)
                
                # Build statistical digest
                statistical_digest = self._build_statistical_digest(df, available_cols, significant_pairs, outliers)
                
                # Calculate correlation matrix for compatibility
                corr_matrix = df[available_cols].corr()
                
                return {
                    'correlation_matrix': corr_matrix.to_dict(),
                    'key_correlations': significant_pairs[:10],  # Use significant pairs instead of all
                    'outliers': outliers,
                    'statistical_digest': statistical_digest,
                    'df': df,  # Pass dataframe for ranked lists
                    'metrics_summary': {
                        'total_subnets': len(df),
                        'avg_tao_score': df['tao_score'].mean() if 'tao_score' in df.columns else 0,
                        'avg_stake_quality': df['stake_quality'].mean() if 'stake_quality' in df.columns else 0,
                        'avg_market_cap': df['market_cap_tao'].mean() if 'market_cap_tao' in df.columns else 0,
                        'high_performers': len(df[df['tao_score'] >= 70]) if 'tao_score' in df.columns else 0,
                        'strong_buy_signals': len(df[df['buy_signal'] >= 4]) if 'buy_signal' in df.columns else 0,
                        'categories': df['category'].nunique() if 'category' in df.columns else 0
                    },
                    'available_metrics': available_cols
                }
                
        except Exception as e:
            logger.error(f"Error getting correlation data: {e}")
            return None

    def _build_enhanced_prompt(self, corr_data: Dict[str, Any]) -> str:
        """Build enhanced prompt with statistical rigor and outlier context."""
        # Format significant correlations with p-values and sample sizes
        corr_lines = []
        for pair in corr_data['key_correlations'][:8]:  # Show more correlations
            corr_lines.append(f"**{pair['metric1']} ↔ {pair['metric2']}**: r = {pair['correlation']:.3f}, p = {pair['p_value']:.3g}, n = {pair['sample_size']}")
        
        # Format outliers with proper subnet names
        outlier_lines = []
        if corr_data.get('outliers'):
            for outlier in corr_data['outliers'][:8]:  # Show more outliers
                outlier_lines.append(f"- **{outlier['subnet_name']}** (uid {outlier['netuid']}) – {outlier['metric']}: {outlier['value']:.2f} (Z={outlier['z_score']:.2f})")
        
        # Generate ranked lists for concrete recommendations
        df = corr_data.get('df', None)
        ranked_lists = self._generate_ranked_lists(df) if df is not None else "No data available for ranked lists."
        
        prompt = f"""
        Analyze this Bittensor subnet correlation data with statistical rigor and provide insights for:
        1) Finding undervalued subnets
        2) Detecting potential scams  
        3) Identifying healthy subnets

        {corr_data['statistical_digest']}

        **TOP SIGNIFICANT CORRELATIONS (|r|≥{MIN_CORRELATION}, p<{MAX_P_VALUE}):**
        {chr(10).join(corr_lines) if corr_lines else "No significant correlations found"}

        **STATISTICAL OUTLIERS (|Z|>{Z_SCORE_THRESHOLD}):**
        {chr(10).join(outlier_lines) if outlier_lines else "No significant outliers detected"}

        **CONCRETE RECOMMENDATIONS:**
        {ranked_lists}

        **Data Summary:**
        - Total subnets: {corr_data['metrics_summary']['total_subnets']}
        - Average TAO-Score: {corr_data['metrics_summary']['avg_tao_score']:.2f}
        - Average Stake Quality: {corr_data['metrics_summary']['avg_stake_quality']:.2f}
        - High performers (≥70): {corr_data['metrics_summary']['high_performers']}
        - Strong buy signals (≥4): {corr_data['metrics_summary']['strong_buy_signals']}
        - Categories: {corr_data['metrics_summary']['categories']}

        Provide actionable insights in these areas:
        1. **Undervalued Subnet Indicators**: What correlation patterns suggest a subnet might be undervalued?
        2. **Scam Detection Red Flags**: What correlations might indicate suspicious activity?
        3. **Health Metrics**: Which correlations indicate genuine network health and growth?
        4. **Outlier Analysis**: What do the statistical outliers tell us about market extremes?
        5. **Key Insights**: Most important findings for investors and validators
        6. **Recommendations**: Specific metrics to focus on for each goal

        Format as clear, actionable insights with bullet points and markdown formatting.
        Focus on practical, actionable advice for Bittensor subnet analysis.
        Consider the statistical significance and sample sizes when interpreting correlations.
        
        **IMPORTANT**: Return your answer as markdown, and append a code-block labelled `json` containing a dictionary with keys:
        ```json
        {{
          "undervalued": [...],
          "scam_flags": [...],
          "healthy": [...]
        }}
        ```
        """
        
        return prompt

    def _generate_ranked_lists(self, df: pd.DataFrame) -> str:
        """Generate ranked lists of subnets for concrete recommendations."""
        if df is None or df.empty:
            return "No data available for ranked lists."
        
        try:
            # Calculate means for thresholds
            tao_score_mean = df['tao_score'].mean() if 'tao_score' in df.columns else 0
            mcap_mean = df['market_cap_tao'].mean() if 'market_cap_tao' in df.columns else 0
            stake_quality_mean = df['stake_quality'].mean() if 'stake_quality' in df.columns else 0
            
            lists = []
            
            # Top undervalued subnets (high TAO-Score, low market cap)
            if 'tao_score' in df.columns and 'market_cap_tao' in df.columns:
                undervalued = df[
                    (df['tao_score'] >= 70) & 
                    (df['market_cap_tao'] < mcap_mean) &
                    (df['market_cap_tao'] > 0)
                ].sort_values(by='market_cap_tao', ascending=True).head(5)
                
                if not undervalued.empty:
                    undervalued_list = [
                        f"{row['subnet_name']} (uid {row['netuid']}, TAO-Score={row['tao_score']:.1f}, mcap={row['market_cap_tao']:,.0f})"
                        for _, row in undervalued.iterrows()
                    ]
                    lists.append(f"**Potentially Undervalued (Top 5)**: {', '.join(undervalued_list)}")
            
            # Low stake quality alerts (statistical outliers)
            if 'stake_quality' in df.columns:
                low_stake_alerts = df[
                    (df['stake_quality'] < 20) & 
                    (df['stake_quality'] > 0)
                ].sort_values(by='stake_quality', ascending=True).head(5)
                
                if not low_stake_alerts.empty:
                    alert_list = [
                        f"{row['subnet_name']} (uid {row['netuid']}, stake_quality={row['stake_quality']:.1f})"
                        for _, row in low_stake_alerts.iterrows()
                    ]
                    lists.append(f"**Low-Stake-Quality Alerts**: {', '.join(alert_list)}")
            
            # Healthy subnets (high scores across metrics)
            if 'tao_score' in df.columns and 'stake_quality' in df.columns:
                healthy = df[
                    (df['tao_score'] >= 70) & 
                    (df['stake_quality'] >= 70)
                ].sort_values(by='tao_score', ascending=False).head(5)
                
                if not healthy.empty:
                    healthy_list = [
                        f"{row['subnet_name']} (uid {row['netuid']}, TAO-Score={row['tao_score']:.1f}, stake_quality={row['stake_quality']:.1f})"
                        for _, row in healthy.iterrows()
                    ]
                    lists.append(f"**Healthy Subnets**: {', '.join(healthy_list)}")
            
            return "\n".join(lists) if lists else "No specific recommendations available."
            
        except Exception as e:
            logger.error(f"Error generating ranked lists: {e}")
            return "Error generating ranked lists."
    
    def _generate_gpt_analysis(self, corr_data: Dict[str, Any]) -> Optional[str]:
        """Generate analysis using GPT-4o with enhanced statistical context."""
        if not client:
            logger.error("OpenAI client not available")
            return None
        
        try:
            # Build enhanced prompt with statistical rigor
            prompt = self._build_enhanced_prompt(corr_data)

            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are an expert Bittensor analyst specializing in subnet correlation analysis and investment insights. Use statistical rigor and focus on actionable insights."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=MAX_TOKENS,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating GPT analysis: {e}")
            return None
    
    def get_analysis(self) -> Dict[str, Any]:
        """
        Get correlation analysis with caching and rate limiting.
        
        Returns:
            Dictionary with analysis data and status
        """
        try:
            # Check rate limits
            if not self._check_rate_limit():
                return {
                    'success': False,
                    'error': 'Rate limit exceeded. Please try again later.',
                    'analysis': None,
                    'status': 'Rate limited',
                    'cache_info': self._get_cache_info()
                }
            
            # Check cache first
            if self._is_cache_valid():
                cache_data = self._load_cache()
                if cache_data:
                    logger.info("Using cached correlation analysis")
                    return {
                        'success': True,
                        'analysis': cache_data['analysis'],
                        'status': 'Cached',
                        'cache_info': self._get_cache_info()
                    }
            
            # Get correlation data
            corr_data = self._get_correlation_data()
            if not corr_data:
                return {
                    'success': False,
                    'error': 'Insufficient data for correlation analysis',
                    'analysis': None,
                    'status': 'No data',
                    'cache_info': self._get_cache_info()
                }
            
            # Generate new analysis
            analysis = self._generate_gpt_analysis(corr_data)
            if not analysis:
                return {
                    'success': False,
                    'error': 'Failed to generate analysis',
                    'analysis': None,
                    'status': 'Generation failed',
                    'cache_info': self._get_cache_info()
                }
            
            # Update rate limits
            self._update_rate_limit()
            
            # Cache the analysis
            self._save_cache(analysis)
            
            logger.info("Generated new correlation analysis")
            return {
                'success': True,
                'analysis': analysis,
                'status': 'Generated',
                'cache_info': self._get_cache_info()
            }
            
        except Exception as e:
            logger.error(f"Error in get_analysis: {e}")
            return {
                'success': False,
                'error': f'Analysis error: {str(e)}',
                'analysis': None,
                'status': 'Error',
                'cache_info': self._get_cache_info()
            }
    
    def _get_cache_info(self) -> Dict[str, Any]:
        """Get cache information."""
        cache_data = self._load_cache()
        rate_data = self._load_rate_limit()
        
        if cache_data:
            last_update = datetime.fromisoformat(cache_data.get('timestamp', '2000-01-01'))
            time_since_update = datetime.now() - last_update
            hours_remaining = max(0, CACHE_DURATION_HOURS - time_since_update.total_seconds() / 3600)
        else:
            hours_remaining = 0
            last_update = None
        
        return {
            'last_update': last_update.isoformat() if last_update else None,
            'hours_remaining': round(hours_remaining, 1),
            'is_valid': self._is_cache_valid(),
            'daily_requests_used': rate_data.get('daily_requests', 0),
            'daily_requests_limit': MAX_REQUESTS_PER_DAY,
            'hourly_requests_used': rate_data.get('hourly_requests', 0),
            'hourly_requests_limit': MAX_REQUESTS_PER_HOUR
        }
    
    def clear_cache(self) -> bool:
        """Clear the analysis cache."""
        try:
            with get_db() as session:
                session.query(CorrelationAnalysis).delete()
                session.commit()
                logger.info("Cleared correlation analysis cache")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
    
    def get_rate_limit_info(self) -> Dict[str, Any]:
        """Get rate limit information."""
        rate_data = self._load_rate_limit()
        return {
            'daily_requests_used': rate_data.get('daily_requests', 0),
            'daily_requests_limit': MAX_REQUESTS_PER_DAY,
            'hourly_requests_used': rate_data.get('hourly_requests', 0),
            'hourly_requests_limit': MAX_REQUESTS_PER_HOUR,
            'last_request': rate_data.get('last_request')
        }

# Global service instance
correlation_service = CorrelationAnalysisService() 