# TAO Analytics Calculation Summary & Critical Issues

## Executive Summary

After comprehensive testing and analysis, here are the **critical issues** that require immediate expert review:

## 🚨 CRITICAL ISSUES

### 1. **Emission ROI Shows 0.000000 for ALL Subnets**
**Problem**: All subnets show `Emission ROI: 0.000000` in the database, but live calculation shows `0.000078` for subnet 1.

**Root Cause**: The daily estimation formula was updated but old data wasn't refreshed.

**Impact**: GPT insights are using incorrect emission ROI data for peer comparisons.

**Fix Required**: 
```bash
python scripts/cron_fetch.py --run-once sdk_snapshot
```

### 2. **Rolling Emission Split Uses Only 3 Blocks (PoC)**
**Problem**: Code comment says "PoC optimization: Use only 3 blocks for speed" instead of 360 blocks (one tempo).

**Current Code**:
```python
max_blocks_to_fetch = 3  # Ultra-fast for PoC
```

**Should Be**:
```python
max_blocks_to_fetch = 360  # One tempo = 360 blocks
```

**Impact**: Emission split calculations are based on insufficient data.

### 3. **Category Statistics Use AVG Instead of MEDIAN**
**Problem**: Code uses `func.avg()` but labels results as 'median'.

**Current Code**:
```python
func.avg(MetricsSnap.stake_quality).label('median_stake_quality'),
func.avg(MetricsSnap.emission_roi).label('median_emission_roi'),
```

**Impact**: GPT insights get incorrect peer comparison data.

## 📊 ACTUAL TEST RESULTS

### Subnet 1 Live Data (Correct)
- **Per-block tao_in_emission**: 0.019137 TAO
- **Daily estimation**: 137.79 TAO (0.019137 × 7200 blocks)
- **Daily emission ROI**: 0.000078 (137.79 ÷ 1,769,165 stake)
- **Stake Quality**: 40.3/100 (HHI: 5972)
- **Consensus Alignment**: 100.0%
- **Trust Score**: 0.427

### Database Data (Incorrect)
- **Emission ROI**: 0.000000 (all subnets)
- **Category stats**: Using averages instead of medians

## 🔧 IMMEDIATE FIXES NEEDED

### Fix 1: Update Database with Correct Emission ROI
```bash
# Run this to fix emission ROI data
python scripts/cron_fetch.py --run-once sdk_snapshot
```

### Fix 2: Fix Category Statistics Calculation
```python
# In scripts/cron_fetch.py, change:
func.avg(MetricsSnap.stake_quality).label('median_stake_quality'),
func.avg(MetricsSnap.emission_roi).label('median_emission_roi'),

# To (if SQLite supports it):
func.percentile_cont(0.5).within_group(MetricsSnap.stake_quality.asc()).label('median_stake_quality'),
func.percentile_cont(0.5).within_group(MetricsSnap.emission_roi.asc()).label('median_emission_roi'),

# Or use Python calculation:
# Calculate medians in Python after fetching data
```

### Fix 3: Fix Rolling Emission Split
```python
# In services/bittensor/metrics.py, change:
max_blocks_to_fetch = 3  # Ultra-fast for PoC

# To:
max_blocks_to_fetch = 360  # One tempo = 360 blocks
```

## 📈 GPT CONTEXT IMPROVEMENTS

### Current Context (Limited)
```
Subnet: subnet_name (ID: netuid)
Category: category
Stake: total_stake_tao TAO
Stake Quality: stake_quality/100
Reserve Momentum: reserve_momentum
Emission ROI: emission_roi
Active Validators: active_validators/256
```

### Recommended Enhanced Context
```
# SUBNET OVERVIEW
Subnet: subnet_name (ID: netuid)
Category: category (X subnets)

# STAKE METRICS
Total Stake: total_stake_tao TAO
Stake Quality: stake_quality/100 (Category median: X)
Stake HHI: stake_hhi (0-10,000, lower = better)
UID Count: uid_count

# EMISSION METRICS
Daily Emission Estimate: daily_tao_emission TAO
Emission ROI: emission_roi (Category median: X)
Emission Split: Owner X%, Miners X%, Validators X%
Alpha Out Emission: alpha_out_emission

# NETWORK HEALTH
Active Validators: active_validators/256
Consensus Alignment: consensus_alignment%
Trust Score: trust_score
Mean Incentive: mean_incentive
P95 Incentive: p95_incentive

# MARKET METRICS
Market Cap: market_cap_tao TAO
Price: price_tao TAO
24h Volume: flow_24h TAO
Price Change 24h: price_1d_change%
Price Change 7d: price_7d_change%
Buy/Sell Ratio: buy_volume/sell_volume

# RESERVE MOMENTUM
Reserve Momentum: reserve_momentum (24h Δ TAO-in / market cap)
```

## 🎯 PRIORITY ACTION ITEMS

### High Priority (Fix Immediately)
1. **Run data refresh**: `python scripts/cron_fetch.py --run-once sdk_snapshot`
2. **Fix category stats calculation** - Use proper median or Python calculation
3. **Fix rolling emission split** - Use 360 blocks instead of 3

### Medium Priority (Next Sprint)
1. **Enhance GPT context** - Add market metrics, network health, peer comparisons
2. **Add data validation** - Check for reasonable value ranges
3. **Add standard deviations** - For better peer comparisons

### Low Priority (Future)
1. **Collect actual daily emission data** - Instead of estimating
2. **Add multiple timeframe momentum** - 1h, 24h, 7d
3. **Add stake-weighted calculations** - For trust, consensus, etc.

## 🔍 EXPERT CONSULTATION NEEDED

### Questions for Bittensor Expert:
1. **Is the daily emission estimation (7200 blocks) accurate?**
2. **Should rolling emission split use 360 blocks (one tempo)?**
3. **Is the consensus tolerance of ±0.10 appropriate for all subnets?**
4. **Should trust scores be stake-weighted?**
5. **Is the HHI normalization correct (divide by 10,000)?**
6. **What's the proper way to calculate median in SQLite?**

### Protocol-Specific Questions:
1. **What does `tao_in_emission` vs `total_emission_tao` represent?**
2. **How should emission ROI be calculated for validators vs miners?**
3. **What's the significance of consensus alignment vs trust score?**
4. **How should reserve momentum be normalized (market cap vs total stake)?**

## 📋 TESTING CHECKLIST

After fixes, verify:
- [ ] Emission ROI shows non-zero values for all subnets
- [ ] Category statistics use proper medians
- [ ] Rolling emission split uses 360 blocks
- [ ] GPT insights include enhanced context
- [ ] All calculations pass validation checks

---

**Status**: Ready for expert review and immediate fixes
**Last Updated**: 2025-07-01
**Test Results**: Available in `test_calculations.py` output 