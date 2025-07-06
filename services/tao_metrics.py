"""
TAO Network Metrics Service for TAO Analytics.
Calculates network overview metrics and subnet performance data for users.
"""

from sqlalchemy import func, desc, and_, or_
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional
import pandas as pd
import json
from sqlalchemy.sql import text

from .db import get_db, load_subnet_frame
from .cache import cached, db_cache
from .db_utils import json_field
from models import ScreenerRaw, SubnetMeta, CoinGeckoPrice
from datetime import datetime, timedelta


class TaoMetricsService:
    """Service for calculating TAO network metrics and subnet performance."""
    
    def __init__(self):
        """Initialize TAO metrics service."""
        pass
    
    @cached(db_cache)
    def get_network_overview(self) -> Dict[str, Any]:
        """
        Get network overview metrics for landing page.
        
        Returns:
            Dictionary with network overview data
        """
        df = load_subnet_frame()
        
        # Basic network metrics
        total_subnets = len(df)
        active_subnets = len(df[df['mcap_tao'] > 0])  # Subnets with market cap
        
        # Market metrics
        total_market_cap = df['mcap_tao'].sum()
        avg_market_cap = df['mcap_tao'].mean()
        
        # Flow metrics (24h)
        total_flow_24h = df['flow_24h'].sum()
        positive_flow_subnets = len(df[df['flow_24h'] > 0])  # Subnets with positive net volume
        
        # Top subnet
        top_subnet = df.loc[df['mcap_tao'].idxmax()] if not df.empty else None
        top_subnet_name = top_subnet['subnet_name'] if top_subnet is not None else 'N/A'
        top_subnet_mcap = top_subnet['mcap_tao'] if top_subnet is not None else 0
        
        # Highest TAO Score subnet
        highest_tao_score_subnet = None
        highest_tao_score_name = 'N/A'
        highest_tao_score_value = 0
        highest_tao_score_momentum = 0
        
        try:
            # Load screener frame which includes TAO score and price momentum
            from .db import load_screener_frame
            screener_df = load_screener_frame()
            
            if not screener_df.empty and 'tao_score' in screener_df.columns:
                # Filter out rows with no TAO score
                valid_scores = screener_df[screener_df['tao_score'] > 0]
                
                if not valid_scores.empty:
                    # Find highest TAO score
                    max_tao_score = valid_scores['tao_score'].max()
                    highest_scorers = valid_scores[valid_scores['tao_score'] == max_tao_score]
                    
                    if len(highest_scorers) > 1:
                        # If multiple subnets have same TAO score, pick the one with highest 1d price momentum
                        highest_scorers = highest_scorers.sort_values('price_7d_change', ascending=False)
                    
                    highest_tao_score_subnet = highest_scorers.iloc[0]
                    highest_tao_score_name = str(highest_tao_score_subnet['subnet_name'])
                    highest_tao_score_value = float(highest_tao_score_subnet['tao_score'])
                    highest_tao_score_momentum = float(highest_tao_score_subnet.get('price_7d_change', 0))
        except Exception as e:
            print(f"Error getting highest TAO score subnet: {e}")
        
        # Network activity (subnets with positive flow)
        recent_subnets = len(df[df['flow_24h'] > 0])  # Subnets with positive net volume
        
        # Get current TAO price and market cap with timestamp
        tao_price_usd = 354.5  # Default fallback
        tao_market_cap_usd = 0  # Default fallback
        tao_price_updated = None
        try:
            with get_db() as session:
                latest_price = session.query(CoinGeckoPrice).order_by(CoinGeckoPrice.fetched_at.desc()).first()
                if latest_price:
                    tao_price_usd = float(latest_price.price_usd)
                    tao_market_cap_usd = float(latest_price.market_cap_usd or 0)
                    tao_price_updated = latest_price.fetched_at.strftime('%Y-%m-%d %H:%M UTC')
        except Exception as e:
            print(f"Error fetching TAO data: {e}")
        
        # Get latest subnet screener data timestamp
        screener_updated = None
        try:
            with get_db() as session:
                latest_screener = session.execute(
                    text("SELECT MAX(fetched_at) as latest FROM screener_raw")
                ).fetchone()
                if latest_screener and latest_screener[0]:
                    # Convert to datetime if it's a string, then to ISO format
                    if isinstance(latest_screener[0], str):
                        dt = datetime.fromisoformat(latest_screener[0].replace('Z', '+00:00'))
                        screener_updated = dt.strftime('%Y-%m-%d %H:%M UTC')
                    else:
                        screener_updated = latest_screener[0].strftime('%Y-%m-%d %H:%M UTC')
        except Exception as e:
            print(f"Error fetching screener timestamp: {e}")
        
        return {
            'total_subnets': total_subnets,
            'active_subnets': active_subnets,
            'total_market_cap': round(float(total_market_cap) / 1000000, 1),  # Convert to millions
            'avg_market_cap': round(float(avg_market_cap) / 1000, 1),  # Convert to thousands
            'total_flow_24h': round(float(total_flow_24h) / 1000, 1),  # Convert to thousands
            'positive_flow_count': positive_flow_subnets,
            'top_subnet_name': top_subnet_name,
            'top_subnet_mcap': round(float(top_subnet_mcap) / 1000, 1),  # Convert to thousands
            'recent_subnets': recent_subnets,
            'positive_flow_percentage': round((recent_subnets / total_subnets * 100), 1) if total_subnets > 0 else 0,
            'tao_price_usd': tao_price_usd,
            'tao_market_cap_usd': round(tao_market_cap_usd / 1000000, 1),  # Convert to millions
            'tao_price_updated': tao_price_updated,
            'screener_updated': screener_updated,
            'highest_tao_score_name': highest_tao_score_name,
            'highest_tao_score_value': round(highest_tao_score_value, 1),
            'highest_tao_score_momentum': round(highest_tao_score_momentum, 1)
        }
    
    @cached(db_cache)
    def get_top_performing_subnets(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get top performing subnets by market cap and flow.
        
        Args:
            limit: Number of subnets to return
            
        Returns:
            List of top performing subnets
        """
        df = load_subnet_frame()
        
        # Sort by market cap
        top_by_mcap = df.nlargest(limit, 'mcap_tao')
        
        subnets = []
        for _, row in top_by_mcap.iterrows():
            subnets.append({
                'netuid': int(row['netuid']),
                'name': str(row['subnet_name'] or ''),
                'market_cap': round(float(row['mcap_tao'] or 0) / 1000, 1),  # Convert to thousands
                'flow_24h': round(float(row['flow_24h'] or 0) / 1000, 1),  # Convert to thousands
                'flow_percentage': round((float(row['flow_24h'] or 0) / float(row['mcap_tao'] or 1) * 100), 1) if row['mcap_tao'] > 0 else 0
            })
        
        return subnets
    
    @cached(db_cache)
    def get_network_activity(self) -> Dict[str, Any]:
        """
        Get network activity metrics.
        
        Returns:
            Dictionary with network activity data
        """
        df = load_subnet_frame()
        
        # Flow analysis
        positive_flow = df[df['flow_24h'] > 0]['flow_24h'].sum()
        negative_flow = df[df['flow_24h'] < 0]['flow_24h'].sum()
        neutral_flow = len(df[df['flow_24h'] == 0])
        
        # Market cap distribution
        high_mcap = len(df[df['mcap_tao'] > 100000])  # > 100k TAO
        medium_mcap = len(df[(df['mcap_tao'] > 10000) & (df['mcap_tao'] <= 100000)])  # 10k-100k TAO
        low_mcap = len(df[df['mcap_tao'] <= 10000])  # <= 10k TAO
        
        return {
            'positive_flow': round(float(positive_flow) / 1000, 1),  # Convert to thousands
            'negative_flow': round(float(negative_flow) / 1000, 1),  # Convert to thousands
            'neutral_subnets': neutral_flow,
            'high_mcap_subnets': high_mcap,
            'medium_mcap_subnets': medium_mcap,
            'low_mcap_subnets': low_mcap,
            'net_flow': round(float(positive_flow + negative_flow) / 1000, 1)  # Convert to thousands
        }
    
    @cached(db_cache)
    def get_market_trends(self) -> Dict[str, Any]:
        """
        Get market trend indicators.
        
        Returns:
            Dictionary with market trend data
        """
        df = load_subnet_frame()
        
        # Calculate trend indicators
        growing_subnets = len(df[df['flow_24h'] > 0])
        declining_subnets = len(df[df['flow_24h'] < 0])
        stable_subnets = len(df[df['flow_24h'] == 0])
        
        # Market concentration
        top_5_mcap = df.nlargest(5, 'mcap_tao')['mcap_tao'].sum()
        total_mcap = df['mcap_tao'].sum()
        concentration = (float(top_5_mcap) / float(total_mcap) * 100) if total_mcap > 0 else 0
        
        # Average flow per subnet
        avg_flow = df['flow_24h'].mean()
        
        return {
            'growing_subnets': growing_subnets,
            'declining_subnets': declining_subnets,
            'stable_subnets': stable_subnets,
            'market_concentration': round(concentration, 1),
            'avg_flow_per_subnet': round(float(avg_flow) / 1000, 1),  # Convert to thousands
            'growth_ratio': round(growing_subnets / (growing_subnets + declining_subnets) * 100, 1) if (growing_subnets + declining_subnets) > 0 else 0
        }


# Global instance
tao_metrics_service = TaoMetricsService() 