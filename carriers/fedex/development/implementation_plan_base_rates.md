# FedEx Base Rate Calculation - Implementation Plan

## Overview

Implement base rate calculation for FedEx Home Delivery and Ground Economy (SmartPost) services following the established OnTrac/USPS patterns.

**Scope**: Base rates only. Surcharges and fuel to be implemented separately.

---

## Phase 1: Reference Data Files

### Task 1.1: Create `data/reference/zones.csv`

**Source**: `temp_files/FedEx Zone Columbus.csv` and `temp_files/FedEx Zone Phoenix.csv`

**Target format**:
```csv
zip_code,state,cmh_zone,phx_zone
01001,MA,4,8
01002,MA,4,8
...
```

**Steps**:
1. Read both zone files
2. Merge on ZIP code
3. Rename columns: `Dest Zip/Postal Code` → `zip_code`, `State/Province` → `state`
4. Output columns: `zip_code`, `state`, `cmh_zone`, `phx_zone`
5. Validate: 58,772 rows expected

**Zone mapping**:
- Zones 2-8: Standard continental
- Zone 9: Hawaii
- Zone 17: Alaska

---

### Task 1.2: Create `data/reference/base_rates_home_delivery.csv`

**Source**: `temp_files/FedEx Rates Combined.xlsx`, sheet "Home Delivery 2025"

**Target format**:
```csv
weight_lbs,zone_2,zone_3,zone_4,zone_5,zone_6,zone_7,zone_8,zone_9,zone_17
1,8.07,8.07,8.07,8.07,8.07,8.07,8.07,40.84,40.84
2,8.07,8.07,8.07,8.07,8.07,8.07,8.07,45.42,45.42
...
150,40.61,41.71,45.06,46.27,50.88,54.96,61.91,606.09,606.09
```

**Steps**:
1. Read Excel sheet, skip first 9 rows
2. Keep columns: weight_lbs, 2, 3, 4, 5, 6, 7, 8, 9, 17
3. Rename zone columns to `zone_N` format
4. Validate: 150 rows (weights 1-150)

**Note**: Rate card has additional zones (14, 22, 23, 25, 92, 96). Per requirements, unknown zones will use the highest available zone rate (zone_17).

---

### Task 1.3: Create `data/reference/base_rates_ground_economy.csv`

**Source**: `temp_files/FedEx Rates Combined.xlsx`, sheet "Ground Economy 2025"

**Target format**:
```csv
weight_lbs,zone_2,zone_3,zone_4,zone_5,zone_6,zone_7,zone_8,zone_9,zone_17
1,6.87,6.87,6.87,6.87,6.87,6.87,6.87,26.22,26.22
2,6.87,6.87,6.87,6.87,6.87,6.90,7.02,29.60,29.60
...
70,41.42,41.42,41.93,43.33,45.03,48.42,53.29,222.23,222.23
```

**Steps**:
1. Read Excel sheet (header in first row)
2. Keep columns: weight_lbs, 2, 3, 4, 5, 6, 7, 8, 9, 17
3. Rename zone columns to `zone_N` format
4. Validate: 70 rows (weights 1-70)

**Note**: Ground Economy rate card zones 9, 10, 17, 26, 99 all have identical rates. Use zone 9 column for both zone 9 and zone 17.

---

### Task 1.4: Create `data/reference/discounts.py`

**Source**: `temp_files/FedEx Rates Combined.xlsx`, sheet "Earned Discounts"

**Content**:
```python
"""FedEx earned discount rates by service."""

HOME_DELIVERY_DISCOUNT = 0.17   # 17% discount
GROUND_ECONOMY_DISCOUNT = 0.045  # 4.5% discount
```

When updating to 2026 rates, we will update these values directly.

---

### Task 1.5: Create `data/reference/service_mapping.py`

**Source**: `temp_files/fedex_pcs_service_mapping.xlsx`

**Content**:
```python
"""FedEx PCS service code to rate service mapping."""

SERVICE_MAPPING = {
    # Ground Economy (SmartPost)
    "FXESPPS": "Ground Economy",
    "FXEGRD": "Ground Economy",
    "FXESPPSL": "Ground Economy",

    # Home Delivery
    "FXE2D": "Home Delivery",
    "FXE2DXLBOR": "Home Delivery",
    "FXE2DTBOR": "Home Delivery",
    "FXESTDO": "Home Delivery",
    "FXEINTECON": "Home Delivery",
    "FXEINTPRIO": "Home Delivery",
    "FXEPO": "Home Delivery",
    "FXE2DSBOR": "Home Delivery",
    "FXEHD": "Home Delivery",
    "FXE2DLBOR": "Home Delivery",
    "FXE2DMBOR": "Home Delivery",
    "FXE2DENVOR": "Home Delivery",
    "FXE2DPAKOR": "Home Delivery",
}

def get_rate_service(pcs_service_code: str) -> str:
    """Map PCS service code to rate service (Home Delivery or Ground Economy)."""
    return SERVICE_MAPPING.get(pcs_service_code, "Home Delivery")  # Default to HD
```

---

## Phase 2: Data Loaders

### Task 2.1: Verify `data/loaders/pcs.py`

The PCS query already contains `extkey` renamed to `pcs_shipping_provider`. We need to:
1. Verify this field is being returned
2. Confirm Columbus and Phoenix are the only origins (Miami is closed)
3. Verify carrier filter is "FEDEX"

No code changes expected, just verification.

---

### Task 2.2: Update `data/__init__.py` exports

**Content**:
```python
from .loaders.pcs import load_shipments
from .reference import (
    load_zones,
    load_base_rates_home_delivery,
    load_base_rates_ground_economy,
    DIM_FACTOR,
    DIM_THRESHOLD,
)
from .reference.discounts import HOME_DELIVERY_DISCOUNT, GROUND_ECONOMY_DISCOUNT
from .reference.service_mapping import SERVICE_MAPPING, get_rate_service
```

---

### Task 2.3: Update `data/reference/__init__.py`

**Add functions**:
```python
def load_zones() -> pl.DataFrame:
    """Load zone lookup table."""
    path = Path(__file__).parent / "zones.csv"
    return pl.read_csv(path)

def load_base_rates_home_delivery() -> pl.DataFrame:
    """Load Home Delivery base rates."""
    path = Path(__file__).parent / "base_rates_home_delivery.csv"
    return pl.read_csv(path)

def load_base_rates_ground_economy() -> pl.DataFrame:
    """Load Ground Economy base rates."""
    path = Path(__file__).parent / "base_rates_ground_economy.csv"
    return pl.read_csv(path)
```

---

## Phase 3: Calculator Implementation

### Task 3.1: Update `calculate_costs.py` - Service Detection

**Add to `supplement_shipments()`**:
```python
def _add_service_type(df: pl.DataFrame) -> pl.DataFrame:
    """Add rate_service column based on PCS service code (pcs_shipping_provider)."""
    from .data.reference.service_mapping import SERVICE_MAPPING

    return df.with_columns(
        pl.col("pcs_shipping_provider")
        .replace(SERVICE_MAPPING, default="Home Delivery")
        .alias("rate_service")
    )
```

---

### Task 3.2: Update `calculate_costs.py` - Zone Lookup

**State-Level Fallback Implementation** (following OnTrac pattern):

```python
def _lookup_zones(df: pl.DataFrame, zones: pl.DataFrame) -> pl.DataFrame:
    """
    Look up shipping zone based on destination ZIP and origin.

    THREE-TIER FALLBACK
    -------------------
    1. Exact ZIP code match from zones.csv
    2. State-level mode (most common zone for that state)
    3. Default zone 5 (mid-range, minimizes worst-case pricing error)
    """
    # Normalize ZIP code to 5 digits with leading zeros
    df = df.with_columns(
        pl.col("shipping_zip_code")
        .cast(pl.Utf8)
        .str.slice(0, 5)
        .str.zfill(5)
        .alias("_zip_normalized")
    )

    zones_subset = zones.select(["zip_code", "state", "phx_zone", "cmh_zone"])

    # State-level fallback: calculate mode (most common) zone per state
    # This handles ZIPs not in our zone file by using the typical zone for that state
    state_zones = (
        zones
        .group_by("state")
        .agg([
            pl.col("phx_zone").mode().first().alias("_state_phx_zone"),
            pl.col("cmh_zone").mode().first().alias("_state_cmh_zone"),
        ])
    )

    # Join on ZIP code (exact match - tier 1)
    df = df.join(zones_subset, left_on="_zip_normalized", right_on="zip_code", how="left")

    # Join state fallback (tier 2)
    df = df.join(state_zones, left_on="shipping_region", right_on="state", how="left")

    # Coalesce: ZIP zone -> state mode zone -> default zone 5
    df = df.with_columns([
        pl.coalesce(["phx_zone", "_state_phx_zone", pl.lit(5)]).alias("_phx_zone_final"),
        pl.coalesce(["cmh_zone", "_state_cmh_zone", pl.lit(5)]).alias("_cmh_zone_final"),
    ])

    # Select zone based on production site
    df = df.with_columns(
        pl.when(pl.col("production_site") == "Phoenix")
        .then(pl.col("_phx_zone_final"))
        .when(pl.col("production_site") == "Columbus")
        .then(pl.col("_cmh_zone_final"))
        .otherwise(pl.lit(5))  # Unknown origin defaults to zone 5
        .alias("shipping_zone")
    )

    # Drop intermediate columns
    df = df.drop([
        "_zip_normalized",
        "phx_zone", "cmh_zone",
        "_state_phx_zone", "_state_cmh_zone",
        "_phx_zone_final", "_cmh_zone_final",
        "state",
    ])

    return df
```

**How state-level fallback works**:
- For each state, we calculate the mode (most common zone) from all ZIPs in that state
- If a specific ZIP isn't found, we use that state's typical zone
- This is better than defaulting to zone 5 because it accounts for geography (e.g., CA ZIPs missing from file will get a CA-typical zone rather than zone 5)

---

### Task 3.3: Update `calculate_costs.py` - Base Rate Lookup

**Add base rate lookup function**:
```python
def _lookup_base_rate(df: pl.DataFrame) -> pl.DataFrame:
    """Look up base rate based on service, zone, and billable weight."""

    # Load rate tables
    hd_rates = load_base_rates_home_delivery()
    ge_rates = load_base_rates_ground_economy()

    # Cap weights at max for each service
    df = df.with_columns(
        pl.when(pl.col("rate_service") == "Home Delivery")
        .then(pl.col("billable_weight_lbs").clip(upper=150))
        .otherwise(pl.col("billable_weight_lbs").clip(upper=70))
        .alias("_capped_weight")
    )

    # Ceiling weight to integer for lookup (1 lb minimum)
    df = df.with_columns(
        pl.col("_capped_weight").ceil().clip(lower=1).cast(pl.Int32).alias("_weight_bracket")
    )

    # Map unknown zones to highest available (zone 17)
    # Known zones: 2, 3, 4, 5, 6, 7, 8, 9, 17
    df = df.with_columns(
        pl.when(pl.col("shipping_zone").is_in([2, 3, 4, 5, 6, 7, 8, 9, 17]))
        .then(pl.col("shipping_zone"))
        .otherwise(pl.lit(17))
        .alias("_rate_zone")
    )

    # Unpivot rate tables to long format for joining
    # Home Delivery rates
    hd_long = hd_rates.unpivot(
        index="weight_lbs",
        variable_name="zone",
        value_name="rate"
    ).with_columns([
        pl.col("zone").str.replace("zone_", "").cast(pl.Int32).alias("zone"),
        pl.lit("Home Delivery").alias("service")
    ])

    # Ground Economy rates
    ge_long = ge_rates.unpivot(
        index="weight_lbs",
        variable_name="zone",
        value_name="rate"
    ).with_columns([
        pl.col("zone").str.replace("zone_", "").cast(pl.Int32).alias("zone"),
        pl.lit("Ground Economy").alias("service")
    ])

    # Combine rate tables
    all_rates = pl.concat([hd_long, ge_long])

    # Join to get base rate
    df = df.join(
        all_rates,
        left_on=["rate_service", "_weight_bracket", "_rate_zone"],
        right_on=["service", "weight_lbs", "zone"],
        how="left"
    ).rename({"rate": "cost_base_list"})

    # Clean up
    df = df.drop(["_capped_weight", "_weight_bracket", "_rate_zone"])

    return df
```

---

### Task 3.4: Update `calculate_costs.py` - Apply Discount

**Add discount application**:
```python
def _apply_earned_discount(df: pl.DataFrame) -> pl.DataFrame:
    """Apply earned discount based on service type."""
    from .data.reference.discounts import HOME_DELIVERY_DISCOUNT, GROUND_ECONOMY_DISCOUNT

    return df.with_columns(
        pl.when(pl.col("rate_service") == "Home Delivery")
        .then(pl.col("cost_base_list") * (1 - HOME_DELIVERY_DISCOUNT))
        .otherwise(pl.col("cost_base_list") * (1 - GROUND_ECONOMY_DISCOUNT))
        .round(2)
        .alias("cost_base")
    )
```

---

## Phase 4: Update `calculate()` Function

### Task 4.1: Integrate Base Rate into Main Flow

**Updated `calculate()` structure**:
```python
def calculate(df: pl.DataFrame) -> pl.DataFrame:
    """Calculate shipping costs."""

    # 1. Look up base rate (list price)
    df = _lookup_base_rate(df)

    # 2. Apply earned discount
    df = _apply_earned_discount(df)

    # 3. Apply surcharges (FUTURE - placeholder for now)
    # df = _apply_surcharges(df, BASE)
    # df = _apply_surcharges(df, DEPENDENT)

    # 4. Calculate subtotal
    df = df.with_columns(
        pl.col("cost_base").alias("cost_subtotal")  # Just base for now
    )

    # 5. Apply fuel surcharge (FUTURE - placeholder for now)
    df = df.with_columns(
        pl.lit(0.0).alias("cost_fuel")
    )

    # 6. Calculate total
    df = df.with_columns(
        (pl.col("cost_subtotal") + pl.col("cost_fuel")).alias("cost_total")
    )

    # 7. Stamp version
    df = df.with_columns(
        pl.lit(VERSION).alias("calculator_version")
    )

    return df
```

---

## Phase 5: Testing & Validation

### Task 5.1: Create Test Data

**File**: `tests/test_calculate_costs.py`

**Test cases**:
1. Home Delivery, Zone 5, 10 lbs, Columbus origin
2. Home Delivery, Zone 8, 25 lbs, Phoenix origin
3. Ground Economy, Zone 3, 5 lbs, Columbus origin
4. Ground Economy, Zone 7, 15 lbs, Phoenix origin
5. Alaska (Zone 17), both services
6. Hawaii (Zone 9), both services
7. Unknown zone fallback (should use zone 17)
8. Weight over max (cap test: 160 lbs → 150 lbs for HD)
9. ZIP not found fallback (should use state mode, then zone 5)

### Task 5.2: Validation Against Invoices

**Approach**:
1. Sample 100 random shipments from invoice data
2. Calculate expected base rate (list price)
3. Compare to invoice data

**Note**: `transportation_charge_amount` in invoices may not contain discounts - we'll verify this during comparison. If it's the list price, compare to `cost_base_list`. If it's discounted, compare to `cost_base`.

---

## File Checklist

### New Files to Create
- [ ] `data/reference/zones.csv`
- [ ] `data/reference/base_rates_home_delivery.csv`
- [ ] `data/reference/base_rates_ground_economy.csv`
- [ ] `data/reference/discounts.py`
- [ ] `data/reference/service_mapping.py`
- [ ] `tests/test_calculate_costs.py`

### Files to Update
- [ ] `data/reference/__init__.py` - Add loader functions
- [ ] `data/__init__.py` - Add exports
- [ ] `data/loaders/pcs.py` - Verify (no changes expected)
- [ ] `calculate_costs.py` - Implement zone lookup, base rate, discount
- [ ] `version.py` - Update version stamp

---

## Implementation Order

```
Phase 1: Reference Data (Tasks 1.1 - 1.5)
    ↓
Phase 2: Data Loaders (Tasks 2.1 - 2.3)
    ↓
Phase 3: Calculator Logic (Tasks 3.1 - 3.4)
    ↓
Phase 4: Integration (Task 4.1)
    ↓
Phase 5: Testing (Tasks 5.1 - 5.2)
```

**Estimated tasks**: 14 discrete tasks across 5 phases

---

## Notes

1. **Dimensional weight**: Reuse existing DIM_FACTOR/DIM_THRESHOLD logic already in skeleton
2. **Multi-shipment handling**: Defer to surcharge phase
3. **Fuel surcharge**: Placeholder for now, implement with other surcharges
4. **Production sites**: Columbus and Phoenix only (Miami is closed)
5. **Invoice comparison**: Will need to verify if `transportation_charge_amount` is list or discounted price
