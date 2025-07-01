# TAO Analytics Test Suite

This directory contains all tests, test utilities, and calculation documentation for TAO Analytics.

## Directory Structure

```
tests/
├── README.md                           # This file
├── test_calculations.py                # Comprehensive calculation tests
├── test_subnet_metrics.py              # Subnet metrics tests
├── test_subnet_detail.py               # Subnet detail page tests
├── CALCULATIONS_DOCUMENTATION.md       # Complete technical documentation
├── CALCULATION_SUMMARY.md              # Executive summary with critical issues
└── fixtures/                           # Test data and fixtures
```

## Running Tests

### Calculation Tests
```bash
# Run comprehensive calculation tests
python tests/test_calculations.py

# This will test:
# - Emission calculations
# - Stake quality calculations
# - Category statistics
# - Consensus alignment
# - GPT context data availability
```

### Subnet Metrics Tests
```bash
# Run subnet metrics tests
python tests/test_subnet_metrics.py
```

### Subnet Detail Tests
```bash
# Run subnet detail page tests
python tests/test_subnet_detail.py
```

## Documentation

### CALCULATIONS_DOCUMENTATION.md
Complete technical review of all calculations used in TAO Analytics, including:
- Emission calculations and issues
- Stake quality formulas
- Reserve momentum calculations
- Category statistics
- Consensus alignment
- Trust score calculations
- GPT insight context recommendations

### CALCULATION_SUMMARY.md
Executive summary with:
- Critical issues requiring immediate attention
- Actual test results
- Immediate fixes needed
- Priority action items
- Expert consultation questions

## Critical Issues Identified

1. **Emission ROI shows 0.000000 for ALL subnets** - Database needs refresh
2. **Rolling emission split uses only 3 blocks** - Should use 360 blocks
3. **Category statistics use AVG instead of MEDIAN** - Incorrect calculation

## Quick Fixes

```bash
# Fix emission ROI data
python scripts/cron_fetch.py --run-once sdk_snapshot

# Run calculation tests to verify
python tests/test_calculations.py
```

## Adding New Tests

When adding new tests:
1. Create test file in this directory
2. Follow naming convention: `test_*.py`
3. Add test description to this README
4. Include any fixtures in `fixtures/` directory

## Test Data

The `fixtures/` directory should contain:
- Sample subnet data
- Mock API responses
- Test database snapshots
- Expected calculation results 