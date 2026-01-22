# USPS Ground Advantage - Calculation Logic

Step-by-step breakdown of how the calculator determines the final shipping cost.

---

## Overview

```
cost_total = cost_base + cost_nsl1 + cost_nsl2 + cost_nsv + cost_peak
```

USPS Ground Advantage has no fuel surcharge (unlike OnTrac).

---

## Input Requirements

| Column | Description | Example |
|--------|-------------|---------|
| `ship_date` | Shipping date | 2025-11-15 |
| `production_site` | Origin facility | "Phoenix" or "Columbus" |
| `shipping_zip_code` | Destination ZIP (5-digit) | "90210" |
| `shipping_region` | Destination state | "California" |
| `length_in` | Package length | 12.0 |
| `width_in` | Package width | 8.0 |
| `height_in` | Package height | 6.0 |
| `weight_lbs` | Actual weight | 2.5 |

---

## Step 1: Calculate Dimensions

From the input dimensions, calculate derived values:

| Calculation | Formula | Example |
|-------------|---------|---------|
| `cubic_in` | length × width × height | 12 × 8 × 6 = 576 |
| `longest_side_in` | max(length, width, height) | 12.0 |
| `second_longest_in` | middle dimension | 8.0 |
| `length_plus_girth` | longest + 2 × (sum of other two) | 12 + 2×(8+6) = 40 |

---

## Step 2: Zone Lookup

Determine shipping zone based on origin and destination.

### Process

1. Extract **3-digit ZIP prefix** from destination (e.g., "90210" → "902")
2. Look up in `zones.csv` using origin-specific column:
   - Phoenix → `phx_zone`
   - Columbus → `cmh_zone`
3. Store as `shipping_zone` (may have asterisk: "1*", "2*", "3*")
4. Strip asterisk for rate lookup → `rate_zone` (integer 1-8)

### Fallback

If ZIP prefix not found:
1. Use mode zone for that origin
2. Default to zone 5

### Example

| Origin | Destination | ZIP Prefix | Zone |
|--------|-------------|------------|------|
| Phoenix | 90210 | 902 | 4 |
| Columbus | 90210 | 902 | 8 |
| Phoenix | 85006 | 850 | 1* → rate_zone = 1 |

---

## Step 3: Calculate Billable Weight

Determine whether to use actual weight or dimensional weight.

### Configuration

| Parameter | Value | Description |
|-----------|-------|-------------|
| `DIM_FACTOR` | 200 | Divisor for DIM weight (contract rate) |
| `DIM_THRESHOLD` | 1,728 cu in | Minimum volume to apply DIM (1 cubic foot) |

### Formula

```
dim_weight_lbs = cubic_in / 200
```

### Logic

```
IF cubic_in > 1,728:
    billable_weight = MAX(weight_lbs, dim_weight_lbs)
    uses_dim_weight = (dim_weight_lbs > weight_lbs)
ELSE:
    billable_weight = weight_lbs
    uses_dim_weight = False
```

### Example

| Package | Cubic In | Actual Wt | DIM Wt | Billable Wt |
|---------|----------|-----------|--------|-------------|
| Small (10×8×6) | 480 | 2.0 | 2.4 | 2.0 (actual, under threshold) |
| Large (20×20×10) | 4,000 | 5.0 | 20.0 | 20.0 (DIM) |
| Heavy (20×20×10) | 4,000 | 25.0 | 20.0 | 25.0 (actual > DIM) |

---

## Step 4: Look Up Base Rate

Find the base shipping rate from `base_rates.csv`.

### Lookup Keys

- `rate_zone` (1-8)
- `billable_weight_lbs` (matched to weight bracket)

### Weight Brackets

| Bracket | Range |
|---------|-------|
| 4 oz | 0 < weight ≤ 0.25 |
| 8 oz | 0.25 < weight ≤ 0.5 |
| 12 oz | 0.5 < weight ≤ 0.75 |
| 1 lb | 0.75 < weight ≤ 1.0 |
| 2 lb | 1.0 < weight ≤ 2.0 |
| 3 lb | 2.0 < weight ≤ 3.0 |
| ... | ... |
| 20 lb | 19.0 < weight ≤ 20.0 |

**Maximum weight: 20 lbs** (Ground Advantage limit)

### Example Rates (Zone 4)

| Weight | Base Rate |
|--------|-----------|
| 0.2 lbs | $3.41 |
| 2.0 lbs | $6.13 |
| 5.0 lbs | $7.45 |
| 20.0 lbs | $11.63 |

---

## Step 5: Apply Surcharges

### 5a. NSL1 - Nonstandard Length Tier 1

| Attribute | Value |
|-----------|-------|
| Condition | longest_side_in > 22" AND ≤ 30" |
| Cost | $3.00 |
| Exclusivity | "length" group (priority 2) |

### 5b. NSL2 - Nonstandard Length Tier 2

| Attribute | Value |
|-----------|-------|
| Condition | longest_side_in > 30" |
| Cost | $3.00 |
| Exclusivity | "length" group (priority 1 - wins over NSL1) |

### 5c. NSV - Nonstandard Volume

| Attribute | Value |
|-----------|-------|
| Condition | cubic_in > 3,456 (2 cubic feet) |
| Cost | $10.00 |
| Exclusivity | None (can stack with NSL) |

### Exclusivity Rules

NSL1 and NSL2 are mutually exclusive (same "length" group):
- If longest side is 35", only NSL2 applies (not both)
- NSL2 has priority 1, NSL1 has priority 2

NSV is independent:
- A 35" × 20" × 10" package triggers both NSL2 ($3) AND NSV ($10)

---

## Step 6: Apply Peak Surcharge

### Peak Periods

| Season | Start | End |
|--------|-------|-----|
| 2025-2026 | Oct 5, 2025 | Jan 18, 2026 |
| 2026-2027 | Oct 5, 2026 | Jan 18, 2027 |

### Peak Rates

| Weight Tier | Zones 1-4 | Zones 5-9 |
|-------------|-----------|-----------|
| 0-3 lbs | $0.30 | $0.35 |
| 4-10 lbs | $0.45 | $0.75 |
| 11-25 lbs | $0.75 | $1.25 |
| 26-70 lbs | $2.25 | $5.50 |

### Logic

```
IF ship_date is within a peak period:
    surcharge_peak = True
    cost_peak = lookup(weight_tier, zone_group)
ELSE:
    surcharge_peak = False
    cost_peak = $0.00
```

### Example

| Ship Date | Weight | Zone | Peak? | Cost |
|-----------|--------|------|-------|------|
| 2025-06-15 | 2 lbs | 4 | No | $0.00 |
| 2025-11-15 | 2 lbs | 4 | Yes | $0.30 |
| 2025-11-15 | 5 lbs | 8 | Yes | $0.75 |
| 2025-11-15 | 15 lbs | 4 | Yes | $0.75 |

---

## Step 7: Calculate Totals

### Subtotal

```
cost_subtotal = cost_base + cost_nsl1 + cost_nsl2 + cost_nsv + cost_peak
```

### Total

```
cost_total = cost_subtotal
```

(No fuel surcharge for USPS)

---

## Complete Example

**Input:**
- Ship date: November 15, 2025
- Origin: Phoenix
- Destination: 90210 (California)
- Dimensions: 25" × 10" × 8"
- Weight: 3.5 lbs

**Step 1 - Dimensions:**
- cubic_in = 25 × 10 × 8 = 2,000
- longest_side_in = 25"
- length_plus_girth = 25 + 2×(10+8) = 61"

**Step 2 - Zone:**
- ZIP prefix "902" from Phoenix → Zone 4

**Step 3 - Billable Weight:**
- cubic_in (2,000) > threshold (1,728) → check DIM
- dim_weight = 2,000 / 200 = 10.0 lbs
- billable_weight = MAX(3.5, 10.0) = 10.0 lbs (uses DIM)

**Step 4 - Base Rate:**
- Zone 4, 9-10 lb bracket → $8.63

**Step 5 - Surcharges:**
- NSL1: longest (25") > 22" AND ≤ 30" → Yes → $3.00
- NSL2: longest (25") > 30" → No → $0.00
- NSV: cubic (2,000) > 3,456 → No → $0.00

**Step 6 - Peak:**
- Nov 15, 2025 is in peak season
- Weight tier: 10 lbs → "4-10 lbs" tier
- Zone group: Zone 4 → "Zones 1-4"
- Peak surcharge: $0.45

**Step 7 - Total:**
```
cost_base     = $8.63
cost_nsl1     = $3.00
cost_nsl2     = $0.00
cost_nsv      = $0.00
cost_peak     = $0.45
─────────────────────
cost_total    = $12.08
```

---

## Output Columns

| Column | Description |
|--------|-------------|
| `cubic_in` | Package volume |
| `longest_side_in` | Longest dimension |
| `second_longest_in` | Second longest dimension |
| `length_plus_girth` | Length + girth calculation |
| `shipping_zone` | Zone with asterisk (e.g., "1*") |
| `rate_zone` | Zone as integer (1-8) |
| `dim_weight_lbs` | Calculated dimensional weight |
| `uses_dim_weight` | True if DIM weight used |
| `billable_weight_lbs` | Weight used for rate lookup |
| `surcharge_nsl1` | NSL1 flag (True/False) |
| `surcharge_nsl2` | NSL2 flag (True/False) |
| `surcharge_nsv` | NSV flag (True/False) |
| `surcharge_peak` | Peak flag (True/False) |
| `cost_base` | Base shipping rate |
| `cost_nsl1` | NSL1 surcharge amount |
| `cost_nsl2` | NSL2 surcharge amount |
| `cost_nsv` | NSV surcharge amount |
| `cost_peak` | Peak surcharge amount |
| `cost_subtotal` | Sum of all costs |
| `cost_total` | Final cost (= subtotal) |
| `calculator_version` | Version stamp for audit |

---

## Reference Files

| File | Purpose |
|------|---------|
| `data/reference/base_rates.csv` | Base rates by zone and weight |
| `data/reference/zones.csv` | ZIP prefix to zone mapping |
| `data/reference/billable_weight.py` | DIM factor and threshold |
| `surcharges/nonstandard_length_22.py` | NSL1 definition |
| `surcharges/nonstandard_length_30.py` | NSL2 definition |
| `surcharges/nonstandard_volume.py` | NSV definition |
| `surcharges/peak.py` | Peak periods and rates |
| `version.py` | Calculator version |
