import os, json, pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .db_utils import json_field, get_db_dialect

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
    """Get base query with database-agnostic JSON extraction."""
    dialect = get_db_dialect()
    
    if dialect == 'sqlite':
        return """
        SELECT sm.*,
               COALESCE(json_extract(sr.raw_json,'$.market_cap_tao'), 0)      AS mcap_tao,
               COALESCE(json_extract(sr.raw_json,'$.net_volume_tao_24h'), 0) AS flow_24h,
               json_extract(sr.raw_json,'$.github_repo')                    AS github_url,
               json_extract(sr.raw_json,'$.subnet_url')                     AS website_url
        FROM   subnet_meta sm
        LEFT JOIN screener_raw sr USING(netuid)
        """
    else:
        # PostgreSQL version
        return """
        SELECT sm.*,
               COALESCE((sr.raw_json->>'market_cap_tao')::numeric, 0)      AS mcap_tao,
               COALESCE((sr.raw_json->>'net_volume_tao_24h')::numeric, 0) AS flow_24h,
               sr.raw_json->>'github_repo'                                AS github_url,
               sr.raw_json->>'subnet_url'                                 AS website_url
        FROM   subnet_meta sm
        LEFT JOIN screener_raw sr USING(netuid)
        """

def load_subnet_frame(category="All", search=""):
    """Return pandas DF filtered by category & search text."""
    clause = []
    params = {}
    if category != "All":
        clause.append("sm.primary_category = :cat"); params["cat"] = category
    if search:
        like = f"%{search.lower()}%"
        clause.append("(lower(sm.subnet_name) LIKE :sea OR lower(sm.secondary_tags) LIKE :sea)")
        params["sea"] = like
    where = "WHERE " + " AND ".join(clause) if clause else ""
    
    query = get_base_query() + where
    df = pd.read_sql(text(query), engine, params=params)
    
    # ensure numeric with proper defaults
    df["mcap_tao"] = pd.to_numeric(df.mcap_tao, errors="coerce").fillna(0.0)
    df["flow_24h"] = pd.to_numeric(df.flow_24h, errors="coerce").fillna(0.0)
    return df 