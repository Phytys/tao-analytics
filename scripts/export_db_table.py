#!/usr/bin/env python
import argparse
import pandas as pd
from pathlib import Path
import sys
from sqlalchemy import create_engine, text

# Add the parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))
from config import DB_URL

def get_table_names(engine):
    """Get list of all tables in the database."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        return [row[0] for row in result]

def export_table_to_csv(table_name: str, output_dir: Path):
    """Export a specific table to CSV."""
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create SQLAlchemy engine
    engine = create_engine(DB_URL)
    
    # Read table into pandas DataFrame
    df = pd.read_sql_table(table_name, engine)
    
    # Export to CSV
    output_file = output_dir / f"{table_name}.csv"
    df.to_csv(output_file, index=False)
    print(f"Exported {table_name} to {output_file}")
    print(f"Shape: {df.shape}")
    print("\nFirst few rows:")
    print(df.head())

def main():
    parser = argparse.ArgumentParser(description="Export SQLite table to CSV")
    parser.add_argument("--table", help="Table name to export (use --list to see available tables)")
    parser.add_argument("--list", action="store_true", help="List all available tables")
    args = parser.parse_args()

    engine = create_engine(DB_URL)
    output_dir = Path(__file__).parent.parent / "db_export"

    if args.list:
        tables = get_table_names(engine)
        print("\nAvailable tables:")
        for table in tables:
            print(f"- {table}")
        return

    if not args.table:
        parser.error("Please specify a table name or use --list to see available tables")

    export_table_to_csv(args.table, output_dir)

if __name__ == "__main__":
    main() 