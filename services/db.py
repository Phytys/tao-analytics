import os, json, pandas as pd
import re
import signal
from contextlib import contextmanager
from sqlalchemy import create_engine, text, select, func, String, and_, Numeric, or_
from sqlalchemy.orm import sessionmaker
from .db_utils import json_field, get_database_type
from models import SubnetMeta, ScreenerRaw
from config import TAO_SCORE_COLUMN

# Use HEROKU_DATABASE_URL for scripts that need to write to Heroku
# Use DATABASE_URL for the main app (defaults to SQLite for development)
HEROKU_DATABASE_URL = os.getenv("HEROKU_DATABASE_URL")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///tao.sqlite")

# For data collection scripts, prefer Heroku database if available
if HEROKU_DATABASE_URL:
    ACTIVE_DATABASE_URL = HEROKU_DATABASE_URL
else:
    ACTIVE_DATABASE_URL = DATABASE_URL

# Fix Heroku postgres:// URLs to postgresql://
if ACTIVE_DATABASE_URL.startswith("postgres://"):
    ACTIVE_DATABASE_URL = ACTIVE_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Configure connection pooling for Heroku PostgreSQL
if ACTIVE_DATABASE_URL.startswith("postgresql://"):
    # Heroku PostgreSQL connection pool configuration
    engine = create_engine(
        ACTIVE_DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,  # Maximum number of connections in the pool
        max_overflow=10,  # Maximum number of connections that can be created beyond pool_size
        pool_timeout=30,  # Timeout for getting a connection from the pool
        pool_recycle=3600,  # Recycle connections after 1 hour
        future=True
    )
else:
    # SQLite configuration (development)
    engine = create_engine(ACTIVE_DATABASE_URL, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True)

@contextmanager
def query_timeout(seconds=30):
    """Context manager to timeout long-running queries."""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Query timed out after {seconds} seconds")
    
    # Set up signal handler for timeout
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        # Restore original signal handler and cancel alarm
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

def sanitize_search_input(search_text):
    """Sanitize search input to prevent SQL injection."""
    if not search_text:
        return ""
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[;\'"\\]', '', search_text)
    # Limit length
    return sanitized[:100]

def get_db():
    """Get database session with timeout protection."""
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise

def safe_query_execute(query, timeout_seconds=30, limit=10000):
    """Execute a query with timeout protection and limits."""
    try:
        with query_timeout(timeout_seconds):
            # Add limit if not already present
            if hasattr(query, 'limit') and not hasattr(query, '_limit_applied'):
                query = query.limit(limit)
                query._limit_applied = True
            
            return query
    except TimeoutError:
        print(f"Query timed out after {timeout_seconds} seconds")
        raise
    except Exception as e:
        print(f"Query execution error: {e}")
        raise

def get_base_query():
    """Get base query with database-agnostic JSON extraction using SQLAlchemy ORM."""
    from models import MetricsSnap
    
    # Use SQLAlchemy ORM with JSON helper and TAO scores - simplified to avoid casting issues
    query = select(
        SubnetMeta,
        json_field(ScreenerRaw.raw_json, 'market_cap_tao').label('mcap_tao'),
        json_field(ScreenerRaw.raw_json, 'net_volume_tao_24h').label('flow_24h'),
        json_field(ScreenerRaw.raw_json, 'net_volume_tao_7d').label('net_volume_tao_7d'),
        json_field(ScreenerRaw.raw_json, 'github_repo').label('github_url'),
        json_field(ScreenerRaw.raw_json, 'subnet_url').label('website_url'),
        getattr(MetricsSnap, TAO_SCORE_COLUMN).label('tao_score')
    ).select_from(
        SubnetMeta.__table__
        .outerjoin(ScreenerRaw.__table__, SubnetMeta.netuid == ScreenerRaw.netuid)
        .outerjoin(
            MetricsSnap.__table__, 
            and_(
                SubnetMeta.netuid == MetricsSnap.netuid,
                MetricsSnap.timestamp == (
                    select(func.max(MetricsSnap.timestamp))
                    .where(MetricsSnap.netuid == SubnetMeta.netuid)
                    .correlate(SubnetMeta)
                    .scalar_subquery()
                )
            )
        )
    ).where(
        # Only include subnets with valid TAO scores
        getattr(MetricsSnap, TAO_SCORE_COLUMN).isnot(None)
    )
    
    return query

def load_subnet_frame(category="All", search=""):
    """Return pandas DF filtered by category & search text."""
    query = get_base_query()
    
    # Sanitize inputs
    category = sanitize_search_input(category) if category else "All"
    search = sanitize_search_input(search) if search else ""
    
    # Add filters
    if category != "All":
        query = query.where(SubnetMeta.primary_category == category)
    
    if search:
        # Handle Greek character mappings for search
        greek_mappings = {
            't': 'τ', 'T': 'τ',  # Latin T to Greek tau
            'a': 'α', 'A': 'α',  # Latin A to Greek alpha
            'b': 'β', 'B': 'β',  # Latin B to Greek beta
            'g': 'γ', 'G': 'γ',  # Latin G to Greek gamma
            'd': 'δ', 'D': 'δ',  # Latin D to Greek delta
            'e': 'ε', 'E': 'ε',  # Latin E to Greek epsilon
            'z': 'ζ', 'Z': 'ζ',  # Latin Z to Greek zeta
            'h': 'η', 'H': 'η',  # Latin H to Greek eta
            'i': 'ι', 'I': 'ι',  # Latin I to Greek iota
            'k': 'κ', 'K': 'κ',  # Latin K to Greek kappa
            'l': 'λ', 'L': 'λ',  # Latin L to Greek lambda
            'm': 'μ', 'M': 'μ',  # Latin M to Greek mu
            'n': 'ν', 'N': 'ν',  # Latin N to Greek nu
            'x': 'ξ', 'X': 'ξ',  # Latin X to Greek xi
            'o': 'ο', 'O': 'ο',  # Latin O to Greek omicron
            'p': 'π', 'P': 'π',  # Latin P to Greek pi
            'r': 'ρ', 'R': 'ρ',  # Latin R to Greek rho
            's': 'σ', 'S': 'σ',  # Latin S to Greek sigma
            'u': 'υ', 'U': 'υ',  # Latin U to Greek upsilon
            'f': 'φ', 'F': 'φ',  # Latin F to Greek phi
            'c': 'χ', 'C': 'χ',  # Latin C to Greek chi
            'y': 'ψ', 'Y': 'ψ',  # Latin Y to Greek psi
            'w': 'ω', 'W': 'ω',  # Latin W to Greek omega
        }
        
        # Create Greek version of search query - only convert first character if it's a single letter
        greek_search = search
        if len(search) > 0 and search[0].lower() in greek_mappings:
            # Only convert the first character to Greek
            first_char = search[0]
            if first_char in greek_mappings:
                greek_search = greek_mappings[first_char] + search[1:]
            elif first_char.lower() in greek_mappings:
                greek_search = greek_mappings[first_char.lower()] + search[1:]
        
        # Build search conditions for both original and Greek versions
        search_conditions = []
        
        # Original search
        search_like = f"%{search.lower()}%"
        search_conditions.append(
            func.lower(func.cast(SubnetMeta.netuid, String)).like(search_like) |
            func.lower(SubnetMeta.subnet_name).like(search_like) |
            func.lower(SubnetMeta.primary_category).like(search_like) |
            func.lower(SubnetMeta.secondary_tags).like(search_like) |
            func.lower(SubnetMeta.tagline).like(search_like) |
            func.lower(SubnetMeta.what_it_does).like(search_like) |
            func.lower(SubnetMeta.primary_use_case).like(search_like) |
            func.lower(SubnetMeta.key_technical_features).like(search_like)
        )
        
        # Greek search (if different from original)
        if greek_search != search:
            greek_like = f"%{greek_search.lower()}%"
            search_conditions.append(
                func.lower(SubnetMeta.subnet_name).like(greek_like) |
                func.lower(SubnetMeta.primary_category).like(greek_like) |
                func.lower(SubnetMeta.secondary_tags).like(greek_like) |
                func.lower(SubnetMeta.tagline).like(greek_like) |
                func.lower(SubnetMeta.what_it_does).like(greek_like) |
                func.lower(SubnetMeta.primary_use_case).like(greek_like) |
                func.lower(SubnetMeta.key_technical_features).like(greek_like)
            )
        
        # Combine all search conditions
        if len(search_conditions) == 1:
            query = query.where(search_conditions[0])
        else:
            query = query.where(search_conditions[0] | search_conditions[1])
        
        # Debug: Print search info
        print(f"Search debug - Original: '{search}', Greek: '{greek_search}', Conditions: {len(search_conditions)}")
    
    # Execute query and convert to DataFrame
    with engine.connect() as conn:
        result = conn.execute(query)
        rows = result.fetchall()
        columns = list(result.keys())
        df = pd.DataFrame(rows, columns=columns)
    
    # ensure numeric with proper defaults
    df["mcap_tao"] = pd.to_numeric(df["mcap_tao"], errors="coerce").fillna(0.0)
    df["flow_24h"] = pd.to_numeric(df["flow_24h"], errors="coerce").fillna(0.0)
    df["net_volume_tao_7d"] = pd.to_numeric(df["net_volume_tao_7d"], errors="coerce").fillna(0.0)
    df["tao_score"] = pd.to_numeric(df["tao_score"], errors="coerce").fillna(0.0)
    return df

def load_screener_frame():
    """Return pandas DF optimized for screener charts with latest metrics."""
    from models import MetricsSnap
    
    query = select(
        SubnetMeta.netuid,
        SubnetMeta.subnet_name,
        SubnetMeta.primary_category,
        # Price and market data
        json_field(ScreenerRaw.raw_json, 'price_tao').label('price_tao'),
        json_field(ScreenerRaw.raw_json, 'market_cap_tao').label('market_cap_tao'),
        json_field(ScreenerRaw.raw_json, 'fdv_tao').label('fdv_tao'),
        json_field(ScreenerRaw.raw_json, 'total_stake_tao').label('total_stake_tao'),
        json_field(ScreenerRaw.raw_json, 'tao_in').label('tao_in'),
        json_field(ScreenerRaw.raw_json, 'buy_volume_tao_1d').label('buy_volume_tao_1d'),
        # Price changes from MetricsSnap
        MetricsSnap.price_1h_change,
        MetricsSnap.price_1d_change,
        MetricsSnap.price_7d_change,
        MetricsSnap.price_30d_change,
        # Volume analysis
        MetricsSnap.sell_volume_tao_1d,
        MetricsSnap.total_volume_tao_1d,
        MetricsSnap.buy_sell_ratio,
        MetricsSnap.net_volume_tao_1h,
        MetricsSnap.net_volume_tao_7d,
        MetricsSnap.buy_volume_pct_change,
        MetricsSnap.sell_volume_pct_change,
        MetricsSnap.total_volume_pct_change,
        # Flow and momentum (legacy)
        json_field(ScreenerRaw.raw_json, 'net_volume_tao_24h').label('flow_24h'),
        # Network health
        MetricsSnap.uid_count,
        MetricsSnap.active_validators,
        MetricsSnap.validators_active,
        MetricsSnap.max_validators,
        # Stake distribution
        MetricsSnap.stake_hhi,
        MetricsSnap.hhi,
        MetricsSnap.gini_coeff_top_100,
        # Core metrics from MetricsSnap
        MetricsSnap.reserve_momentum,
        MetricsSnap.stake_quality,
        MetricsSnap.validator_util_pct,
        MetricsSnap.active_stake_ratio,
        MetricsSnap.consensus_alignment,
        MetricsSnap.emission_pct,
        MetricsSnap.alpha_emitted_pct,
        MetricsSnap.emission_roi,
        getattr(MetricsSnap, TAO_SCORE_COLUMN).label('tao_score'),
        MetricsSnap.stake_quality_rank_pct,
        MetricsSnap.momentum_rank_pct,
        # PnL and performance
        MetricsSnap.realized_pnl_tao,
        MetricsSnap.unrealized_pnl_tao,
        MetricsSnap.ath_60d,
        MetricsSnap.atl_60d,
        # Token flow
        MetricsSnap.alpha_in,
        MetricsSnap.alpha_out,
        MetricsSnap.alpha_circ,
        MetricsSnap.alpha_prop,
        MetricsSnap.root_prop,
        # Timestamps
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
        'buy_volume_tao_1d', 'price_1h_change', 'price_1d_change', 'price_7d_change', 'price_30d_change',
        'sell_volume_tao_1d', 'total_volume_tao_1d', 'buy_sell_ratio', 'net_volume_tao_1h', 'net_volume_tao_7d',
        'buy_volume_pct_change', 'sell_volume_pct_change', 'total_volume_pct_change', 'flow_24h',
        'uid_count', 'active_validators', 'validators_active', 'max_validators',
        'stake_hhi', 'hhi', 'gini_coeff_top_100', 'reserve_momentum', 'stake_quality', 
        'validator_util_pct', 'active_stake_ratio', 'consensus_alignment', 'emission_pct', 
        'alpha_emitted_pct', 'emission_roi', 'tao_score', 'stake_quality_rank_pct', 'momentum_rank_pct',
        'realized_pnl_tao', 'unrealized_pnl_tao', 'ath_60d', 'atl_60d',
        'alpha_in', 'alpha_out', 'alpha_circ', 'alpha_prop', 'root_prop'
    ]
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    

    
    return df 

# --- Unified search function for all search bars (API and Dash) ---
def search_subnets(query=None, category=None, return_type='dataframe', limit=10):
    """
    Unified search for subnets. Handles netuid, name (with Greek/Latin mapping), category, etc.
    Args:
        query: Search string (can be netuid, name, etc.)
        category: Optional category filter
        return_type: 'dataframe' (default) or 'dict' (for API)
        limit: Max number of results (for API)
    Returns:
        DataFrame (for Dash) or list of dicts (for API)
    """
    from models import SubnetMeta
    
    # Sanitize inputs
    category = sanitize_search_input(category) if category else "All"
    search = sanitize_search_input(query) if query else ""
    
    # Start query
    query_obj = get_base_query()
    
    # Category filter
    if category != "All":
        query_obj = query_obj.where(SubnetMeta.primary_category == category)
    
    # Search logic
    search_conditions = []
    if search:
        # Netuid search
        if search.isdigit():
            search_conditions.append(SubnetMeta.netuid == int(search))
        
        # Greek/Latin mapping (first character only)
        greek_mappings = {
            't': 'τ', 'T': 'τ',
            'a': 'α', 'A': 'α',
            'b': 'β', 'B': 'β',
            'g': 'γ', 'G': 'γ',
            'd': 'δ', 'D': 'δ',
            'e': 'ε', 'E': 'ε',
            'z': 'ζ', 'Z': 'ζ',
            'h': 'η', 'H': 'η',
            'i': 'ι', 'I': 'ι',
            'k': 'κ', 'K': 'κ',
            'l': 'λ', 'L': 'λ',
            'm': 'μ', 'M': 'μ',
            'n': 'ν', 'N': 'ν',
            'x': 'ξ', 'X': 'ξ',
            'o': 'ο', 'O': 'ο',
            'p': 'π', 'P': 'π',
            'r': 'ρ', 'R': 'ρ',
            's': 'σ', 'S': 'σ',
            'u': 'υ', 'U': 'υ',
            'f': 'φ', 'F': 'φ',
            'c': 'χ', 'C': 'χ',
            'y': 'ψ', 'Y': 'ψ',
            'w': 'ω', 'W': 'ω',
        }
        greek_search = search
        if len(search) > 0 and search[0].lower() in greek_mappings:
            first_char = search[0]
            if first_char in greek_mappings:
                greek_search = greek_mappings[first_char] + search[1:]
            elif first_char.lower() in greek_mappings:
                greek_search = greek_mappings[first_char.lower()] + search[1:]
        
        # Name/category/tagline/fields search (original and Greek-mapped)
        search_like = f"%{search.lower()}%"
        greek_like = f"%{greek_search.lower()}%" if greek_search != search else None
        
        name_fields = [
            SubnetMeta.subnet_name,
            SubnetMeta.primary_category,
            SubnetMeta.secondary_tags,
            SubnetMeta.tagline,
            SubnetMeta.what_it_does,
            SubnetMeta.primary_use_case,
            SubnetMeta.key_technical_features,
        ]
        
        # Original
        for field in name_fields:
            search_conditions.append(func.lower(field).like(search_like))
        # Greek-mapped
        if greek_like:
            for field in name_fields:
                search_conditions.append(func.lower(field).like(greek_like))
    
    # Combine all search conditions
    if search_conditions:
        query_obj = query_obj.where(or_(*search_conditions))
    
    # Execute query and convert to DataFrame
    with engine.connect() as conn:
        result = conn.execute(query_obj)
        rows = result.fetchall()
        columns = list(result.keys())
        df = pd.DataFrame(rows, columns=columns)
    
    # Ensure numeric with proper defaults (for Dash)
    for col in ["mcap_tao", "flow_24h", "net_volume_tao_7d", "tao_score"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    
    if return_type == 'dataframe':
        return df
    else:
        # For API: return list of dicts (limit results)
        results = []
        for _, row in df.iterrows():
            results.append({
                'netuid': row.get('netuid'),
                'name': row.get('subnet_name') or f"Subnet {row.get('netuid')}",
                'category': row.get('primary_category'),
            })
            if len(results) >= limit:
                break
        return results 