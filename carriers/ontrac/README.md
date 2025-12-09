# OnTrac Shipping Cost Calculator

Calculates expected shipping costs for OnTrac carrier shipments, uploads them to Redshift, and compares against actual invoice costs.

---

## Quick Reference

| Task | Command |
|------|---------|
| **Review config against contracts** | **`/review-config`** |
| Upload expected costs (incremental) | `python -m carriers.ontrac.scripts.upload_expected --incremental` |
| Upload actual costs (incremental) | `python -m carriers.ontrac.scripts.upload_actuals --incremental` |
| Compare expected vs actual | `python -m carriers.ontrac.scripts.compare_expected_to_actuals` |
| Calculate single shipment | `python -m carriers.ontrac.scripts.calculator` |
| Update zones from invoices | `python -m carriers.ontrac.maintenance.generate_zones` |
| Run tests | `pytest carriers/ontrac/tests/` |

---

## /review-config Slash Command

**Before making any configuration changes, run `/review-config` in Claude Code.**

This slash command reviews the current calculator configuration against:
- OnTrac contract documents (in `data/reference/contracts/`)
- OnTrac website for current fuel rates
- Demand period dates

It will identify any discrepancies and recommend specific changes with source citations.

---

## Scripts

### 1. Upload Expected Costs

Calculates expected shipping costs from PCS shipment data and uploads to the database.

```bash
# Incremental: from latest date in DB (recommended for daily use)
python -m carriers.ontrac.scripts.upload_expected --incremental

# Full: recalculate everything from 2025-01-01
python -m carriers.ontrac.scripts.upload_expected --full

# Last N days only
python -m carriers.ontrac.scripts.upload_expected --days 7

# Preview without making changes
python -m carriers.ontrac.scripts.upload_expected --incremental --dry-run
```

**Options:**
- `--production-sites Phoenix Columbus` - Filter by production site (default: both)
- `--batch-size 1000` - Rows per INSERT batch
- `--dry-run` - Preview without database changes

**Output table:** `shipping_costs.expected_shipping_costs_ontrac`

---

### 2. Upload Actual Costs

Pulls actual costs from OnTrac invoices and uploads to the database.

```bash
# Incremental: only orders without actuals (recommended)
python -m carriers.ontrac.scripts.upload_actuals --incremental

# Full: delete all and repull from invoices
python -m carriers.ontrac.scripts.upload_actuals --full

# Last N days
python -m carriers.ontrac.scripts.upload_actuals --days 7

# Limit number of orders to process
python -m carriers.ontrac.scripts.upload_actuals --incremental --limit 1000
```

**Output table:** `shipping_costs.actual_shipping_costs_ontrac`

---

### 3. Compare Expected to Actuals

Generates an HTML accuracy report comparing calculated vs actual invoice costs.

```bash
# All data
python -m carriers.ontrac.scripts.compare_expected_to_actuals

# Specific invoice
python -m carriers.ontrac.scripts.compare_expected_to_actuals --invoice INV-12345

# Date range
python -m carriers.ontrac.scripts.compare_expected_to_actuals --date_from 2025-01-01 --date_to 2025-01-31

# Custom output file
python -m carriers.ontrac.scripts.compare_expected_to_actuals --output my_report.html
```

**Report includes:**
- Portfolio summary (total expected/actual, variance)
- Cost position accuracy (base, each surcharge, fuel)
- Zone accuracy and cost impact
- Surcharge detection precision/recall
- Top outliers by variance

**Output:** `carriers/ontrac/scripts/output/accuracy_reports/comparison_report_YYYYMMDD_HHMMSS.html`

---

### 4. Interactive Calculator

CLI tool to calculate cost for a single shipment interactively.

```bash
python -m carriers.ontrac.scripts.calculator
```

Prompts for:
- Dimensions (L x W x H in inches)
- Weight (lbs)
- Destination ZIP and state
- Production site (Phoenix/Columbus)
- Ship date

Outputs detailed cost breakdown with surcharges.

---

## Typical Workflow

### Daily Operations
```bash
# 1. Upload new expected costs
python -m carriers.ontrac.scripts.upload_expected --incremental

# 2. Upload new actuals (after invoices arrive)
python -m carriers.ontrac.scripts.upload_actuals --incremental

# 3. Generate accuracy report
python -m carriers.ontrac.scripts.compare_expected_to_actuals
```

### After Configuration Changes
```bash
# 1. Run /review-config to verify changes are correct
# 2. Run tests to verify changes
pytest carriers/ontrac/tests/ -v

# 3. Full recalculation
python -m carriers.ontrac.scripts.upload_expected --full
```

---

## Directory Structure

```
carriers/ontrac/
├── calculate_costs.py      # Core calculation pipeline
├── version.py              # Version stamp for audit trail
├── data/
│   ├── loaders/            # Dynamic data loaders
│   │   └── pcs.py          # Load shipments from PCS database
│   └── reference/          # Static reference data
│       ├── zones.csv       # ZIP to zone mappings
│       ├── base_rates.csv  # Rate card by weight x zone
│       ├── fuel.py         # Fuel surcharge config
│       ├── billable_weight.py  # DIM factor config
│       ├── archive/        # Historical zones
│       └── contracts/      # Contract PDFs
├── surcharges/             # Surcharge implementations
│   ├── over_maximum_limits.py   # OML
│   ├── large_package.py         # LPS
│   ├── additional_handling.py   # AHS
│   ├── delivery_area.py         # DAS
│   ├── extended_delivery_area.py # EDAS
│   ├── residential.py           # RES (allocated)
│   └── demand_*.py              # Seasonal demand surcharges
├── scripts/                # CLI tools
│   ├── upload_expected.py
│   ├── upload_actuals.py
│   ├── compare_expected_to_actuals.py
│   ├── calculator.py
│   └── output/             # Generated reports
├── maintenance/            # Config update tools
│   └── generate_zones.py   # Update zones from invoices
└── tests/
    └── test_calculate_costs.py
```

---

## Core Concepts

### Two-Stage Calculation Pipeline

```python
from carriers.ontrac.calculate_costs import calculate_costs

# Input: DataFrame with shipment data
# Output: Same DataFrame with costs appended
result = calculate_costs(df)
```

**Stage 1: `supplement_shipments()`**
- Calculates dimensions (cubic inches, longest side, girth)
- Looks up zones (3-tier fallback: ZIP -> state mode -> default 5)
- Calculates billable weight (actual vs dimensional)

**Stage 2: `calculate()`**
- Applies surcharges with exclusivity rules
- Enforces minimum billable weights
- Looks up base rate from rate card
- Calculates fuel and total

### Required Input Columns

| Column | Type | Description |
|--------|------|-------------|
| `ship_date` | date | For demand period checks |
| `production_site` | str | "Phoenix" or "Columbus" |
| `shipping_zip_code` | str/int | 5-digit destination ZIP |
| `shipping_region` | str | State name (fallback for zone) |
| `length_in` | float | Package length in inches |
| `width_in` | float | Package width in inches |
| `height_in` | float | Package height in inches |
| `weight_lbs` | float | Actual weight in pounds |

### Surcharges

**Dimensional (mutually exclusive - highest priority wins):**
| Surcharge | Triggers | Net Cost |
|-----------|----------|----------|
| OML | weight > 150 lbs OR longest > 108" OR L+girth > 165" | $1,300.00 |
| LPS | longest > 72" OR cubic > 17,280 | $104.00 |
| AHS | weight > 50 lbs OR longest > 48" OR 2nd > 30" | $9.60 |

**Delivery Area (mutually exclusive):**
| Surcharge | Triggers | Net Cost |
|-----------|----------|----------|
| EDAS | Extended delivery area ZIP | $3.32 |
| DAS | Delivery area ZIP | $2.46 |

**Allocated:**
| Surcharge | Description | Net Cost |
|-----------|-------------|----------|
| RES | Residential (95% allocation) | $0.58/shipment |

**Demand (seasonal, Sept 27 - Jan 16):**
- DEM_AHS, DEM_LPS, DEM_OML: Apply when base surcharge triggers during period
- DEM_RES (Oct 25 - Jan 16): Applied to all shipments during period

---

## Configuration Maintenance

### Update Zones (Monthly/Quarterly)

```bash
python -m carriers.ontrac.maintenance.generate_zones --start-date 2025-01-01
```

Analyzes invoice data to find mode zones per ZIP, merges with existing zones file.

### Update Fuel Rate (Weekly)

1. Run `/review-config` to check current OnTrac website rate
2. Edit `carriers/ontrac/data/reference/fuel.py`
3. Update `carriers/ontrac/version.py`
4. Run: `python -m carriers.ontrac.scripts.upload_expected --incremental`

### Update Base Rates (Annual)

1. Update `carriers/ontrac/data/reference/base_rates.csv` with new rate card
2. Update `carriers/ontrac/version.py`
3. Run tests: `pytest carriers/ontrac/tests/ -v`
4. Full recalculation: `python -m carriers.ontrac.scripts.upload_expected --full`

### Update Surcharge Pricing

1. Edit surcharge class in `carriers/ontrac/surcharges/`
2. Update `list_price`, `discount`, or thresholds
3. Update `carriers/ontrac/version.py`
4. Run tests and recalculate

---

## Database

**Connection:** Redshift `bi_stage_dev` (credentials in `shared/database/pass.txt`)

**Tables:**
- `shipping_costs.expected_shipping_costs_ontrac` - Calculated expected costs
- `shipping_costs.actual_shipping_costs_ontrac` - Invoice actual costs

---

## Testing

```bash
# Run all tests
pytest carriers/ontrac/tests/ -v

# Run specific test class
pytest carriers/ontrac/tests/test_calculate_costs.py::TestSurchargeFlags -v
```

---

## Documentation

See `ontrac-calculator.html` in the project root for interactive documentation with diagrams and a working cost calculator demo.
