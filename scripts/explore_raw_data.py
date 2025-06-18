#!/usr/bin/env python
import pandas as pd
import json
import ast
from pathlib import Path
import sys

# Add the parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))
from config import DB_URL

def explore_raw_data():
    # Read the raw data
    df = pd.read_csv('db_export/screener_raw.csv')
    
    # Parse the first row's JSON to see available fields
    first_row = ast.literal_eval(df.iloc[0]['raw_json'])
    print("\nAvailable fields in raw data:")
    for key in first_row.keys():
        print(f"- {key}")
    
    # Create a new DataFrame with parsed JSON
    parsed_data = []
    for _, row in df.iterrows():
        json_data = ast.literal_eval(row['raw_json'])
        parsed_data.append(json_data)
    
    parsed_df = pd.DataFrame(parsed_data)
    
    # Dynamically select up to 6 important columns that exist
    preferred_cols = [
        'netuid', 'subnet_name', 'price', 'market_cap_tao',
        'github_repo', 'subnet_website', 'symbol', 'owner_coldkey'
    ]
    display_cols = [col for col in preferred_cols if col in parsed_df.columns][:6]
    display_df = parsed_df[display_cols].copy()
    
    # Format numeric columns if present
    for col in ['price', 'market_cap_tao']:
        if col in display_df.columns:
            display_df[col] = display_df[col].round(4)
    
    print(f"\nFirst 10 subnets (showing columns: {', '.join(display_cols)}):")
    print(display_df.sort_values('netuid').head(10).to_string(index=False))
    
    # Save the parsed data
    output_file = Path('db_export/parsed_subnets.csv')
    parsed_df.to_csv(output_file, index=False)
    print(f"\nFull parsed data saved to: {output_file}")

if __name__ == "__main__":
    explore_raw_data() 