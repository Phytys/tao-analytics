"""
Migration: Add correlation_analysis table for Heroku-compatible caching.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base, CorrelationAnalysis
from services.db import get_db
from sqlalchemy import create_engine
from config import DB_URL

def migrate():
    """Add correlation_analysis table."""
    print("Creating correlation_analysis table...")
    
    engine = create_engine(DB_URL)
    
    # Create the table
    CorrelationAnalysis.__table__.create(engine, checkfirst=True)
    
    print("✅ correlation_analysis table created successfully!")

if __name__ == "__main__":
    migrate() 