import os, json, pandas as pd
from sqlalchemy import create_engine, text, select, func, String
from sqlalchemy.orm import sessionmaker
from .db_utils import json_field, get_database_type
from models import SubnetMeta, ScreenerRaw

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///tao.sqlite")
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True)

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise

def get_base_query():
    """Get base query with database-agnostic JSON extraction using SQLAlchemy ORM."""
    # Use SQLAlchemy ORM with JSON helper
    query = select(
        SubnetMeta,
        func.coalesce(json_field(ScreenerRaw.raw_json, 'market_cap_tao'), 0).label('mcap_tao'),
        func.coalesce(json_field(ScreenerRaw.raw_json, 'net_volume_tao_24h'), 0).label('flow_24h'),
        json_field(ScreenerRaw.raw_json, 'github_repo').label('github_url'),
        json_field(ScreenerRaw.raw_json, 'subnet_url').label('website_url')
    ).select_from(
        SubnetMeta.__table__.outerjoin(ScreenerRaw.__table__, SubnetMeta.netuid == ScreenerRaw.netuid)
    )
    
    return query

def load_subnet_frame(category="All", search=""):
    """Return pandas DF filtered by category & search text."""
    query = get_base_query()
    
    # Add filters
    if category != "All":
        query = query.where(SubnetMeta.primary_category == category)
    
    if search:
        search_like = f"%{search.lower()}%"
        # Expanded search: match against all relevant fields
        query = query.where(
            func.lower(func.cast(SubnetMeta.netuid, String)).like(search_like) |
            func.lower(SubnetMeta.subnet_name).like(search_like) |
            func.lower(SubnetMeta.primary_category).like(search_like) |
            func.lower(SubnetMeta.secondary_tags).like(search_like) |
            func.lower(SubnetMeta.tagline).like(search_like) |
            func.lower(SubnetMeta.what_it_does).like(search_like) |
            func.lower(SubnetMeta.primary_use_case).like(search_like) |
            func.lower(SubnetMeta.key_technical_features).like(search_like)
        )
    
    # Execute query and convert to DataFrame
    with engine.connect() as conn:
        result = conn.execute(query)
        rows = result.fetchall()
        columns = list(result.keys())
        df = pd.DataFrame(rows, columns=columns)
    
    # ensure numeric with proper defaults
    df["mcap_tao"] = pd.to_numeric(df["mcap_tao"], errors="coerce").fillna(0.0)
    df["flow_24h"] = pd.to_numeric(df["flow_24h"], errors="coerce").fillna(0.0)
    return df

def load_screener_frame():
    """Return pandas DF optimized for screener charts with latest metrics."""
    from models import MetricsSnap
    
    query = select(
        SubnetMeta.netuid,
        SubnetMeta.subnet_name,
        SubnetMeta.primary_category,
        # Price and market data
        func.coalesce(json_field(ScreenerRaw.raw_json, 'price_tao'), 0).label('price_tao'),
        func.coalesce(json_field(ScreenerRaw.raw_json, 'market_cap_tao'), 0).label('market_cap_tao'),
        func.coalesce(json_field(ScreenerRaw.raw_json, 'fdv_tao'), 0).label('fdv_tao'),
        func.coalesce(json_field(ScreenerRaw.raw_json, 'total_stake_tao'), 0).label('total_stake_tao'),
        func.coalesce(json_field(ScreenerRaw.raw_json, 'tao_in'), 0).label('tao_in'),
        func.coalesce(json_field(ScreenerRaw.raw_json, 'buy_volume_tao_1d'), 0).label('buy_volume_tao_1d'),
        # Price changes from MetricsSnap
        MetricsSnap.price_7d_change,
        MetricsSnap.price_30d_change,
        # Flow and momentum
        func.coalesce(json_field(ScreenerRaw.raw_json, 'net_volume_tao_24h'), 0).label('flow_24h'),
        # Metrics from MetricsSnap
        MetricsSnap.reserve_momentum,
        MetricsSnap.stake_quality,
        MetricsSnap.validator_util_pct,
        MetricsSnap.active_stake_ratio,
        MetricsSnap.consensus_alignment,
        MetricsSnap.emission_pct,
        MetricsSnap.alpha_emitted_pct,
        MetricsSnap.tao_score,
        MetricsSnap.stake_quality_rank_pct,
        MetricsSnap.momentum_rank_pct,
        MetricsSnap.timestamp.label('metrics_timestamp'),
        ScreenerRaw.fetched_at.label('screener_timestamp')
    ).select_from(
        SubnetMeta.__table__
        .outerjoin(ScreenerRaw.__table__, SubnetMeta.netuid == ScreenerRaw.netuid)
        .outerjoin(MetricsSnap.__table__, SubnetMeta.netuid == MetricsSnap.netuid)
    ).where(
        # Get latest metrics for each subnet
        MetricsSnap.timestamp == (
            select(func.max(MetricsSnap.timestamp))
            .where(MetricsSnap.netuid == SubnetMeta.netuid)
            .correlate(SubnetMeta)
            .scalar_subquery()
        )
    )
    
    # Execute query and convert to DataFrame
    with engine.connect() as conn:
        result = conn.execute(query)
        rows = result.fetchall()
        columns = list(result.keys())
        df = pd.DataFrame(rows, columns=columns)
    
    # Ensure numeric with proper defaults
    numeric_columns = [
        'price_tao', 'market_cap_tao', 'fdv_tao', 'total_stake_tao', 'tao_in', 
        'buy_volume_tao_1d', 'price_7d_change', 'price_30d_change', 'flow_24h',
        'reserve_momentum', 'stake_quality', 'validator_util_pct', 'active_stake_ratio',
        'consensus_alignment', 'emission_pct', 'alpha_emitted_pct', 'tao_score',
        'stake_quality_rank_pct', 'momentum_rank_pct'
    ]
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    

    
    return df 