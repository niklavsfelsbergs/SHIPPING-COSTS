# USPS Ground Advantage - Calculation Logic

Complete documentation of how expected shipping costs are calculated for USPS Ground Advantage.

**Service:** USPS Ground Advantage
**Max Weight:** 20 lbs
**Calculator Version:** 2026.01.21

---

## Executive Summary

USPS Ground Advantage shipping cost is calculated as follows:

1. **Determine the zone** based on the first 3 digits of the destination ZIP code and the origin facility (Phoenix or Columbus). Zones range from 1-9, with higher zones being further away and more expensive.

2. **Calculate billable weight** as the greater of actual weight or dimensional weight. Dimensional weight only applies for packages larger than 1 cubic foot (1,728 cu in), calculated as cubic inches ÷ 200.

3. **Look up the base rate** from the USPS rate card using the zone and billable weight. Rates range from ~$3.41 (light, nearby) to ~$58.80 (heavy, far).

4. **Apply surcharges** for non-standard packages:
   - Packages longer than 30" ($3.00)
   - Packages between 22" and 30" long ($3.00) - only if not already over 30"
   - Packages larger than 2 cubic feet / 3,456 cu in ($10.00)
   - These can stack: a 35" package over 2 cu ft pays both surcharges ($13.00 total)

5. **Apply peak season surcharge** during holiday period (Oct 5 - Jan 18). Ranges from $0.30 (light package, nearby) to $5.50 (heavy package, far zone).

6. **No fuel surcharge** - unlike other carriers, USPS does not charge a fuel surcharge.

**Final cost = Base Rate + Surcharges + Peak Surcharge**

---

## 1. Input Requirements

| Column              | Type      | Description                          | Example      |
|---------------------|-----------|--------------------------------------|--------------|
| `ship_date`         | date      | Ship date (for peak season checks)   | 2025-11-15   |
| `production_site`   | str       | Origin: "Phoenix" or "Columbus"      | "Phoenix"    |
| `shipping_zip_code` | str/int   | 5-digit destination ZIP code         | "90210"      |
| `shipping_region`   | str       | Destination state (fallback)         | "California" |
| `length_in`         | float     | Package length in inches             | 10.0         |
| `width_in`          | float     | Package width in inches              | 8.0          |
| `height_in`         | float     | Package height in inches             | 6.0          |
| `weight_lbs`        | float     | Actual weight in pounds              | 2.0          |

---

## 2. Calculation Pipeline

```
Input DataFrame
      │
      ▼
┌─────────────────────────────┐
│  Stage 1: supplement_shipments()  │
│  ├── Calculate dimensions         │
│  ├── Look up zone                 │
│  └── Calculate billable weight    │
└─────────────────────────────┘
      │
      ▼
┌─────────────────────────────┐
│  Stage 2: calculate()            │
│  ├── Apply surcharges            │
│  ├── Look up base rate           │
│  ├── Apply peak surcharge        │
│  └── Calculate totals            │
└─────────────────────────────┘
      │
      ▼
Output DataFrame with cost columns
```

---

## 3. Dimensional Calculations

All dimensions are **rounded to 1 decimal place** before threshold comparisons to prevent floating-point precision issues.

| Field               | Calculation                                    | Rounding   |
|---------------------|------------------------------------------------|------------|
| `cubic_in`          | length × width × height                        | 0 decimals |
| `longest_side_in`   | max(length, width, height)                     | 1 decimal  |
| `second_longest_in` | middle value when sorted                       | 1 decimal  |
| `length_plus_girth` | longest + 2 × (sum of other two)               | 1 decimal  |

**Example:** Package 10" × 8" × 6"

| Field               | Value |
|---------------------|-------|
| `cubic_in`          | 480   |
| `longest_side_in`   | 10.0  |
| `second_longest_in` | 8.0   |
| `length_plus_girth` | 38.0  |

---

## 4. Zone Lookup

### 4.1 Zone Source

**File:** `carriers/usps/data/reference/zones.csv`

Zones are based on **3-digit ZIP prefix** (first 3 digits) and are **origin-dependent**.

| Column       | Description                    |
|--------------|--------------------------------|
| `zip_prefix` | 3-digit ZIP prefix (e.g. 902)  |
| `phx_zone`   | Zone from Phoenix origin       |
| `cmh_zone`   | Zone from Columbus origin      |

### 4.2 Asterisk Zones

Some zones have asterisks (e.g., "1*", "2*", "3*") indicating local delivery:

- `shipping_zone` - Stores zone WITH asterisk (for reference)
- `rate_zone` - Asterisk stripped, cast to integer (for rate lookup)

### 4.3 Fallback Logic

| Priority | Method                          | Description                        |
|----------|--------------------------------|------------------------------------|
| 1        | Exact 3-digit ZIP match        | Look up zip_prefix in zones.csv    |
| 2        | State-level mode               | Most common zone for that state    |
| 3        | Default zone 5                 | Fallback if no match found         |

**Example:** ZIP 90210 from Phoenix
- 3-digit prefix: "902"
- Look up in zones.csv → phx_zone = 4
- `shipping_zone` = "4", `rate_zone` = 4

---

## 5. Billable Weight

### 5.1 Configuration

| Parameter       | Value                      |
|-----------------|----------------------------|
| DIM Factor      | 200 cubic inches per pound |
| DIM Threshold   | 1,728 cubic inches (1 cu ft) |

### 5.2 Calculation Logic

```
IF cubic_in > 1,728:
    dim_weight_lbs = cubic_in / 200
    uses_dim_weight = (dim_weight_lbs > weight_lbs)
    billable_weight_lbs = MAX(weight_lbs, dim_weight_lbs)
ELSE:
    dim_weight_lbs = cubic_in / 200
    uses_dim_weight = False
    billable_weight_lbs = weight_lbs
```

**Example:** 20" × 20" × 10" package, 5 lbs actual

| Calculation          | Value              |
|----------------------|--------------------|
| `cubic_in`           | 4,000              |
| DIM threshold check  | 4,000 > 1,728 ✓    |
| `dim_weight_lbs`     | 4,000 / 200 = 20.0 |
| `uses_dim_weight`    | True (20 > 5)      |
| `billable_weight_lbs`| 20.0               |

---

## 6. Surcharges

### 6.1 Surcharge Summary

| Surcharge | Condition                     | Cost   | Exclusivity |
|-----------|-------------------------------|--------|-------------|
| NSL2      | longest_side > 30"            | $3.00  | "length" (priority 1) |
| NSL1      | 22" < longest_side ≤ 30"      | $3.00  | "length" (priority 2) |
| NSV       | cubic_in > 3,456              | $10.00 | None (independent) |

### 6.2 NSL2 (Nonstandard Length - Over 30")

| Attribute         | Value                          |
|-------------------|--------------------------------|
| **Condition**     | `longest_side_in > 30"`        |
| **Cost**          | $3.00                          |
| **Exclusivity**   | "length" group, priority 1     |

- At 30.0": Does NOT trigger (condition is `>`, not `>=`)
- At 30.1": Triggers

### 6.3 NSL1 (Nonstandard Length - 22" to 30")

| Attribute         | Value                          |
|-------------------|--------------------------------|
| **Condition**     | `22" < longest_side_in ≤ 30"`  |
| **Cost**          | $3.00                          |
| **Exclusivity**   | "length" group, priority 2     |

- At 22.0": Does NOT trigger (condition is `>`, not `>=`)
- At 22.1" to 30.0": Triggers
- At 30.1": NSL2 triggers instead (higher priority)

### 6.4 NSV (Nonstandard Volume)

| Attribute         | Value                          |
|-------------------|--------------------------------|
| **Condition**     | `cubic_in > 3,456` (> 2 cu ft) |
| **Cost**          | $10.00                         |
| **Exclusivity**   | None (can stack with NSL1/NSL2)|

- At 3,456 cu in: Does NOT trigger (condition is `>`, not `>=`)
- At 3,457 cu in: Triggers

### 6.5 Exclusivity Logic

NSL1 and NSL2 are mutually exclusive (same "length" group). Only the **highest priority (lowest number)** that matches is applied:

1. Check NSL2 first (priority 1): if longest > 30", apply NSL2, skip NSL1
2. Check NSL1 only if NSL2 didn't match (priority 2)
3. NSV is independent - always checked regardless

**Example:** Package 35" × 11" × 10"

| Surcharge | Check                    | Result       | Cost   |
|-----------|--------------------------|--------------|--------|
| NSL2      | 35.0 > 30?               | True         | $3.00  |
| NSL1      | Skipped (NSL2 matched)   | False        | $0.00  |
| NSV       | 3,850 > 3,456?           | True         | $10.00 |
| **Total** |                          |              | **$13.00** |

---

## 7. Base Rate Lookup

### 7.1 Rate Source

**File:** `carriers/usps/data/reference/base_rates.csv`

### 7.2 Rate Structure

| Dimension      | Values                              |
|----------------|-------------------------------------|
| Weight brackets| 24 brackets from 0-0.25 lbs to 19-20 lbs |
| Zones          | 1-9                                 |
| Max weight     | 20 lbs (>20 lbs = $58.80 penalty)   |

### 7.3 Weight Brackets

| Lower | Upper | Description |
|-------|-------|-------------|
| 0     | 0.25  | 4 oz        |
| 0.25  | 0.5   | 8 oz        |
| 0.5   | 0.75  | 12 oz       |
| 0.75  | 1     | 1 lb        |
| 1     | 2     | 1-2 lbs     |
| 2     | 3     | 2-3 lbs     |
| ...   | ...   | ...         |
| 19    | 20    | 19-20 lbs   |
| 20    | 100   | >20 lbs (penalty) |

### 7.4 Lookup Logic

```
Find row where:
    weight_lbs_lower < billable_weight_lbs ≤ weight_lbs_upper

Return rate from zone_{rate_zone} column
```

**Example:** 2 lbs to Zone 4
- Bracket: 1 < 2.0 ≤ 2 (1-2 lb bracket)
- `cost_base` = $6.13

---

## 8. Peak Season Surcharge

### 8.1 Peak Periods

| Period         | Start Date   | End Date     |
|----------------|--------------|--------------|
| 2025-2026      | Oct 5, 2025  | Jan 18, 2026 |
| 2026-2027      | Oct 5, 2026  | Jan 18, 2027 |

Dates are **inclusive** on both ends.

### 8.2 Weight Tiers

| Tier | Weight Range      |
|------|-------------------|
| 1    | 0 < weight ≤ 3    |
| 2    | 3 < weight ≤ 10   |
| 3    | 10 < weight ≤ 25  |
| 4    | 25 < weight ≤ 70  |

### 8.3 Zone Groups

| Group | Zones |
|-------|-------|
| 1     | 1-4   |
| 2     | 5-9   |

### 8.4 Peak Rate Table

| Weight Tier | Zones 1-4 | Zones 5-9 |
|-------------|-----------|-----------|
| 0-3 lbs     | $0.30     | $0.35     |
| 4-10 lbs    | $0.45     | $0.75     |
| 11-25 lbs   | $0.75     | $1.25     |
| 26-70 lbs   | $2.25     | $5.50     |

### 8.5 Peak Calculation

```
IF ship_date in peak period:
    surcharge_peak = True
    Determine weight_tier from billable_weight_lbs
    Determine zone_group from rate_zone
    cost_peak = PEAK_RATES[(weight_tier, zone_group)]
ELSE:
    surcharge_peak = False
    cost_peak = $0.00
```

**Example:** Nov 15, 2025 shipment, 5 lbs, Zone 8

| Step              | Value                        |
|-------------------|------------------------------|
| In peak period?   | Yes (Oct 5 - Jan 18)         |
| Weight tier       | Tier 2 (3 < 5 ≤ 10)          |
| Zone group        | Group 2 (zone 8 > 4)         |
| `cost_peak`       | $0.75                        |

---

## 9. Total Cost Calculation

### 9.1 Formula

```
cost_subtotal = cost_base + cost_nsl1 + cost_nsl2 + cost_nsv + cost_peak

cost_total = cost_subtotal
```

**Note:** USPS has **no fuel surcharge**. Total always equals subtotal.

### 9.2 Complete Example

**Package:** 35" × 11" × 10", 19 lbs, Phoenix to ZIP 90210, Nov 15, 2025

**Stage 1: Supplement**

| Calculation          | Value              |
|----------------------|--------------------|
| `cubic_in`           | 3,850              |
| `longest_side_in`    | 35.0               |
| `rate_zone`          | 4 (Phoenix → 902)  |
| `billable_weight_lbs`| 19.0               |

**Stage 2: Surcharges**

| Surcharge       | Condition              | Result | Cost   |
|-----------------|------------------------|--------|--------|
| NSL2            | 35 > 30                | True   | $3.00  |
| NSL1            | Skipped (NSL2 matched) | False  | $0.00  |
| NSV             | 3,850 > 3,456          | True   | $10.00 |
| Peak            | Nov 15 in peak period  | True   | $0.75  |

**Stage 3: Base Rate**

| Lookup          | Value                  |
|-----------------|------------------------|
| Weight bracket  | 19-20 lbs              |
| Zone            | 4                      |
| `cost_base`     | $15.38                 |

**Stage 4: Totals**

| Component       | Amount |
|-----------------|--------|
| `cost_base`     | $15.38 |
| `cost_nsl2`     | $3.00  |
| `cost_nsv`      | $10.00 |
| `cost_peak`     | $0.75  |
| **cost_total**  | **$29.13** |

---

## 10. Output Columns

### 10.1 Dimensional

| Column              | Type  | Description                     |
|---------------------|-------|---------------------------------|
| `cubic_in`          | int   | Package volume in cubic inches  |
| `longest_side_in`   | float | Longest dimension (1 decimal)   |
| `second_longest_in` | float | Middle dimension (1 decimal)    |
| `length_plus_girth` | float | Longest + 2×(sum of others)     |

### 10.2 Zone

| Column          | Type | Description                      |
|-----------------|------|----------------------------------|
| `shipping_zone` | str  | Zone with asterisk preserved     |
| `rate_zone`     | int  | Zone without asterisk            |

### 10.3 Weight

| Column              | Type  | Description                     |
|---------------------|-------|---------------------------------|
| `dim_weight_lbs`    | float | Dimensional weight              |
| `uses_dim_weight`   | bool  | True if DIM weight used         |
| `billable_weight_lbs`| float| Final billable weight           |

### 10.4 Surcharge Flags

| Column          | Type | Description                      |
|-----------------|------|----------------------------------|
| `surcharge_nsl1`| bool | True if NSL1 applies             |
| `surcharge_nsl2`| bool | True if NSL2 applies             |
| `surcharge_nsv` | bool | True if NSV applies              |
| `surcharge_peak`| bool | True if in peak season           |

### 10.5 Costs

| Column          | Type  | Description                     |
|-----------------|-------|---------------------------------|
| `cost_base`     | float | Base shipping rate              |
| `cost_nsl1`     | float | NSL1 surcharge ($0 or $3.00)    |
| `cost_nsl2`     | float | NSL2 surcharge ($0 or $3.00)    |
| `cost_nsv`      | float | NSV surcharge ($0 or $10.00)    |
| `cost_peak`     | float | Peak season surcharge           |
| `cost_subtotal` | float | Sum of all costs                |
| `cost_total`    | float | Same as subtotal (no fuel)      |

### 10.6 Metadata

| Column              | Type | Description           |
|---------------------|------|-----------------------|
| `calculator_version`| str  | Version stamp         |

---

## 11. Data Sources

| File                                        | Purpose                    |
|---------------------------------------------|----------------------------|
| `carriers/usps/data/reference/zones.csv`    | 3-digit ZIP to zone mapping|
| `carriers/usps/data/reference/base_rates.csv`| Weight × zone rate card   |
| `carriers/usps/data/reference/billable_weight.py` | DIM factor config    |
| `carriers/usps/surcharges/peak.py`          | Peak periods & rates       |
| `carriers/usps/surcharges/nsl1.py`          | NSL1 surcharge class       |
| `carriers/usps/surcharges/nsl2.py`          | NSL2 surcharge class       |
| `carriers/usps/surcharges/nsv.py`           | NSV surcharge class        |

---

## 12. Key Constraints

| Constraint              | Value / Rule                           |
|-------------------------|----------------------------------------|
| Max weight              | 20 lbs                                 |
| DIM factor              | 200 (not standard 166)                 |
| DIM threshold           | 1,728 cubic inches                     |
| Zone lookup             | 3-digit ZIP prefix (not 5-digit)       |
| Surcharge boundaries    | Use `>` not `>=` for all thresholds    |
| Fuel surcharge          | None                                   |

---

*Last updated: February 2026*
