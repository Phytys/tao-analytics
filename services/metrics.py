"""
Metrics service for TAO Analytics.
Calculates dashboard KPIs and statistics with caching.
"""

from sqlalchemy import func, desc, and_, or_
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional
import pandas as pd

from .db import get_db
from .cache import cached, db_cache
from .db_utils import json_field
from models import ScreenerRaw, SubnetMeta


class MetricsService:
    """Service for calculating dashboard metrics and KPIs."""
    
    def __init__(self):
        """Initialize metrics service."""
        pass
    
    @cached(db_cache)
    def get_landing_kpis(self) -> Dict[str, Any]:
        """
        Get landing page KPIs.
        
        Returns:
            Dictionary with KPI data
        """
        db = get_db()
        
        try:
            # Total subnets
            total_subnets = db.query(ScreenerRaw).count()
            
            # Enriched subnets
            enriched_subnets = db.query(SubnetMeta).count()
            
            # Categories count
            categories = db.query(
                SubnetMeta.primary_category,
                func.count(SubnetMeta.netuid).label('count')
            ).group_by(SubnetMeta.primary_category).all()
            
            # Average confidence
            avg_confidence = db.query(
                func.avg(SubnetMeta.confidence)
            ).scalar() or 0
            
            # High confidence subnets (>=90)
            high_confidence = db.query(SubnetMeta).filter(
                SubnetMeta.confidence >= 90
            ).count()
            
            # Total market cap
            total_market_cap = db.query(
                func.sum(json_field(ScreenerRaw.raw_json, 'market_cap_tao'))
            ).scalar() or 0
            
            return {
                'total_subnets': total_subnets,
                'enriched_subnets': enriched_subnets,
                'enrichment_rate': round((enriched_subnets / total_subnets * 100), 1) if total_subnets > 0 else 0,
                'categories': len(categories),
                'avg_confidence': round(avg_confidence, 1),
                'high_confidence': high_confidence,
                'high_confidence_rate': round((high_confidence / enriched_subnets * 100), 1) if enriched_subnets > 0 else 0,
                'total_market_cap': round(total_market_cap, 2)
            }
        finally:
            db.close()
    
    @cached(db_cache)
    def get_category_stats(self) -> List[Dict[str, Any]]:
        """
        Get category statistics.
        
        Returns:
            List of category stats
        """
        db = get_db()
        
        try:
            # Get category counts and averages
            stats = db.query(
                SubnetMeta.primary_category,
                func.count(SubnetMeta.netuid).label('count'),
                func.avg(SubnetMeta.confidence).label('avg_confidence'),
                func.avg(json_field(ScreenerRaw.raw_json, 'market_cap_tao')).label('avg_market_cap'),
                func.sum(json_field(ScreenerRaw.raw_json, 'market_cap_tao')).label('total_market_cap')
            ).join(
                ScreenerRaw, SubnetMeta.netuid == ScreenerRaw.netuid
            ).group_by(
                SubnetMeta.primary_category
            ).order_by(
                desc('count')
            ).all()
            
            return [
                {
                    'category': stat.primary_category,
                    'count': stat.count,
                    'avg_confidence': round(stat.avg_confidence or 0, 1),
                    'avg_market_cap': round(stat.avg_market_cap or 0, 2),
                    'total_market_cap': round(stat.total_market_cap or 0, 2)
                }
                for stat in stats
            ]
        finally:
            db.close()
    
    @cached(db_cache)
    def get_confidence_distribution(self) -> List[Dict[str, Any]]:
        """
        Get confidence score distribution.
        
        Returns:
            List of confidence buckets
        """
        db = get_db()
        
        try:
            # Define confidence buckets
            buckets = [
                (0, 20, '0-20'),
                (20, 40, '20-40'),
                (40, 60, '40-60'),
                (60, 80, '60-80'),
                (80, 90, '80-90'),
                (90, 100, '90-100')
            ]
            
            distribution = []
            for min_score, max_score, label in buckets:
                count = db.query(SubnetMeta).filter(
                    and_(
                        SubnetMeta.confidence >= min_score,
                        SubnetMeta.confidence < max_score
                    )
                ).count()
                
                distribution.append({
                    'range': label,
                    'count': count
                })
            
            return distribution
        finally:
            db.close()
    
    @cached(db_cache)
    def get_provenance_stats(self) -> Dict[str, Any]:
        """
        Get provenance statistics.
        
        Returns:
            Dictionary with provenance stats
        """
        db = get_db()
        
        try:
            # Count by provenance
            provenance_counts = db.query(
                SubnetMeta.provenance,
                func.count(SubnetMeta.netuid).label('count')
            ).group_by(SubnetMeta.provenance).all()
            
            # Context token distribution
            context_stats = db.query(
                func.avg(SubnetMeta.context_tokens).label('avg_tokens'),
                func.min(SubnetMeta.context_tokens).label('min_tokens'),
                func.max(SubnetMeta.context_tokens).label('max_tokens')
            ).scalar()
            
            return {
                'provenance_counts': [
                    {'provenance': p.provenance, 'count': p.count}
                    for p in provenance_counts
                ],
                'context_tokens': {
                    'avg': round(context_stats.avg_tokens or 0, 1),
                    'min': context_stats.min_tokens or 0,
                    'max': context_stats.max_tokens or 0
                }
            }
        finally:
            db.close()
    
    @cached(db_cache)
    def get_top_subnets(self, limit: int = 10, sort_by: str = 'market_cap') -> List[Dict[str, Any]]:
        """
        Get top subnets by various metrics.
        
        Args:
            limit: Number of subnets to return
            sort_by: Sort field ('market_cap', 'confidence', 'context_tokens')
            
        Returns:
            List of top subnets
        """
        db = get_db()
        
        try:
            query = db.query(
                SubnetMeta,
                ScreenerRaw
            ).join(
                ScreenerRaw, SubnetMeta.netuid == ScreenerRaw.netuid
            )
            
            # Apply sorting
            if sort_by == 'market_cap':
                query = query.order_by(
                    desc(json_field(ScreenerRaw.raw_json, 'market_cap_tao'))
                )
            elif sort_by == 'confidence':
                query = query.order_by(desc(SubnetMeta.confidence))
            elif sort_by == 'context_tokens':
                query = query.order_by(desc(SubnetMeta.context_tokens))
            
            results = query.limit(limit).all()
            
            return [
                {
                    'netuid': result[0].netuid,
                    'name': result[0].subnet_name,
                    'category': result[0].primary_category,
                    'confidence_score': result[0].confidence,
                    'market_cap': json_field(result[1].raw_json, 'market_cap_tao'),
                    'context_tokens': result[0].context_tokens,
                    'provenance': result[0].provenance
                }
                for result in results
            ]
        finally:
            db.close()
    
    def get_search_results(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search subnets by name, category, or tags.
        
        Args:
            query: Search query
            limit: Maximum results to return
            
        Returns:
            List of matching subnets
        """
        db = get_db()
        
        try:
            # Search in name, category, and tags
            search_query = f"%{query.lower()}%"
            
            results = db.query(
                SubnetMeta,
                ScreenerRaw
            ).join(
                ScreenerRaw, SubnetMeta.netuid == ScreenerRaw.netuid
            ).filter(
                or_(
                    func.lower(SubnetMeta.subnet_name).like(search_query),
                    func.lower(SubnetMeta.primary_category).like(search_query),
                    func.lower(SubnetMeta.secondary_tags).like(search_query)
                )
            ).limit(limit).all()
            
            return [
                {
                    'netuid': result[0].netuid,
                    'name': result[0].subnet_name,
                    'category': result[0].primary_category,
                    'confidence_score': result[0].confidence,
                    'market_cap': json_field(result[1].raw_json, 'market_cap_tao'),
                    'tags': result[0].secondary_tags
                }
                for result in results
            ]
        finally:
            db.close()


# Global instance
metrics_service = MetricsService() 