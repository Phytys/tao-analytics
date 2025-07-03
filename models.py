from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    JSON, Text, DateTime, func, Boolean
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

from config import DB_URL

Base = declarative_base()
engine = create_engine(DB_URL, echo=False, future=True)
Session = sessionmaker(bind=engine, autoflush=False)

class ScreenerRaw(Base):
    __tablename__ = "screener_raw"
    netuid = Column(Integer, primary_key=True)
    raw_json = Column(JSON)
    fetched_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

class SubnetMeta(Base):
    __tablename__ = "subnet_meta"
    netuid = Column(Integer, primary_key=True)
    subnet_name = Column(String)

    # — fields to be filled by the LLM —
    tagline = Column(String)
    what_it_does = Column(Text)
    primary_use_case = Column(Text)  # What is the subnet's primary use case?
    key_technical_features = Column(Text)  # What are the key technical features?
    primary_category = Column(String(32))  # New granular category
    category_suggestion = Column(Text)  # LLM suggestion for new category if needed
    secondary_tags = Column(Text)  # CSV string of normalized tags
    confidence = Column(Float)
    context_hash = Column(String)  # MD5 hash of the context JSON
    context_tokens = Column(Integer, default=0)  # How much context was available
    provenance = Column(Text)  # JSON string tracking where each field came from
    privacy_security_flag = Column(Boolean, default=False)  # Privacy/security focus flag
    favicon_url = Column(String)  # Cached favicon URL for the subnet

    # — timestamps —
    last_enriched_at = Column(DateTime)  # When LLM fields were last updated
    updated_at = Column(DateTime, onupdate=func.now())

class CoinGeckoPrice(Base):
    __tablename__ = 'coingecko'
    id = Column(Integer, primary_key=True, autoincrement=True)
    price_usd = Column(Float, nullable=False)
    market_cap_usd = Column(Float, nullable=True)  # Bittensor's total market cap
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class MetricsSnap(Base):
    """Nightly snapshot of subnet metrics for historical analysis."""
    __tablename__ = "metrics_snap"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)  # Snapshot timestamp
    netuid = Column(Integer, nullable=False, index=True)  # Subnet ID
    
    # Market metrics from screener
    market_cap_tao = Column(Float)  # Market cap in TAO
    flow_24h = Column(Float)  # 24h net volume in TAO
    price_tao = Column(Float)  # Price in TAO
    
    # NEW: Price action metrics from screener
    price_1d_change = Column(Float)  # 1-day price change %
    price_7d_change = Column(Float)  # 7-day price change %
    price_30d_change = Column(Float)  # 30-day price change %
    buy_volume_tao_1d = Column(Float)  # 24h buy volume in TAO
    sell_volume_tao_1d = Column(Float)  # 24h sell volume in TAO
    
    # NEW: Flow metrics from screener
    tao_in = Column(Float)  # TAO reserves
    alpha_circ = Column(Float)  # Circulating Alpha tokens
    alpha_prop = Column(Float)  # Alpha proportion
    root_prop = Column(Float)  # Root proportion
    
    # Stake metrics from SDK
    total_stake_tao = Column(Float)  # Total stake in TAO
    stake_hhi = Column(Float)  # Herfindahl-Hirschman Index (0-10,000)
    uid_count = Column(Integer)  # Number of registered UIDs
    
    # Incentive metrics from SDK
    mean_incentive = Column(Float)  # Average incentive across UIDs
    p95_incentive = Column(Float)  # 95th percentile incentive
    
    # Network health metrics
    consensus_alignment = Column(Float)  # Percentage within ±0.10 of mean consensus
    trust_score = Column(Float)  # Average trust score
    active_stake_ratio = Column(Float)  # % of total stake on active validators
    mean_consensus = Column(Float)  # Raw mean consensus value
    pct_aligned = Column(Float)  # Percentage within ±0.10 of mean consensus
    
    # Emission metrics
    emission_owner = Column(Float)  # Owner share of emissions (0-1)
    emission_miners = Column(Float)  # Miners share of emissions (0-1)
    emission_validators = Column(Float)  # Validators share of emissions (0-1)
    total_emission_tao = Column(Float)  # Total emissions in TAO
    tao_in_emission = Column(Float)  # TAO tokens going into subnet
    alpha_out_emission = Column(Float)  # Alpha tokens going out of subnet
    
    # Metadata
    subnet_name = Column(String)  # Subnet name for reference
    category = Column(String)  # Primary category if available
    confidence = Column(Float)  # Enrichment confidence score
    
    # Network activity metrics
    active_validators = Column(Integer)  # Number of active validators (validator_permit.sum())
    max_validators = Column(Integer)     # Maximum allowed validators for subnet
    
    # Sprint 5 computed metrics
    stake_quality = Column(Float)  # HHI-adjusted score (0-100)
    reserve_momentum = Column(Float)  # Δ TAO-in 24h / supply
    emission_roi = Column(Float)  # TAO-in/day ÷ stake
    validators_active = Column(Integer)  # Active validators count
    
    # Expert-level ranking fields for GPT insights
    stake_quality_rank_pct = Column(Integer)  # Top X% in category (0-100)
    momentum_rank_pct = Column(Integer)       # Top X% in category (0-100)
    validator_util_pct = Column(Integer)      # Validator utilization % (0-100)
    buy_sell_ratio = Column(Float)            # buy_vol / sell_vol ratio
    tao_score = Column(Float)                 # TAO-Score (0-100)
    
    # NEW: Investor-focused fields
    fdv_tao = Column(Float)  # Fully diluted valuation in TAO
    buy_vol_tao_1d = Column(Float)  # 24h buy volume in TAO
    sell_vol_tao_1d = Column(Float)  # 24h sell volume in TAO
    data_quality_flag = Column(String(20))  # 'complete', 'partial', 'failed'
    last_screener_update = Column(DateTime)  # When screener data was last updated
    
    # Additional screener fields for comprehensive data storage
    total_volume_tao_1d = Column(Float)  # Total 24h volume in TAO
    net_volume_tao_1h = Column(Float)  # 1h net volume in TAO
    net_volume_tao_7d = Column(Float)  # 7d net volume in TAO
    price_1h_change = Column(Float)  # 1h price change %
    buy_volume_pct_change = Column(Float)  # Buy volume % change
    sell_volume_pct_change = Column(Float)  # Sell volume % change
    total_volume_pct_change = Column(Float)  # Total volume % change
    alpha_in = Column(Float)  # Alpha tokens in
    alpha_out = Column(Float)  # Alpha tokens out
    emission_pct = Column(Float)  # Emission percentage
    alpha_emitted_pct = Column(Float)  # Alpha emitted percentage
    realized_pnl_tao = Column(Float)  # Realized PnL in TAO
    unrealized_pnl_tao = Column(Float)  # Unrealized PnL in TAO
    ath_60d = Column(Float)  # 60-day all-time high price
    atl_60d = Column(Float)  # 60-day all-time low price
    gini_coeff_top_100 = Column(Float)  # Gini coefficient for top 100
    hhi = Column(Float)  # Herfindahl-Hirschman Index from screener
    symbol = Column(String(10))  # Subnet symbol
    github_repo = Column(String)  # GitHub repository URL
    subnet_contact = Column(String)  # Subnet contact info
    subnet_url = Column(String)  # Subnet URL
    subnet_website = Column(String)  # Subnet website
    discord = Column(String)  # Discord link
    additional = Column(Text)  # Additional info
    owner_coldkey = Column(String)  # Owner coldkey
    owner_hotkey = Column(String)  # Owner hotkey
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Composite index for efficient queries
    __table_args__ = (
        # Index for time-series queries by subnet
        {'sqlite_autoincrement': True}
    )

class CategoryStats(Base):
    """Category-level statistics for peer comparisons."""
    __tablename__ = "category_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String, nullable=False, unique=True)  # Primary category
    median_stake_quality = Column(Float)  # Median stake quality for category
    median_emission_roi = Column(Float)  # Median emission ROI for category
    subnet_count = Column(Integer)  # Number of subnets in category
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)  # When stats were computed
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=func.now())

class GptInsights(Base):
    """GPT-4o insights cache for subnet analysis."""
    __tablename__ = "gpt_insights"
    
    netuid = Column(Integer, primary_key=True)  # Subnet ID
    text = Column(Text, nullable=False)  # 120-word insight text
    ts = Column(DateTime, nullable=False, default=datetime.utcnow)  # Cache timestamp
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=func.now())

class AggregatedCache(Base):
    """Cache for TAO.app /subnets/aggregated API responses."""
    __tablename__ = "aggregated_cache"
    
    netuid = Column(Integer, primary_key=True)  # Subnet ID
    data = Column(JSON, nullable=False)  # Cached API response
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)  # Cache timestamp
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=func.now())

class HoldersCache(Base):
    """Cache for TAO.app /subnets/holders API responses."""
    __tablename__ = "holders_cache"
    
    netuid = Column(Integer, primary_key=True)  # Subnet ID
    data = Column(JSON, nullable=False)  # Cached API response
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)  # Cache timestamp
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=func.now())

class ValidatorsCache(Base):
    """Cache for validators data (from taostats scrape or other sources)."""
    __tablename__ = "validators_cache"
    
    netuid = Column(Integer, primary_key=True)  # Subnet ID
    data = Column(JSON, nullable=False)  # Cached validators data
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)  # Cache timestamp
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=func.now())

class DailyEmissionStats(Base):
    """Daily emission statistics for each subnet."""
    __tablename__ = 'daily_emission_stats'
    
    id = Column(Integer, primary_key=True)
    netuid = Column(Integer, nullable=False)
    date = Column(DateTime, nullable=False)  # Date for the emission data
    tao_emission = Column(Float)  # Daily TAO emission
    method = Column(String(10))   # 'native' or 'diff'
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=func.now())

class ApiQuota(Base):
    """API quota tracking for TAO.app endpoints."""
    __tablename__ = 'api_quota'
    
    id = Column(Integer, primary_key=True)
    source = Column(String(50), nullable=False)  # 'screener', 'holders', etc.
    calls_made = Column(Integer, default=0)
    month = Column(String(7), nullable=False)  # YYYY-MM format
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=func.now())

class GptInsightsNew(Base):
    """GPT insights cache for each subnet (new version with date-based caching)."""
    __tablename__ = 'gpt_insights_new'
    
    id = Column(Integer, primary_key=True)
    netuid = Column(Integer, nullable=False)
    date = Column(DateTime, nullable=False)  # Date for the insight
    text = Column(Text, nullable=False)
    tokens_used = Column(Integer)
    cost_usd = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=func.now())

Base.metadata.create_all(engine) 