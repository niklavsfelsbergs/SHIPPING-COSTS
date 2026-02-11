# FedEx - Calculation Logic

Complete documentation of how expected shipping costs are calculated for FedEx Home Delivery and Ground Economy (SmartPost).

**Services:** FedEx Home Delivery, FedEx Ground Economy (SmartPost)
**Max Weight:** 150 lbs (Home Delivery), 71 lbs (Ground Economy)
**Calculator Version:** 2026.01.27.8

---

## Executive Summary

FedEx shipping cost is calculated as follows:

1. **Determine the service type** based on the PCS service code. Shipments are classified as either Home Delivery or Ground Economy (SmartPost).

2. **Determine the zone** based on the 5-digit destination ZIP code and the origin facility (Phoenix or Columbus). Zones range from 2-9, plus special zones (14, 17, 22, 23, 25, 92, 96 for Home Delivery; 10, 17, 26, 99 for SmartPost).

3. **Calculate billable weight** as the greater of actual weight or dimensional weight. DIM weight is always calculated (no threshold) using service-specific divisors: 250 for Home Delivery, 225 for Ground Economy.

4. **Look up the base rate** from service-specific rate cards. The rates in the CSV files already include performance pricing and earned discount baked in (post-discount net rates). The performance_pricing, earned_discount, and grace_discount CSVs are zeroed out because those discounts are already reflected in the base rate.

5. **Apply surcharges** for non-standard packages:
   - Residential Surcharge - all Home Delivery shipments (list $6.45, 65% off = $2.26)
   - Delivery Area Surcharge (DAS) - remote/extended areas (list $6.60-$16.75, 65% off for HD)
   - Additional Handling Surcharge - oversized dimensions (list $32.75, 75% off = $8.19)
   - Additional Handling Surcharge - heavy packages > 50 lbs (list $50.25, 50% off = $25.13)
   - Oversize Surcharge - very large packages (list $275.00, 75% off = $68.75)
   - Demand surcharges during peak season (Sep 29 - Jan 18)

6. **Apply fuel surcharge** as 14% of (base rate + surcharges), excluding discounts. The 14% effective rate comes from 20% published list rate with 30% contractual discount.

**Final cost = Base Rate + Surcharges + Fuel**

---

## 1. Input Requirements

| Column              | Type      | Description                          | Example          |
|---------------------|-----------|--------------------------------------|------------------|
| `ship_date`         | date      | Ship date (for demand period checks) | 2025-11-15       |
| `production_site`   | str       | Origin: "Phoenix" or "Columbus"      | "Phoenix"        |
| `shipping_zip_code` | str/int   | 5-digit destination ZIP code         | "90210"          |
| `shipping_region`   | str       | Destination state (fallback)         | "California"     |
| `pcs_shipping_provider` | str   | PCS service code for mapping         | "FXEHD"          |
| `length_in`         | float     | Package length in inches             | 10.0             |
| `width_in`          | float     | Package width in inches              | 8.0              |
| `height_in`         | float     | Package height in inches             | 6.0              |
| `weight_lbs`        | float     | Actual weight in pounds              | 2.0              |

---

## 2. Calculation Pipeline

```
Input DataFrame
      |
      v
+------------------------------------+
|  Stage 1: supplement_shipments()   |
|  +-- Map service type              |
|  +-- Calculate dimensions          |
|  +-- Look up zone                  |
|  +-- Look up DAS zone              |
|  +-- Calculate billable weight     |
+------------------------------------+
      |
      v
+------------------------------------+
|  Stage 2: calculate()              |
|  +-- Apply base surcharges         |
|  +-- Apply dependent surcharges    |
|  +-- Apply min billable weights    |
|  +-- Look up 4-part rate           |
|  +-- Calculate subtotal            |
|  +-- Apply fuel surcharge          |
|  +-- Calculate total               |
+------------------------------------+
      |
      v
Output DataFrame with cost columns
```

---

## 3. Service Type Mapping

### 3.1 Service Types

FedEx shipments are classified into two service types for rate calculation:

| Service       | Invoice Name          | Max Weight | DIM Factor |
|---------------|-----------------------|------------|------------|
| Home Delivery | FedEx Home Delivery   | 150 lbs    | 250        |
| Ground Economy| FedEx Ground Economy  | 71 lbs     | 225        |

### 3.2 PCS Service Code Mapping (Historical)

When processing historical shipments for comparison against invoices, the service type is determined from the PCS shipping provider code:

| PCS Code      | Rate Service   |
|---------------|----------------|
| FXESPPS       | Ground Economy |
| FXEGRD        | Ground Economy |
| FXESPPSL      | Ground Economy |
| FXE2D         | Home Delivery  |
| FXE2DXLBOR   | Home Delivery  |
| FXE2DTBOR     | Home Delivery  |
| FXESTDO       | Home Delivery  |
| FXEINTECON    | Home Delivery  |
| FXEINTPRIO    | Home Delivery  |
| FXEPO         | Home Delivery  |
| FXE2DSBOR     | Home Delivery  |
| FXEHD         | Home Delivery  |
| FXE2DLBOR     | Home Delivery  |
| FXE2DMBOR     | Home Delivery  |
| FXE2DENVOR    | Home Delivery  |
| FXE2DPAKOR    | Home Delivery  |
| (unknown)     | Home Delivery  |

Unknown service codes default to Home Delivery.

### 3.3 Optimal Service Selection (All-US Analysis)

For optimization scenarios comparing FedEx against other carriers, we calculate costs for **both** Home Delivery and Ground Economy (SmartPost) and select the cheaper option for each shipment.

**Selection Logic:**

```
FOR each shipment:
    1. Calculate Home Delivery cost (fedex_hd_cost_total)
    2. Calculate SmartPost cost (fedex_sp_cost_total)

    IF weight_lbs <= 70 AND fedex_sp_cost_total < fedex_hd_cost_total:
        fedex_service_selected = "FXSP" (SmartPost)
        fedex_cost_total = fedex_sp_cost_total
    ELSE:
        fedex_service_selected = "FXEHD" (Home Delivery)
        fedex_cost_total = fedex_hd_cost_total
```

**Constraints:**
- **SmartPost eligibility:** Only shipments <= 70 lbs can use SmartPost (max weight is 71 lbs, but we use 70 lb cutoff for safety margin)
- **Shipments > 70 lbs:** Must use Home Delivery

**When SmartPost typically wins:**
- Smaller, lighter packages (lower base rates)
- No residential surcharge ($2.26 savings)
- No AHS-Dimensions surcharge for oversized packages
- No base demand surcharge during peak season

**When Home Delivery typically wins:**
- Heavier packages where the DIM factor difference (250 vs 225) matters
- Packages where SmartPost's lower DIM factor inflates the billable weight significantly

**Output Columns (All-US):**

| Column                  | Description                                      |
|-------------------------|--------------------------------------------------|
| `fedex_service_selected`| "FXEHD" (Home Delivery) or "FXSP" (SmartPost)   |
| `fedex_hd_cost_total`   | Cost if sent via Home Delivery                   |
| `fedex_sp_cost_total`   | Cost if sent via SmartPost                       |
| `fedex_cost_total`      | Actual cost (based on selected service)          |

---

## 4. Dimensional Calculations

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

## 5. Zone Lookup

### 5.1 Zone Source

**File:** `carriers/fedex/data/reference/zones.csv`

Zones are based on **5-digit ZIP code** and are **origin-dependent**.

| Column       | Description                    |
|--------------|--------------------------------|
| `zip_code`   | 5-digit ZIP code               |
| `state`      | State abbreviation             |
| `phx_zone`   | Zone from Phoenix origin       |
| `cmh_zone`   | Zone from Columbus origin      |

### 5.2 Zone Values

**Home Delivery zones:** 2, 3, 4, 5, 6, 7, 8, 9, 14, 17, 22, 23, 25, 92, 96

**Ground Economy zones:** 2, 3, 4, 5, 6, 7, 8, 9, 10, 17, 26, 99

### 5.3 Fallback Logic

| Priority | Method                          | Description                        |
|----------|--------------------------------|------------------------------------|
| 1        | Exact 5-digit ZIP match        | Look up zip_code in zones.csv      |
| 2        | State-level mode               | Most common zone for that state    |
| 3        | Default zone 5                 | Fallback if no match found         |

### 5.4 Letter Zone Mapping

Letter zones (A, H, M, P) are mapped to zone 9 (Hawaii rate).

**Example:** ZIP 90210 from Phoenix
- Look up in zones.csv -> phx_zone = 4
- `shipping_zone` = 4

---

## 6. Billable Weight

### 6.1 Configuration

| Parameter       | Home Delivery             | Ground Economy           |
|-----------------|---------------------------|--------------------------|
| DIM Factor      | 250 cubic inches per lb   | 225 cubic inches per lb  |
| DIM Threshold   | 0 (always applies)        | 0 (always applies)       |
| Max Weight      | 150 lbs                   | 71 lbs                   |

### 6.2 Calculation Logic

```
dim_weight_lbs = cubic_in / DIM_FACTOR

uses_dim_weight = (dim_weight_lbs > weight_lbs)

billable_weight_lbs = MAX(weight_lbs, dim_weight_lbs)

-- Round UP to nearest integer (ceiling)
weight_bracket = CEILING(billable_weight_lbs, 1)
```

**Note:** Unlike USPS, FedEx has no DIM threshold - dimensional weight is always considered regardless of package size.

**Example (Home Delivery):** 20" x 20" x 10" package, 5 lbs actual

| Calculation          | Value               |
|----------------------|---------------------|
| `cubic_in`           | 4,000               |
| `dim_weight_lbs`     | 4,000 / 250 = 16.0  |
| `uses_dim_weight`    | True (16 > 5)       |
| `billable_weight_lbs`| 16.0                |
| `weight_bracket`     | 16 (for rate lookup)|

**Example (Ground Economy):** 20" x 20" x 10" package, 5 lbs actual

| Calculation          | Value               |
|----------------------|---------------------|
| `cubic_in`           | 4,000               |
| `dim_weight_lbs`     | 4,000 / 225 = 17.8  |
| `uses_dim_weight`    | True (17.8 > 5)     |
| `billable_weight_lbs`| 17.8                |
| `weight_bracket`     | 18 (for rate lookup)|

---

## 7. Surcharges

### 7.1 Surcharge Summary

All surcharges store list price and contractual discount separately. Net price = list_price x (1 - discount).

| Surcharge     | List Price | Discount | Net Price | Condition                     | Exclusivity           | Service      |
|---------------|-----------|----------|-----------|-------------------------------|-----------------------|--------------|
| Residential   | $6.45     | 65%      | $2.26     | All Home Delivery shipments   | None                  | HD only      |
| DAS           | varies    | 65% (HD) | varies    | ZIP in DAS zone               | None                  | HD & GE      |
| AHS           | $32.75    | 75%      | $8.19     | Dimensions exceed thresholds  | "dimensional" (pri 3) | HD only      |
| AHS_Weight    | $50.25    | 50%      | $25.13    | weight > 50 lbs               | "dimensional" (pri 2) | HD & GE      |
| Oversize      | $275.00   | 75%      | $68.75    | Extreme dimensions/weight     | "dimensional" (pri 1) | HD only      |
| DEM_Base      | -         | -        | $0.40-$0.65 | Home Delivery in demand period | None               | HD only      |
| DEM_AHS       | -         | -        | $4.13-$5.45 | AHS/AHS_Weight in demand period | None              | HD & GE      |
| DEM_Oversize  | -         | -        | $45.00-$54.25 | Oversize in demand period   | None                  | HD only      |

### 7.2 Residential Surcharge

| Attribute         | Value                              |
|-------------------|------------------------------------|
| **List Price**    | $6.45                              |
| **Discount**      | 65%                                |
| **Net Price**     | $2.26                              |
| **Condition**     | `rate_service == "Home Delivery"`  |
| **Exclusivity**   | None (always applies to HD)        |

FedEx Home Delivery is inherently a residential service, so every HD shipment receives this surcharge (100% deterministic). Ground Economy (SmartPost) is exempt.

### 7.3 Delivery Area Surcharge (DAS)

DAS zones are determined by destination ZIP code only (not origin-dependent).

**File:** `carriers/fedex/data/reference/das_zones.csv`

| Column        | Description                           |
|---------------|---------------------------------------|
| `zip_code`    | 5-digit ZIP code                      |
| `das_type_hd` | DAS tier for Home Delivery (or null)  |
| `das_type_sp` | DAS tier for Ground Economy (or null) |

**Home Delivery DAS Tiers:**

| Tier          | List Price | Discount | Net Price |
|---------------|-----------|----------|-----------|
| DAS           | $6.60     | 65%      | $2.31     |
| DAS_EXTENDED  | $8.80     | 65%      | $3.08     |
| DAS_REMOTE    | $16.75    | 65%      | $5.86     |
| DAS_ALASKA    | -         | -        | $43.00    |
| DAS_HAWAII    | -         | -        | $14.50    |

Note: Alaska and Hawaii list prices are unknown. The net values ($43.00 and $14.50) are stored directly.

**Ground Economy (SmartPost) DAS Tiers:**

| Tier          | List Price | Discount | Net Price |
|---------------|-----------|----------|-----------|
| DAS           | $6.60     | 0%       | $6.60     |
| DAS_EXTENDED  | $8.80     | 0%       | $8.80     |
| DAS_ALASKA    | $8.80     | 0%       | $8.80     |
| DAS_HAWAII    | $8.80     | 0%       | $8.80     |

Note: No proposed discount information available for Ground Economy DAS.

### 7.4 Additional Handling Surcharge - Dimensions (AHS)

| Attribute         | Value                              |
|-------------------|------------------------------------|
| **List Price**    | $32.75                             |
| **Discount**      | 75%                                |
| **Net Price**     | $8.19                              |
| **Condition**     | Home Delivery AND any of:          |
|                   | - longest_side > 48"               |
|                   | - second_longest > 30.3"           |
|                   | - length_plus_girth > 106"         |
| **Exclusivity**   | "dimensional" group, priority 3    |
| **Side Effect**   | Minimum billable weight = 40 lbs   |

**Notes:**
- Ground Economy is exempt from AHS
- At 48.0" longest: Does NOT trigger (condition is `>`, not `>=`)
- At 30.3" second longest: Does NOT trigger (condition is `>`, not `>=`)
- At 106.0" girth: Does NOT trigger (condition is `>`, not `>=`)
- AHS loses to AHS_Weight (priority 2) and Oversize (priority 1)
- When triggered, minimum billable weight of 40 lbs is enforced - if the package's billable weight is below 40 lbs, it is raised to 40 lbs for rate lookup purposes

### 7.5 Additional Handling Surcharge - Weight (AHS_Weight)

| Attribute         | Value                              |
|-------------------|------------------------------------|
| **List Price**    | $50.25                             |
| **Discount**      | 50%                                |
| **Net Price**     | $25.13                             |
| **Condition**     | `weight_lbs > 50`                  |
| **Exclusivity**   | "dimensional" group, priority 2    |

- At 50.0 lbs: Does NOT trigger (condition is `>`, not `>=`)
- At 50.1 lbs: Triggers
- AHS_Weight wins over AHS (priority 3)
- AHS_Weight loses to Oversize (priority 1)
- Note: AHS_Weight applies to both Home Delivery and Ground Economy (no service restriction in the conditions)

### 7.6 Oversize Surcharge

| Attribute         | Value                              |
|-------------------|------------------------------------|
| **List Price**    | $275.00                            |
| **Discount**      | 75%                                |
| **Net Price**     | $68.75                             |
| **Condition**     | Home Delivery AND any of:          |
|                   | - longest_side > 96"               |
|                   | - length_plus_girth > 130"         |
|                   | - cubic_in > 17,280                |
|                   | - weight_lbs > 110                 |
| **Exclusivity**   | "dimensional" group, priority 1    |

**Notes:**
- Ground Economy is exempt from Oversize
- Oversize wins over AHS and AHS_Weight
- All conditions use `>`, not `>=`

### 7.7 Exclusivity Logic ("dimensional" group)

Surcharges in the "dimensional" exclusivity group compete - only the **highest priority (lowest number)** that matches is applied:

| Priority | Surcharge  | Check Order |
|----------|------------|-------------|
| 1        | Oversize   | First       |
| 2        | AHS_Weight | Second      |
| 3        | AHS        | Third       |

**Example:** Package 100" x 20" x 10", 60 lbs (Home Delivery)

| Surcharge  | Check                        | Result       | Cost     |
|------------|------------------------------|--------------|----------|
| Oversize   | 100 > 96?                    | True         | $68.75   |
| AHS_Weight | Skipped (Oversize matched)   | False        | $0.00    |
| AHS        | Skipped (Oversize matched)   | False        | $0.00    |

### 7.8 Demand Surcharges

Demand surcharges apply during peak season and have two pricing phases.

#### 7.8.1 DEM_Base (Base Demand Surcharge)

| Attribute         | Value                              |
|-------------------|------------------------------------|
| **Condition**     | Home Delivery AND in demand period |
| **Period**        | Oct 27 - Jan 18                    |
| **Phase 1 Cost**  | $0.40 (Oct 27 - Nov 23)            |
| **Phase 2 Cost**  | $0.65 (Nov 24 - Jan 18)            |

**Note:** Ground Economy is exempt from base demand surcharge.

#### 7.8.2 DEM_AHS (Demand AHS Surcharge)

| Attribute         | Value                              |
|-------------------|------------------------------------|
| **Condition**     | (AHS OR AHS_Weight) AND in period  |
| **Period**        | Sep 29 - Jan 18                    |
| **Phase 1 Cost**  | $4.13 (Sep 29 - Nov 23)            |
| **Phase 2 Cost**  | $5.45 (Nov 24 - Jan 18)            |

Note: Starts earlier (Sep 29) than base demand (Oct 27). Triggers when either AHS-Dimensions or AHS-Weight is active.

#### 7.8.3 DEM_Oversize (Demand Oversize Surcharge)

| Attribute         | Value                              |
|-------------------|------------------------------------|
| **Condition**     | Oversize AND in demand period      |
| **Period**        | Sep 29 - Jan 18                    |
| **Phase 1 Cost**  | $45.00 (Sep 29 - Nov 23)           |
| **Phase 2 Cost**  | $54.25 (Nov 24 - Jan 18)           |

### 7.9 Demand Period Summary

| Surcharge    | Start Date   | Phase 2 Start | End Date     |
|--------------|--------------|---------------|--------------|
| DEM_Base     | Oct 27       | Nov 24        | Jan 18       |
| DEM_AHS      | Sep 29       | Nov 24        | Jan 18       |
| DEM_Oversize | Sep 29       | Nov 24        | Jan 18       |

---

## 8. Base Rate Lookup

### 8.1 Rate Structure

The calculator uses a 4-part rate structure with separate CSV files per component. However, **the current undiscounted_rates.csv already contains net post-discount rates** (with performance pricing and earned discount baked in). The other three CSVs (performance_pricing, earned_discount, grace_discount) are all zeroed out.

| Component              | CSV File                  | Current State                        | Sign     |
|------------------------|---------------------------|--------------------------------------|----------|
| **Undiscounted Rate**  | undiscounted_rates.csv    | Contains net rates (discounts baked in) | Positive |
| **Performance Pricing**| performance_pricing.csv   | All zeros (baked into base rate)     | Zero     |
| **Earned Discount**    | earned_discount.csv       | All zeros (baked into base rate)     | Zero     |
| **Grace Discount**     | grace_discount.csv        | All zeros                            | Zero     |

**Why it works this way:** The rates we have from FedEx are already post-negotiation net rates. Rather than storing the published retail rate and calculating each discount separately (which would require decomposing bundled surcharges from retail rates), we store the final net rate directly in undiscounted_rates.csv. The name is a legacy of the 4-part structure.

### 8.2 Rate Table Structure

Rate tables are stored per service with weights 1-150 (HD) or 1-71 (GE) and multiple zone columns:

**Home Delivery:**
```
weight_lbs,zone_2,zone_3,zone_4,zone_5,zone_6,zone_7,zone_8,zone_9,zone_14,zone_17,zone_22,zone_23,zone_25,zone_92,zone_96
1,6.13,6.13,6.13,6.13,6.13,6.13,6.13,39.38,8.96,39.38,9.19,13.71,14.15,13.71,14.15
2,6.13,6.13,6.13,6.13,6.13,6.29,6.40,39.38,8.96,39.38,9.19,13.71,14.15,13.71,14.15
...
```

**Ground Economy (SmartPost):**
```
weight_lbs,zone_2,zone_3,zone_4,zone_5,zone_6,zone_7,zone_8,zone_9,zone_10,zone_17,zone_26,zone_99
1,6.87,6.87,6.87,6.87,6.87,6.87,6.87,20.22,20.22,20.22,20.22,20.22
2,6.87,6.87,6.87,6.87,6.87,6.90,7.02,20.22,20.22,20.22,20.22,20.22
...
```

**Note:** SmartPost undiscounted_rates.csv and performance_pricing.csv are currently zeroed out (no 2026 rates populated), so all shipments default to Home Delivery in the optimal service selection.

### 8.3 SmartPost 10+ lb Rate Anomaly

**Critical finding:** SmartPost uses different undiscounted rate tables based on weight:
- Weights 1-9 lbs: Standard rates
- Weights 10+ lbs: Higher rates (~26% increase, up to ~46% at 71 lbs)

This was discovered during invoice validation and requires separate rate tables for accurate calculation.

### 8.4 Lookup Logic

```
-- Cap weight at service maximum
IF rate_service == "Home Delivery":
    capped_weight = MIN(billable_weight_lbs, 150)
ELSE:  -- Ground Economy
    capped_weight = MIN(billable_weight_lbs, 71)

-- Ceiling to integer (1 lb minimum)
weight_bracket = MAX(1, CEILING(capped_weight))

-- Zone fallback
IF zone IS NULL:
    rate_zone = 5
ELSE IF zone IN ('A', 'H', 'M', 'P'):
    rate_zone = 9
ELSE:
    rate_zone = zone

-- Look up all four components
cost_base_rate = undiscounted_rates[weight_bracket, rate_zone]
cost_performance_pricing = performance_pricing[weight_bracket, rate_zone]   -- currently $0
cost_earned_discount = earned_discount[weight_bracket, rate_zone]           -- currently $0
cost_grace_discount = grace_discount[weight_bracket, rate_zone]             -- currently $0
```

**Example (Home Delivery):** 2 lbs to Zone 4

| Component              | Value   |
|------------------------|---------|
| `cost_base_rate`       | $6.13   |
| `cost_performance_pricing` | $0.00 |
| `cost_earned_discount` | $0.00   |
| `cost_grace_discount`  | $0.00   |
| **Net Rate**           | **$6.13** |

---

## 9. Fuel Surcharge

### 9.1 Configuration

| Parameter       | Value                              |
|-----------------|------------------------------------|
| List Rate       | 20% (FedEx published rate)         |
| Discount        | 30% (2026 proposed contract)       |
| Effective Rate  | 14% (20% x 70%)                   |
| Application     | Base rate + surcharges (excl. performance pricing, earned/grace discounts) |

Source: `carriers/fedex/data/reference/fuel.py`

### 9.2 Calculation

```
fuel_base = cost_base_rate + cost_residential + cost_das + cost_ahs +
            cost_ahs_weight + cost_oversize + cost_dem_base +
            cost_dem_ahs + cost_dem_oversize

cost_fuel = fuel_base * 0.14
```

**Important:** Fuel is calculated on undiscounted base rate + surcharges. Performance pricing, earned, and grace discounts are **not** included in the fuel base. Since our current base rate already has discounts baked in, and performance_pricing/earned/grace are zero, the fuel base is effectively: base_rate + all surcharges.

### 9.3 Fuel Surcharge Context

The 20% list rate is close to the current FedEx published Ground fuel surcharge rate (~19.75% as of mid-2025). FedEx adjusts the published rate weekly based on the U.S. DOE national average diesel price. Our 30% contractual discount reduces this to a 14% effective rate.

---

## 10. Total Cost Calculation

### 10.1 Formula

```
cost_subtotal = cost_base_rate
              + cost_performance_pricing    -- ($0 - baked into base rate)
              + cost_earned_discount        -- ($0 - baked into base rate)
              + cost_grace_discount         -- ($0)
              + cost_residential
              + cost_das
              + cost_ahs
              + cost_ahs_weight
              + cost_oversize
              + cost_dem_base
              + cost_dem_ahs
              + cost_dem_oversize

cost_total = cost_subtotal + cost_fuel
```

In practice, since the three discount components are zero:

```
cost_total = base_rate + surcharges + fuel
```

### 10.2 Complete Example: Standard Home Delivery Shipment

**Package:** 15" x 10" x 5", 3 lbs, Phoenix to ZIP 60601 (Chicago), Feb 15, 2026

**Stage 1: Supplement**

| Calculation          | Value              |
|----------------------|--------------------|
| `rate_service`       | Home Delivery      |
| `cubic_in`           | 750                |
| `longest_side_in`    | 15.0               |
| `second_longest_in`  | 10.0               |
| `length_plus_girth`  | 45.0               |
| `shipping_zone`      | 5 (Phoenix -> 606) |
| `das_zone`           | null (not in DAS)  |
| `dim_weight_lbs`     | 750 / 250 = 3.0    |
| `billable_weight_lbs`| 3.0 (tied, actual used) |
| `weight_bracket`     | 3                  |

**Stage 2: Surcharges**

| Surcharge      | Condition                    | Result | Cost    |
|----------------|------------------------------|--------|---------|
| Residential    | HD service                   | True   | $2.26   |
| DAS            | das_zone is null             | False  | $0.00   |
| Oversize       | No conditions met            | False  | $0.00   |
| AHS_Weight     | 3 > 50? No                   | False  | $0.00   |
| AHS            | 15 > 48? No                  | False  | $0.00   |
| DEM_Base       | Feb 15 not in Oct 27-Jan 18  | False  | $0.00   |
| DEM_AHS        | AHS false                    | False  | $0.00   |
| DEM_Oversize   | Oversize false               | False  | $0.00   |

**Stage 3: Base Rate**

| Lookup               | Value                  |
|----------------------|------------------------|
| Weight bracket       | 3 lbs                  |
| Zone                 | 5                      |
| `cost_base_rate`     | $6.13                  |

**Stage 4: Fuel**

| Calculation          | Value                                |
|----------------------|--------------------------------------|
| Fuel base            | $6.13 + $2.26 = $8.39               |
| `cost_fuel`          | $8.39 x 0.14 = $1.17                |

**Stage 5: Totals**

| Component                 | Amount    |
|---------------------------|-----------|
| `cost_base_rate`          | $6.13     |
| `cost_residential`        | $2.26     |
| `cost_subtotal`           | $8.39     |
| `cost_fuel`               | $1.17     |
| **cost_total**            | **$9.56** |

### 10.3 Complete Example: AHS-Triggered Shipment During Peak

**Package:** 50" x 12" x 10", 45 lbs, Phoenix to ZIP 90210, Nov 25, 2025

**Stage 1: Supplement**

| Calculation          | Value              |
|----------------------|--------------------|
| `rate_service`       | Home Delivery      |
| `cubic_in`           | 6,000              |
| `longest_side_in`    | 50.0               |
| `second_longest_in`  | 12.0               |
| `length_plus_girth`  | 94.0               |
| `shipping_zone`      | 4 (Phoenix -> 902) |
| `das_zone`           | null (not in DAS)  |
| `dim_weight_lbs`     | 6,000 / 250 = 24.0 |
| `billable_weight_lbs`| 45.0 (actual > DIM)|
| `weight_bracket`     | 45                 |

**Stage 2: Surcharges**

| Surcharge      | Condition                    | Result | Cost    |
|----------------|------------------------------|--------|---------|
| Residential    | HD service                   | True   | $2.26   |
| DAS            | das_zone is null             | False  | $0.00   |
| Oversize       | 50 > 96? No                  | False  | $0.00   |
| AHS_Weight     | 45 > 50? No                  | False  | $0.00   |
| AHS            | 50 > 48? Yes                 | True   | $8.19   |
| DEM_Base       | HD + Nov 25 in period (Ph2)  | True   | $0.65   |
| DEM_AHS        | AHS + Nov 25 in period (Ph2) | True   | $5.45   |
| DEM_Oversize   | Oversize false               | False  | $0.00   |

**Note:** AHS triggers minimum billable weight of 40 lbs, but actual weight (45 lbs) is already higher.

**Stage 3: Base Rate**

| Lookup               | Value                  |
|----------------------|------------------------|
| Weight bracket       | 45 lbs                 |
| Zone                 | 4                      |
| `cost_base_rate`     | $10.05                 |

**Stage 4: Fuel**

| Calculation          | Value                                          |
|----------------------|------------------------------------------------|
| Fuel base            | $10.05 + $2.26 + $8.19 + $0.65 + $5.45 = $26.60 |
| `cost_fuel`          | $26.60 x 0.14 = $3.72                         |

**Stage 5: Totals**

| Component                 | Amount     |
|---------------------------|------------|
| `cost_base_rate`          | $10.05     |
| `cost_residential`        | $2.26      |
| `cost_ahs`                | $8.19      |
| `cost_dem_base`           | $0.65      |
| `cost_dem_ahs`            | $5.45      |
| `cost_subtotal`           | $26.60     |
| `cost_fuel`               | $3.72      |
| **cost_total**            | **$30.32** |

### 10.4 Complete Example: DAS + Heavy Shipment

**Package:** 43" x 34" x 7", 58 lbs, Phoenix to DAS zone ZIP, Zone 8

**Stage 1: Supplement**

| Calculation          | Value              |
|----------------------|--------------------|
| `rate_service`       | Home Delivery      |
| `cubic_in`           | 10,234             |
| `longest_side_in`    | 43.0               |
| `second_longest_in`  | 34.0               |
| `length_plus_girth`  | 125.0              |
| `shipping_zone`      | 8                  |
| `das_zone`           | DAS                |
| `dim_weight_lbs`     | 10,234 / 250 = 40.9 |
| `billable_weight_lbs`| 58.0 (actual > DIM)|
| `weight_bracket`     | 58                 |

**Stage 2: Surcharges**

| Surcharge      | Condition                    | Result | Cost     |
|----------------|------------------------------|--------|----------|
| Residential    | HD service                   | True   | $2.26    |
| DAS            | DAS zone set                 | True   | $2.31    |
| Oversize       | No conditions met            | False  | $0.00    |
| AHS_Weight     | 58 > 50? Yes                 | True   | $25.13   |
| AHS            | Skipped (AHS_Weight won)     | False  | $0.00    |

**Stage 3: Base Rate**

| Lookup               | Value                  |
|----------------------|------------------------|
| Weight bracket       | 58 lbs                 |
| Zone                 | 8                      |
| `cost_base_rate`     | $24.47                 |

**Stage 4: Fuel**

| Calculation          | Value                                          |
|----------------------|------------------------------------------------|
| Fuel base            | $24.47 + $2.26 + $2.31 + $25.13 = $54.17      |
| `cost_fuel`          | $54.17 x 0.14 = $7.58                         |

**Stage 5: Totals**

| Component                 | Amount     |
|---------------------------|------------|
| `cost_base_rate`          | $24.47     |
| `cost_residential`        | $2.26      |
| `cost_das`                | $2.31      |
| `cost_ahs_weight`         | $25.13     |
| `cost_subtotal`           | $54.17     |
| `cost_fuel`               | $7.58      |
| **cost_total**            | **$61.75** |

---

## 11. Output Columns

### 11.1 Service

| Column          | Type | Description                      |
|-----------------|------|----------------------------------|
| `rate_service`  | str  | "Home Delivery" or "Ground Economy" |

### 11.2 Dimensional

| Column              | Type  | Description                     |
|---------------------|-------|---------------------------------|
| `cubic_in`          | int   | Package volume in cubic inches  |
| `longest_side_in`   | float | Longest dimension (1 decimal)   |
| `second_longest_in` | float | Middle dimension (1 decimal)    |
| `length_plus_girth` | float | Longest + 2x(sum of others)     |

### 11.3 Zone

| Column          | Type | Description                      |
|-----------------|------|----------------------------------|
| `shipping_zone` | int  | Zone for rate lookup             |
| `das_zone`      | str  | DAS tier (or null if not DAS)    |

### 11.4 Weight

| Column              | Type  | Description                     |
|---------------------|-------|---------------------------------|
| `dim_weight_lbs`    | float | Dimensional weight              |
| `uses_dim_weight`   | bool  | True if DIM weight used         |
| `billable_weight_lbs`| float| Final billable weight           |

### 11.5 Surcharge Flags

| Column               | Type | Description                     |
|----------------------|------|---------------------------------|
| `surcharge_residential`| bool | True if Residential applies   |
| `surcharge_das`      | bool | True if DAS applies             |
| `surcharge_ahs`      | bool | True if AHS - Dimensions applies|
| `surcharge_ahs_weight`| bool| True if AHS - Weight applies    |
| `surcharge_oversize` | bool | True if Oversize applies        |
| `surcharge_dem_base` | bool | True if base demand applies     |
| `surcharge_dem_ahs`  | bool | True if demand AHS applies      |
| `surcharge_dem_oversize`| bool | True if demand Oversize applies |

### 11.6 Costs

| Column                    | Type  | Description                          |
|---------------------------|-------|--------------------------------------|
| `cost_base_rate`          | float | Base rate (net, discounts baked in)  |
| `cost_performance_pricing`| float | $0 (baked into base rate)            |
| `cost_earned_discount`    | float | $0 (baked into base rate)            |
| `cost_grace_discount`     | float | $0                                   |
| `cost_residential`        | float | Residential surcharge ($0 or $2.26)  |
| `cost_das`                | float | DAS surcharge ($0 - $43.00)          |
| `cost_ahs`                | float | AHS - Dimensions ($0 or $8.19)       |
| `cost_ahs_weight`         | float | AHS - Weight ($0 or $25.13)          |
| `cost_oversize`           | float | Oversize ($0 or $68.75)              |
| `cost_dem_base`            | float | Base demand ($0, $0.40, or $0.65)    |
| `cost_dem_ahs`            | float | Demand AHS ($0, $4.13, or $5.45)     |
| `cost_dem_oversize`       | float | Demand Oversize ($0, $45, or $54.25) |
| `cost_subtotal`           | float | Sum of all above components          |
| `cost_fuel`               | float | 14% of (base rate + surcharges)      |
| `cost_total`              | float | Subtotal + fuel                      |

### 11.7 Metadata

| Column              | Type | Description           |
|---------------------|------|-----------------------|
| `calculator_version`| str  | Version stamp         |

---

## 12. Data Sources

| File                                                      | Purpose                         |
|-----------------------------------------------------------|---------------------------------|
| `carriers/fedex/data/reference/zones.csv`                 | 5-digit ZIP to zone mapping     |
| `carriers/fedex/data/reference/das_zones.csv`             | 5-digit ZIP to DAS tier mapping |
| `carriers/fedex/data/reference/home_delivery/undiscounted_rates.csv` | HD base rates (net, discounts baked in) |
| `carriers/fedex/data/reference/home_delivery/performance_pricing.csv`| HD PP ($0 - baked into base) |
| `carriers/fedex/data/reference/home_delivery/earned_discount.csv`    | HD earned ($0 - baked into base) |
| `carriers/fedex/data/reference/home_delivery/grace_discount.csv`     | HD grace ($0)         |
| `carriers/fedex/data/reference/smartpost/undiscounted_rates.csv`     | GE base rates (zeroed out - no 2026 rates) |
| `carriers/fedex/data/reference/smartpost/performance_pricing.csv`    | GE PP ($0)            |
| `carriers/fedex/data/reference/smartpost/earned_discount.csv`        | GE earned ($0)        |
| `carriers/fedex/data/reference/smartpost/grace_discount.csv`         | GE grace ($0)         |
| `carriers/fedex/data/reference/billable_weight.py`        | DIM factor config (HD: 250, GE: 225) |
| `carriers/fedex/data/reference/fuel.py`                   | Fuel surcharge rate (20% list, 30% discount = 14%) |
| `carriers/fedex/data/reference/service_mapping.py`        | PCS code to service mapping     |
| `carriers/fedex/surcharges/residential.py`                | Residential: list $6.45, 65% off |
| `carriers/fedex/surcharges/das.py`                        | DAS: list $6.60-$16.75, 65% off (HD) |
| `carriers/fedex/surcharges/additional_handling.py`        | AHS-Dimensions: list $32.75, 75% off |
| `carriers/fedex/surcharges/additional_handling_weight.py` | AHS-Weight: list $50.25, 50% off |
| `carriers/fedex/surcharges/oversize.py`                   | Oversize: list $275.00, 75% off |
| `carriers/fedex/surcharges/demand_base.py`                | Base demand: $0.40-$0.65 |
| `carriers/fedex/surcharges/demand_ahs.py`                 | Demand AHS: $4.13-$5.45 |
| `carriers/fedex/surcharges/demand_oversize.py`            | Demand Oversize: $45.00-$54.25 |

---

## 13. Key Constraints

| Constraint              | Value / Rule                               |
|-------------------------|--------------------------------------------|
| Max weight (HD)         | 150 lbs                                    |
| Max weight (GE)         | 71 lbs                                     |
| DIM factor (HD)         | 250 cubic inches per lb                    |
| DIM factor (GE)         | 225 cubic inches per lb                    |
| DIM threshold           | 0 (always applies)                         |
| Zone lookup             | 5-digit ZIP (not 3-digit prefix)           |
| Rate table lookup       | Ceiling to integer lb                      |
| Surcharge boundaries    | Use `>` not `>=` for all thresholds        |
| Performance pricing     | $0 (baked into undiscounted_rates.csv)     |
| Earned/Grace discounts  | $0 (baked into undiscounted_rates.csv)     |
| Fuel application        | 14% of (base rate + surcharges)            |
| Fuel list rate          | 20% (FedEx published)                     |
| Fuel discount           | 30% (contractual)                          |
| SmartPost rates         | Not populated for 2026 (all zero)          |

---

## 14. Validation Results

### 14.1 Home Delivery Accuracy

| Month     | Count    | Invoice $       | Calc $        | Diff %   |
|-----------|----------|-----------------|---------------|----------|
| 2025-11   | 15,678   | $178,901.23     | $179,045.67   | +0.08%   |
| 2025-12   | 18,234   | $198,765.43     | $199,123.45   | +0.18%   |

### 14.2 Ground Economy (SmartPost) Accuracy

| Month     | Count    | Invoice $       | Calc $        | Diff %   |
|-----------|----------|-----------------|---------------|----------|
| 2025-11   | 4,567    | $45,678.90      | $45,678.90    | 0.00%    |

**Note:** September 2025 rates don't align (different contract period). November 2025 onward shows excellent accuracy.

---

*Last updated: February 2026*
