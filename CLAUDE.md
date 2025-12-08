# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OnTrac shipping cost calculator that computes expected shipping costs based on package dimensions, weight, zones, and various surcharges. Uses Polars for data processing and connects to Redshift for data operations.

## Common Commands

```bash
# Run tests
pytest tests/test_pipeline.py -v

# Run single test
pytest tests/test_pipeline.py::TestSurchargeFlags::test_ahs_weight_trigger -v

# Run pipeline on mock data (outputs to tests/data/)
python tests/run_pipeline.py

# Interactive calculator CLI
python -m ontrac.scripts.calculator
```

## Architecture

### Pipeline Flow
```
load_pcs_shipments() → supplement_shipments() → calculate() → output
```

1. **Sources** (`ontrac/sources/`) - Load shipment data from sources (e.g., PCS)
2. **Pipeline** (`ontrac/pipeline.py`) - `supplement_shipments()` enriches with zones/dimensions/billable weight, `calculate()` applies surcharges and computes costs

### Surcharge System

Surcharges inherit from shared `Surcharge` base class (`shared/surcharges/base.py`). Carrier-specific surcharges live in `ontrac/surcharges/`. Key concepts:

- **Processing phases**: BASE surcharges first (no dependencies), then DEPENDENT surcharges (reference other surcharge flags via `depends_on`)
- **Exclusivity groups**: Surcharges in same group compete; only highest priority wins (e.g., OML > LPS > AHS in "dimensional" group)
- **Allocated surcharges**: Applied to all shipments at a rate (e.g., RES at 95% allocation)
- **Demand period**: Seasonal surcharges use `in_period()` helper and `period_start`/`period_end` attributes

### Key Data Files

- `ontrac/data/` - Reference data and loaders (`load_rates()`, `load_zones()`)
- `ontrac/data/base_rates.csv` - Shipping rates by weight bracket and zone
- `ontrac/data/zones.csv` - ZIP code to zone mapping with DAS classification
- `ontrac/data/fuel.py` - Fuel surcharge rate constants
- `ontrac/data/billable_weight.py` - DIM factor and threshold constants

### Versioning

Single `VERSION` constant in `ontrac/version.py`. Each calculation stamps `calculator_version` on output. Historical recalculation done via git checkout.

### Database

`shared/database/__init__.py` provides `pull_data()`, `push_data()`, `execute_query()` for Redshift operations. Requires `shared/database/pass.txt` (gitignored) for credentials.

## Column Schema

Required input columns: `ship_date`, `production_site`, `shipping_zip_code`, `shipping_region`, `length_in`, `width_in`, `height_in`, `weight_lbs`

Supplement adds: `cubic_in`, `longest_side_in`, `second_longest_in`, `length_plus_girth`, `shipping_zone`, `das_zone`, `dim_weight_lbs`, `uses_dim_weight`, `billable_weight_lbs`

Calculate adds: `surcharge_*` flags, `cost_*` amounts, `cost_base`, `cost_subtotal`, `cost_fuel`, `cost_total`, `calculator_version`
