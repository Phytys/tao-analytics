#!/usr/bin/env python3
"""
Data loader for backtesting TAO Score v2.1 performance.
Loads historical metrics and calculates future price returns.
"""

import sys
import os
# Add parent directory to path to access services and models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db import get_db
from models import MetricsSnap
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional

class BacktestDataLoader:
    """Loads historical data for TAO Score backtesting."""
    
    def __init__(self):
        """Initialize the data loader."""
        self.session = get_db()
    
    def load_historical_data(self, start_date: Optional[datetime] = None, 
                           end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Load historical metrics data for backtesting.
        
        Args:
            start_date: Start date for data (default: 30 days ago)
            end_date: End date for data (default: yesterday)
            
        Returns:
            DataFrame with historical metrics and calculated future returns
        """
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.utcnow() - timedelta(days=1)
        
        print(f"Loading historical data from {start_date.date()} to {end_date.date()}")
        
        # Load all metrics data in the date range
        records = self.session.query(MetricsSnap).filter(
            MetricsSnap.timestamp >= start_date,
            MetricsSnap.timestamp <= end_date
        ).order_by(MetricsSnap.timestamp, MetricsSnap.netuid).all()
        
        print(f"Found {len(records)} records")
        
        # Convert to DataFrame
        data = []
        for record in records:
            data.append({
                'date': record.timestamp.date(),
                'netuid': record.netuid,
                'timestamp': record.timestamp,
                
                # Input metrics for TAO Score calculation
                'stake_quality': record.stake_quality,
                'active_validators': record.active_validators,
                'stake_hhi': record.stake_hhi,
                'market_cap_tao': record.market_cap_tao,
                'emission_pct': record.emission_pct,
                'flow_24h': record.flow_24h,
                'root_prop': record.root_prop,
                'price_30d_change': record.price_30d_change,
                'total_volume_tao_1d': record.total_volume_tao_1d,
                'fdv_tao': record.fdv_tao,
                'total_emission_tao': record.total_emission_tao,
                'alpha_circ': record.alpha_circ,
                'price_tao': record.price_tao,
                
                # Current TAO Score (for comparison)
                'tao_score_v21': record.tao_score_v21,
                'tao_score_v11': record.tao_score,
                
                # Price data for return calculation
                'price_tao': record.price_tao,
            })
        
        df = pd.DataFrame(data)
        
        if df.empty:
            print("No data found in the specified date range")
            return df
        
        # Calculate future returns
        df = self._calculate_future_returns(df)
        
        # Calculate root_prop_prev for delta calculation
        df = self._calculate_root_prop_prev(df)
        
        print(f"Loaded data for {df['netuid'].nunique()} subnets across {df['date'].nunique()} dates")
        return df
    
    def _calculate_future_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate future price returns for each record."""
        print("Calculating future returns...")
        
        # Sort by date and netuid
        df = df.sort_values(['netuid', 'date'])
        
        # Calculate future returns for different horizons
        horizons = [1, 7, 30]  # days
        
        for horizon in horizons:
            future_returns = []
            
            for idx, row in df.iterrows():
                future_date = row['date'] + timedelta(days=horizon)
                
                # Find future price for this subnet
                future_price = df[
                    (df['netuid'] == row['netuid']) & 
                    (df['date'] == future_date)
                ]['price_tao'].iloc[0] if len(df[
                    (df['netuid'] == row['netuid']) & 
                    (df['date'] == future_date)
                ]) > 0 else None
                
                if future_price is not None and row['price_tao'] is not None and row['price_tao'] > 0:
                    return_pct = ((future_price - row['price_tao']) / row['price_tao']) * 100
                else:
                    return_pct = None
                
                future_returns.append(return_pct)
            
            df[f'return_{horizon}d'] = future_returns
        
        # Count valid return data points
        for horizon in horizons:
            valid_returns = df[f'return_{horizon}d'].notna().sum()
            print(f"  {horizon}d returns: {valid_returns} valid data points")
        
        return df
    
    def _calculate_root_prop_prev(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate previous day's root_prop for delta calculation."""
        print("Calculating root_prop_prev...")
        
        # Sort by date and netuid
        df = df.sort_values(['netuid', 'date'])
        
        root_prop_prev = []
        
        for idx, row in df.iterrows():
            prev_date = row['date'] - timedelta(days=1)
            
            # Find previous root_prop for this subnet
            prev_root_prop = df[
                (df['netuid'] == row['netuid']) & 
                (df['date'] == prev_date)
            ]['root_prop'].iloc[0] if len(df[
                (df['netuid'] == row['netuid']) & 
                (df['date'] == prev_date)
            ]) > 0 else None
            
            root_prop_prev.append(prev_root_prop)
        
        df['root_prop_prev'] = root_prop_prev
        
        valid_prev = df['root_prop_prev'].notna().sum()
        print(f"  root_prop_prev: {valid_prev} valid data points")
        
        return df
    
    def get_data_summary(self, df: pd.DataFrame) -> Dict:
        """Get summary statistics of the loaded data."""
        summary = {
            'total_records': len(df),
            'unique_subnets': df['netuid'].nunique(),
            'unique_dates': df['date'].nunique(),
            'date_range': f"{df['date'].min()} to {df['date'].max()}",
            'valid_tao_scores': df['tao_score_v21'].notna().sum(),
            'valid_returns_1d': df['return_1d'].notna().sum(),
            'valid_returns_7d': df['return_7d'].notna().sum(),
            'valid_returns_30d': df['return_30d'].notna().sum(),
        }
        
        return summary 