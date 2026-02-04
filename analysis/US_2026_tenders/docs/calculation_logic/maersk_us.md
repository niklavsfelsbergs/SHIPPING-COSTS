# Maersk US - Calculation Logic

Complete documentation of how expected shipping costs are calculated for Maersk US.

**Service:** Maersk US Ground
**Max Weight:** 70 lbs
**Calculator Version:** 2026.02.03
**Status:** Early Development

---

## Executive Summary

Maersk US shipping cost is calculated as follows:

1. **Determine the zone** based on the first 3 digits of the destination ZIP code. Zones range from 1-9, with higher zones being further away and more expensive. Maersk US operates from a single origin (Columbus).

2. **Calculate billable weight** as the greater of actual weight or dimensional weight. Dimensional weight is **always** calculated (no threshold), using cubic inches / 166.

3. **Look up the base rate** from the Maersk US rate card using the zone and billable weight. Rates range from ~$3.11 (light, Zone 1) to ~$175.85 (heavy, Zone 9). Note: There is a significant rate jump at 30 lbs across all zones.

4. **Apply surcharges** for non-standard packages:
   - Packages longer than 30" ($4.00)
   - Packages between 21" and 30" long ($4.00) - only if not already over 30"
   - Packages larger than 2 cubic feet / 3,456 cu in ($18.00)
   - Pickup fee of $0.04 per billable pound (always applies)
   - NSL1 and NSD can stack: a 22" package over 2 cu ft pays both ($22.00 total)
   - NSL2 and NSD can stack: a 35" package over 2 cu ft pays both ($22.00 total)

5. **No fuel surcharge** - Maersk US does not charge a separate fuel surcharge.

6. **No peak season surcharge** - Not implemented (TODO).

**Final cost = Base Rate + Surcharges + Pickup Fee**

---

## 1. Input Requirements

| Column              | Type      | Description                          | Example      |
|---------------------|-----------|--------------------------------------|--------------|
| `ship_date`         | date      | Ship date (currently unused)         | 2025-11-15   |
| `production_site`   | str       | Origin: Columbus only                | "Columbus"   |
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
      |
      v
+-----------------------------+
|  Stage 1: supplement_shipments()  |
|  +-- Calculate dimensions         |
|  +-- Look up zone                 |
|  +-- Calculate billable weight    |
+-----------------------------+
      |
      v
+-----------------------------+
|  Stage 2: calculate()            |
|  +-- Apply surcharges            |
|  +-- Look up base rate           |
|  +-- Calculate totals            |
+-----------------------------+
      |
      v
Output DataFrame with cost columns
```

---

## 3. Dimensional Calculations

All dimensions are **rounded to 1 decimal place** before threshold comparisons to prevent floating-point precision issues.

| Field               | Calculation                                    | Rounding   |
|---------------------|------------------------------------------------|------------|
| `cubic_in`          | length x width x height                        | 0 decimals |
| `longest_side_in`   | max(length, width, height)                     | 1 decimal  |
| `second_longest_in` | middle value when sorted                       | 1 decimal  |

**Example:** Package 10" x 8" x 6"

| Field               | Value |
|---------------------|-------|
| `cubic_in`          | 480   |
| `longest_side_in`   | 10.0  |
| `second_longest_in` | 8.0   |

---

## 4. Zone Lookup

### 4.1 Zone Source

**File:** `carriers/maersk_us/data/reference/zones.csv`

Zones are based on **3-digit ZIP prefix** (first 3 digits). Maersk US operates from a **single origin (Columbus)**, so there is no origin-dependent zone logic.

| Column       | Description                    |
|--------------|--------------------------------|
| `zip_prefix` | 3-digit ZIP prefix (e.g. 902)  |
| `zone`       | Zone (1-9)                     |

### 4.2 No Asterisk Zones

Unlike USPS, Maersk US does not use asterisk zones. All zones are simple integers 1-9.

### 4.3 Fallback Logic

| Priority | Method                          | Description                        |
|----------|--------------------------------|------------------------------------|
| 1        | Exact 3-digit ZIP match        | Look up zip_prefix in zones.csv    |
| 2        | Mode zone                      | Most common zone across all entries|
| 3        | Default zone 5                 | Fallback if no match found         |

**Example:** ZIP 90210
- 3-digit prefix: "902"
- Look up in zones.csv -> zone = 8
- `shipping_zone` = 8

---

## 5. Billable Weight

### 5.1 Configuration

| Parameter       | Value                      |
|-----------------|----------------------------|
| DIM Factor      | 166 cubic inches per pound |
| DIM Threshold   | 0 (always compare)         |

### 5.2 Calculation Logic

```
dim_weight_lbs = cubic_in / 166
uses_dim_weight = (dim_weight_lbs > weight_lbs)
billable_weight_lbs = MAX(weight_lbs, dim_weight_lbs)
```

**Key difference from other carriers:** Maersk US has **no DIM threshold**. Dimensional weight is always compared against actual weight, regardless of package size.

**Example:** 20" x 20" x 10" package, 5 lbs actual

| Calculation          | Value              |
|----------------------|--------------------|
| `cubic_in`           | 4,000              |
| `dim_weight_lbs`     | 4,000 / 166 = 24.1 |
| `uses_dim_weight`    | True (24.1 > 5)    |
| `billable_weight_lbs`| 24.1               |

---

## 6. Surcharges

### 6.1 Surcharge Summary

| Surcharge | Condition                     | Cost        | Exclusivity |
|-----------|-------------------------------|-------------|-------------|
| NSL2      | longest_side > 30"            | $4.00       | "length" (priority 1) |
| NSL1      | longest_side > 21"            | $4.00       | "length" (priority 2) |
| NSD       | cubic_in > 3,456              | $18.00      | None (independent) |
| PICKUP    | Always applies                | $0.04/lb    | None (independent) |

### 6.2 NSL2 (Nonstandard Length - Over 30")

| Attribute         | Value                          |
|-------------------|--------------------------------|
| **Condition**     | `longest_side_in > 30"`        |
| **Cost**          | $4.00                          |
| **Discount**      | 0%                             |
| **Exclusivity**   | "length" group, priority 1     |

- At 30.0": Does NOT trigger (condition is `>`, not `>=`)
- At 30.1": Triggers

### 6.3 NSL1 (Nonstandard Length - Over 21")

| Attribute         | Value                          |
|-------------------|--------------------------------|
| **Condition**     | `longest_side_in > 21"`        |
| **Cost**          | $4.00                          |
| **Discount**      | 0%                             |
| **Exclusivity**   | "length" group, priority 2     |

- At 21.0": Does NOT trigger (condition is `>`, not `>=`)
- At 21.1": Triggers
- At 30.1": NSL2 triggers instead (higher priority)

**Note:** Unlike USPS, which has an upper bound on NSL1 (22-30"), Maersk US NSL1 triggers for **any** package over 21". The exclusivity logic ensures only NSL2 applies when longest side exceeds 30".

### 6.4 NSD (Nonstandard Dimensions)

| Attribute         | Value                          |
|-------------------|--------------------------------|
| **Condition**     | `cubic_in > 3,456` (> 2 cu ft) |
| **Cost**          | $18.00                         |
| **Discount**      | 0%                             |
| **Exclusivity**   | None (can stack with NSL1/NSL2)|

- At 3,456 cu in: Does NOT trigger (condition is `>`, not `>=`)
- At 3,457 cu in: Triggers

### 6.5 PICKUP (Pickup Fee)

| Attribute         | Value                          |
|-------------------|--------------------------------|
| **Condition**     | Always applies                 |
| **Cost**          | $0.04 per billable pound       |
| **Discount**      | 0%                             |
| **Exclusivity**   | None (always applied)          |

The pickup fee is calculated as:
```
cost_pickup = CEIL(billable_weight_lbs) * $0.04
```

**Example:** 5.3 lbs billable weight -> CEIL(5.3) = 6 -> $0.24

### 6.6 Exclusivity Logic

NSL1 and NSL2 are mutually exclusive (same "length" group). Only the **highest priority (lowest number)** that matches is applied:

1. Check NSL2 first (priority 1): if longest > 30", apply NSL2, skip NSL1
2. Check NSL1 only if NSL2 didn't match (priority 2)
3. NSD is independent - always checked regardless
4. PICKUP is independent - always applies

**Example:** Package 35" x 11" x 10"

| Surcharge | Check                    | Result       | Cost   |
|-----------|--------------------------|--------------|--------|
| NSL2      | 35.0 > 30?               | True         | $4.00  |
| NSL1      | Skipped (NSL2 matched)   | False        | $0.00  |
| NSD       | 3,850 > 3,456?           | True         | $18.00 |
| PICKUP    | Always applies           | True         | $2.80 (70 lbs ceil) |
| **Total** |                          |              | **$24.80** |

---

## 7. Base Rate Lookup

### 7.1 Rate Source

**File:** `carriers/maersk_us/data/reference/base_rates.csv`

### 7.2 Rate Structure

| Dimension      | Values                              |
|----------------|-------------------------------------|
| Weight brackets| 75 brackets from 0-0.25 lbs to 69-70 lbs |
| Zones          | 1-9                                 |
| Max weight     | 70 lbs                              |

### 7.3 Weight Brackets

| Lower  | Upper   | Description      |
|--------|---------|------------------|
| 0      | 0.25    | 4 oz             |
| 0.25   | 0.5     | 8 oz             |
| 0.5    | 0.75    | 12 oz            |
| 0.75   | 0.9999  | < 1 lb           |
| 0.9999 | 1.0     | Exactly 1 lb     |
| 1.0    | 2.0     | 1-2 lbs          |
| ...    | ...     | ...              |
| 29.0   | 30.0    | 29-30 lbs        |
| 30.0   | 31.0    | 30-31 lbs **     |
| ...    | ...     | ...              |
| 69.0   | 70.0    | 69-70 lbs        |

** Note: There is a significant rate increase at 30 lbs across all zones.

### 7.4 Rate Jump at 30 lbs

The rate structure shows a dramatic increase at the 30 lb threshold:

| Zone | 29-30 lbs Rate | 30-31 lbs Rate | Increase  |
|------|----------------|----------------|-----------|
| 1    | $7.61          | $22.40         | +$14.79   |
| 2    | $7.61          | $24.67         | +$17.06   |
| 3    | $8.99          | $28.10         | +$19.11   |
| 4    | $9.84          | $34.54         | +$24.70   |
| 5    | $11.81         | $45.18         | +$33.37   |
| 6    | $14.75         | $54.63         | +$39.88   |
| 7    | $17.17         | $64.17         | +$47.00   |
| 8    | $20.36         | $73.60         | +$53.24   |
| 9    | $88.79         | $91.52         | +$2.73    |

### 7.5 Sample Rates by Zone

| Weight     | Zone 1 | Zone 5  | Zone 8  | Zone 9  |
|------------|--------|---------|---------|---------|
| 0-0.25 lbs | $3.11  | $3.34   | $3.71   | $5.09   |
| 1-2 lbs    | $4.22  | $5.19   | $5.72   | $12.08  |
| 5-6 lbs    | $4.70  | $6.16   | $7.14   | $18.13  |
| 10-11 lbs  | $5.58  | $6.89   | $9.39   | $24.70  |
| 20-21 lbs  | $6.58  | $9.02   | $14.65  | $39.53  |
| 30-31 lbs  | $22.40 | $45.18  | $73.60  | $91.52  |
| 50-51 lbs  | $32.19 | $67.25  | $112.58 | $140.29 |
| 69-70 lbs  | $39.57 | $82.01  | $140.84 | $175.85 |

### 7.6 Lookup Logic

```
Find row where:
    weight_lbs_lower < billable_weight_lbs <= weight_lbs_upper
    AND zone = shipping_zone

Return rate from rate column
```

**Example:** 2 lbs to Zone 4
- Bracket: 1.0 < 2.0 <= 2.0 (1-2 lb bracket)
- Zone: 4
- `cost_base` = $5.08

---

## 8. Fuel Surcharge

**Maersk US does not have a fuel surcharge.** The base rate includes all fuel costs.

---

## 9. Peak Season Surcharge

**TODO:** Peak season surcharge is not yet implemented for Maersk US.

---

## 10. Total Cost Calculation

### 10.1 Formula

```
cost_subtotal = cost_base + cost_nsl1 + cost_nsl2 + cost_nsd + cost_pickup

cost_total = cost_subtotal
```

**Note:** Maersk US has **no fuel surcharge**. Total always equals subtotal.

### 10.2 Complete Example

**Package:** 35" x 11" x 10", 19 lbs, Columbus to ZIP 90210

**Stage 1: Supplement**

| Calculation          | Value              |
|----------------------|--------------------|
| `cubic_in`           | 3,850              |
| `longest_side_in`    | 35.0               |
| `shipping_zone`      | 8 (902 prefix)     |
| `dim_weight_lbs`     | 3,850 / 166 = 23.2 |
| `uses_dim_weight`    | True (23.2 > 19)   |
| `billable_weight_lbs`| 23.2               |

**Stage 2: Surcharges**

| Surcharge       | Condition              | Result | Cost   |
|-----------------|------------------------|--------|--------|
| NSL2            | 35 > 30                | True   | $4.00  |
| NSL1            | Skipped (NSL2 matched) | False  | $0.00  |
| NSD             | 3,850 > 3,456          | True   | $18.00 |
| PICKUP          | Always applies         | True   | $0.96 (24 * $0.04) |

**Stage 3: Base Rate**

| Lookup          | Value                  |
|-----------------|------------------------|
| Weight bracket  | 23-24 lbs              |
| Zone            | 8                      |
| `cost_base`     | $16.82                 |

**Stage 4: Totals**

| Component       | Amount |
|-----------------|--------|
| `cost_base`     | $16.82 |
| `cost_nsl2`     | $4.00  |
| `cost_nsd`      | $18.00 |
| `cost_pickup`   | $0.96  |
| **cost_total**  | **$39.78** |

---

## 11. Output Columns

### 11.1 Dimensional

| Column              | Type  | Description                     |
|---------------------|-------|---------------------------------|
| `cubic_in`          | int   | Package volume in cubic inches  |
| `longest_side_in`   | float | Longest dimension (1 decimal)   |
| `second_longest_in` | float | Middle dimension (1 decimal)    |

### 11.2 Zone

| Column          | Type | Description                      |
|-----------------|------|----------------------------------|
| `shipping_zone` | int  | Zone (1-9)                       |

### 11.3 Weight

| Column              | Type  | Description                     |
|---------------------|-------|---------------------------------|
| `dim_weight_lbs`    | float | Dimensional weight              |
| `uses_dim_weight`   | bool  | True if DIM weight used         |
| `billable_weight_lbs`| float| Final billable weight           |

### 11.4 Surcharge Flags

| Column          | Type | Description                      |
|-----------------|------|----------------------------------|
| `surcharge_nsl1`| bool | True if NSL1 applies             |
| `surcharge_nsl2`| bool | True if NSL2 applies             |
| `surcharge_nsd` | bool | True if NSD applies              |
| `surcharge_pickup`| bool | Always True                    |

### 11.5 Costs

| Column          | Type  | Description                     |
|-----------------|-------|---------------------------------|
| `cost_base`     | float | Base shipping rate              |
| `cost_nsl1`     | float | NSL1 surcharge ($0 or $4.00)    |
| `cost_nsl2`     | float | NSL2 surcharge ($0 or $4.00)    |
| `cost_nsd`      | float | NSD surcharge ($0 or $18.00)    |
| `cost_pickup`   | float | Pickup fee ($0.04/lb)           |
| `cost_subtotal` | float | Sum of all costs                |
| `cost_total`    | float | Same as subtotal (no fuel)      |

### 11.6 Metadata

| Column              | Type | Description           |
|---------------------|------|-----------------------|
| `calculator_version`| str  | Version stamp         |

---

## 12. Data Sources

| File                                              | Purpose                    |
|---------------------------------------------------|----------------------------|
| `carriers/maersk_us/data/reference/zones.csv`     | 3-digit ZIP to zone mapping|
| `carriers/maersk_us/data/reference/base_rates.csv`| Weight x zone rate card    |
| `carriers/maersk_us/data/reference/billable_weight.py` | DIM factor config     |
| `carriers/maersk_us/surcharges/nonstandard_length_1.py` | NSL1 surcharge class |
| `carriers/maersk_us/surcharges/nonstandard_length_2.py` | NSL2 surcharge class |
| `carriers/maersk_us/surcharges/nonstandard_dimensions.py` | NSD surcharge class |
| `carriers/maersk_us/surcharges/pickup_fee.py`     | Pickup fee surcharge class |

---

## 13. Key Constraints

| Constraint              | Value / Rule                           |
|-------------------------|----------------------------------------|
| Max weight              | 70 lbs                                 |
| DIM factor              | 166 (standard industry factor)         |
| DIM threshold           | 0 (always compare actual vs DIM)       |
| Zone lookup             | 3-digit ZIP prefix (single origin)     |
| Surcharge boundaries    | Use `>` not `>=` for all thresholds    |
| Fuel surcharge          | None                                   |
| Peak surcharge          | Not implemented (TODO)                 |
| Origin                  | Columbus only                          |

---

## 14. Development Status

Maersk US is in **early development**. The following features are implemented:

**Implemented:**
- [x] Zone lookup from 3-digit ZIP prefix
- [x] Dimensional weight calculation (DIM factor 166, no threshold)
- [x] Base rate lookup by zone and weight
- [x] NSL1 surcharge (longest side > 21")
- [x] NSL2 surcharge (longest side > 30")
- [x] NSD surcharge (volume > 3,456 cu in)
- [x] Pickup fee ($0.04/lb)
- [x] Exclusivity group handling for NSL1/NSL2
- [x] Version stamping

**Not Yet Implemented (TODO):**
- [ ] Peak/demand season surcharges
- [ ] Residential delivery surcharge
- [ ] Delivery area surcharges (DAS/EDAS)
- [ ] Additional handling surcharges (weight/dimension-based)
- [ ] Multiple origin support (currently Columbus only)
- [ ] Actuals upload and comparison
- [ ] Streamlit dashboard

---

*Last updated: February 2026*
