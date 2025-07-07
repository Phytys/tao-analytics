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
                if cached:
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
                if cached:
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
    
    def _get_correlation_data(self) -> Optional[Dict[str, Any]]:
        """Get correlation data from database."""
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
                
                # Calculate correlation matrix
                corr_matrix = df[available_cols].corr()
                
                # Find strongest correlations
                corr_pairs = []
                for i in range(len(corr_matrix.columns)):
                    for j in range(i+1, len(corr_matrix.columns)):
                        corr_value = corr_matrix.iloc[i, j]
                        if not pd.isna(corr_value):
                            corr_pairs.append({
                                'metric1': corr_matrix.columns[i],
                                'metric2': corr_matrix.columns[j],
                                'correlation': corr_value
                            })
                
                # Sort by absolute correlation value
                corr_pairs.sort(key=lambda x: abs(x['correlation']), reverse=True)
                
                return {
                    'correlation_matrix': corr_matrix.to_dict(),
                    'key_correlations': corr_pairs[:10],
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
    
    def _generate_gpt_analysis(self, corr_data: Dict[str, Any]) -> Optional[str]:
        """Generate analysis using GPT-4o."""
        if not client:
            logger.error("OpenAI client not available")
            return None
        
        try:
            # Create analysis prompt
            prompt = f"""
            Analyze this Bittensor subnet correlation data and provide insights for:
            1) Finding undervalued subnets
            2) Detecting potential scams
            3) Identifying healthy subnets

            Data Summary:
            - Total subnets: {corr_data['metrics_summary']['total_subnets']}
            - Average TAO-Score: {corr_data['metrics_summary']['avg_tao_score']:.2f}
            - Average Stake Quality: {corr_data['metrics_summary']['avg_stake_quality']:.2f}
            - High performers (≥70): {corr_data['metrics_summary']['high_performers']}
            - Strong buy signals (≥4): {corr_data['metrics_summary']['strong_buy_signals']}
            - Categories: {corr_data['metrics_summary']['categories']}

            Top Correlations:
            {chr(10).join([f"- {pair['metric1']} vs {pair['metric2']}: {pair['correlation']:.3f}" for pair in corr_data['key_correlations'][:5]])}

            Provide actionable insights in these areas:
            1. **Undervalued Subnet Indicators**: What correlation patterns suggest a subnet might be undervalued?
            2. **Scam Detection Red Flags**: What correlations might indicate suspicious activity?
            3. **Health Metrics**: Which correlations indicate genuine network health and growth?
            4. **Key Insights**: Most important findings for investors and validators
            5. **Recommendations**: Specific metrics to focus on for each goal

            Format as clear, actionable insights with bullet points and markdown formatting.
            Focus on practical, actionable advice for Bittensor subnet analysis.
            """

            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are an expert Bittensor analyst specializing in subnet correlation analysis and investment insights."},
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