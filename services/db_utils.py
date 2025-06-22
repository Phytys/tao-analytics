"""
Database utilities for TAO Analytics.
Provides database-agnostic helpers for JSON field extraction.
"""

from sqlalchemy import func
from flask import current_app
import os


def json_field(col, key):
    """
    Extract JSON field in a database-agnostic way.
    
    Args:
        col: SQLAlchemy column containing JSON data
        key: JSON key to extract
        
    Returns:
        SQLAlchemy expression for JSON extraction
        
    Usage:
        # Instead of: json_extract(raw_json, '$.market_cap_tao')
        # Use: json_field(screener_raw.raw_json, 'market_cap_tao')
    """
    # Detect database dialect
    dialect = get_db_dialect()
    
    if dialect == 'sqlite':
        # SQLite: json_extract(col, '$.key')
        return func.json_extract(col, f'$.{key}')
    else:
        # PostgreSQL: col->>'key'
        return col.op('->>')(key)


def get_db_dialect():
    """
    Get the current database dialect.
    
    Returns:
        str: 'sqlite' or 'postgresql'
    """
    # Try to get from Flask app context first
    try:
        database_url = current_app.config.get('DATABASE_URL', 'sqlite:///tao.sqlite')
    except RuntimeError:
        # Fall back to environment variable if not in app context
        database_url = os.getenv('DATABASE_URL', 'sqlite:///tao.sqlite')
    
    if 'sqlite' in database_url.lower():
        return 'sqlite'
    elif 'postgres' in database_url.lower():
        return 'postgresql'
    else:
        # Default to SQLite for unknown databases
        return 'sqlite' 