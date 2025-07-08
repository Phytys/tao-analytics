#!/usr/bin/env python3
"""
TAO Score v2.1 weight optimizer for backtesting.
Tunes the 9 weight parameters to maximize correlation with future returns.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.calc_metrics import calculate_tao_score_v21
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

class TAOScoreOptimizer:
    """Optimizes TAO Score v2.1 weights based on backtest performance."""
    
    def __init__(self, data: pd.DataFrame):
        """
        Initialize optimizer with historical data.
        
        Args:
            data: DataFrame with historical metrics and future returns
        """
        self.data = data
        self.best_weights = None
        self.best_correlation = -1
        
        # Default weights from the current v2.1 formula
        self.default_weights = {
            'sq': 0.18,      # stake_quality
            'av': 0.10,      # active_validators
            'hhi': 0.07,     # stake_hhi (inverted)
            'mcap': 0.15,    # market_cap_tao
            'eff': 0.10,     # emission_efficiency (inverted)
            'fvel': 0.08,    # flow_velocity
            'rpd': 0.07,     # root_prop_delta (inverted)
            'sharpe': 0.15,  # sharpe_30d
            'vol': 0.10      # total_volume_tao_1d
        }
    
    def calculate_tao_score_with_weights(self, row: pd.Series, weights: Dict) -> float:
        """
        Calculate TAO Score v2.1 with custom weights.
        
        Args:
            row: DataFrame row with metrics
            weights: Dictionary of weights for each component
            
        Returns:
            Calculated TAO Score
        """
        try:
            # Extract metrics
            stake_quality = row['stake_quality']
            active_validators = row['active_validators']
            stake_hhi = row['stake_hhi']
            market_cap_tao = row['market_cap_tao']
            emission_pct = row['emission_pct']
            flow_24h = row['flow_24h']
            root_prop = row['root_prop']
            price_30d_change = row['price_30d_change']
            total_volume_tao_1d = row['total_volume_tao_1d']
            fdv_tao = row['fdv_tao']
            total_emission_tao = row['total_emission_tao']
            alpha_circ = row['alpha_circ']
            price_tao = row['price_tao']
            root_prop_prev = row['root_prop_prev']
            
            # Check if core metrics are available
            if any(metric is None for metric in [stake_quality, active_validators, stake_hhi, market_cap_tao]):
                return None
            
            # Calculate derived metrics
            emission_efficiency = None
            if emission_pct is not None and fdv_tao is not None and fdv_tao > 0:
                emission_efficiency = emission_pct / fdv_tao if emission_pct > 0 else 0
            
            flow_velocity = None
            if flow_24h is not None and alpha_circ is not None and alpha_circ > 0:
                flow_velocity = abs(flow_24h) / alpha_circ
            
            root_prop_delta = None
            if root_prop is not None and root_prop_prev is not None:
                root_prop_delta = root_prop - root_prop_prev
            
            sharpe_30d = None
            if price_30d_change is not None:
                sharpe_30d = price_30d_change / 100
            
            # Apply transformations
            sq = max(0, min(100, stake_quality or 0))
            av = max(0, min(100, (active_validators or 0) / 256 * 100))
            
            def sqrt_transform(x):
                if x is None or x <= 0:
                    return 0
                return np.sqrt(abs(x))
            
            def normalized_z_score(x, mean=0, std=1, min_val=-3, max_val=3):
                if x is None:
                    return 0
                z = (x - mean) / std if std > 0 else 0
                z_clipped = max(min_val, min(max_val, z))
                return (z_clipped - min_val) / (max_val - min_val) * 100
            
            hhi = normalized_z_score(stake_hhi or 0, mean=5000, std=2000)
            mcap = sqrt_transform(market_cap_tao or 0)
            eff = sqrt_transform(emission_efficiency or 0)
            fvel = sqrt_transform(flow_velocity or 0)
            rpd = normalized_z_score(root_prop_delta or 0, mean=0, std=0.1)
            sharpe = normalized_z_score(sharpe_30d or 0, mean=0, std=0.2)
            vol = sqrt_transform(total_volume_tao_1d or 0)
            
            # Normalize to 0-100 range
            mcap_norm = min(100, (mcap / 1000) * 100) if mcap > 0 else 0
            eff_norm = min(100, (eff / 0.1) * 100) if eff > 0 else 0
            fvel_norm = min(100, (fvel / 0.5) * 100) if fvel > 0 else 0
            vol_norm = min(100, (vol / 10000) * 100) if vol > 0 else 0
            
            # Calculate weighted score with custom weights
            tao_score = (
                sq * weights['sq'] +
                av * weights['av'] +
                (100 - hhi) * weights['hhi'] +
                mcap_norm * weights['mcap'] +
                (100 - eff_norm) * weights['eff'] +
                fvel_norm * weights['fvel'] +
                (100 - rpd) * weights['rpd'] +
                sharpe * weights['sharpe'] +
                vol_norm * weights['vol']
            )
            
            return max(0, min(100, tao_score))
            
        except Exception as e:
            return None
    
    def calculate_correlation(self, weights: Dict, return_column: str = 'return_7d') -> float:
        """
        Calculate correlation between TAO Score and future returns.
        
        Args:
            weights: Dictionary of weights
            return_column: Column name for future returns
            
        Returns:
            Correlation coefficient (negative for minimization)
        """
        # Calculate TAO scores with custom weights
        tao_scores = []
        returns = []
        
        for _, row in self.data.iterrows():
            tao_score = self.calculate_tao_score_with_weights(row, weights)
            future_return = row[return_column]
            
            if tao_score is not None and future_return is not None and not np.isnan(future_return):
                tao_scores.append(tao_score)
                returns.append(future_return)
        
        if len(tao_scores) < 10:  # Need minimum data points
            return -0.1  # Poor correlation penalty
        
        # Calculate correlation
        correlation = np.corrcoef(tao_scores, returns)[0, 1]
        
        if np.isnan(correlation):
            return -0.1
        
        return -correlation  # Negative for minimization
    
    def optimize_weights(self, return_column: str = 'return_7d', 
                        method: str = 'L-BFGS-B') -> Dict:
        """
        Optimize TAO Score weights to maximize correlation with future returns.
        
        Args:
            return_column: Column name for future returns
            method: Optimization method
            
        Returns:
            Dictionary with optimized weights and performance metrics
        """
        print(f"Optimizing weights for {return_column}...")
        
        # Initial weights (flattened for optimization)
        initial_weights = list(self.default_weights.values())
        
        # Bounds for weights (0 to 1, sum to 1)
        bounds = [(0.01, 0.5) for _ in range(9)]  # Reasonable bounds
        
        # Constraint: weights must sum to 1
        def weight_constraint(weights):
            return np.sum(weights) - 1.0
        
        constraints = {'type': 'eq', 'fun': weight_constraint}
        
        # Optimize
        result = minimize(
            lambda w: self.calculate_correlation(dict(zip(self.default_weights.keys(), w)), return_column),
            initial_weights,
            method=method,
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            optimized_weights = dict(zip(self.default_weights.keys(), result.x))
            correlation = -result.fun  # Convert back to positive
            
            print(f"Optimization successful!")
            print(f"Correlation: {correlation:.4f}")
            print("Optimized weights:")
            for metric, weight in optimized_weights.items():
                print(f"  {metric}: {weight:.4f}")
            
            return {
                'weights': optimized_weights,
                'correlation': correlation,
                'success': True,
                'iterations': result.nit
            }
        else:
            print(f"Optimization failed: {result.message}")
            return {
                'weights': self.default_weights,
                'correlation': 0.0,
                'success': False,
                'message': result.message
            }
    
    def compare_weights(self, weights1: Dict, weights2: Dict, 
                       return_column: str = 'return_7d') -> Dict:
        """
        Compare performance of two weight configurations.
        
        Args:
            weights1: First weight configuration
            weights2: Second weight configuration
            return_column: Column name for future returns
            
        Returns:
            Dictionary with comparison results
        """
        corr1 = -self.calculate_correlation(weights1, return_column)
        corr2 = -self.calculate_correlation(weights2, return_column)
        
        return {
            'weights1_correlation': corr1,
            'weights2_correlation': corr2,
            'improvement': corr2 - corr1,
            'improvement_pct': ((corr2 - corr1) / abs(corr1)) * 100 if corr1 != 0 else 0
        } 