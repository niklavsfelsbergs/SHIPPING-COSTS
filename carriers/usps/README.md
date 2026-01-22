# USPS Shipping Cost Calculator

Calculates expected shipping costs for USPS Ground Advantage shipments, uploads them to Redshift, and compares against actual invoice costs.

**Service:** Ground Advantage (max 20 lbs)

---

## Quick Reference

| Task | Command |
|------|---------|
| Upload expected costs (incremental) | `python -m carriers.usps.scripts.upload_expected --incremental` |
| Upload actual costs (incremental) | `python -m carriers.usps.scripts.upload_actuals --incremental` |
| Compare expected vs actual | `python -m carriers.usps.scripts.compare_expected_to_actuals` |
| Calculate single shipment | `python -m carriers.usps.scripts.calculator` |
| Run tests | `pytest carriers/usps/tests/` |

---

## Scripts

### 1. Upload Expected Costs

Calculates expected shipping costs from PCS shipment data and uploads to the database.

```bash
# Incremental: from latest date in DB (recommended for daily use)
python -m carriers.usps.scripts.upload_expected --incremental

# Full: recalculate everything from 2025-01-01
python -m carriers.usps.scripts.upload_expected --full

# Last N days only
python -m carriers.usps.scripts.upload_expected --days 7

# Preview without making changes
python -m carriers.usps.scripts.upload_expected --full --dry-run
```

**Options:**
- `--production-sites Phoenix Columbus` - Filter by production site (default: both)
- `--batch-size 1000` - Rows per INSERT batch
- `--dry-run` - Preview without database changes

**Output table:** `shipping_costs.expected_shipping_costs_usps`

---

### 2. Upload Actual Costs

Pulls actual costs from USPS invoices and uploads to the database.

```bash
# Incremental: only orders without actuals (recommended)
python -m carriers.usps.scripts.upload_actuals --incremental

# Full: delete all and repull from invoices
python -m carriers.usps.scripts.upload_actuals --full

# Last N days
python -m carriers.usps.scripts.upload_actuals --days 7

# Limit number of orders to process
python -m carriers.usps.scripts.upload_actuals --incremental --limit 1000
```

**Options:**
- `--batch-size 1000` - Rows per INSERT batch
- `--limit N` - Limit orders to process (for incremental mode)
- `--dry-run` - Preview without database changes

**Output table:** `shipping_costs.actual_shipping_costs_usps`

---

### 3. Compare Expected to Actuals

Generates an HTML accuracy report comparing calculated vs actual invoice costs.

```bash
# All data
python -m carriers.usps.scripts.compare_expected_to_actuals

# Date range
python -m carriers.usps.scripts.compare_expected_to_actuals --date_from 2025-01-01 --date_to 2025-01-31
```

**Output:** `carriers/usps/scripts/output/accuracy_reports/comparison_report_YYYYMMDD_HHMMSS.html`

---

### 4. Interactive Calculator

CLI tool to calculate cost for a single shipment interactively.

```bash
python -m carriers.usps.scripts.calculator
```

Prompts for:
- Dimensions (L x W x H in inches)
- Weight (lbs)
- Destination ZIP and state
- Production site (Phoenix/Columbus)
- Ship date

Outputs detailed cost breakdown with surcharges.

---

## Directory Structure

```
carriers/usps/
├── calculate_costs.py      # Core calculation pipeline
├── version.py              # Version stamp for audit trail
├── data/
│   ├── loaders/            # Dynamic data loaders
│   │   └── pcs.py          # Load shipments from PCS database
│   └── reference/          # Static reference data
│       ├── zones.csv       # 3-digit ZIP prefix to zone mapping
│       ├── base_rates.csv  # Rate card by weight x zone
│       ├── billable_weight.py  # DIM factor config
│       └── contracts/      # Contract PDFs
├── surcharges/             # Surcharge implementations
│   ├── nonstandard_length_22.py   # NSL1 (22-30")
│   ├── nonstandard_length_30.py   # NSL2 (>30")
│   ├── nonstandard_volume.py      # NSV (>2 cu ft)
│   └── peak.py                    # Peak season surcharge
├── scripts/                # CLI tools
│   ├── upload_expected.py
│   ├── upload_actuals.py
│   ├── compare_expected_to_actuals.py
│   ├── calculator.py
│   └── output/             # Generated reports
└── tests/
    └── test_calculate_costs.py
```

---

## Core Concepts

### Two-Stage Calculation Pipeline

```python
from carriers.usps.calculate_costs import calculate_costs

# Input: DataFrame with shipment data
# Output: Same DataFrame with costs appended
result = calculate_costs(df)
```

**Stage 1: `supplement_shipments()`**
- Calculates dimensions (cubic inches, longest side, second longest)
- Rounds dimensions to 1 decimal place (prevents floating-point threshold issues)
- Looks up zones by 3-digit ZIP prefix (3-tier fallback: ZIP -> mode -> default 5)
- Handles asterisk zones (1*, 2*, 3*) - stripped for rate lookup
- Calculates billable weight (actual vs dimensional)

**Stage 2: `calculate()`**
- Applies base surcharges (NSL1, NSL2, NSV)
- Looks up base rate from rate card
- Applies peak season surcharge (if applicable)
- Calculates total (no fuel surcharge for USPS)

### Required Input Columns

| Column | Type | Description |
|--------|------|-------------|
| `ship_date` | date | For peak season checks |
| `production_site` | str | "Phoenix" or "Columbus" |
| `shipping_zip_code` | str/int | 5-digit destination ZIP |
| `shipping_region` | str | State name (fallback for zone) |
| `length_in` | float | Package length in inches |
| `width_in` | float | Package width in inches |
| `height_in` | float | Package height in inches |
| `weight_lbs` | float | Actual weight in pounds |

### Surcharges

**Length-based (mutually exclusive - highest priority wins):**
| Surcharge | Triggers | Cost |
|-----------|----------|------|
| NSL2 | longest > 30" | $3.00 |
| NSL1 | longest > 22" AND <= 30" | $3.00 |

**Volume-based (independent, can stack with length):**
| Surcharge | Triggers | Cost |
|-----------|----------|------|
| NSV | cubic > 3,456 cu in (2 cu ft) | $10.00 |

**Peak Season (Oct 5 - Jan 18):**
| Weight Tier | Zones 1-4 | Zones 5-9 |
|-------------|-----------|-----------|
| 0-3 lbs | $0.30 | $0.35 |
| 4-10 lbs | $0.45 | $0.75 |
| 11-25 lbs | $0.75 | $1.25 |

---

## Key Differences from OnTrac

| Aspect | USPS | OnTrac |
|--------|------|--------|
| Zone lookup | 3-digit ZIP prefix | 5-digit ZIP |
| Asterisk zones | Yes (1*, 2*, 3*) | No |
| Fuel surcharge | None | 18.75% of subtotal |
| Max weight | 20 lbs | 150 lbs |
| DIM factor | 200 | 250 |
| DIM threshold | 1,728 cu in (1 cu ft) | 1,728 cu in |
| Surcharges | 3 + peak | 10 (incl. demand) |
| Min billable weight | None | Yes (OML/LPS/AHS) |

---

## Billable Weight Calculation

USPS uses dimensional weight when:
1. `cubic_in > 1,728` (1 cubic foot threshold)
2. `dim_weight > actual_weight`

Dimensional weight formula:
```
dim_weight_lbs = cubic_in / 200
billable_weight_lbs = max(weight_lbs, dim_weight_lbs)
```

---

## Zone Lookup

USPS zones are determined by 3-digit ZIP prefix (first 3 digits of ZIP code), unlike OnTrac which uses full 5-digit ZIP.

**Asterisk Zones:**
Some zones have asterisk variants (1*, 2*, 3*) indicating local delivery. The asterisk is preserved in `shipping_zone` for reference but stripped in `rate_zone` for rate table lookup.

**Fallback Order:**
1. Exact 3-digit ZIP prefix match from zones.csv
2. Overall mode zone (most common zone across all ZIPs)
3. Default zone 5

---

## Configuration

### DIM Factor
- **Factor:** 200 (cubic inches per pound)
- **Threshold:** 1,728 cu in (1 cubic foot)
- **Location:** `data/reference/billable_weight.py`

### Base Rates
- **Format:** CSV with weight brackets and zone columns
- **Location:** `data/reference/base_rates.csv`
- **Zones:** 1-8

### Peak Periods
- **Location:** `surcharges/peak.py`
- **Current periods:** Oct 5 - Jan 18 each year

---

## Database

**Connection:** Redshift `bi_stage_dev` (credentials in `shared/database/pass.txt`)

**Tables:**
- `shipping_costs.expected_shipping_costs_usps` - Calculated expected costs
- `shipping_costs.actual_shipping_costs_usps` - Invoice actual costs

---

## Testing

```bash
# Run all tests
pytest carriers/usps/tests/ -v

# Run specific test class
pytest carriers/usps/tests/test_calculate_costs.py::TestSurchargeFlags -v
```

---

## Contract References

See `data/reference/contracts/current/` for contract documents including:
- Base rate tables (Tier 1 pricing)
- Zone charts by origin
- Surcharge schedules
