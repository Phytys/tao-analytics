# TAO Analytics Calculations Documentation

## Overview
This document provides a comprehensive review of all calculations used in TAO Analytics, their correctness, and recommendations for GPT insight context.

## 1. Emission Calculations

### 1.1 Current Implementation Issues

#### Problem 1: Rolling Emission Split Uses Only 3 Blocks
```python
# services/bittensor/metrics.py lines 190-195
# PoC optimization: Use only 3 blocks for speed
max_blocks_to_fetch = 3  # Ultra-fast for PoC
start_block = current_block - max_blocks_to_fetch + 1
```
**Issue**: This is marked as "PoC" (Proof of Concept) and only uses 3 blocks instead of the intended 360 blocks (one tempo).

#### Problem 2: Daily Emission Estimation
```python
# scripts/cron_fetch.py lines 287-292
# Estimate daily emission: per-block emission × blocks per day (~7,200 blocks)
# Bittensor produces ~1 block every 12 seconds = 7,200 blocks per day
blocks_per_day = 7200
daily_tao_emission = tao_in_emission * blocks_per_day
emission_roi = daily_tao_emission / total_stake
```
**Issue**: This is an estimation, not actual daily data.

### 1.2 Emission Data Sources

#### Current Block Emission
- `tao_in_emission`: TAO tokens going INTO subnet (per block)
- `alpha_out_emission`: Alpha tokens going OUT of subnet (per block)
- `total_emission_tao`: Total emission in TAO (per block)

#### Rolling Emission Split
- Uses only 3 blocks instead of 360 (one tempo)
- Calculates owner/miners/validators ratios
- Cached for performance

### 1.3 Recommended Fixes

#### Fix 1: Use Full Tempo for Rolling Emission
```python
# Change from 3 blocks to 360 blocks (one tempo)
max_blocks_to_fetch = 360  # One tempo = 360 blocks
```

#### Fix 2: Collect Historical Daily Data
```python
# Add to models.py
class DailyEmissionStats(Base):
    __tablename__ = 'daily_emission_stats'
    
    id = Column(Integer, primary_key=True)
    netuid = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    total_tao_emission = Column(Float)
    total_alpha_emission = Column(Float)
    blocks_counted = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)
```

## 2. Stake Quality Calculation

### 2.1 Current Implementation
```python
# services/bittensor/async_metrics.py lines 200-201
# Stake Quality: HHI-adjusted score (0-100)
stake_quality = max(0, 100 - (hhi / 100)) if hhi is not None else None
```

### 2.2 Analysis
**Formula**: `max(0, 100 - (HHI / 100))`
- HHI ranges from 0 to 10,000
- For HHI = 0 (perfect distribution): Quality = 100
- For HHI = 10,000 (monopoly): Quality = 0
- Linear relationship

**Issues**:
1. HHI should be normalized to 0-1 range first
2. Formula assumes HHI max is 10,000
3. Linear relationship may not reflect real stake quality

### 2.3 Recommended Fix
```python
# Normalize HHI to 0-1 range first
normalized_hhi = hhi / 10000 if hhi is not None else None
stake_quality = max(0, 100 - (normalized_hhi * 100)) if normalized_hhi is not None else None
```

## 3. Reserve Momentum Calculation

### 3.1 Current Implementation
```python
# scripts/cron_fetch.py lines 270-280
# Calculate reserve momentum: Δ TAO-in 24h / supply
reserve_momentum = None
if latest_screener and previous_screener:
    current_tao_in = latest_screener.raw_json.get('tao_in')
    previous_tao_in = previous_screener.raw_json.get('tao_in')
    
    if current_tao_in is not None and previous_tao_in is not None:
        tao_in_change = current_tao_in - previous_tao_in
        market_cap = latest_screener.raw_json.get('market_cap_tao')
        
        if market_cap and market_cap > 0:
            reserve_momentum = tao_in_change / market_cap
```

### 3.2 Analysis
**Formula**: `(current_tao_in - previous_tao_in) / market_cap`
- Measures 24h change in TAO-in relative to market cap
- Positive = accumulating demand
- Negative = distributing demand

**Issues**:
1. Uses screener data (external source) instead of on-chain data
2. Depends on screener's 24h window definition
3. Market cap denominator may not be the best normalization

### 3.3 Recommended Improvements
```python
# Option 1: Use on-chain emission data
reserve_momentum = (current_tao_emission - previous_tao_emission) / total_stake

# Option 2: Use multiple timeframes
reserve_momentum_1h = calculate_momentum(1)
reserve_momentum_24h = calculate_momentum(24)
reserve_momentum_7d = calculate_momentum(168)
```

## 4. Category Statistics Calculation

### 4.1 Current Implementation
```python
# scripts/cron_fetch.py lines 420-440
category_stats = session.query(
    MetricsSnap.category,
    func.avg(MetricsSnap.stake_quality).label('median_stake_quality'),
    func.avg(MetricsSnap.emission_roi).label('median_emission_roi'),
    func.count(MetricsSnap.netuid).label('subnet_count')
).filter(
    MetricsSnap.timestamp == latest_timestamp,
    MetricsSnap.category.isnot(None)
).group_by(MetricsSnap.category).all()
```

### 4.2 Issues
1. **Uses `func.avg()` but labels as 'median'** - This is incorrect
2. Only calculates 2 metrics per category
3. No standard deviation or other distribution stats

### 4.3 Recommended Fix
```python
# Use proper median calculation
from sqlalchemy import func
from sqlalchemy.sql import text

category_stats = session.query(
    MetricsSnap.category,
    func.percentile_cont(0.5).within_group(MetricsSnap.stake_quality.asc()).label('median_stake_quality'),
    func.percentile_cont(0.5).within_group(MetricsSnap.emission_roi.asc()).label('median_emission_roi'),
    func.avg(MetricsSnap.stake_quality).label('mean_stake_quality'),
    func.avg(MetricsSnap.emission_roi).label('mean_emission_roi'),
    func.stddev(MetricsSnap.stake_quality).label('stake_quality_std'),
    func.stddev(MetricsSnap.emission_roi).label('emission_roi_std'),
    func.count(MetricsSnap.netuid).label('subnet_count')
).filter(
    MetricsSnap.timestamp == latest_timestamp,
    MetricsSnap.category.isnot(None)
).group_by(MetricsSnap.category).all()
```

## 5. Consensus Alignment Calculation

### 5.1 Current Implementation
```python
# services/bittensor/async_metrics.py lines 180-185
if hasattr(mg, 'consensus') and mg.consensus is not None:
    mean_consensus = mg.consensus.mean()
    aligned = np.abs(mg.consensus - mean_consensus) < 0.10
    consensus_alignment = aligned.mean().item() * 100
    pct_aligned = consensus_alignment  # Store the percentage
```

### 5.2 Analysis
**Formula**: Percentage of UIDs within ±0.10 of subnet mean consensus
- Uses 0.10 as tolerance threshold
- Measures how aligned the subnet is

**Issues**:
1. Hard-coded tolerance of 0.10 may not be appropriate for all subnets
2. No consideration of stake-weighted alignment

### 5.3 Recommended Improvements
```python
# Option 1: Dynamic tolerance based on subnet variance
std_consensus = mg.consensus.std()
tolerance = min(0.10, std_consensus * 2)  # Use 2 standard deviations or 0.10 max

# Option 2: Stake-weighted alignment
stake_weights = mg.S / mg.S.sum()
weighted_alignment = (np.abs(mg.consensus - mean_consensus) < tolerance) * stake_weights
consensus_alignment = weighted_alignment.sum().item() * 100
```

## 6. Trust Score Calculation

### 6.1 Current Implementation
```python
# services/bittensor/async_metrics.py lines 187-190
if hasattr(mg, 'trust') and mg.trust is not None:
    trust_score = mg.trust.mean().item()
```

### 6.2 Analysis
**Formula**: Simple mean of all trust scores
- No weighting by stake
- No consideration of active vs inactive validators

### 6.3 Recommended Improvements
```python
# Option 1: Stake-weighted trust
if hasattr(mg, 'trust') and mg.trust is not None and hasattr(mg, 'S'):
    stake_weights = mg.S / mg.S.sum()
    trust_score = (mg.trust * stake_weights).sum().item()

# Option 2: Active validator trust only
if hasattr(mg, 'trust') and mg.trust is not None and hasattr(mg, 'validator_permit'):
    active_trust = mg.trust[mg.validator_permit]
    trust_score = active_trust.mean().item() if len(active_trust) > 0 else 0.0
```

## 7. GPT Insight Context Recommendations

### 7.1 Current Context
```python
# services/gpt_insight.py lines 140-150
context = f"""
Subnet: {subnet_name} (ID: {netuid})
Category: {category}
Stake: {total_stake_tao:,.0f} TAO
Stake Quality: {stake_quality:.1f}/100
Reserve Momentum: {reserve_momentum:.4f}
Emission ROI: {emission_roi:.4f} if emission_roi else "N/A"
Active Validators: {active_validators}/256
"""
```

### 7.2 Recommended Enhanced Context

#### 7.2.1 Add Market Context
```python
# Add market metrics
market_context = f"""
Market Cap: {market_cap_tao:,.0f} TAO
Price: {price_tao:.6f} TAO
24h Volume: {flow_24h:,.0f} TAO
Price Change 24h: {price_1d_change:.2f}%
Price Change 7d: {price_7d_change:.2f}%
Buy/Sell Ratio: {buy_volume_tao_1d/sell_volume_tao_1d:.2f} if sell_volume_tao_1d > 0 else "N/A"
"""
```

#### 7.2.2 Add Network Health Metrics
```python
# Add network health indicators
health_context = f"""
Consensus Alignment: {consensus_alignment:.1f}%
Trust Score: {trust_score:.3f}
Mean Incentive: {mean_incentive:.6f}
P95 Incentive: {p95_incentive:.6f}
Stake HHI: {stake_hhi:.0f} (0-10,000)
UID Count: {uid_count}
"""
```

#### 7.2.3 Add Emission Details
```python
# Add detailed emission information
emission_context = f"""
Daily Emission Estimate: {daily_tao_emission:.2f} TAO
Emission Split - Owner: {emission_owner:.1%}, Miners: {emission_miners:.1%}, Validators: {emission_validators:.1%}
Alpha Out Emission: {alpha_out_emission:.2f}
"""
```

#### 7.2.4 Add Peer Comparison Context
```python
# Add category peer comparison
peer_context = f"""
Category: {category} ({category_stats.subnet_count} subnets)
Category Median Stake Quality: {category_stats.median_stake_quality:.1f}
Category Median Emission ROI: {category_stats.median_emission_roi:.6f}
Category Stake Quality Std: {category_stats.stake_quality_std:.1f}
Category Emission ROI Std: {category_stats.emission_roi_std:.6f}
"""
```

### 7.3 Complete Enhanced Context
```python
enhanced_context = f"""
# SUBNET OVERVIEW
Subnet: {subnet_name} (ID: {netuid})
Category: {category} ({category_stats.subnet_count} subnets)

# STAKE METRICS
Total Stake: {total_stake_tao:,.0f} TAO
Stake Quality: {stake_quality:.1f}/100 (Category median: {category_stats.median_stake_quality:.1f})
Stake HHI: {stake_hhi:.0f} (0-10,000, lower = better distribution)
UID Count: {uid_count}

# EMISSION METRICS
Daily Emission Estimate: {daily_tao_emission:.2f} TAO
Emission ROI: {emission_roi:.6f} (Category median: {category_stats.median_emission_roi:.6f})
Emission Split: Owner {emission_owner:.1%}, Miners {emission_miners:.1%}, Validators {emission_validators:.1%}
Alpha Out Emission: {alpha_out_emission:.2f}

# NETWORK HEALTH
Active Validators: {active_validators}/256
Consensus Alignment: {consensus_alignment:.1f}%
Trust Score: {trust_score:.3f}
Mean Incentive: {mean_incentive:.6f}
P95 Incentive: {p95_incentive:.6f}

# MARKET METRICS
Market Cap: {market_cap_tao:,.0f} TAO
Price: {price_tao:.6f} TAO
24h Volume: {flow_24h:,.0f} TAO
Price Change 24h: {price_1d_change:.2f}%
Price Change 7d: {price_7d_change:.2f}%
Buy/Sell Ratio: {buy_volume_tao_1d/sell_volume_tao_1d:.2f} if sell_volume_tao_1d > 0 else "N/A"

# RESERVE MOMENTUM
Reserve Momentum: {reserve_momentum:.6f} (24h Δ TAO-in / market cap)

# CATEGORY CONTEXT
Category Stake Quality Std: {category_stats.stake_quality_std:.1f}
Category Emission ROI Std: {category_stats.emission_roi_std:.6f}
"""
```

## 8. Critical Issues to Address

### 8.1 High Priority
1. **Fix rolling emission split** - Use 360 blocks instead of 3
2. **Fix category stats** - Use proper median calculation
3. **Add stake-weighted calculations** - For trust, consensus, etc.
4. **Collect actual daily emission data** - Instead of estimating

### 8.2 Medium Priority
1. **Improve stake quality formula** - Normalize HHI properly
2. **Add market context to GPT** - Price, volume, buy/sell ratios
3. **Add standard deviations** - For better peer comparisons
4. **Dynamic consensus tolerance** - Based on subnet variance

### 8.3 Low Priority
1. **Add multiple timeframe momentum** - 1h, 24h, 7d
2. **Add emission trend analysis** - Historical patterns
3. **Add validator performance metrics** - Individual validator stats

## 9. Data Quality Recommendations

### 9.1 Validation Checks
```python
# Add validation for all calculations
def validate_metrics(metrics):
    assert 0 <= metrics['stake_quality'] <= 100, "Stake quality out of range"
    assert metrics['emission_roi'] >= 0, "Emission ROI cannot be negative"
    assert 0 <= metrics['consensus_alignment'] <= 100, "Consensus alignment out of range"
    # ... more validations
```

### 9.2 Data Freshness
```python
# Add data freshness checks
def check_data_freshness(timestamp, max_age_hours=24):
    age = datetime.utcnow() - timestamp
    return age.total_seconds() < (max_age_hours * 3600)
```

### 9.3 Error Handling
```python
# Add proper error handling for all calculations
def safe_calculation(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Calculation error in {func.__name__}: {e}")
        return None
```

## 10. Testing Recommendations

### 10.1 Unit Tests
- Test all calculation functions with known inputs/outputs
- Test edge cases (zero values, missing data)
- Test data validation functions

### 10.2 Integration Tests
- Test complete data pipeline end-to-end
- Test GPT insight generation with various subnet types
- Test category statistics calculation

### 10.3 Performance Tests
- Test calculation speed for large datasets
- Test memory usage for concurrent calculations
- Test database query optimization

---

**Note**: This documentation should be reviewed by a Bittensor expert to ensure all calculations align with the protocol's specifications and best practices. 