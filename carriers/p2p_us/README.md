# P2P US Shipping Cost Calculator

Calculates expected shipping costs for P2P Parcel Flex Advantage Plus (PFAP2) shipments, uploads them to Redshift, and compares against actual invoice costs.

**Service:** Parcel Flex Advantage Plus (PFAP2, max 50 lbs)

---

## Quick Reference

| Task | Command |
|------|---------|
| Upload expected costs (incremental) | `python -m carriers.p2p_us.scripts.upload_expected_all_us --incremental` |
| Calculate single shipment | `python -m carriers.p2p_us.scripts.calculator` |

---

## Scripts

### 1. Upload Expected Costs

Calculates expected shipping costs from PCS shipment data and uploads to the database.

```bash
# Incremental: from latest date in DB (recommended for daily use)
python -m carriers.p2p_us.scripts.upload_expected_all_us --incremental

# Full: recalculate everything from 2025-01-01
python -m carriers.p2p_us.scripts.upload_expected_all_us --full

# Last N days only
python -m carriers.p2p_us.scripts.upload_expected_all_us --days 7

# Preview without making changes
python -m carriers.p2p_us.scripts.upload_expected_all_us --full --dry-run
```

**Options:**
- `--production-sites Columbus` - Filter by production site (default: Columbus)
- `--batch-size 5000` - Rows per INSERT batch
- `--dry-run` - Preview without database changes

**Output table:** `shipping_costs.expected_shipping_costs_p2p_us`

---

### 2. Interactive Calculator

CLI tool to calculate cost for a single shipment interactively.

```bash
python -m carriers.p2p_us.scripts.calculator
```

Prompts for:
- Dimensions (L x W x H in inches)
- Weight (lbs)
- Destination ZIP (5-digit)
- Ship date

Outputs detailed cost breakdown with surcharges.

---

## Directory Structure

```
carriers/p2p_us/
├── calculate_costs.py      # Core calculation pipeline
├── version.py              # Version stamp for audit trail
├── data/
│   ├── loaders/            # Dynamic data loaders
│   │   └── pcs.py          # Load shipments from PCS database
│   └── reference/          # Static reference data
│       ├── zones.csv       # 5-digit ZIP to zone mapping
│       ├── base_rates.csv  # Rate card by weight x zone
│       └── billable_weight.py  # DIM factor config
├── surcharges/             # Surcharge implementations
│   ├── additional_handling.py  # AHS ($29)
│   └── oversize.py             # Oversize ($125)
├── scripts/                # CLI tools
│   ├── upload_expected_all_us.py
│   ├── calculator.py
│   └── sql/
│       └── create_expected_table.sql
└── temp_files/             # Source Excel files
```

---

## Core Concepts

### Two-Stage Calculation Pipeline

```python
from carriers.p2p_us.calculate_costs import calculate_costs

# Input: DataFrame with shipment data
# Output: Same DataFrame with costs appended
result = calculate_costs(df)
```

**Stage 1: `supplement_shipments()`**
- Calculates dimensions (cubic inches, longest side, second longest, length+girth)
- Rounds dimensions to 1 decimal place (prevents floating-point threshold issues)
- Looks up zones by 5-digit ZIP (fallback: mode -> default 5)
- Calculates billable weight (always compares actual vs dimensional - no threshold)

**Stage 2: `calculate()`**
- Applies AHS minimum billable weight (30 lbs) for dimensional conditions
- Applies surcharges (AHS, Oversize)
- Looks up base rate from rate card
- Calculates total (no fuel surcharge)

### Required Input Columns

| Column | Type | Description |
|--------|------|-------------|
| `ship_date` | date | Ship date |
| `production_site` | str | "Columbus" |
| `shipping_zip_code` | str/int | 5-digit destination ZIP |
| `shipping_region` | str | State name (for reference) |
| `length_in` | float | Package length in inches |
| `width_in` | float | Package width in inches |
| `height_in` | float | Package height in inches |
| `weight_lbs` | float | Actual weight in pounds |

---

## Surcharges

### Additional Handling (AHS) - $29.00

Triggers when ANY of these conditions are met:
| Condition | Threshold |
|-----------|-----------|
| Longest side | > 48" |
| Second longest side | > 30" |
| Length + Girth | > 105" |
| Billable weight | > 30 lbs |

**Side Effect:** When AHS triggers due to dimensional conditions (1-3), enforces a **30 lb minimum billable weight** before rate lookup.

### Oversize - $125.00

| Condition | Threshold |
|-----------|-----------|
| Billable weight | > 70 lbs |

Note: Since max service weight is 50 lbs, this only applies when DIM weight exceeds 70 lbs.

---

## Billable Weight Calculation

P2P US **always** compares actual vs dimensional weight (no threshold):

```
dim_weight_lbs = cubic_in / 250
billable_weight_lbs = max(weight_lbs, dim_weight_lbs)
```

**AHS Minimum Weight:** When AHS triggers due to dimensional conditions (longest >48", second longest >30", or L+G >105"), billable weight is bumped to at least 30 lbs before rate lookup.

| Config | Value |
|--------|-------|
| DIM Factor | 250 |
| DIM Threshold | None (always compare) |
| AHS Min Weight | 30 lbs |

---

## Zone Lookup

P2P US zones are determined by **5-digit ZIP code** (full ZIP, not prefix).

**Fallback Order:**
1. Exact 5-digit ZIP match from zones.csv
2. Overall mode zone (most common zone across all ZIPs)
3. Default zone 5

**Zone Mapping:**
- Zones 1-8 from rate card
- Puerto Rico (zone 9) and Hawaii (zone 12) mapped to zone 8

---

## Key Differences from Other Carriers

| Aspect | P2P US | Maersk US | USPS |
|--------|--------|-----------|------|
| Zone lookup | 5-digit ZIP | 3-digit prefix | 3-digit prefix |
| DIM factor | 250 | 166 | 200 |
| DIM threshold | None | None | 1,728 cu in |
| Max weight | 50 lbs | 70 lbs | 20 lbs |
| Fuel surcharge | None | None | None |
| Min billable weight | 30 lbs (AHS) | None | None |
| Zones | 1-8 | 1-9 | 1-8 |

---

## Configuration

### Base Rates
- **Format:** CSV with weight brackets (oz and lb) and zone columns
- **Location:** `data/reference/base_rates.csv`
- **Weight brackets:** 16 oz brackets + 50 lb brackets (66 total)
- **Zones:** 1-8

### Zone Mapping
- **Format:** CSV with 5-digit ZIP and zone
- **Location:** `data/reference/zones.csv`
- **Entries:** ~10,430 ZIPs
- **Origin:** ORD (Chicago)

---

## Database

**Connection:** Redshift `bi_stage_dev` (credentials in `shared/database/pass.txt`)

**Tables:**
- `shipping_costs.expected_shipping_costs_p2p_us` - Calculated expected costs

**DDL:** `scripts/sql/create_expected_table.sql`

---

## Reference Data Sources

- **Rate card:** `temp_files/P2PG_PicaNova_PFAP2_20260127.xlsx` (P2PG_PFAP sheet)
- **Zone mapping:** `temp_files/P2PG_PicaNova_PFAP2_20260127.xlsx` (PFAP_Zips_ORD sheet)
