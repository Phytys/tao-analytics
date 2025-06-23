"""
Metrics service for TAO Analytics.
Calculates dashboard KPIs and statistics with caching.
"""

from sqlalchemy import func, desc, and_, or_
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional
import pandas as pd
import json

from .db import get_db, load_subnet_frame
from .cache import cached, db_cache
from .db_utils import json_field
from models import ScreenerRaw, SubnetMeta
from datetime import datetime, timedelta


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
        df = load_subnet_frame()
        
        # Basic metrics
        total_subnets = len(df)
        enriched_subnets = len(df[df['primary_category'].notna()])
        enrichment_rate = (enriched_subnets / total_subnets * 100) if total_subnets > 0 else 0
        
        # Category distribution
        category_counts = df['primary_category'].value_counts().to_dict() if 'primary_category' in df.columns else {}
        
        # Confidence metrics
        avg_confidence = df['confidence'].mean() if 'confidence' in df.columns else 0
        
        # Privacy focus
        privacy_focused = len(df[df['privacy_security_flag'] == True]) if 'privacy_security_flag' in df.columns else 0
        privacy_rate = (privacy_focused / total_subnets * 100) if total_subnets > 0 else 0
        
        # Market cap metrics
        total_market_cap = df['mcap_tao'].sum() if 'mcap_tao' in df.columns else 0
        high_confidence = len(df[df['confidence'] >= 90]) if 'confidence' in df.columns else 0
        
        return {
            'total_subnets': total_subnets,
            'enriched_subnets': enriched_subnets,
            'enrichment_rate': round(enrichment_rate, 1),
            'avg_confidence': round(avg_confidence, 1),
            'privacy_focused': privacy_focused,
            'privacy_rate': round(privacy_rate, 1),
            'total_market_cap': round(total_market_cap / 1000000, 1),  # Convert to millions
            'high_confidence': high_confidence,
            'category_distribution': category_counts
        }
    
    @cached(db_cache)
    def get_category_stats(self) -> List[Dict[str, Any]]:
        """
        Get category statistics.
        
        Returns:
            List of category stats
        """
        df = load_subnet_frame()
        
        # Get category counts and averages
        stats = df.groupby('primary_category').agg(
            count=('netuid', 'count'),
            avg_confidence=('confidence', 'mean'),
            avg_market_cap=('mcap_tao', 'mean'),
            total_market_cap=('mcap_tao', 'sum')
        ).reset_index()
        
        return [
            {
                'category': str(category or ''),
                'count': int(count),
                'avg_confidence': round(float(avg_confidence or 0), 1),
                'avg_market_cap': round(float(avg_market_cap or 0), 2),
                'total_market_cap': round(float(total_market_cap or 0), 2)
            }
            for category, count, avg_confidence, avg_market_cap, total_market_cap in stats.values
        ]
    
    @cached(db_cache)
    def get_confidence_distribution(self) -> List[Dict[str, Any]]:
        """
        Get confidence score distribution.
        
        Returns:
            List of confidence buckets
        """
        df = load_subnet_frame()
        
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
            count = len(df[(df['confidence'] >= min_score) & (df['confidence'] < max_score)])
            
            distribution.append({
                'range': label,
                'count': count
            })
        
        return distribution
    
    @cached(db_cache)
    def get_provenance_stats(self) -> Dict[str, Any]:
        """
        Get provenance statistics.
        
        Returns:
            Dictionary with provenance stats
        """
        df = load_subnet_frame()
        
        # Count by provenance
        provenance_counts = df['provenance'].value_counts().to_dict()
        
        # Context token distribution
        context_stats = df['context_tokens'].agg(['mean', 'min', 'max']).to_dict()
        
        return {
            'provenance_counts': [
                {'provenance': str(provenance or ''), 'count': int(count)}
                for provenance, count in provenance_counts.items()
            ],
            'context_tokens': {
                'avg': round(float(context_stats['mean'] or 0), 1),
                'min': int(context_stats['min'] or 0),
                'max': int(context_stats['max'] or 0)
            }
        }
    
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
        df = load_subnet_frame()
        
        # Apply sorting
        if sort_by == 'market_cap':
            df = df.sort_values(by='mcap_tao', ascending=False)
        elif sort_by == 'confidence':
            df = df.sort_values(by='confidence', ascending=False)
        elif sort_by == 'context_tokens':
            df = df.sort_values(by='context_tokens', ascending=False)
        
        results = df.head(limit).reset_index(drop=True)
        
        subnets = []
        for _, row in results.iterrows():
            subnets.append({
                'netuid': int(row['netuid']),
                'name': str(row['subnet_name'] or ''),
                'category': str(row['primary_category'] or ''),
                'confidence_score': float(row['confidence'] or 0),
                'market_cap': float(row['mcap_tao'] or 0),
                'context_tokens': int(row['context_tokens'] or 0),
                'provenance': str(row['provenance'] or '')
            })
        
        return subnets
    
    def get_search_results(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search subnets by name, category, or tags.
        
        Args:
            query: Search query
            limit: Maximum results to return
            
        Returns:
            List of matching subnets
        """
        df = load_subnet_frame()
        
        # Search in name, category, and tags
        search_query = f"%{query.lower()}%"
        
        results = df[
            (df['subnet_name'].str.lower().str.contains(search_query)) |
            (df['primary_category'].str.lower().str.contains(search_query)) |
            (df['secondary_tags'].str.lower().str.contains(search_query))
        ].head(limit).reset_index(drop=True)
        
        search_results = []
        for _, row in results.iterrows():
            search_results.append({
                'netuid': int(row['netuid']),
                'name': str(row['subnet_name'] or ''),
                'category': str(row['primary_category'] or ''),
                'confidence_score': float(row['confidence'] or 0),
                'market_cap': float(row['mcap_tao'] or 0),
                'tags': str(row['secondary_tags'] or '')
            })
        
        return search_results

    def category_evolution_metrics(self) -> Dict[str, Any]:
        """Get metrics for category evolution and suggestions."""
        df = load_subnet_frame()
        
        # Filter enriched subnets
        enriched = df[df['primary_category'].notna()].copy()
        
        if len(enriched) == 0:
            return {
                'total_enriched': 0,
                'category_suggestions': 0,
                'suggestion_rate': 0,
                'suggested_categories': [],
                'category_coverage': {},
                'optimization_insights': []
            }
        
        # Category suggestions analysis
        category_suggestions = enriched[enriched['category_suggestion'].notna() & (enriched['category_suggestion'] != '')]
        suggestion_count = len(category_suggestions)
        suggestion_rate = (suggestion_count / len(enriched) * 100) if len(enriched) > 0 else 0
        
        # Get suggested categories
        suggested_categories = category_suggestions['category_suggestion'].value_counts().to_dict()
        
        # Category coverage analysis
        category_coverage = enriched['primary_category'].value_counts().to_dict()
        
        # Optimization insights
        insights = []
        
        # Check for categories with many suggestions
        if suggestion_count > 0:
            insights.append(f"{suggestion_count} subnets have suggested new categories")
            
            # Find most suggested categories
            if suggested_categories:
                top_suggestion = max(suggested_categories.items(), key=lambda x: x[1])
                insights.append(f"Most suggested category: '{top_suggestion[0]}' ({top_suggestion[1]} times)")
        
        # Check for category imbalance
        if category_coverage:
            max_category_count = max(category_coverage.values())
            min_category_count = min(category_coverage.values())
            
            if max_category_count > min_category_count * 3:  # Significant imbalance
                most_common = max(category_coverage.items(), key=lambda x: x[1])
                least_common = min(category_coverage.items(), key=lambda x: x[1])
                insights.append(f"Category imbalance: '{most_common[0]}' ({most_common[1]}) vs '{least_common[0]}' ({least_common[1]})")
        
        # Check for uncategorized subnets
        uncategorized = len(df[df['primary_category'].isna()])
        if uncategorized > 0:
            insights.append(f"{uncategorized} subnets still need categorization")
        
        return {
            'total_enriched': len(enriched),
            'category_suggestions': suggestion_count,
            'suggestion_rate': round(suggestion_rate, 1),
            'suggested_categories': suggested_categories,
            'category_coverage': category_coverage,
            'optimization_insights': insights
        }


# Global instance
metrics_service = MetricsService() 