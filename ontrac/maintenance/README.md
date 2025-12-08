# OnTrac Maintenance Guide

Instructions for updating carrier data when rates, zones, or contract terms change.

---

## Base Rates

**Location:** `ontrac/data/base_rates.csv`

### When to Update
- When OnTrac sends a new rate card (typically annually or with contract renewals)

### File Format

| Column | Description |
|--------|-------------|
| weight_lbs_lower | Weight bracket lower bound (exclusive) |
| weight_lbs_upper | Weight bracket upper bound (inclusive) |
| zone_2...zone_8 | Rate per zone in USD |

### How to Update

1. Replace the contents of `base_rates.csv` with the new rate card
2. Update `ontrac/version.py`: `VERSION = "YYYY.MM.DD"`
3. Commit: `git commit -m "Rate update effective YYYY-MM-DD"`

**Note:** Git handles versioning. To recalculate with old rates: `git checkout <commit>` and run.

---

## Zones

**Location:** `ontrac/data/zones.csv`

### When to Update
- Periodically (e.g., monthly or quarterly) to align zones with actual invoice data
- After noticing zone mismatches in cost calculations

### File Format

| Column | Description |
|--------|-------------|
| zip_code | 5-digit ZIP code (zero-padded) |
| shipping_state | Full state name |
| phx_zone | Zone for Phoenix production site (2-8) |
| cmh_zone | Zone for Columbus production site (2-8) |
| das | Delivery Area Surcharge: "DAS", "EDAS", or "NO" |

### How to Update

Run from project root (`SHIPPING-COSTS/`):

```bash
# Update from all historical invoice data
python -m ontrac.maintenance.generate_zones

# Update from specific date range
python -m ontrac.maintenance.generate_zones --start-date 2025-01-01
python -m ontrac.maintenance.generate_zones --start-date 2025-01-01 --end-date 2025-06-30
```

### What the Script Does

1. Loads invoice data joined with PCS shipment data
2. Calculates the most common (mode) zone for each ZIP + production site
3. Compares with existing zones and reports changes
4. Archives the current `zones.csv` to `ontrac/data/archive/` with timestamp
5. Saves updated zones to `zones.csv`

### Archive

Previous zone files are saved to `ontrac/data/archive/` with format `zones_YYYY-MM-DD.csv`.

---

## Surcharges

**Location:** `ontrac/surcharges/*.py`

Each surcharge is defined as a class inheriting from `Surcharge` base class.

### When to Update
- When contract amendments change discounts
- When OnTrac changes list prices (check ontrac.com/surcharges)
- When trigger thresholds change

### Surcharge File Structure

```python
class AHS(Surcharge):
    name = "AHS"

    # Pricing
    list_price = 32.00    # Published rate
    discount = 0.70       # 70% off (contract)

    # Thresholds (if applicable)
    WEIGHT_LBS = 50
    LONGEST_IN = 48

    @classmethod
    def conditions(cls) -> pl.Expr:
        # Polars expression for when surcharge triggers
        ...
```

### How to Update Discounts

1. Edit the surcharge file (e.g., `ontrac/surcharges/additional_handling.py`)
2. Update `discount` value
3. Update `ontrac/version.py`: `VERSION = "YYYY.MM.DD"`
4. Commit: `git commit -m "AHS discount changed to X% per Amendment Y"`

### How to Update List Prices

1. Edit the surcharge file
2. Update `list_price` value
3. Update version and commit

### How to Update Thresholds

1. Edit the surcharge file
2. Update threshold constants (e.g., `WEIGHT_LBS`, `LONGEST_IN`)
3. Update version and commit

---

## Fuel Rate

**Location:** `ontrac/data/fuel.py`

### When to Update
- Weekly (fuel rate changes every Monday on ontrac.com/surcharges)
- Or when running calculations for a specific period

### How to Update

Edit `ontrac/data/fuel.py`:

```python
LIST_RATE = 0.195   # 19.5% - check ontrac.com/surcharges
DISCOUNT = 0.35     # 35% contract discount (rarely changes)
```

Update the "Last updated" comment at the top of the file.

---

## Billable Weight (DIM Factor)

**Location:** `ontrac/data/billable_weight.py`

### When to Update
- When contract DIM factor changes (rare)

### How to Update

Edit `ontrac/data/billable_weight.py`:

```python
DIM_FACTOR = 250      # Cubic inches per pound
DIM_THRESHOLD = 1728  # Min cubic inches to apply DIM weight
```

---

## Demand Periods

**Location:** Individual surcharge files in `ontrac/surcharges/demand_*.py`

### When to Update
- Annually (OnTrac announces demand period dates each year)
- Check ontrac.com/surcharges in late summer for upcoming season

### How to Update

Edit the demand surcharge files (e.g., `demand_residential.py`):

```python
class DEM_RES(Surcharge):
    period_start = (10, 25)  # Oct 25
    period_end = (1, 16)     # Jan 16
```

---

## Version Management

**Location:** `ontrac/version.py`

Always update `VERSION` when changing any configuration:

```python
VERSION = "2025.12.08"  # YYYY.MM.DD format
```

This version is stamped on every calculation output (`calculator_version` column) for audit purposes.
