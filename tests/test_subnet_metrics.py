#!/usr/bin/env python
"""
Unit tests for subnet metrics calculation.
"""

import sys
import os
import unittest
import pickle
import numpy as np
from unittest.mock import Mock, patch

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from services.bittensor.metrics import calculate_subnet_metrics

class TestSubnetMetrics(unittest.TestCase):
    """Test cases for subnet metrics calculation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_sub = Mock()
        self.mock_mg = Mock()
        
        # Mock metagraph data for subnet 3
        self.mock_mg.uids = np.array([0, 1, 2, 3])
        self.mock_mg.stake = np.array([1000000000, 2000000000, 500000000, 1000000000])  # 1, 2, 0.5, 1 TAO
        self.mock_mg.incentive = np.array([0.1, 0.2, 0.05, 0.15])
        self.mock_mg.consensus = np.array([0.8, 0.85, 0.82, 0.83])  # All within ±0.10 of mean
        self.mock_mg.trust = np.array([0.5, 0.6, 0.4, 0.7])
        
        # Mock emission vectors (all zero for subnet 3)
        self.mock_mg.owner_emission = np.array([0, 0, 0, 0])
        self.mock_mg.miner_emission = np.array([0, 0, 0, 0])
        self.mock_mg.validator_emission = np.array([0, 0, 0, 0])
        
        self.mock_sub.metagraph.return_value = self.mock_mg
        
    @patch('services.bittensor.metrics.bt')
    def test_calculate_subnet_metrics_basic(self, mock_bt):
        """Test basic metrics calculation."""
        mock_bt.subtensor.return_value = self.mock_sub
        
        result = calculate_subnet_metrics(3)
        
        # Basic assertions
        self.assertEqual(result['netuid'], 3)
        self.assertEqual(result['uid_count'], 4)
        self.assertIn('total_stake_tao', result)
        self.assertIn('stake_hhi', result)
        self.assertIn('mean_incentive', result)
        self.assertIn('p95_incentive', result)
        self.assertIn('consensus_alignment', result)
        self.assertIn('trust_score', result)
        self.assertIn('emission_split', result)
        
    @patch('services.bittensor.metrics.bt')
    def test_emission_split_zero_emissions(self, mock_bt):
        """Test emission split when no emissions are enabled."""
        mock_bt.subtensor.return_value = self.mock_sub
        
        result = calculate_subnet_metrics(3)
        
        # All emission splits should be zero
        self.assertEqual(result['emission_split']['owner'], 0.0)
        self.assertEqual(result['emission_split']['miners'], 0.0)
        self.assertEqual(result['emission_split']['validators'], 0.0)
        
    @patch('services.bittensor.metrics.bt')
    def test_emission_split_with_emissions(self, mock_bt):
        """Test emission split calculation with actual emissions."""
        mock_bt.subtensor.return_value = self.mock_sub
        
        # Mock emission vectors with actual values
        self.mock_mg.owner_emission = np.array([0, 1000000000, 0, 0])  # 1 TAO to owner
        self.mock_mg.miner_emission = np.array([500000000, 0, 500000000, 500000000])  # 1.5 TAO to miners
        self.mock_mg.validator_emission = np.array([200000000, 200000000, 200000000, 200000000])  # 0.8 TAO to validators
        
        result = calculate_subnet_metrics(3)
        
        # Total emissions: 1 + 1.5 + 0.8 = 3.3 TAO
        # Ratios should sum to 1 (within floating point precision)
        emission_split = result['emission_split']
        total_ratio = emission_split['owner'] + emission_split['miners'] + emission_split['validators']
        
        self.assertAlmostEqual(total_ratio, 1.0, places=5)  # More tolerant for floating point
        self.assertAlmostEqual(emission_split['owner'], 1.0/3.3, places=5)
        self.assertAlmostEqual(emission_split['miners'], 1.5/3.3, places=5)
        self.assertAlmostEqual(emission_split['validators'], 0.8/3.3, places=5)
        
    @patch('services.bittensor.metrics.bt')
    def test_consensus_alignment_calculation(self, mock_bt):
        """Test consensus alignment calculation with ±0.10 tolerance."""
        mock_bt.subtensor.return_value = self.mock_sub
        
        result = calculate_subnet_metrics(3)
        
        # All consensus values are within ±0.10 of mean (0.825)
        # So alignment should be 100%
        self.assertAlmostEqual(result['consensus_alignment'], 100.0, places=2)
        
    @patch('services.bittensor.metrics.bt')
    def test_stake_hhi_calculation(self, mock_bt):
        """Test stake HHI calculation."""
        mock_bt.subtensor.return_value = self.mock_sub
        
        result = calculate_subnet_metrics(3)
        
        # HHI should be between 0 and 10,000
        self.assertGreaterEqual(result['stake_hhi'], 0)
        self.assertLessEqual(result['stake_hhi'], 10000)
        
    @patch('services.bittensor.metrics.bt')
    def test_error_handling(self, mock_bt):
        """Test error handling when metagraph fails."""
        mock_bt.subtensor.side_effect = Exception("Connection failed")
        
        result = calculate_subnet_metrics(3)
        
        # Should return error information
        self.assertIn('error', result)
        self.assertEqual(result['netuid'], 3)

if __name__ == '__main__':
    unittest.main() 