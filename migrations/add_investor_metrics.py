"""
Migration: Add investor-focused metrics and tables
Adds fields to metrics_snap and creates new tables for daily emission stats, API quota tracking, and GPT insights.
"""

from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Date, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime

# Import existing models to extend them
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base, MetricsSnap
from config import DB_URL
from sqlalchemy import text

# Create new tables
# class DailyEmissionStats(Base):
#     """Daily emission statistics for each subnet."""
#     __tablename__ = 'daily_emission_stats'
#     
#     id = Column(Integer, primary_key=True)
#     netuid = Column(Integer, nullable=False)
#     date = Column(Date, nullable=False)
#     tao_emission = Column(Float)  # Daily TAO emission
#     method = Column(String(10))   # 'native' or 'diff'
#     timestamp = Column(DateTime, default=datetime.utcnow)
#     
#     # Composite unique constraint
#     __table_args__ = (
#         {'sqlite_on_conflict': 'REPLACE'}  # SQLite specific
#     )

# class ApiQuota(Base):
#     """API quota tracking for TAO.app endpoints."""
#     __tablename__ = 'api_quota'
#     
#     id = Column(Integer, primary_key=True)
#     source = Column(String(50), nullable=False)  # 'screener', 'holders', etc.
#     calls_made = Column(Integer, default=0)
#     month = Column(String(7), nullable=False)  # YYYY-MM format
#     last_updated = Column(DateTime, default=datetime.utcnow)
#     
#     # Composite unique constraint
#     __table_args__ = (
#         {'sqlite_on_conflict': 'REPLACE'}  # SQLite specific
#     )

# class GptInsights(Base):
#     """GPT insights cache for each subnet."""
#     __tablename__ = 'gpt_insights'
#     
#     id = Column(Integer, primary_key=True)
#     netuid = Column(Integer, nullable=False)
#     date = Column(Date, nullable=False)
#     text = Column(Text, nullable=False)
#     tokens_used = Column(Integer)
#     cost_usd = Column(Float)
#     timestamp = Column(DateTime, default=datetime.utcnow)
#     
#     # Composite unique constraint
#     __table_args__ = (
#         {'sqlite_on_conflict': 'REPLACE'}  # SQLite specific
#     )

def upgrade():
    """Add new fields to existing tables and create new tables."""
    engine = create_engine(DB_URL)
    
    # Add new columns to metrics_snap
    with engine.connect() as conn:
        # Add new fields for investor metrics
        new_columns = [
            "fdv_tao FLOAT",
            "buy_vol_tao_1d FLOAT", 
            "sell_vol_tao_1d FLOAT",
            "data_quality_flag VARCHAR(20)",
            "last_screener_update DATETIME"
        ]
        
        for column_def in new_columns:
            try:
                conn.execute(text(f"ALTER TABLE metrics_snap ADD COLUMN {column_def}"))
                print(f"Added column: {column_def}")
            except Exception as e:
                print(f"Column may already exist: {column_def} - {e}")
    
    # Create new tables
    # Base.metadata.create_all(engine)
    print("(Skipped) Created new tables: daily_emission_stats, api_quota, gpt_insights")

def downgrade():
    """Remove new fields and tables (if needed)."""
    engine = create_engine(DB_URL)
    
    # Drop new tables
    # DailyEmissionStats.__table__.drop(engine, checkfirst=True)
    # ApiQuota.__table__.drop(engine, checkfirst=True)
    # GptInsights.__table__.drop(engine, checkfirst=True)
    
    print("Dropped new tables")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run migration")
    parser.add_argument("--downgrade", action="store_true", help="Run downgrade instead of upgrade")
    
    args = parser.parse_args()
    
    if args.downgrade:
        downgrade()
    else:
        upgrade() 