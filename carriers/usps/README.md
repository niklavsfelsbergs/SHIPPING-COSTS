# USPS Shipping Cost Calculator

Expected cost calculator for USPS shipments.

## Status

**In Development** - Skeleton structure created, implementation pending.

## Structure

```
carriers/usps/
├── __init__.py
├── version.py              # Calculator version for audit trail
├── calculate_costs.py      # Main calculator (DataFrame in/out)
├── README.md
├── data/
│   ├── __init__.py
│   ├── loaders/
│   │   ├── __init__.py
│   │   └── pcs.py          # Load shipments from PCS database
│   └── reference/
│       ├── __init__.py
│       ├── billable_weight.py   # DIM factor configuration
│       ├── base_rates.csv       # TODO: Rate card by weight/zone
│       ├── zones.csv            # TODO: ZIP to zone mapping
│       └── contracts/
│           └── current/         # Contract documents
├── surcharges/
│   ├── __init__.py         # Surcharge registry
│   └── *.py                # TODO: Individual surcharge classes
├── scripts/
│   ├── __init__.py
│   ├── calculator.py       # Interactive CLI calculator
│   ├── upload_expected.py  # Upload expected costs to DB
│   └── compare_expected_to_actuals.py
├── tests/
│   ├── __init__.py
│   └── test_calculate_costs.py
└── maintenance/
    ├── __init__.py
    └── *.py                # TODO: Zone/rate update scripts
```

## Usage

### Calculate Costs
```python
from carriers.usps.calculate_costs import calculate_costs
result = calculate_costs(df)  # df must have required columns
```

### Interactive Calculator
```bash
python -m carriers.usps.scripts.calculator
```

### Upload Expected Costs
```bash
python -m carriers.usps.scripts.upload_expected --full
python -m carriers.usps.scripts.upload_expected --incremental
python -m carriers.usps.scripts.upload_expected --days 7
python -m carriers.usps.scripts.upload_expected --dry-run
```

### Compare Expected vs Actual
```bash
python -m carriers.usps.scripts.compare_expected_to_actuals
python -m carriers.usps.scripts.compare_expected_to_actuals --date_from 2025-01-01 --date_to 2025-01-31
```

### Run Tests
```bash
pytest carriers/usps/tests/ -v
```

## TODO

- [ ] Add contract documents to `data/reference/contracts/current/`
- [ ] Create `base_rates.csv` with rate card
- [ ] Create `zones.csv` with ZIP to zone mapping
- [ ] Implement surcharge classes in `surcharges/`
- [ ] Implement `calculate_costs.py` calculation logic
- [ ] Implement scripts (calculator, upload, compare)
- [ ] Add tests

## Configuration Updates

See `maintenance/README.md` for instructions on updating:
- Base rates
- Zones
- Surcharge list prices and discounts
