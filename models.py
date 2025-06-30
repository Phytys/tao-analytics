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
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Composite index for efficient queries
    __table_args__ = (
        # Index for time-series queries by subnet
        {'sqlite_autoincrement': True}
    )

Base.metadata.create_all(engine) 