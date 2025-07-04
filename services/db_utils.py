"""
Database utility functions for TAO Analytics.

This module provides database-agnostic utilities that work with both SQLite and Postgres.
"""

from sqlalchemy import func, text, Column
from typing import Any


def json_field(column: Column, key: str) -> Any:
    """
    Extract a value from a JSON column in a database-agnostic way.
    
    Args:
        column: The JSON column to extract from
        key: The JSON key to extract (supports dot notation like 'user.name')
    
    Returns:
        SQLAlchemy expression that extracts the JSON value
        
    Examples:
        # Extract simple key
        json_field(SubnetMeta.raw_json, 'website_url')
        
        # Extract nested key
        json_field(SubnetMeta.raw_json, 'user.profile.name')
    """
    # Get database type from models engine
    from models import engine
    dialect = engine.dialect.name
    
    if dialect == 'sqlite':
        return _sqlite_json_extract(column, key)
    elif dialect == 'postgresql':
        return _postgres_json_extract(column, key)
    else:
        # Default to SQLite for unknown databases
        return _sqlite_json_extract(column, key)


def _sqlite_json_extract(column: Column, key: str) -> Any:
    """SQLite JSON extraction using json_extract function."""
    return func.json_extract(column, f'$.{key}')


def _postgres_json_extract(column: Column, key: str) -> Any:
    """PostgreSQL JSON extraction using -> operator."""
    # Handle nested keys by chaining -> operators
    keys = key.split('.')
    result = column
    
    # Use -> for all keys except the last one
    for i, k in enumerate(keys[:-1]):
        result = result.op('->')(k)
    
    # Use ->> for the final extraction to get text
    if keys:
        result = result.op('->>')(keys[-1])
    
    return result


def get_database_type() -> str:
    """
    Get the current database type (sqlite or postgresql).
    
    Returns:
        Database type as string
    """
    from models import engine
    return engine.dialect.name


def is_sqlite() -> bool:
    """Check if current database is SQLite."""
    return get_database_type() == 'sqlite'


def is_postgresql() -> bool:
    """Check if current database is PostgreSQL."""
    return get_database_type() == 'postgresql' 