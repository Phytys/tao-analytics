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
from config import OPENAI_KEY, OPENAI_MODEL

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

def get_subnet_metrics_for_insight(netuid: int) -> Dict[str, Any]:
    """
    Get expert-level subnet metrics for GPT analysis with rank percentages.
    
    Args:
        netuid: Subnet ID to analyze
        
    Returns:
        Dictionary with distilled metrics for expert commentary
    """
    try:
        with get_db() as session:
            # Get latest metrics snapshot
            latest_metrics = session.query(MetricsSnap).filter_by(netuid=netuid)\
                .order_by(MetricsSnap.timestamp.desc()).first()
            
            # Get subnet metadata
            subnet_meta = session.query(SubnetMeta).filter_by(netuid=netuid).first()
            
            if not latest_metrics:
                return {}
            
            # Build expert-level payload with only essential cues
            metrics = {
                'netuid': netuid,
                'name': subnet_meta.subnet_name if subnet_meta else f'Subnet {netuid}',
                'category': latest_metrics.category or 'Unknown',
                
                # Core metrics with rank percentages
                'stake_quality_score': latest_metrics.stake_quality,
                'stake_quality_rank_pct': latest_metrics.stake_quality_rank_pct,
                'momentum_pct': latest_metrics.reserve_momentum,
                'momentum_rank_pct': latest_metrics.momentum_rank_pct,
                'validators_active': latest_metrics.active_validators,
                'validator_util_pct': latest_metrics.validator_util_pct,
                'consensus_alignment': latest_metrics.consensus_alignment,
                'trust_score': latest_metrics.trust_score,
                'buy_sell_ratio': latest_metrics.buy_sell_ratio,
            }
            
            return metrics
            
    except Exception as e:
        logger.error(f"Error getting subnet metrics for insight: {e}")
        return {}

def format_metrics_for_gpt(metrics: Dict[str, Any]) -> str:
    """
    Format metrics for expert-level GPT analysis with rank percentages.
    
    Args:
        metrics: Subnet metrics dictionary with rank percentages
        
    Returns:
        Formatted string for GPT prompt
    """
    if not metrics:
        return "No metrics available for analysis."
    
    # Extract expert-level metrics
    netuid = metrics.get('netuid', 'Unknown')
    name = metrics.get('name', f'Subnet {netuid}')
    category = metrics.get('category', 'Unknown')
    
    # Core metrics with rank percentages
    stake_quality_score = metrics.get('stake_quality_score')
    stake_quality_rank_pct = metrics.get('stake_quality_rank_pct')
    momentum_pct = metrics.get('momentum_pct')
    momentum_rank_pct = metrics.get('momentum_rank_pct')
    validators_active = metrics.get('validators_active')
    validator_util_pct = metrics.get('validator_util_pct')
    consensus_alignment = metrics.get('consensus_alignment')
    trust_score = metrics.get('trust_score')
    buy_sell_ratio = metrics.get('buy_sell_ratio')
    
    # Format the expert-level prompt
    formatted = f"""
You are writing a 90-110-word briefing for crypto investors.

Data:
{{
  "netuid": {netuid},
  "name": "{name}",
  "category": "{category}",
  "stake_quality_score": {stake_quality_score},
  "stake_quality_rank_pct": {stake_quality_rank_pct},
  "momentum_pct": {momentum_pct},
  "momentum_rank_pct": {momentum_rank_pct},
  "validators_active": {validators_active},
  "validator_util_pct": {validator_util_pct},
  "consensus_alignment": {consensus_alignment},
  "trust_score": {trust_score},
  "buy_sell_ratio": {buy_sell_ratio}
}}

Write 2–3 sentences:
• Sentence 1 – what the subnet does (use name + category).
• Sentence 2 – health: stake quality vs peer %, validator utilisation, consensus / trust.
• Sentence 3 – capital flow: buy:sell ratio and momentum rank; flag risk or upside.

Avoid numeric overkill: max 5 numbers. No questions; no bullet points.
"""
    
    return formatted

def get_cached_insight(netuid: int) -> Optional[str]:
    """
    Get cached insight from database if fresh (within 24 hours).
    
    Args:
        netuid: Subnet ID
        
    Returns:
        Cached insight text or None if not found/expired
    """
    try:
        with get_db() as session:
            # Check for fresh insight (within 24 hours)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
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

def generate_insight(netuid: int) -> str:
    """
    Generate AI-powered insight for a subnet.
    
    Args:
        netuid: Subnet ID to analyze
        
    Returns:
        AI-generated insight text (120 words max) or fallback message
    """
    # Check if we're in development mode or no OpenAI key
    if not client or os.getenv('FLASK_ENV') == 'development':
        logger.info(f"GPT disabled in dev mode for subnet {netuid}")
        return "(demo insight – GPT disabled in dev)"
    
    try:
        # Get subnet metrics
        metrics = get_subnet_metrics_for_insight(netuid)
        if not metrics:
            logger.warning(f"No metrics available for subnet {netuid}")
            return "Unable to generate insight - no subnet data available."
        
        # Add netuid to metrics for context
        metrics['netuid'] = netuid
        
        # Format metrics for GPT
        formatted_metrics = format_metrics_for_gpt(metrics)
        
        # Call OpenAI API with v1 prompt format
        def make_api_call(max_tokens=300):
            if not client:
                return "(demo insight – GPT disabled in dev)"
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "user", "content": formatted_metrics}
                ],
                max_tokens=max_tokens,
                temperature=0.3
            )
            return response.choices[0].message.content.strip() if response.choices[0].message.content else ""
        
        # First attempt
        insight = make_api_call(max_tokens=300)
        
        if insight:
            # Check for truncation: too short or doesn't end with proper punctuation
            words = insight.split()
            if len(words) < 15 or not insight.rstrip().endswith((".", "!", "?")):
                logger.info(f"Insight appears truncated for subnet {netuid}, retrying with more tokens...")
                # Retry with more tokens
                insight = make_api_call(max_tokens=400)
            
            # Final length check (120 words ≈ 600 characters)
            if len(insight) > 600:
                insight = insight[:597] + "..."
            
            logger.info(f"Generated insight for subnet {netuid}: {len(insight.split())} words, {len(insight)} characters")
            return insight
        else:
            logger.warning(f"No insight generated for subnet {netuid}")
            return "Unable to generate AI insight at this time."
        
    except Exception as e:
        logger.error(f"Error generating insight for subnet {netuid}: {e}")
        return "Error generating insight - please try again later."

def get_insight(netuid: int) -> str:
    """
    Get insight for a subnet - cached or generate new.
    
    Args:
        netuid: Subnet ID
        
    Returns:
        Insight text (cached or newly generated)
    """
    # First try to get from cache
    cached_insight = get_cached_insight(netuid)
    if cached_insight:
        return cached_insight
    
    # Generate new insight
    insight = generate_insight(netuid)
    
    # Save to database (only if it's not a demo/error message)
    if insight and not insight.startswith("(demo") and not insight.startswith("Unable to") and not insight.startswith("Error"):
        save_insight_to_db(netuid, insight)
    
    return insight

# Global instance for easy access
gpt_insight_service = {
    'get_insight': get_insight,
    'get_cached_insight': get_cached_insight,
    'generate_insight': generate_insight,
    'save_insight_to_db': save_insight_to_db
} 