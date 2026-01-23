# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Project Overview

Shipping cost validation system. Calculates expected shipping costs from PCS (production system) shipment data, uploads to Redshift, and compares against actual carrier invoices to catch billing errors and understand cost drivers.

**Carriers implemented:**
| Carrier | Status | Accuracy |
|---------|--------|----------|
| OnTrac | Production | -0.52% variance |
| USPS | Production | +0.65% variance |
| DPD UK | In development | - |

## Project Structure

```
SHIPPING-COSTS/
├── carriers/
│   ├── ontrac/                 # OnTrac Ground (US West)
│   │   ├── calculate_costs.py  # Main calculator
│   │   ├── version.py          # Version stamp for audit
│   │   ├── data/
│   │   │   ├── loaders/pcs.py  # Load from PCS database
│   │   │   └── reference/      # zones.csv, base_rates.csv, fuel.py
│   │   ├── surcharges/         # OML, LPS, AHS, DAS, EDAS, RES, DEM_*
│   │   ├── scripts/            # upload_expected, upload_actuals, compare, calculator
│   │   ├── maintenance/        # generate_zones
│   │   └── tests/
│   │
│   ├── usps/                   # USPS Ground Advantage
│   │   └── (same structure)
│   │
│   └── dpd_uk/                 # DPD UK (in development)
│       └── (same structure)
│
├── shared/
│   ├── database/               # Redshift connection (pull_data, push_data)
│   ├── surcharges/base.py      # Surcharge base class
│   └── sql/                    # Shared SQL templates
│
└── CLAUDE.md                   # This file
```

## Setup

```bash
pip install -e .    # Install as editable package (required)
```

This registers `shared` and `carriers` as importable packages.

## How It Works

### Data Flow

```
PCS Database → calculate_costs() → upload_expected → Redshift
                                                         ↓
Carrier Invoice → upload_actuals ──────────────────→ Redshift
                                                         ↓
                                   compare_expected_to_actuals → HTML Report
```

### Calculator Pattern

All carriers follow the same pattern - DataFrame in, DataFrame out:

```python
from carriers.ontrac.calculate_costs import calculate_costs
result = calculate_costs(df)  # Returns df with cost columns appended
```

**Two-stage calculation:**
1. `supplement_shipments()` - Add zones, calculated dimensions, billable weight
2. `calculate()` - Apply surcharges, look up base rate, compute total

**Required input columns:**
- `ship_date`, `production_site`, `shipping_zip_code`, `shipping_region`
- `length_in`, `width_in`, `height_in`, `weight_lbs`

**Output columns added:**
- Dimensions: `cubic_in`, `longest_side_in`, `second_longest_in`
- Zone: `shipping_zone`, `das_zone` (OnTrac) or `rate_zone` (USPS)
- Weight: `dim_weight_lbs`, `uses_dim_weight`, `billable_weight_lbs`
- Surcharges: `surcharge_*` flags, `cost_*` amounts
- Total: `cost_subtotal`, `cost_fuel` (OnTrac), `cost_total`

## Commands

### OnTrac
```bash
python -m carriers.ontrac.scripts.calculator                    # Interactive calculator
python -m carriers.ontrac.scripts.upload_expected --incremental # Upload expected costs
python -m carriers.ontrac.scripts.upload_actuals --incremental  # Upload invoice costs
python -m carriers.ontrac.scripts.compare_expected_to_actuals   # Generate accuracy report
python -m carriers.ontrac.scripts.compare_expected_to_actuals --invoice 26D0I70116  # Specific invoice
pytest carriers/ontrac/tests/ -v                                # Run tests
```

### USPS
```bash
python -m carriers.usps.scripts.calculator
python -m carriers.usps.scripts.upload_expected --incremental
python -m carriers.usps.scripts.upload_actuals --incremental
python -m carriers.usps.scripts.compare_expected_to_actuals
python -m carriers.usps.scripts.compare_expected_to_actuals --date_from 2026-01-01
pytest carriers/usps/tests/ -v
```

### Common Options
```bash
--full          # Delete all, recalculate from 2025-01-01
--incremental   # From latest date in DB (recommended for daily use)
--days N        # Last N days only
--dry-run       # Preview without database changes
```

## Shared Components

### Database (`shared/database/`)
```python
from shared.database import pull_data, push_data, execute_query

df = pull_data("SELECT * FROM table")           # Returns Polars DataFrame
push_data(df, "schema.table", columns=[...])    # Upload (batched, single commit)
execute_query("DELETE FROM table WHERE ...")    # DDL/DML
```

Credentials: `shared/database/pass.txt` (not in git)

### Surcharge Base Class (`shared/surcharges/base.py`)

All surcharges inherit from `Surcharge`:

```python
class AHS(Surcharge):
    name = "AHS"
    list_price = 36.00
    discount = 0.70                    # 70% off → net $10.80
    exclusivity_group = "dimensional"  # Competes with OML, LPS
    priority = 3                       # Lower wins (OML=1, LPS=2, AHS=3)
    min_billable_weight = 30           # Side effect when triggered

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("weight_lbs") > 50

    @classmethod
    def cost(cls) -> float | pl.Expr:  # Can return expression for conditional costs
        return cls.list_price * (1 - cls.discount)
```

**Surcharge types:**
- **Deterministic**: Trigger based on package attributes (AHS, LPS, OML, NSL1, NSL2)
- **Allocated**: Applied to percentage of shipments (RES at 95%)
- **Dependent**: Trigger when base surcharge + date condition (DEM_AHS, DEM_RES)

## Database Tables

### Expected Costs
- `shipping_costs.expected_shipping_costs_ontrac`
- `shipping_costs.expected_shipping_costs_usps`

Contains: order IDs, dimensions, zones, surcharge flags, all cost components, calculator version

### Actual Costs
- `shipping_costs.actual_shipping_costs_ontrac`
- `shipping_costs.actual_shipping_costs_usps`

Contains: order IDs, invoice data, actual charges by category

## Key Design Decisions

### Floating-Point Precision
Dimensions rounded to 1 decimal place before threshold comparisons. Prevents issues like 762mm → 30.0000001980" incorrectly triggering >30" threshold.

### Borderline Allocation (OnTrac AHS)
OnTrac inconsistently charges AHS for packages at 30.3" second_longest (~50% of the time). Rather than always overstate or understate, we apply 50% of the surcharge cost for the 30.0-30.5" range.

### Peak in Base (USPS)
USPS includes peak surcharge in their base rate on invoices. Comparison report combines `cost_base + cost_peak` as "Base" for proper comparison.

### Zone Fallback
Three-tier fallback for zone lookup:
1. Exact ZIP match (5-digit for OnTrac, 3-digit prefix for USPS)
2. State-level mode (most common zone for that state)
3. Default zone 5

## Adding a New Carrier

1. Create directory structure: `carriers/{carrier}/`
2. Implement `calculate_costs.py` following the two-stage pattern
3. Create surcharge classes in `surcharges/`
4. Add reference data: `data/reference/zones.csv`, `base_rates.csv`
5. Implement scripts: `upload_expected.py`, `upload_actuals.py`, `compare_expected_to_actuals.py`
6. Add tests
7. Create `README.md` documenting carrier-specific details

## Configuration Updates

Each carrier has different update frequencies:
- **Base rates**: Annually (contract renewal)
- **Zones**: Monthly/quarterly (from invoice data)
- **Fuel rate**: Weekly (OnTrac only)
- **Surcharge prices**: As announced by carrier
- **Demand periods**: Annually

Always update `version.py` when changing configuration.

## Slash Commands

- `/review-config` - Review OnTrac config against contract documents and website

## Carrier-Specific Documentation

See detailed README in each carrier directory:
- `carriers/ontrac/README.md` - Surcharge details, contract references, maintenance procedures
- `carriers/usps/README.md` - Ground Advantage specifics, peak surcharge tiers
