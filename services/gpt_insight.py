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

# GPT Insight Configuration
MODEL_NAME = "gpt-4o-2024-05-13"
MAX_WORDS = 200
MAX_TOKENS_V4 = 400
MAX_TOKENS_V5 = 850  # ~700 prompt + 150 answer

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
                'price_30d_pct': round(latest_metrics.price_30d_change, 1) if latest_metrics.price_30d_change else None,
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
        "price_30d_pct": metrics.get('price_30d_pct'),
        "tao_score": metrics.get('tao_score'),
        "tao_score_rank_pct": metrics.get('tao_score_rank_pct'),
        "category_subnet_count": metrics.get('category_subnet_count')
    }
    
    import json
    return json.dumps(context_json, indent=2)

def get_cached_insight(netuid: int) -> Optional[str]:
    """
    Get cached insight from database if the underlying data hasn't changed.
    Uses data-driven caching: only regenerates if metrics data is newer than cached insight.
    
    Args:
        netuid: Subnet ID
        
    Returns:
        Cached insight text or None if not found/expired
    """
    try:
        with get_db() as session:
            # Get the cached insight
            cached_insight = session.query(GptInsights).filter_by(netuid=netuid).first()
            
            if not cached_insight:
                logger.info(f"No cached insight found for subnet {netuid}")
                return None
            
            # Get the latest metrics timestamp for this subnet
            latest_metrics = session.query(MetricsSnap).filter_by(netuid=netuid)\
                .order_by(MetricsSnap.timestamp.desc()).first()
            
            if not latest_metrics or not latest_metrics.timestamp:
                logger.warning(f"No metrics data found for subnet {netuid}, using fallback TTL")
                # Fallback to 12-hour TTL if no metrics data available
                cutoff_time = datetime.utcnow() - timedelta(hours=12)
                if cached_insight.ts < cutoff_time:
                    logger.info(f"Cached insight for subnet {netuid} expired (fallback TTL)")
                    return None
                else:
                    logger.info(f"Using cached insight for subnet {netuid} (fallback TTL)")
                    return cached_insight.text
            
            # Data-driven caching: check if metrics data is newer than cached insight
            if latest_metrics.timestamp > cached_insight.ts:
                logger.info(f"Metrics data updated for subnet {netuid} since last insight generation")
                logger.info(f"Latest metrics: {latest_metrics.timestamp}, cached insight: {cached_insight.ts}")
                return None
            else:
                logger.info(f"Using cached insight for subnet {netuid} (data unchanged)")
                return cached_insight.text
            
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
    Generate GPT insight v4 for a subnet with comprehensive analysis.
    
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

        def make_api_call(max_tokens=MAX_TOKENS_V4):
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
            insight = make_api_call(max_tokens=MAX_TOKENS_V4 // 2)
        
        return insight
        
    except Exception as e:
        logger.error(f"Error generating insight for subnet {netuid}: {e}")
        return f"Error generating analysis: {str(e)}"

def get_subnet_metrics_for_insight_v5(netuid: int) -> Dict[str, Any]:
    """
    Get streamlined subnet metrics for GPT v5 analysis.
    
    Args:
        netuid: Subnet ID to analyze
        
    Returns:
        Dictionary with streamlined metrics for v5 analysis
    """
    try:
        with get_db() as session:
            # Get latest metrics snapshot
            latest_metrics = session.query(MetricsSnap).filter_by(netuid=netuid)\
                .order_by(MetricsSnap.timestamp.desc()).first()
            
            # Get subnet metadata
            subnet_meta = session.query(SubnetMeta).filter_by(netuid=netuid).first()
            
            # Get category stats for peer count
            category_stats = None
            if latest_metrics and latest_metrics.category:
                category_stats = session.query(CategoryStats).filter_by(category=latest_metrics.category).first()
            
            if not latest_metrics:
                return {}
            
            # Build streamlined v5 payload
            metrics = {
                'name': subnet_meta.subnet_name if subnet_meta else f'Subnet {netuid}',
                'id': netuid,
                'category': latest_metrics.category or 'Unknown',
                'peers_in_cat': category_stats.subnet_count if category_stats else 0,
                'price': round(latest_metrics.price_tao, 3) if latest_metrics.price_tao else None,
                'mcap_tao': int(latest_metrics.market_cap_tao) if latest_metrics.market_cap_tao else None,
                'fdv_tao': int(latest_metrics.fdv_tao) if latest_metrics.fdv_tao else None,
                'stake_weight': int(latest_metrics.total_stake_tao) if latest_metrics.total_stake_tao else None,
                'stake_quality': round(latest_metrics.stake_quality, 1) if latest_metrics.stake_quality else None,
                'validator_util': round(latest_metrics.validator_util_pct, 1) if latest_metrics.validator_util_pct else None,
                'active_stake_ratio': round(latest_metrics.active_stake_ratio, 1) if latest_metrics.active_stake_ratio else None,
                'consensus': round(latest_metrics.consensus_alignment, 1) if latest_metrics.consensus_alignment else None,
                'annual_infl': round(latest_metrics.emission_pct, 1) if latest_metrics.emission_pct else None,
                'reserve_momentum': round(latest_metrics.reserve_momentum, 2) if latest_metrics.reserve_momentum else None,
                'emission_progress': round(latest_metrics.alpha_emitted_pct, 1) if latest_metrics.alpha_emitted_pct else None,
                'price_1d_pct': round(latest_metrics.price_1d_change, 1) if latest_metrics.price_1d_change else None,
                'price_7d_pct': round(latest_metrics.price_7d_change, 1) if latest_metrics.price_7d_change else None,
                'price_30d_pct': round(latest_metrics.price_30d_change, 1) if latest_metrics.price_30d_change else None,
                'tao_score': round(latest_metrics.tao_score, 1) if latest_metrics.tao_score else None,
                'momentum_rank_pct': latest_metrics.momentum_rank_pct if hasattr(latest_metrics, 'momentum_rank_pct') else None,
                'stake_rank_pct': latest_metrics.stake_quality_rank_pct if hasattr(latest_metrics, 'stake_quality_rank_pct') else None
            }
            
            return metrics
            
    except Exception as e:
        logger.error(f"Error getting subnet metrics for v5 insight: {e}")
        return {}

def generate_insight_v5(netuid: int) -> str:
    """
    Generate GPT insight v5 for a subnet with streamlined analysis.
    
    Args:
        netuid: Subnet ID to analyze
        
    Returns:
        Generated insight text
    """
    if not client:
        return "GPT analysis unavailable - API key not configured."
    
    try:
        # Get streamlined metrics
        metrics = get_subnet_metrics_for_insight_v5(netuid)
        if not metrics:
            return "No metrics available for analysis."
        
        # Build context string in the exact format specified
        context_lines = [
            f"name={metrics.get('name', 'Unknown')}",
            f"id={metrics.get('id', 0)}",
            f"category={metrics.get('category', 'Unknown')}",
            f"peers_in_cat={metrics.get('peers_in_cat', 0)}",
            f"price={metrics.get('price', 'n/a')}",
            f"mcap_tao={metrics.get('mcap_tao', 'n/a')}",
            f"fdv_tao={metrics.get('fdv_tao', 'n/a')}",
            f"stake_weight={metrics.get('stake_weight', 'n/a')}",
            f"stake_quality={metrics.get('stake_quality', 'n/a')}",
            f"validator_util={metrics.get('validator_util', 'n/a')}",
            f"active_stake_ratio={metrics.get('active_stake_ratio', 'n/a')}",
            f"consensus={metrics.get('consensus', 'n/a')}",
            f"annual_infl={metrics.get('annual_infl', 'n/a')}",
            f"reserve_momentum={metrics.get('reserve_momentum', 'n/a')}",
            f"emission_progress={metrics.get('emission_progress', 'n/a')}",
            f"price_1d_pct={metrics.get('price_1d_pct', 'n/a')}",
            f"price_7d_pct={metrics.get('price_7d_pct', 'n/a')}",
            f"price_30d_pct={metrics.get('price_30d_pct', 'n/a')}",
            f"tao_score={metrics.get('tao_score', 'n/a')}",
            f"momentum_rank_pct={metrics.get('momentum_rank_pct', 'n/a')}",
            f"stake_rank_pct={metrics.get('stake_rank_pct', 'n/a')}"
        ]
        
        context = "\n".join(context_lines)
        
        # GPT v5 Prompt Template (exact specification)
        system_prompt = """You are a professional Bittensor subnet analyst writing for crypto investors.
Write ≤200 words. Start with the subnet name. End with: "Buy-Signal: X/5"."""

        user_prompt = f"""Context:
{context}

Guidelines:
1. One sentence what the subnet does.
2. Assess network health (stake, consensus, validators).
3. Assess token economics (inflation, emission progress, reserve momentum).
4. Comment on market action (price ∆, buy/sell flow, momentum rank).
5. Conclude with a 1–5 Buy-Signal (5 = strong buy, 3 = neutral, 1 = avoid).
Avoid hype; be concise, numeric, actionable."""

        def make_api_call(max_tokens=MAX_TOKENS_V5):
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
            insight = make_api_call(max_tokens=MAX_TOKENS_V5 // 2)
        
        return insight
        
    except Exception as e:
        logger.error(f"Error generating v5 insight for subnet {netuid}: {e}")
        return f"Error generating analysis: {str(e)}"

def get_insight(netuid: int) -> str:
    """
    Get GPT insight v5 for a subnet with data-driven caching.
    
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
        
        # Generate new insight using v5
        insight = generate_insight_v5(netuid)
        
        # Save to cache
        if insight and not insight.startswith("Error"):
            save_insight_to_db(netuid, insight)
        
        return insight
        
    except Exception as e:
        logger.error(f"Error getting insight for subnet {netuid}: {e}")
        return f"Error retrieving analysis: {str(e)}"


def get_latest_data_timestamp(netuid: int) -> Optional[datetime]:
    """
    Get the timestamp of the latest metrics data for a subnet.
    Useful for debugging caching behavior.
    
    Args:
        netuid: Subnet ID
        
    Returns:
        Latest metrics timestamp or None if no data available
    """
    try:
        with get_db() as session:
            latest_metrics = session.query(MetricsSnap).filter_by(netuid=netuid)\
                .order_by(MetricsSnap.timestamp.desc()).first()
            
            return latest_metrics.timestamp if latest_metrics else None
            
    except Exception as e:
        logger.error(f"Error getting latest data timestamp for subnet {netuid}: {e}")
        return None

def get_insight_cache_info(netuid: int) -> Dict[str, Any]:
    """
    Get detailed information about insight caching for a subnet.
    Useful for debugging and monitoring.
    
    Args:
        netuid: Subnet ID
        
    Returns:
        Dictionary with cache information
    """
    try:
        with get_db() as session:
            # Get cached insight
            cached_insight = session.query(GptInsights).filter_by(netuid=netuid).first()
            
            # Get latest metrics
            latest_metrics = session.query(MetricsSnap).filter_by(netuid=netuid)\
                .order_by(MetricsSnap.timestamp.desc()).first()
            
            info = {
                'netuid': netuid,
                'has_cached_insight': cached_insight is not None,
                'cached_insight_timestamp': cached_insight.ts if cached_insight else None,
                'latest_metrics_timestamp': latest_metrics.timestamp if latest_metrics else None,
                'cache_is_valid': False,
                'reason': 'No cached insight'
            }
            
            if not cached_insight:
                return info
            
            if not latest_metrics or not latest_metrics.timestamp:
                # Fallback to TTL check
                cutoff_time = datetime.utcnow() - timedelta(hours=12)
                info['cache_is_valid'] = cached_insight.ts >= cutoff_time
                info['reason'] = 'Using fallback TTL (no metrics data)'
            else:
                # Data-driven check
                info['cache_is_valid'] = latest_metrics.timestamp <= cached_insight.ts
                info['reason'] = 'Data-driven cache check'
            
            return info
            
    except Exception as e:
        logger.error(f"Error getting cache info for subnet {netuid}: {e}")
        return {
            'netuid': netuid,
            'error': str(e),
            'cache_is_valid': False
        }

def extract_buy_signal_from_insight(insight_text: str) -> Optional[int]:
    """
    Extract buy signal score (1-5) from GPT insight text.
    
    Args:
        insight_text: The full insight text from GPT
        
    Returns:
        Buy signal score (1-5) or None if not found
    """
    if not insight_text:
        return None
    
    try:
        # Look for "Buy-Signal: X/5" pattern
        import re
        pattern = r'Buy-Signal:\s*(\d+)/5'
        match = re.search(pattern, insight_text, re.IGNORECASE)
        
        if match:
            score = int(match.group(1))
            # Validate score is in valid range
            if 1 <= score <= 5:
                return score
        
        return None
        
    except Exception as e:
        logger.error(f"Error extracting buy signal from insight: {e}")
        return None

def get_buy_signal_from_db(netuid: int) -> Optional[int]:
    """
    Get buy signal score for a subnet directly from the database.
    
    Args:
        netuid: Subnet ID
        
    Returns:
        Buy signal score (1-5) or None if not available
    """
    try:
        with get_db() as session:
            # Get the latest metrics snapshot for this subnet
            latest_snap = session.query(MetricsSnap).filter_by(netuid=netuid)\
                .order_by(MetricsSnap.timestamp.desc()).first()
            
            if latest_snap and latest_snap.buy_signal is not None:
                return latest_snap.buy_signal
            
            return None
            
    except Exception as e:
        logger.error(f"Error getting buy signal from DB for subnet {netuid}: {e}")
        return None

def get_buy_signal_for_subnet(netuid: int) -> Optional[int]:
    """
    Get buy signal score for a subnet from database first, then from cached insight.
    
    Args:
        netuid: Subnet ID
        
    Returns:
        Buy signal score (1-5) or None if not available
    """
    try:
        # First try to get from database
        db_signal = get_buy_signal_from_db(netuid)
        if db_signal is not None:
            return db_signal
        
        # Fallback to cached insight
        cached_insight = get_cached_insight(netuid)
        
        if cached_insight:
            return extract_buy_signal_from_insight(cached_insight)
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting buy signal for subnet {netuid}: {e}")
        return None

# Global instance for easy access
gpt_insight_service = {
    'get_insight': get_insight,
    'get_cached_insight': get_cached_insight,
    'generate_insight': generate_insight,
    'generate_insight_v5': generate_insight_v5,
    'save_insight_to_db': save_insight_to_db,
    'clear_gpt_insights_cache': clear_gpt_insights_cache,
    'clear_subnet_insight_cache': clear_subnet_insight_cache,
    'get_latest_data_timestamp': get_latest_data_timestamp,
    'get_insight_cache_info': get_insight_cache_info,
    'extract_buy_signal_from_insight': extract_buy_signal_from_insight,
    'get_buy_signal_for_subnet': get_buy_signal_for_subnet,
    'get_buy_signal_from_db': get_buy_signal_from_db
} 