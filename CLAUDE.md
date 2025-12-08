# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Shipping cost calculator for OnTrac carrier. Calculates expected shipping costs from PCS (production system) shipment data, uploads to Redshift database, and compares against actual invoice costs.

## Setup (Required)

This project is a Python package. Install it before running any scripts:

```bash
pip install -e .
```

This registers `shared` and `ontrac` as importable packages. The `-e` flag means "editable" - code changes take effect immediately without reinstalling.

For Docker/production deployment, use `pip install .` (without `-e`).

## Commands

### Run Tests
```bash
pytest                                      # Run all tests
pytest ontrac/tests/test_calculate_costs.py # Run specific test file
pytest -v                                   # Verbose output
```

### Interactive Calculator
```bash
python -m ontrac.scripts.calculator    # CLI tool to calculate cost for single shipment
```

### Upload Expected Costs to Database
```bash
python -m ontrac.scripts.upload_expected --full         # Full recalculation from 2025-01-01
python -m ontrac.scripts.upload_expected --incremental  # From latest date in DB
python -m ontrac.scripts.upload_expected --days 7       # Last N days
python -m ontrac.scripts.upload_expected --dry-run      # Preview without changes
```

### Compare Expected vs Actual
```bash
python -m ontrac.scripts.compare_expected_to_actuals
python -m ontrac.scripts.compare_expected_to_actuals --invoice INV-12345
python -m ontrac.scripts.compare_expected_to_actuals --date_from 2025-01-01 --date_to 2025-01-31
```

### Update Zones from Invoice Data
```bash
python -m ontrac.maintenance.generate_zones
python -m ontrac.maintenance.generate_zones --start-date 2025-01-01
```

## Architecture

### Cost Calculator (`ontrac/calculate_costs.py`)
DataFrame in, DataFrame out. Main entry point:
```python
from ontrac.calculate_costs import calculate_costs
result = calculate_costs(df)  # df must have required columns (see module docstring)
```

Two-stage calculation (also available separately for debugging):
1. `supplement_shipments()` - Enriches raw shipment data with zones, dimensions, billable weight
2. `calculate()` - Applies surcharges and calculates costs

### Surcharges (`ontrac/surcharges/`)
Each surcharge is a class inheriting from `Surcharge` (defined in `shared/surcharges/base.py`):
- **Pricing**: `list_price`, `discount`
- **Exclusivity**: Surcharges in same `exclusivity_group` compete; lowest `priority` wins (e.g., OML > LPS > AHS for dimensional)
- **Dependencies**: `depends_on` references another surcharge flag (for demand surcharges)
- **Side effects**: `min_billable_weight` enforces minimum when triggered

Processing order:
1. BASE surcharges (OML, LPS, AHS, DAS, EDAS, RES) - don't reference other surcharge flags
2. DEPENDENT surcharges (DEM_RES, DEM_AHS, DEM_LPS, DEM_OML) - reference BASE flags

### Data Sources
- `ontrac/sources/pcs.py` - Loads shipment data from PCS database
- `ontrac/data/zones.csv` - ZIP code to zone mapping (PHX and CMH production sites)
- `ontrac/data/base_rates.csv` - Rate card by weight bracket and zone
- `ontrac/data/fuel.py` - Weekly fuel surcharge rate
- `ontrac/data/billable_weight.py` - DIM factor configuration

### Database (`shared/database/`)
- Connects to Redshift (`bi_stage_dev`)
- Requires `shared/database/pass.txt` with password (not in git)
- `pull_data()` - Execute SELECT, returns Polars DataFrame
- `push_data()` - Upload DataFrame to table (uses `executemany` with parameterized queries, batch size 5000, single commit at end)

## Key Patterns

### Zone Lookup with Fallback
Zone lookup uses three-tier fallback:
1. Exact ZIP code match
2. State-level mode (most common zone for state)
3. Default zone 5

### Surcharge Conditions
Override `conditions()` method with Polars expression:
```python
@classmethod
def conditions(cls) -> pl.Expr:
    return pl.col("weight_lbs") > cls.WEIGHT_LBS
```

### Version Stamping
Update `ontrac/version.py` when changing rates/config. Version is stamped on all calculator output for audit trail.

## Configuration Updates

See `ontrac/maintenance/README.md` for detailed instructions on updating:
- Base rates (annually with contract renewals)
- Zones (monthly/quarterly from invoice data)
- Surcharge list prices and discounts
- Fuel rate (weekly)
- Demand period dates (annually)

## Slash Commands

- `/review-config` - Compare current config against OnTrac contract documents and website
