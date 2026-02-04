# P2P US - Calculation Logic

Complete documentation of how expected shipping costs are calculated for P2P US Parcel Flex Advantage Plus.

**Service:** Parcel Flex Advantage Plus (PFAP2)
**Max Weight:** 50 lbs
**Calculator Version:** 2026.02.03

---

## Executive Summary

P2P US Parcel Flex Advantage Plus shipping cost is calculated as follows:

1. **Determine the zone** based on the full 5-digit destination ZIP code. Zones range from 1-8, with higher zones being further from the Chicago (ORD) origin and more expensive.

2. **Calculate billable weight** as the greater of actual weight or dimensional weight. Unlike other carriers, P2P US **always** compares actual vs dimensional weight with no minimum volume threshold. Dimensional weight is calculated as cubic inches / 250.

3. **Apply AHS minimum weight** if dimensional conditions trigger. When packages exceed dimensional thresholds (longest > 48", second longest > 30", or L+G > 105"), billable weight is bumped to at least 30 lbs before rate lookup.

4. **Look up the base rate** from the P2P rate card using the zone and billable weight. Rates range from ~$3.56 (light, nearby) to ~$20.48 (heavy, far).

5. **Apply surcharges** for non-standard packages:
   - Additional Handling for packages with large dimensions or heavy weight ($29.00)
   - Oversize for packages with billable weight over 70 lbs ($125.00)
   - These can stack: a package with longest > 48" and DIM weight > 70 lbs pays both ($154.00 total)

6. **No fuel surcharge** - P2P US does not charge a fuel surcharge.

**Final cost = Base Rate + Surcharges**

---

## 1. Input Requirements

| Column              | Type      | Description                          | Example      |
|---------------------|-----------|--------------------------------------|--------------|
| `ship_date`         | date      | Ship date                            | 2025-11-15   |
| `production_site`   | str       | Origin: "Columbus"                   | "Columbus"   |
| `shipping_zip_code` | str/int   | 5-digit destination ZIP code         | "90210"      |
| `shipping_region`   | str       | Destination state (reference)        | "California" |
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
|  +-- Apply AHS min weight        |
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

**File:** `carriers/p2p_us/data/reference/zones.csv`

Zones are based on **full 5-digit ZIP code** (not 3-digit prefix like USPS). The origin is **Chicago (ORD)**.

| Column | Description                    |
|--------|--------------------------------|
| `zip`  | 5-digit ZIP code               |
| `zone` | Shipping zone (1-8)            |

### 4.2 Zone Distribution

| Zone | ZIP Count | Percentage |
|------|-----------|------------|
| 5    | 5,268     | 50.5%      |
| 7    | 1,458     | 14.0%      |
| 4    | 1,134     | 10.9%      |
| 6    | 832       | 8.0%       |
| 3    | 832       | 8.0%       |
| 1    | 408       | 3.9%       |
| 8    | 324       | 3.1%       |
| 2    | 174       | 1.7%       |

### 4.3 Fallback Logic

| Priority | Method                          | Description                        |
|----------|--------------------------------|------------------------------------|
| 1        | Exact 5-digit ZIP match        | Look up full ZIP in zones.csv      |
| 2        | Mode zone                      | Most common zone (zone 5)          |
| 3        | Default zone 5                 | Fallback if no match found         |

**Note:** Puerto Rico (zone 9) and Hawaii (zone 12) are mapped to zone 8 in the reference data.

**Example:** ZIP 07820 from Chicago
- 5-digit ZIP: "07820"
- Look up in zones.csv -> zone = 5
- `shipping_zone` = 5

---

## 5. Billable Weight

### 5.1 Configuration

| Parameter       | Value                      |
|-----------------|----------------------------|
| DIM Factor      | 250 cubic inches per pound |
| DIM Threshold   | None (always compare)      |
| AHS Min Weight  | 30 lbs (when dimensional conditions trigger) |

### 5.2 Calculation Logic

```
dim_weight_lbs = cubic_in / 250
uses_dim_weight = (dim_weight_lbs > weight_lbs)
billable_weight_lbs = MAX(weight_lbs, dim_weight_lbs)

IF AHS dimensional conditions met (longest >48", second longest >30", or L+G >105"):
    billable_weight_lbs = MAX(billable_weight_lbs, 30)
```

**Key Difference:** P2P US has **no DIM threshold**. Dimensional weight is always calculated and compared against actual weight, even for small packages.

**Example 1:** Standard package 20" x 20" x 10", 5 lbs actual

| Calculation          | Value              |
|----------------------|--------------------|
| `cubic_in`           | 4,000              |
| `dim_weight_lbs`     | 4,000 / 250 = 16.0 |
| `uses_dim_weight`    | True (16 > 5)      |
| `billable_weight_lbs`| 16.0               |

**Example 2:** Large package 50" x 20" x 10", 5 lbs actual (AHS dimensional trigger)

| Calculation          | Value              |
|----------------------|--------------------|
| `cubic_in`           | 10,000             |
| `dim_weight_lbs`     | 10,000 / 250 = 40.0|
| AHS dimensional?     | Yes (longest 50 > 48) |
| `billable_weight_lbs`| 40.0 (already > 30)|

**Example 3:** Large but light package 50" x 10" x 10", 2 lbs actual (AHS bumps weight)

| Calculation          | Value              |
|----------------------|--------------------|
| `cubic_in`           | 5,000              |
| `dim_weight_lbs`     | 5,000 / 250 = 20.0 |
| AHS dimensional?     | Yes (longest 50 > 48) |
| `billable_weight_lbs`| 30.0 (bumped from 20)|

---

## 6. Surcharges

### 6.1 Surcharge Summary

| Surcharge | Condition                              | Cost    | Exclusivity |
|-----------|----------------------------------------|---------|-------------|
| AHS       | Dimensional OR weight threshold        | $29.00  | None (standalone) |
| OVERSIZE  | billable_weight > 70 lbs               | $125.00 | None (standalone) |

### 6.2 AHS (Additional Handling Surcharge)

| Attribute         | Value                          |
|-------------------|--------------------------------|
| **Condition**     | Any of the 4 conditions below  |
| **Cost**          | $29.00 (list price, no discount) |
| **Exclusivity**   | None (standalone surcharge)    |

**Triggers when ANY of these conditions are met:**

| # | Condition          | Threshold            | Comparison |
|---|-------------------|----------------------|------------|
| 1 | Longest side      | > 48"                | `>`        |
| 2 | Second longest    | > 30"                | `>`        |
| 3 | Length + Girth    | > 105"               | `>`        |
| 4 | Billable weight   | > 30 lbs             | `>`        |

**Boundary Behavior:**
- At 48.0" longest: Does NOT trigger (condition is `>`, not `>=`)
- At 48.1" longest: Triggers
- At 30.0" second longest: Does NOT trigger
- At 30.1" second longest: Triggers
- At 105.0" L+G: Does NOT trigger
- At 105.1" L+G: Triggers
- At 30.0 lbs billable: Does NOT trigger
- At 30.1 lbs billable: Triggers

**Side Effect:** When AHS triggers due to dimensional conditions (1-3), the **minimum billable weight is set to 30 lbs** before rate lookup. This side effect does NOT apply when AHS triggers only due to weight condition (4).

### 6.3 OVERSIZE

| Attribute         | Value                          |
|-------------------|--------------------------------|
| **Condition**     | `billable_weight_lbs > 70`     |
| **Cost**          | $125.00 (list price, no discount) |
| **Exclusivity**   | None (standalone surcharge)    |

- At 70.0 lbs: Does NOT trigger (condition is `>`, not `>=`)
- At 70.1 lbs: Triggers

**Note:** Since the max service weight is 50 lbs actual, this surcharge only applies when dimensional weight exceeds 70 lbs (packages > 17,500 cubic inches).

### 6.4 Surcharge Stacking

Both surcharges are standalone (no exclusivity groups), so they can stack:

**Example:** Package 50" x 35" x 15", 10 lbs actual

| Surcharge | Check                         | Result | Cost    |
|-----------|-------------------------------|--------|---------|
| AHS       | 50 > 48?                      | True   | $29.00  |
| OVERSIZE  | 26,250/250 = 105 lbs > 70?    | True   | $125.00 |
| **Total** |                               |        | **$154.00** |

---

## 7. Base Rate Lookup

### 7.1 Rate Source

**File:** `carriers/p2p_us/data/reference/base_rates.csv`

### 7.2 Rate Structure

| Dimension       | Values                              |
|-----------------|-------------------------------------|
| Weight brackets | 66 brackets from 0-0.0625 lbs to 49-50 lbs |
| Zones           | 1-8                                 |
| Max weight      | 50 lbs                              |

### 7.3 Weight Brackets

The rate card uses fine-grained weight brackets:

**Ounce Brackets (0-1 lb):**

| Lower   | Upper    | Description |
|---------|----------|-------------|
| 0       | 0.0625   | 1 oz        |
| 0.0625  | 0.125    | 2 oz        |
| 0.125   | 0.1875   | 3 oz        |
| 0.1875  | 0.25     | 4 oz        |
| 0.25    | 0.3125   | 5 oz        |
| ...     | ...      | ...         |
| 0.9375  | 0.999375 | 16 oz       |
| 0.999375| 1.0      | 1 lb        |

**Pound Brackets (1-50 lbs):**

| Lower | Upper | Description |
|-------|-------|-------------|
| 1     | 2     | 1-2 lbs     |
| 2     | 3     | 2-3 lbs     |
| ...   | ...   | ...         |
| 49    | 50    | 49-50 lbs   |

### 7.4 Sample Rates

| Weight Bracket | Zone 1 | Zone 4 | Zone 5 | Zone 8 |
|----------------|--------|--------|--------|--------|
| 0-1 oz         | $3.56  | $3.89  | $3.96  | $4.46  |
| 1-2 lbs        | $4.16  | $4.24  | $4.31  | $4.87  |
| 9-10 lbs       | $4.78  | $4.88  | $4.96  | $5.60  |
| 19-20 lbs      | $7.42  | $7.59  | $7.71  | $8.77  |
| 29-30 lbs      | $9.78  | $10.00 | $10.18 | $11.59 |
| 49-50 lbs      | $17.21 | $17.60 | $17.92 | $20.48 |

### 7.5 Lookup Logic

```
Find row where:
    weight_lbs_lower < billable_weight_lbs <= weight_lbs_upper

Return rate for matching zone column
```

**Example:** 15 lbs to Zone 5
- Bracket: 14 < 15.0 <= 15 (14-15 lb bracket)
- `cost_base` = $6.17

---

## 8. Fuel Surcharge

**P2P US has no fuel surcharge.**

---

## 9. Total Cost Calculation

### 9.1 Formula

```
cost_subtotal = cost_base + cost_ahs + cost_oversize

cost_total = cost_subtotal
```

**Note:** P2P US has **no fuel surcharge**. Total always equals subtotal.

### 9.2 Complete Example

**Package:** 50" x 25" x 10", 8 lbs, Columbus to ZIP 90210, Feb 1, 2026

**Stage 1: Supplement**

| Calculation          | Value              |
|----------------------|--------------------|
| `cubic_in`           | 12,500             |
| `longest_side_in`    | 50.0               |
| `second_longest_in`  | 25.0               |
| `length_plus_girth`  | 120.0              |
| `shipping_zone`      | 8 (ZIP 90210)      |
| `dim_weight_lbs`     | 12,500 / 250 = 50.0|
| `uses_dim_weight`    | True (50 > 8)      |

**AHS Min Weight Check:**
- Longest 50 > 48? Yes - dimensional trigger!
- Billable weight = max(50.0, 30) = 50.0 lbs

**Stage 2: Surcharges**

| Surcharge       | Condition                    | Result | Cost    |
|-----------------|------------------------------|--------|---------|
| AHS             | longest 50 > 48 OR billable 50 > 30 | True | $29.00  |
| OVERSIZE        | 50 > 70                      | False  | $0.00   |

**Stage 3: Base Rate**

| Lookup          | Value                  |
|-----------------|------------------------|
| Weight bracket  | 49-50 lbs              |
| Zone            | 8                      |
| `cost_base`     | $20.48                 |

**Stage 4: Totals**

| Component       | Amount  |
|-----------------|---------|
| `cost_base`     | $20.48  |
| `cost_ahs`      | $29.00  |
| `cost_oversize` | $0.00   |
| **cost_total**  | **$49.48** |

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
| `shipping_zone` | int  | Shipping zone (1-8)              |

### 10.3 Weight

| Column              | Type  | Description                     |
|---------------------|-------|---------------------------------|
| `dim_weight_lbs`    | float | Dimensional weight              |
| `uses_dim_weight`   | bool  | True if DIM weight used         |
| `billable_weight_lbs`| float| Final billable weight           |

### 10.4 Surcharge Flags

| Column            | Type | Description                      |
|-------------------|------|----------------------------------|
| `surcharge_ahs`   | bool | True if AHS applies              |
| `surcharge_oversize` | bool | True if Oversize applies      |

### 10.5 Costs

| Column            | Type  | Description                     |
|-------------------|-------|---------------------------------|
| `cost_base`       | float | Base shipping rate              |
| `cost_ahs`        | float | AHS surcharge ($0 or $29.00)    |
| `cost_oversize`   | float | Oversize surcharge ($0 or $125.00) |
| `cost_subtotal`   | float | Sum of all costs                |
| `cost_total`      | float | Same as subtotal (no fuel)      |

### 10.6 Metadata

| Column              | Type | Description           |
|---------------------|------|-----------------------|
| `calculator_version`| str  | Version stamp         |

---

## 11. Data Sources

| File                                           | Purpose                    |
|------------------------------------------------|----------------------------|
| `carriers/p2p_us/data/reference/zones.csv`      | 5-digit ZIP to zone mapping|
| `carriers/p2p_us/data/reference/base_rates.csv` | Weight x zone rate card   |
| `carriers/p2p_us/data/reference/billable_weight.py` | DIM factor config    |
| `carriers/p2p_us/surcharges/additional_handling.py` | AHS surcharge class  |
| `carriers/p2p_us/surcharges/oversize.py`        | Oversize surcharge class   |

---

## 12. Key Constraints

| Constraint              | Value / Rule                           |
|-------------------------|----------------------------------------|
| Max weight              | 50 lbs                                 |
| DIM factor              | 250                                    |
| DIM threshold           | None (always compare)                  |
| Zone lookup             | 5-digit ZIP (not 3-digit prefix)       |
| Surcharge boundaries    | Use `>` not `>=` for all thresholds    |
| Fuel surcharge          | None                                   |
| AHS min weight          | 30 lbs (dimensional triggers only)     |
| Origin                  | Chicago (ORD)                          |
| Production sites        | Columbus only                          |

---

*Last updated: February 2026*
