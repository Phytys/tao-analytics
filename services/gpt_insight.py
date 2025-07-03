"""
GPT Insight Service for TAO Analytics.
Provides AI-powered subnet analysis with 24-hour database caching.
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from openai import OpenAI

from .db import get_db
from models import GptInsights, MetricsSnap, SubnetMeta, CategoryStats
from config import OPENAI_KEY

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

# GPT Insight v4 Configuration
MODEL_NAME = "gpt-4o-2024-05-13"
MAX_WORDS = 200
MAX_TOKENS = 400

def get_subnet_metrics_for_insight(netuid: int) -> Dict[str, Any]:
    """
    Get comprehensive subnet metrics for GPT v4 analysis with expanded context.
    Ensures data consistency with the metrics display.
    
    Args:
        netuid: Subnet ID to analyze
        
    Returns:
        Dictionary with comprehensive metrics for expert commentary
    """
    try:
        with get_db() as session:
            # Get latest metrics snapshot
            latest_metrics = session.query(MetricsSnap).filter_by(netuid=netuid)\
                .order_by(MetricsSnap.timestamp.desc()).first()
            
            # Get subnet metadata
            subnet_meta = session.query(SubnetMeta).filter_by(netuid=netuid).first()
            
            # Get category stats for peer comparison
            category_stats = None
            if latest_metrics and latest_metrics.category:
                category_stats = session.query(CategoryStats).filter_by(category=latest_metrics.category).first()
            
            if not latest_metrics:
                return {}
            
            # Calculate validator utilization percentage to ensure consistency
            active_validators = latest_metrics.active_validators or 0
            max_validators = latest_metrics.max_validators or 64
            validator_util_pct = (active_validators / max_validators * 100) if max_validators > 0 else 0
            
            # Calculate buy/sell ratio to ensure consistency
            buy_volume = latest_metrics.buy_volume_tao_1d or 0
            sell_volume = latest_metrics.sell_volume_tao_1d or 0
            buy_sell_ratio = (buy_volume / sell_volume) if sell_volume > 0 else 0
            
            # Build comprehensive v4 payload with expanded context
            metrics = {
                'name': subnet_meta.subnet_name if subnet_meta else f'Subnet {netuid}',
                'id': netuid,
                'category': latest_metrics.category or 'Unknown',
                'price_tao': round(latest_metrics.price_tao, 3) if latest_metrics.price_tao else None,
                'mcap_tao': int(latest_metrics.market_cap_tao) if latest_metrics.market_cap_tao else None,
                'fdv_tao': int(latest_metrics.fdv_tao) if latest_metrics.fdv_tao else None,
                'stake_weight': int(latest_metrics.total_stake_tao) if latest_metrics.total_stake_tao else None,
                'stake_quality': round(latest_metrics.stake_quality, 1) if latest_metrics.stake_quality else None,
                'sq_rank_pct': latest_metrics.stake_quality_rank_pct,
                'validator_util_pct': round(validator_util_pct, 1),
                'max_validators': max_validators,
                'active_validators': active_validators,
                'active_stake_ratio': round(latest_metrics.active_stake_ratio, 1) if latest_metrics.active_stake_ratio else None,
                'consensus_align_pct': round(latest_metrics.consensus_alignment, 1) if latest_metrics.consensus_alignment else None,
                'inflation_pct': round(latest_metrics.emission_pct, 2) if latest_metrics.emission_pct else None,
                'alpha_emitted_pct': round(latest_metrics.alpha_emitted_pct, 2) if latest_metrics.alpha_emitted_pct else None,
                'reserve_mom': latest_metrics.reserve_momentum,
                'buy_sell_ratio_24h': round(buy_sell_ratio, 2),
                'price_1d_pct': round(latest_metrics.price_1d_change, 1) if latest_metrics.price_1d_change else None,
                'price_7d_pct': round(latest_metrics.price_7d_change, 1) if latest_metrics.price_7d_change else None,
                'tao_score': round(latest_metrics.tao_score, 1) if latest_metrics.tao_score else None,
                'tao_score_rank_pct': latest_metrics.tao_score_rank_pct if hasattr(latest_metrics, 'tao_score_rank_pct') else None,
                'category_subnet_count': category_stats.subnet_count if category_stats else None
            }
            
            return metrics
            
    except Exception as e:
        logger.error(f"Error getting subnet metrics for insight: {e}")
        return {}

def format_metrics_for_gpt(metrics: Dict[str, Any]) -> str:
    """
    Format metrics for GPT v4 analysis with comprehensive context.
    
    Args:
        metrics: Subnet metrics dictionary with comprehensive data
        
    Returns:
        Formatted JSON string for GPT prompt
    """
    if not metrics:
        return "No metrics available for analysis."
    
    # Format reserve momentum
    reserve_mom = metrics.get('reserve_mom')
    if reserve_mom is None:
        reserve_mom_str = '"n/a"'
    else:
        reserve_mom_str = f'{reserve_mom:.3f}'
    
    # Build comprehensive context JSON
    context_json = {
        "name": metrics.get('name', 'Unknown'),
        "id": metrics.get('id', 0),
        "category": metrics.get('category', 'Unknown'),
        "price_tao": metrics.get('price_tao'),
        "mcap_tao": metrics.get('mcap_tao'),
        "fdv_tao": metrics.get('fdv_tao'),
        "stake_weight": metrics.get('stake_weight'),
        "stake_quality": metrics.get('stake_quality'),
        "sq_rank_pct": metrics.get('sq_rank_pct'),
        "validator_util_pct": metrics.get('validator_util_pct'),
        "max_validators": metrics.get('max_validators'),
        "active_stake_ratio": metrics.get('active_stake_ratio'),
        "consensus_align_pct": metrics.get('consensus_align_pct'),
        "inflation_pct": metrics.get('inflation_pct'),
        "alpha_emitted_pct": metrics.get('alpha_emitted_pct'),
        "reserve_mom": reserve_mom_str,
        "buy_sell_ratio_24h": metrics.get('buy_sell_ratio_24h'),
        "price_1d_pct": metrics.get('price_1d_pct'),
        "price_7d_pct": metrics.get('price_7d_pct'),
        "tao_score": metrics.get('tao_score'),
        "tao_score_rank_pct": metrics.get('tao_score_rank_pct'),
        "category_subnet_count": metrics.get('category_subnet_count')
    }
    
    import json
    return json.dumps(context_json, indent=2)

def get_cached_insight(netuid: int) -> Optional[str]:
    """
    Get cached insight from database if fresh (within 12 hours).
    Reduced TTL to ensure more frequent updates.
    
    Args:
        netuid: Subnet ID
        
    Returns:
        Cached insight text or None if not found/expired
    """
    try:
        with get_db() as session:
            # Check for fresh insight (within 12 hours instead of 24)
            cutoff_time = datetime.utcnow() - timedelta(hours=12)
            cached_insight = session.query(GptInsights).filter(
                GptInsights.netuid == netuid,
                GptInsights.ts > cutoff_time
            ).first()
            
            if cached_insight:
                logger.info(f"Using cached insight for subnet {netuid}")
                return cached_insight.text
            
            return None
            
    except Exception as e:
        logger.error(f"Error getting cached insight for subnet {netuid}: {e}")
        return None

def save_insight_to_db(netuid: int, text: str) -> bool:
    """
    Save insight to database with upsert logic.
    
    Args:
        netuid: Subnet ID
        text: Insight text
        
    Returns:
        True if saved successfully
    """
    try:
        with get_db() as session:
            # Use upsert logic: INSERT ... ON CONFLICT DO UPDATE
            existing = session.query(GptInsights).filter_by(netuid=netuid).first()
            
            if existing:
                # Update existing record
                existing.text = text
                existing.ts = datetime.utcnow()
            else:
                # Create new record
                new_insight = GptInsights(
                    netuid=netuid,
                    text=text,
                    ts=datetime.utcnow()
                )
                session.add(new_insight)
            
            session.commit()
            logger.info(f"Saved insight for subnet {netuid}")
            return True
            
    except Exception as e:
        logger.error(f"Error saving insight for subnet {netuid}: {e}")
        return False

def clear_gpt_insights_cache() -> bool:
    """
    Clear all GPT insights from the database cache.
    
    Returns:
        True if cleared successfully
    """
    try:
        with get_db() as session:
            # Delete all GPT insights
            session.query(GptInsights).delete()
            session.commit()
            logger.info("Cleared all GPT insights cache")
            return True
            
    except Exception as e:
        logger.error(f"Error clearing GPT insights cache: {e}")
        return False

def clear_subnet_insight_cache(netuid: int) -> bool:
    """
    Clear cached insight for a specific subnet to force regeneration.
    
    Args:
        netuid: Subnet ID
        
    Returns:
        True if cleared successfully
    """
    try:
        with get_db() as session:
            # Delete insight for specific subnet
            session.query(GptInsights).filter(GptInsights.netuid == netuid).delete()
            session.commit()
            logger.info(f"Cleared insight cache for subnet {netuid}")
            return True
            
    except Exception as e:
        logger.error(f"Error clearing insight cache for subnet {netuid}: {e}")
        return False

def generate_insight(netuid: int) -> str:
    """
    Generate GPT insight for a subnet with comprehensive analysis.
    
    Args:
        netuid: Subnet ID to analyze
        
    Returns:
        Generated insight text
    """
    if not client:
        return "GPT analysis unavailable - API key not configured."
    
    try:
        # Get comprehensive metrics
        metrics = get_subnet_metrics_for_insight(netuid)
        if not metrics:
            return "No metrics available for analysis."
        
        # Format context for GPT
        context_json = format_metrics_for_gpt(metrics)
        
        # GPT v4 Prompt Template
        system_prompt = """You are "TAO-Analytics Insight", a sell-side research analyst covering Bittensor subnets.
Audience: professional crypto investors. Tone: crisp, numbers-first, no hype, no emojis."""

        user_prompt = f"""Context JSON:
{context_json}

TASK – ≤200 words, three paragraphs, plain text:

1) **What it does** – one crisp sentence, include subnet name.

2) **Network health** – comment on stake-quality (incl rank), validator utilisation (X/Y), consensus, active-stake, TAO-Score (colour), inflation & supply-emitted; call out any red flags or strengths.

3) **Market angle** – price momentum (1d/7d), buy:sell, reserve-momentum if present, and how {metrics.get('name', 'this subnet')} ranks versus its category peers ({metrics.get('category_subnet_count', 0)}). Conclude with a one-word Buy-Signal (1–5) per rule:  
 TAO-Score ≥75 → 5; 60-74 → 4; 45-59 → 3; 30-44 → 2; <30 → 1.  
 Return as: "Buy-Signal: 3 /5 (neutral)".

Return exactly three paragraphs, no bullet lists, no markdown."""

        def make_api_call(max_tokens=MAX_TOKENS):
            """Make API call with retry logic."""
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=0.3,
                    top_p=0.9
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"OpenAI API error: {e}")
                return f"Analysis error: {str(e)}"
        
        # Generate insight with retry logic
        insight = make_api_call()
        
        # Check word count and retry if needed
        word_count = len(insight.split())
        if word_count > MAX_WORDS:
            logger.warning(f"Insight too long ({word_count} words), retrying with reduced tokens")
            insight = make_api_call(max_tokens=MAX_TOKENS // 2)
        
        return insight
        
    except Exception as e:
        logger.error(f"Error generating insight for subnet {netuid}: {e}")
        return f"Error generating analysis: {str(e)}"

def get_insight(netuid: int) -> str:
    """
    Get GPT insight for a subnet with caching.
    
    Args:
        netuid: Subnet ID
        
    Returns:
        Insight text (cached or generated)
    """
    try:
        # Check cache first
        cached = get_cached_insight(netuid)
        if cached:
            return cached
        
        # Generate new insight
        insight = generate_insight(netuid)
        
        # Save to cache
        if insight and not insight.startswith("Error"):
            save_insight_to_db(netuid, insight)
        
        return insight
        
    except Exception as e:
        logger.error(f"Error getting insight for subnet {netuid}: {e}")
        return f"Error retrieving analysis: {str(e)}"

# Global instance for easy access
gpt_insight_service = {
    'get_insight': get_insight,
    'get_cached_insight': get_cached_insight,
    'generate_insight': generate_insight,
    'save_insight_to_db': save_insight_to_db
} 