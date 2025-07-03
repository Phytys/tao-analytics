"""
Simple test for TAO-Score v1.1 calculation.
Tests the new scaling, dynamic weighting, and hard caps.
"""

import os
import sys
sys.path.append('.')

from services.calc_metrics import calculate_tao_score

def test_full_metrics_score():
    """Test TAO-Score calculation with all metrics available."""
    print("Testing full metrics score...")
    
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
    print(f"Expected: {expected}, Got: {score}")
    assert score == expected, f"Expected {expected}, got {score}"
    print("✓ Full metrics score test passed")

def test_missing_inflation_redistributes_to_core():
    """Test that missing inflation weight goes only to core metrics."""
    print("Testing missing inflation redistribution...")
    
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
    print(f"Expected: {expected}, Got: {score}")
    assert score == expected, f"Expected {expected}, got {score}"
    print("✓ Missing inflation redistribution test passed")

def test_negative_momentum_clipped_to_zero():
    """Test that negative momentum is clipped to 0."""
    print("Testing negative momentum clipping...")
    
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
    expected = 72.2  # Rounded to 1 decimal
    print(f"Expected: {expected}, Got: {score}")
    assert score == expected, f"Expected {expected}, got {score}"
    print("✓ Negative momentum clipping test passed")

def test_hard_caps_applied():
    """Test that hard caps (0-100) are applied."""
    print("Testing hard caps...")
    
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
    
    print(f"High score: {score_high}")
    assert score_high == 100.0, f"Expected 100.0, got {score_high}"
    
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
    
    print(f"Low score: {score_low}")
    assert score_low == 0.0, f"Expected 0.0, got {score_low}"
    print("✓ Hard caps test passed")

def test_missing_core_metrics_returns_none():
    """Test that missing core metrics return None."""
    print("Testing missing core metrics...")
    
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
    assert score is None, f"Expected None, got {score}"
    
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
    assert score is None, f"Expected None, got {score}"
    
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
    assert score is None, f"Expected None, got {score}"
    print("✓ Missing core metrics test passed")

def main():
    """Run all tests."""
    print("Running TAO-Score v1.1 tests...\n")
    
    try:
        test_full_metrics_score()
        test_missing_inflation_redistributes_to_core()
        test_negative_momentum_clipped_to_zero()
        test_hard_caps_applied()
        test_missing_core_metrics_returns_none()
        
        print("\n🎉 All tests passed! TAO-Score v1.1 is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 