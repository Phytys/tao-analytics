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