from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    JSON, Text, DateTime, func
)
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DB_URL

Base = declarative_base()
engine = create_engine(DB_URL, echo=False, future=True)
Session = sessionmaker(bind=engine, autoflush=False)

class ScreenerRaw(Base):
    __tablename__ = "screener_raw"
    netuid = Column(Integer, primary_key=True)
    raw_json = Column(JSON)
    fetched_at = Column(DateTime, server_default=func.now())

class SubnetMeta(Base):
    __tablename__ = "subnet_meta"
    netuid = Column(Integer, primary_key=True)
    subnet_name = Column(String)

    # — fields to be filled by the LLM —
    tagline = Column(String)
    what_it_does = Column(Text)
    category = Column(String)
    tags = Column(String)   # comma-sep string to stay simple
    confidence = Column(Float)
    context_hash = Column(String)  # MD5 hash of the context JSON
    context_tokens = Column(Integer, default=0)  # How much context was available
    provenance = Column(Text)  # JSON string tracking where each field came from

    # — timestamps —
    last_enriched_at = Column(DateTime)  # When LLM fields were last updated
    updated_at = Column(DateTime, onupdate=func.now())

Base.metadata.create_all(engine) 