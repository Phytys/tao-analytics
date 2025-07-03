"""
Unit tests for TAO-Score v1.1 calculation.
Tests the new scaling, dynamic weighting, and hard caps.
"""

import pytest
import os
from services.calc_metrics import calculate_tao_score

class TestTAOScoreV1_1:
    """Test TAO-Score v1.1 calculation with new scaling and weighting."""
    
    def test_full_metrics_score(self):
        """Test TAO-Score calculation with all metrics available."""
        # Test case with all metrics
        score = calculate_tao_score(
            stake_quality=80.0,
            consensus_alignment=85.0,
            trust_score=0.75,
            emission_roi=0.001,
            reserve_momentum=0.02,  # Positive momentum
            validator_util_pct=60.0,
            inflation_pct=8.0  # Perfect target
        )
        
        # Expected calculation:
        # sq=80, cons=85, trust=75, util=60, infl=100, mom=2
        # weights: sq=0.35, cons=0.20, trust=0.15, util=0.10, infl=0.10, mom=0.10
        # score = 80*0.35 + 85*0.20 + 75*0.15 + 60*0.10 + 100*0.10 + 2*0.10
        # score = 28 + 17 + 11.25 + 6 + 10 + 0.2 = 72.45
        expected = 72.5  # Rounded to 1 decimal
        assert score == expected
    
    def test_missing_inflation_redistributes_to_core(self):
        """Test that missing inflation weight goes only to core metrics."""
        score = calculate_tao_score(
            stake_quality=80.0,
            consensus_alignment=85.0,
            trust_score=0.75,
            emission_roi=0.001,
            reserve_momentum=0.02,
            validator_util_pct=60.0,
            inflation_pct=None  # Missing
        )
        
        # Expected calculation:
        # sq=80, cons=85, trust=75, util=60, mom=2
        # Original weights: sq=0.35, cons=0.20, trust=0.15, util=0.10, mom=0.10
        # Missing infl weight (0.10) redistributed to core only
        # Core weight sum = 0.35 + 0.20 + 0.15 = 0.70
        # New weights: sq=0.35 + 0.10*(0.35/0.70) = 0.40
        #              cons=0.20 + 0.10*(0.20/0.70) = 0.229
        #              trust=0.15 + 0.10*(0.15/0.70) = 0.171
        #              util=0.10, mom=0.10
        # score = 80*0.40 + 85*0.229 + 75*0.171 + 60*0.10 + 2*0.10
        # score = 32 + 19.465 + 12.825 + 6 + 0.2 = 70.49
        expected = 70.5  # Rounded to 1 decimal
        assert score == expected
    
    def test_missing_momentum_redistributes_to_core(self):
        """Test that missing momentum weight goes only to core metrics."""
        score = calculate_tao_score(
            stake_quality=80.0,
            consensus_alignment=85.0,
            trust_score=0.75,
            emission_roi=0.001,
            reserve_momentum=None,  # Missing
            validator_util_pct=60.0,
            inflation_pct=8.0
        )
        
        # Expected calculation:
        # sq=80, cons=85, trust=75, util=60, infl=100
        # Original weights: sq=0.35, cons=0.20, trust=0.15, util=0.10, infl=0.10
        # Missing mom weight (0.10) redistributed to core only
        # Core weight sum = 0.35 + 0.20 + 0.15 = 0.70
        # New weights: sq=0.35 + 0.10*(0.35/0.70) = 0.40
        #              cons=0.20 + 0.10*(0.20/0.70) = 0.229
        #              trust=0.15 + 0.10*(0.15/0.70) = 0.171
        #              util=0.10, infl=0.10
        # score = 80*0.40 + 85*0.229 + 75*0.171 + 60*0.10 + 100*0.10
        # score = 32 + 19.465 + 12.825 + 6 + 10 = 80.29
        expected = 80.3  # Rounded to 1 decimal
        assert score == expected
    
    def test_negative_momentum_clipped_to_zero(self):
        """Test that negative momentum is clipped to 0."""
        score = calculate_tao_score(
            stake_quality=80.0,
            consensus_alignment=85.0,
            trust_score=0.75,
            emission_roi=0.001,
            reserve_momentum=-0.05,  # Negative momentum
            validator_util_pct=60.0,
            inflation_pct=8.0
        )
        
        # Expected calculation:
        # sq=80, cons=85, trust=75, util=60, infl=100, mom=0 (clipped)
        # weights: sq=0.35, cons=0.20, trust=0.15, util=0.10, infl=0.10, mom=0.10
        # score = 80*0.35 + 85*0.20 + 75*0.15 + 60*0.10 + 100*0.10 + 0*0.10
        # score = 28 + 17 + 11.25 + 6 + 10 + 0 = 72.25
        expected = 72.3  # Rounded to 1 decimal
        assert score == expected
    
    def test_inflation_deviation_penalty(self):
        """Test inflation deviation penalty from target."""
        # Test with 10% inflation (2% above 8% target)
        score_high = calculate_tao_score(
            stake_quality=80.0,
            consensus_alignment=85.0,
            trust_score=0.75,
            emission_roi=0.001,
            reserve_momentum=0.02,
            validator_util_pct=60.0,
            inflation_pct=10.0  # 2% above target
        )
        
        # Expected inflation score: 100 - abs(10-8)*4 = 100 - 8 = 92
        # This should be slightly lower than perfect inflation case
        
        # Test with 6% inflation (2% below 8% target)
        score_low = calculate_tao_score(
            stake_quality=80.0,
            consensus_alignment=85.0,
            trust_score=0.75,
            emission_roi=0.001,
            reserve_momentum=0.02,
            validator_util_pct=60.0,
            inflation_pct=6.0  # 2% below target
        )
        
        # Both should be lower than perfect inflation case
        perfect_score = 72.5  # From test_full_metrics_score
        assert score_high is not None and score_high < perfect_score
        assert score_low is not None and score_low < perfect_score
        assert score_high == score_low  # Same deviation penalty
    
    def test_hard_caps_applied(self):
        """Test that hard caps (0-100) are applied."""
        # Test with values that would exceed 100
        score_high = calculate_tao_score(
            stake_quality=100.0,
            consensus_alignment=100.0,
            trust_score=1.0,
            emission_roi=0.001,
            reserve_momentum=1.0,  # Would scale to 100
            validator_util_pct=100.0,
            inflation_pct=8.0
        )
        
        assert score_high == 100.0  # Should be capped at 100
        
        # Test with values that would go below 0
        score_low = calculate_tao_score(
            stake_quality=0.0,
            consensus_alignment=0.0,
            trust_score=0.0,
            emission_roi=0.001,
            reserve_momentum=-1.0,  # Would be clipped to 0
            validator_util_pct=0.0,
            inflation_pct=20.0  # Would give negative inflation score
        )
        
        assert score_low == 0.0  # Should be capped at 0
    
    def test_missing_core_metrics_returns_none(self):
        """Test that missing core metrics return None."""
        # Missing stake_quality
        score = calculate_tao_score(
            stake_quality=None,
            consensus_alignment=85.0,
            trust_score=0.75,
            emission_roi=0.001,
            reserve_momentum=0.02,
            validator_util_pct=60.0,
            inflation_pct=8.0
        )
        assert score is None
        
        # Missing consensus_alignment
        score = calculate_tao_score(
            stake_quality=80.0,
            consensus_alignment=None,
            trust_score=0.75,
            emission_roi=0.001,
            reserve_momentum=0.02,
            validator_util_pct=60.0,
            inflation_pct=8.0
        )
        assert score is None
        
        # Missing trust_score
        score = calculate_tao_score(
            stake_quality=80.0,
            consensus_alignment=85.0,
            trust_score=None,
            emission_roi=0.001,
            reserve_momentum=0.02,
            validator_util_pct=60.0,
            inflation_pct=8.0
        )
        assert score is None
    
    def test_input_scaling(self):
        """Test that inputs are properly scaled to 0-100 range."""
        # Test with values outside 0-100 range
        score = calculate_tao_score(
            stake_quality=150.0,  # Above 100
            consensus_alignment=-10.0,  # Below 0
            trust_score=1.5,  # Above 1.0
            emission_roi=0.001,
            reserve_momentum=0.02,
            validator_util_pct=200.0,  # Above 100
            inflation_pct=8.0
        )
        
        # Should still calculate a valid score with scaled inputs
        assert score is not None
        assert 0 <= score <= 100
    
    def test_custom_inflation_target(self):
        """Test custom inflation target from environment variable."""
        # Set custom target
        os.environ['TAO_INF_TARGET'] = '10'
        
        # Test with 12% inflation (2% above 10% target)
        score = calculate_tao_score(
            stake_quality=80.0,
            consensus_alignment=85.0,
            trust_score=0.75,
            emission_roi=0.001,
            reserve_momentum=0.02,
            validator_util_pct=60.0,
            inflation_pct=12.0  # 2% above new target
        )
        
        # Expected inflation score: 100 - abs(12-10)*4 = 100 - 8 = 92
        # This should be lower than perfect inflation case
        
        # Reset to default
        os.environ['TAO_INF_TARGET'] = '8'
        
        assert score is not None
        assert 0 <= score <= 100

if __name__ == "__main__":
    pytest.main([__file__]) 