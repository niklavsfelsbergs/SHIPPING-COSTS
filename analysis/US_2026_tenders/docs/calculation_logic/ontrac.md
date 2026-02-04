# OnTrac Ground - Calculation Logic

Complete documentation of how expected shipping costs are calculated for OnTrac Ground.

**Service:** OnTrac Ground
**Max Weight:** 150 lbs (packages exceeding limits incur OML penalty)
**Calculator Version:** 2026.01.29

---

## Executive Summary

OnTrac Ground shipping cost is calculated as follows:

1. **Determine the zone** based on the 5-digit destination ZIP code and the origin facility (Phoenix or Columbus). Zones range from 2-8, with higher zones being further away and more expensive.

2. **Calculate billable weight** as the greater of actual weight or dimensional weight. Dimensional weight only applies for packages larger than 1 cubic foot (1,728 cu in), calculated as cubic inches / 250.

3. **Apply dimensional surcharges** (mutually exclusive - highest priority wins):
   - Over Maximum Limits for oversized packages ($1,875.00, no discount)
   - Large Package for packages exceeding 72" or 17,280 cu in ($114.00 after 60% discount)
   - Additional Handling for packages exceeding 48", 30" second longest, 50 lbs, or 8,640 cu in ($10.80 after 70% discount)

4. **Apply delivery area surcharges** (mutually exclusive - highest priority wins):
   - Extended Delivery Area for remote ZIPs ($3.52 after 60% discount)
   - Delivery Area for standard DAS ZIPs ($2.64 after 60% discount)

5. **Apply residential surcharge** as an allocated cost across all shipments. Since we cannot predict which addresses are residential, the cost is spread evenly based on 95% historical residential rate ($0.627/shipment after 90% discount).

6. **Apply demand surcharges** during peak season (Sept 27 - Jan 16):
   - DEM_AHS, DEM_LPS, DEM_OML apply when the base surcharge triggers during the period
   - DEM_RES (Oct 25 - Jan 16) applies to all shipments during the period

7. **Look up base rate** from the rate card using zone and billable weight. Rates range from ~$4.18 (light, nearby) to ~$59.12 (heavy, far).

8. **Apply fuel surcharge** as a percentage of the subtotal. Current rate: 18.75% list with 35% discount = 12.1875% effective.

**Final cost = (Base Rate + Surcharges) * (1 + Fuel Rate)**

---

## 1. Input Requirements

| Column              | Type      | Description                          | Example      |
|---------------------|-----------|--------------------------------------|--------------|
| `ship_date`         | date      | Ship date (for demand period checks) | 2025-11-15   |
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
│  ├── Look up zone (+ DAS zone)    │
│  └── Calculate billable weight    │
└─────────────────────────────┘
      │
      ▼
┌─────────────────────────────┐
│  Stage 2: calculate()            │
│  ├── Apply BASE surcharges       │
│  ├── Apply DEPENDENT surcharges  │
│  ├── Apply min billable weights  │
│  ├── Look up base rate           │
│  ├── Calculate subtotal          │
│  ├── Apply fuel surcharge        │
│  └── Calculate total             │
└─────────────────────────────┘
      │
      ▼
Output DataFrame with cost columns
```

---

## 3. Dimensional Calculations

All dimensions are **rounded to 1 decimal place** before threshold comparisons to prevent floating-point precision issues (e.g., 762mm = 30.0000001980" incorrectly triggering >30" threshold).

| Field               | Calculation                                    | Rounding   |
|---------------------|------------------------------------------------|------------|
| `cubic_in`          | length x width x height                        | 0 decimals |
| `longest_side_in`   | max(length, width, height)                     | 1 decimal  |
| `second_longest_in` | middle value when sorted                       | 1 decimal  |
| `length_plus_girth` | longest + 2 x (sum of other two)               | 1 decimal  |

**Example:** Package 10" x 8" x 6"

| Field               | Value |
|---------------------|-------|
| `cubic_in`          | 480   |
| `longest_side_in`   | 10.0  |
| `second_longest_in` | 8.0   |
| `length_plus_girth` | 38.0  |

---

## 4. Zone Lookup

### 4.1 Zone Source

**File:** `carriers/ontrac/data/reference/zones.csv`

Zones are based on **5-digit ZIP code** (not 3-digit like USPS) and are **origin-dependent**.

| Column          | Description                    |
|-----------------|--------------------------------|
| `zip_code`      | 5-digit ZIP code               |
| `shipping_state`| State abbreviation             |
| `phx_zone`      | Zone from Phoenix origin (2-8) |
| `cmh_zone`      | Zone from Columbus origin (2-8)|
| `das`           | DAS zone: "NO", "DAS", or "EDAS"|

### 4.2 Zone Selection

Zones are selected based on production site:
- Phoenix origin → `phx_zone`
- Columbus origin → `cmh_zone`

### 4.3 Fallback Logic

| Priority | Method                          | Description                        |
|----------|--------------------------------|------------------------------------|
| 1        | Exact 5-digit ZIP match        | Look up zip_code in zones.csv      |
| 2        | State-level mode               | Most common zone for that state    |
| 3        | Default zone 5                 | Fallback if no match found         |

**Example:** ZIP 90210 from Phoenix
- 5-digit ZIP: "90210"
- Look up in zones.csv → phx_zone = 4
- DAS zone = "NO" (standard delivery area)
- `shipping_zone` = 4

### 4.4 DAS Zone Lookup

The same zones.csv file also determines DAS (Delivery Area Surcharge) status:
- `das` = "NO" → No delivery area surcharge
- `das` = "DAS" → Standard DAS applies
- `das` = "EDAS" → Extended DAS applies (higher surcharge)

---

## 5. Billable Weight

### 5.1 Configuration

| Parameter       | Value                      |
|-----------------|----------------------------|
| DIM Factor      | 250 cubic inches per pound |
| DIM Threshold   | 1,728 cubic inches (1 cu ft) |
| Threshold Field | `cubic_in`                 |
| Factor Field    | `cubic_in`                 |

**Note:** OnTrac's negotiated DIM factor of 250 is much higher than the standard 139, resulting in lower dimensional weights.

### 5.2 Calculation Logic

```
IF cubic_in > 1,728:
    dim_weight_lbs = cubic_in / 250
    uses_dim_weight = (dim_weight_lbs > weight_lbs)
    billable_weight_lbs = MAX(weight_lbs, dim_weight_lbs)
ELSE:
    dim_weight_lbs = cubic_in / 250
    uses_dim_weight = False
    billable_weight_lbs = weight_lbs
```

### 5.3 Minimum Billable Weights

Certain surcharges enforce minimum billable weights:

| Surcharge | Min Billable Weight |
|-----------|---------------------|
| OML       | 150 lbs             |
| LPS       | 90 lbs              |
| AHS       | 30 lbs              |

These are applied AFTER surcharge evaluation, ensuring packages pay the higher base rate.

**Example:** 20" x 20" x 10" package, 5 lbs actual

| Calculation          | Value              |
|----------------------|--------------------|
| `cubic_in`           | 4,000              |
| DIM threshold check  | 4,000 > 1,728 ✓    |
| `dim_weight_lbs`     | 4,000 / 250 = 16.0 |
| `uses_dim_weight`    | True (16 > 5)      |
| `billable_weight_lbs`| 16.0               |

---

## 6. Surcharges

### 6.1 Surcharge Summary

| Surcharge | Type         | Condition                          | List Price | Discount | Net Cost   |
|-----------|--------------|-----------------------------------|------------|----------|------------|
| OML       | Dimensional  | weight > 150 OR longest > 108" OR L+G > 165" | $1,875.00 | 0% | $1,875.00 |
| LPS       | Dimensional  | longest > 72" OR cubic > 17,280   | $285.00    | 60%      | $114.00    |
| AHS       | Dimensional  | weight > 50 OR longest > 48" OR 2nd > 30" OR cubic > 8,640 | $36.00 | 70% | $10.80 |
| EDAS      | Delivery     | das_zone = "EDAS"                 | $8.80      | 60%      | $3.52      |
| DAS       | Delivery     | das_zone = "DAS"                  | $6.60      | 60%      | $2.64      |
| RES       | Allocated    | All shipments (95% rate)          | $6.60      | 90%      | $0.627     |
| DEM_AHS   | Demand       | AHS + demand period               | $11.00     | 0%       | $11.00     |
| DEM_LPS   | Demand       | LPS + demand period               | $105.00    | 50%      | $52.50     |
| DEM_OML   | Demand       | OML + demand period               | $550.00    | 50%      | $275.00    |
| DEM_RES   | Demand+Alloc | RES + demand period (95% rate)    | $1.00      | 50%      | $0.475     |

### 6.2 Exclusivity Groups

Surcharges within the same exclusivity group are mutually exclusive. Only the **highest priority (lowest number)** that matches is applied.

**Dimensional Group:**

| Priority | Surcharge | Triggers When |
|----------|-----------|---------------|
| 1        | OML       | Exceeds maximum limits |
| 2        | LPS       | Exceeds large package thresholds |
| 3        | AHS       | Exceeds additional handling thresholds |

**Delivery Group:**

| Priority | Surcharge | Triggers When |
|----------|-----------|---------------|
| 1        | EDAS      | Extended delivery area ZIP |
| 2        | DAS       | Delivery area ZIP |

### 6.3 OML (Over Maximum Limits)

| Attribute         | Value                                          |
|-------------------|------------------------------------------------|
| **Condition**     | `weight_lbs > 150` OR `longest_side_in > 108"` OR `length_plus_girth > 165"` |
| **List Price**    | $1,875.00                                      |
| **Discount**      | 0% (penalty surcharge)                         |
| **Net Cost**      | $1,875.00                                      |
| **Exclusivity**   | "dimensional" group, priority 1                |
| **Min Weight**    | 150 lbs                                        |

- At 150 lbs: Does NOT trigger (condition is `>`, not `>=`)
- At 150.1 lbs: Triggers

### 6.4 LPS (Large Package Surcharge)

| Attribute         | Value                                          |
|-------------------|------------------------------------------------|
| **Condition**     | `longest_side_in > 72"` OR `cubic_in > 17,280` |
| **List Price**    | $285.00                                        |
| **Discount**      | 60%                                            |
| **Net Cost**      | $114.00                                        |
| **Exclusivity**   | "dimensional" group, priority 2                |
| **Min Weight**    | 90 lbs                                         |

- At 72.0": Does NOT trigger (condition is `>`, not `>=`)
- At 72.1": Triggers
- 17,280 cu in = 24" x 24" x 30"

### 6.5 AHS (Additional Handling Surcharge)

| Attribute         | Value                                          |
|-------------------|------------------------------------------------|
| **Condition**     | `weight_lbs > 50` OR `longest_side_in > 48"` OR `second_longest_in > 30"` OR `cubic_in > 8,640` |
| **List Price**    | $36.00                                         |
| **Discount**      | 70% (per Third Amendment)                      |
| **Net Cost**      | $10.80                                         |
| **Exclusivity**   | "dimensional" group, priority 3                |
| **Min Weight**    | 30 lbs (negotiated down from 40 lbs)           |

- At 48.0" longest: Does NOT trigger (condition is `>`, not `>=`)
- At 48.1" longest: Triggers
- At 30.0" second longest: Does NOT trigger
- At 30.1" second longest: Triggers (with borderline handling)
- 8,640 cu in = 18" x 20" x 24"

**Borderline Allocation (30.0" - 30.5" second longest):**

OnTrac inconsistently charges AHS for packages with `second_longest_in` in the 30.0" - 30.5" range (~50% of the time). Rather than overstating or understating:

```
IF second_longest_in in (30.0, 30.5] AND no other AHS trigger:
    cost_ahs = $10.80 * 0.50 = $5.40
ELSE:
    cost_ahs = $10.80
```

The 30 lbs minimum billable weight is still applied at 100% for borderline cases.

### 6.6 EDAS (Extended Delivery Area Surcharge)

| Attribute         | Value                          |
|-------------------|--------------------------------|
| **Condition**     | `das_zone == "EDAS"`           |
| **List Price**    | $8.80                          |
| **Discount**      | 60%                            |
| **Net Cost**      | $3.52                          |
| **Exclusivity**   | "delivery" group, priority 1   |

Applies to remote ZIP codes requiring extended delivery routes.

### 6.7 DAS (Delivery Area Surcharge)

| Attribute         | Value                          |
|-------------------|--------------------------------|
| **Condition**     | `das_zone == "DAS"`            |
| **List Price**    | $6.60                          |
| **Discount**      | 60%                            |
| **Net Cost**      | $2.64                          |
| **Exclusivity**   | "delivery" group, priority 2   |

Applies to ZIP codes in designated delivery areas.

### 6.8 RES (Residential Surcharge)

| Attribute         | Value                          |
|-------------------|--------------------------------|
| **Condition**     | All shipments                  |
| **List Price**    | $6.60                          |
| **Discount**      | 90%                            |
| **Allocation**    | 95%                            |
| **Net Cost**      | $6.60 * 0.10 * 0.95 = $0.627   |

**Allocated Surcharge Pattern:**

Unlike deterministic surcharges, RES cannot be predicted per-shipment because we don't know if a destination is residential or commercial. OnTrac charges RES on ~95% of shipments historically. The cost is allocated across ALL shipments:

```
cost_res = list_price * (1 - discount) * allocation_rate
cost_res = $6.60 * 0.10 * 0.95 = $0.627 per shipment
```

### 6.9 Demand Surcharges

Demand surcharges apply during peak season and depend on base surcharges triggering.

**Processing Note:** Demand surcharges are processed in Phase 2 (DEPENDENT) because they reference base surcharge flags from Phase 1.

**Billing Lag:** OnTrac applies demand surcharges based on billing date, not ship date. A 5-day billing lag is applied when checking period boundaries.

#### DEM_AHS (Demand Additional Handling)

| Attribute         | Value                          |
|-------------------|--------------------------------|
| **Condition**     | `surcharge_ahs = True` AND ship_date in demand period |
| **Period**        | Sept 27 - Jan 16               |
| **List Price**    | $11.00                         |
| **Discount**      | 0% (per Fourth Amendment)      |
| **Net Cost**      | $11.00                         |

Uses same borderline allocation as AHS (50% cost for 30.0" - 30.5" second_longest).

#### DEM_LPS (Demand Large Package)

| Attribute         | Value                          |
|-------------------|--------------------------------|
| **Condition**     | `surcharge_lps = True` AND ship_date in demand period |
| **Period**        | Sept 27 - Jan 16               |
| **List Price**    | $105.00                        |
| **Discount**      | 50% (per Second Amendment)     |
| **Net Cost**      | $52.50                         |

#### DEM_OML (Demand Over Maximum Limits)

| Attribute         | Value                          |
|-------------------|--------------------------------|
| **Condition**     | `surcharge_oml = True` AND ship_date in demand period |
| **Period**        | Sept 27 - Jan 16               |
| **List Price**    | $550.00                        |
| **Discount**      | 50% (per Second Amendment)     |
| **Net Cost**      | $275.00                        |

#### DEM_RES (Demand Residential)

| Attribute         | Value                          |
|-------------------|--------------------------------|
| **Condition**     | `surcharge_res = True` AND ship_date in demand period |
| **Period**        | Oct 25 - Jan 16 (shorter than others) |
| **List Price**    | $1.00                          |
| **Discount**      | 50% (per Second Amendment)     |
| **Allocation**    | 95%                            |
| **Net Cost**      | $1.00 * 0.50 * 0.95 = $0.475   |

### 6.10 Demand Periods

| Surcharge | Start Date   | End Date     |
|-----------|--------------|--------------|
| DEM_AHS   | Sept 27      | Jan 16       |
| DEM_LPS   | Sept 27      | Jan 16       |
| DEM_OML   | Sept 27      | Jan 16       |
| DEM_RES   | Oct 25       | Jan 16       |

Dates are **inclusive** on both ends. A 5-day billing lag is applied.

---

## 7. Base Rate Lookup

### 7.1 Rate Source

**File:** `carriers/ontrac/data/reference/base_rates.csv`

### 7.2 Rate Structure

| Dimension       | Values                              |
|-----------------|-------------------------------------|
| Weight brackets | 151 brackets from 0-1 lbs to 149-150 lbs |
| Zones           | 2-8                                 |
| Max weight      | 150 lbs (>150 lbs triggers OML)     |

### 7.3 Weight Brackets

| Lower | Upper | Description |
|-------|-------|-------------|
| 0     | 1     | 0-1 lb      |
| 1     | 2     | 1-2 lbs     |
| 2     | 3     | 2-3 lbs     |
| ...   | ...   | ...         |
| 149   | 150   | 149-150 lbs |

### 7.4 Sample Rates (Zone 4)

| Weight Bracket | Rate     |
|----------------|----------|
| 0-1 lb         | $4.40    |
| 1-2 lbs        | $5.03    |
| 5-6 lbs        | $5.70    |
| 10-11 lbs      | $6.24    |
| 20-21 lbs      | $7.50    |
| 50-51 lbs      | $14.23   |
| 100-101 lbs    | $26.81   |
| 149-150 lbs    | $42.98   |

### 7.5 Lookup Logic

```
Find row where:
    weight_lbs_lower < billable_weight_lbs <= weight_lbs_upper

Return rate from zone_{shipping_zone} column
```

**Example:** 2 lbs to Zone 4
- Bracket: 1 < 2.0 <= 2 (1-2 lb bracket)
- `cost_base` = $5.03

---

## 8. Fuel Surcharge

### 8.1 Configuration

| Parameter       | Value                              |
|-----------------|------------------------------------|
| List Rate       | 18.75%                             |
| Discount        | 35%                                |
| Effective Rate  | 18.75% * (1 - 0.35) = 12.1875%     |
| Application     | Applied to subtotal (LAST)         |

**Source:** Updated weekly from ontrac.com/surcharges

### 8.2 Calculation

```
cost_fuel = cost_subtotal * 0.121875
```

**Example:** Subtotal of $20.00
- `cost_fuel` = $20.00 * 0.121875 = $2.44

---

## 9. Total Cost Calculation

### 9.1 Formula

```
cost_subtotal = cost_base + cost_oml + cost_lps + cost_ahs + cost_edas + cost_das +
                cost_res + cost_dem_ahs + cost_dem_lps + cost_dem_oml + cost_dem_res

cost_fuel = cost_subtotal * 0.121875

cost_total = cost_subtotal + cost_fuel
```

### 9.2 Complete Example

**Package:** 50" x 32" x 10", 25 lbs, Phoenix to ZIP 85001 (DAS zone), Nov 15, 2025

**Stage 1: Supplement**

| Calculation          | Value              |
|----------------------|--------------------|
| `cubic_in`           | 16,000             |
| `longest_side_in`    | 50.0               |
| `second_longest_in`  | 32.0               |
| `length_plus_girth`  | 50 + 2*(32+10) = 134 |
| `shipping_zone`      | 2 (Phoenix → 85001)|
| `das_zone`           | "DAS"              |
| `dim_weight_lbs`     | 16,000 / 250 = 64  |
| `uses_dim_weight`    | True (64 > 25)     |

**Stage 2: Surcharges (Phase 1 - BASE)**

| Surcharge       | Condition                     | Result | Cost    |
|-----------------|-------------------------------|--------|---------|
| OML             | 25 > 150 OR 50 > 108 OR 134 > 165 | False | $0.00  |
| LPS             | 50 > 72 OR 16,000 > 17,280    | False  | $0.00   |
| AHS             | 25 > 50 OR 50 > 48 OR 32 > 30 | True   | $10.80  |
| EDAS            | das_zone == "EDAS"            | False  | $0.00   |
| DAS             | das_zone == "DAS"             | True   | $2.64   |
| RES             | All (allocated 95%)           | True   | $0.627  |

**Stage 2: Surcharges (Phase 2 - DEPENDENT)**

| Surcharge       | Condition                     | Result | Cost    |
|-----------------|-------------------------------|--------|---------|
| DEM_AHS         | AHS + Nov 15 in demand period | True   | $11.00  |
| DEM_LPS         | LPS + demand period           | False  | $0.00   |
| DEM_OML         | OML + demand period           | False  | $0.00   |
| DEM_RES         | RES + Nov 15 in Oct 25-Jan 16 | True   | $0.475  |

**Stage 3: Apply Min Billable Weights**

| Surcharge       | Min Weight | Current | Result |
|-----------------|------------|---------|--------|
| AHS             | 30 lbs     | 64 lbs  | 64 lbs (no change) |

`billable_weight_lbs` = 64 lbs

**Stage 4: Base Rate**

| Lookup          | Value                  |
|-----------------|------------------------|
| Weight bracket  | 63 < 64 <= 64          |
| Zone            | 2                      |
| `cost_base`     | $10.93                 |

**Stage 5: Totals**

| Component       | Amount   |
|-----------------|----------|
| `cost_base`     | $10.93   |
| `cost_ahs`      | $10.80   |
| `cost_das`      | $2.64    |
| `cost_res`      | $0.627   |
| `cost_dem_ahs`  | $11.00   |
| `cost_dem_res`  | $0.475   |
| `cost_subtotal` | $36.472  |
| `cost_fuel`     | $4.45    |
| **cost_total**  | **$40.92** |

---

## 10. Output Columns

### 10.1 Dimensional

| Column              | Type  | Description                     |
|---------------------|-------|---------------------------------|
| `cubic_in`          | int   | Package volume in cubic inches  |
| `longest_side_in`   | float | Longest dimension (1 decimal)   |
| `second_longest_in` | float | Middle dimension (1 decimal)    |
| `length_plus_girth` | float | Longest + 2x(sum of others)     |

### 10.2 Zone

| Column          | Type | Description                      |
|-----------------|------|----------------------------------|
| `shipping_zone` | int  | Zone (2-8)                       |
| `das_zone`      | str  | DAS status: "NO", "DAS", "EDAS"  |

### 10.3 Weight

| Column              | Type  | Description                     |
|---------------------|-------|---------------------------------|
| `dim_weight_lbs`    | float | Dimensional weight              |
| `uses_dim_weight`   | bool  | True if DIM weight used         |
| `billable_weight_lbs`| float| Final billable weight           |

### 10.4 Surcharge Flags

| Column              | Type | Description                      |
|---------------------|------|----------------------------------|
| `surcharge_oml`     | bool | True if OML applies              |
| `surcharge_lps`     | bool | True if LPS applies              |
| `surcharge_ahs`     | bool | True if AHS applies              |
| `surcharge_das`     | bool | True if DAS applies              |
| `surcharge_edas`    | bool | True if EDAS applies             |
| `surcharge_res`     | bool | True if RES applies (always)     |
| `surcharge_dem_ahs` | bool | True if DEM_AHS applies          |
| `surcharge_dem_lps` | bool | True if DEM_LPS applies          |
| `surcharge_dem_oml` | bool | True if DEM_OML applies          |
| `surcharge_dem_res` | bool | True if DEM_RES applies          |

### 10.5 Costs

| Column              | Type  | Description                     |
|---------------------|-------|---------------------------------|
| `cost_base`         | float | Base shipping rate              |
| `cost_oml`          | float | OML surcharge ($0 or $1,875.00) |
| `cost_lps`          | float | LPS surcharge ($0 or $114.00)   |
| `cost_ahs`          | float | AHS surcharge ($0, $5.40, or $10.80) |
| `cost_das`          | float | DAS surcharge ($0 or $2.64)     |
| `cost_edas`         | float | EDAS surcharge ($0 or $3.52)    |
| `cost_res`          | float | RES surcharge ($0.627)          |
| `cost_dem_ahs`      | float | DEM_AHS surcharge ($0, $5.50, or $11.00) |
| `cost_dem_lps`      | float | DEM_LPS surcharge ($0 or $52.50)|
| `cost_dem_oml`      | float | DEM_OML surcharge ($0 or $275.00)|
| `cost_dem_res`      | float | DEM_RES surcharge ($0 or $0.475)|
| `cost_subtotal`     | float | Sum of all costs before fuel    |
| `cost_fuel`         | float | Fuel surcharge (12.1875% of subtotal) |
| `cost_total`        | float | Final total cost                |

### 10.6 Metadata

| Column              | Type | Description           |
|---------------------|------|-----------------------|
| `calculator_version`| str  | Version stamp         |

---

## 11. Data Sources

| File                                              | Purpose                     |
|---------------------------------------------------|-----------------------------|
| `carriers/ontrac/data/reference/zones.csv`        | 5-digit ZIP to zone mapping |
| `carriers/ontrac/data/reference/base_rates.csv`   | Weight x zone rate card     |
| `carriers/ontrac/data/reference/billable_weight.py`| DIM factor config          |
| `carriers/ontrac/data/reference/fuel.py`          | Fuel surcharge config       |
| `carriers/ontrac/surcharges/over_maximum_limits.py`| OML surcharge class        |
| `carriers/ontrac/surcharges/large_package.py`     | LPS surcharge class         |
| `carriers/ontrac/surcharges/additional_handling.py`| AHS surcharge class        |
| `carriers/ontrac/surcharges/delivery_area.py`     | DAS surcharge class         |
| `carriers/ontrac/surcharges/extended_delivery_area.py`| EDAS surcharge class    |
| `carriers/ontrac/surcharges/residential.py`       | RES surcharge class         |
| `carriers/ontrac/surcharges/demand_additional_handling.py`| DEM_AHS surcharge class |
| `carriers/ontrac/surcharges/demand_large_package.py`| DEM_LPS surcharge class   |
| `carriers/ontrac/surcharges/demand_over_maximum_limits.py`| DEM_OML surcharge class |
| `carriers/ontrac/surcharges/demand_residential.py`| DEM_RES surcharge class     |
| `carriers/ontrac/version.py`                      | Calculator version          |

---

## 12. Key Constraints

| Constraint              | Value / Rule                           |
|-------------------------|----------------------------------------|
| Max weight              | 150 lbs (OML penalty for >150)         |
| DIM factor              | 250 (negotiated, standard is 139)      |
| DIM threshold           | 1,728 cubic inches                     |
| Zone lookup             | 5-digit ZIP (not 3-digit)              |
| Zone range              | 2-8                                    |
| Surcharge boundaries    | Use `>` not `>=` for all thresholds    |
| Fuel surcharge          | 12.1875% (18.75% list - 35% discount)  |
| Demand period           | Sept 27 - Jan 16 (DEM_RES: Oct 25 - Jan 16) |
| Billing lag             | 5 days for demand period calculations  |
| Borderline AHS          | 50% allocation for 30.0" - 30.5" second longest |
| Current accuracy        | -0.52% variance                        |

---

*Last updated: February 2026*
