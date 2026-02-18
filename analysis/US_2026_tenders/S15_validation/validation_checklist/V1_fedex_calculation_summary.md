# V1: FedEx Calculator — Step-by-Step Cost Breakdown

This document walks through every step of the FedEx cost calculation, in the
exact order the calculator executes them. Each step includes the specific
numbers and formulas used, and what to validate against the 2026 contract.

Calculator version: `2026.02.18.1`
Rate tables: 2026 contract rates (baked — see Step 6)

---

## Overview: How Cost Flows

```
Raw shipment data
  |
  v
Step 1:  Service selection (HD vs SmartPost)
Step 2:  SmartPost size/weight limit enforcement
Step 3:  Zone lookup (origin-dependent)
Step 4:  DAS zone lookup
Step 5:  Dimensional weight and billable weight
Step 6:  Base rate lookup ("baked" rate from rate table)
Step 7:  Surcharges (DAS, Residential, AHS/Oversize, Demand)
Step 8:  Minimum billable weight adjustment (AHS → 40 lbs)
Step 9:  Re-lookup base rate (if weight changed in Step 8)
Step 10: Fuel surcharge
Step 11: Total assembly
Step 12: S15 earned discount adjustment (scenario-level)
  |
  v
Final cost per shipment
```

---

## Step 1: Service Selection

**What the calculator does:**
Maps the PCS shipping provider code to either "Home Delivery" or
"Ground Economy" (SmartPost).

| PCS Code               | Service          |
|------------------------|------------------|
| FXEHD                  | Home Delivery    |
| FXE2D, FXE2DXLBOR, FXE2DTBOR, FXESTDO, FXEINTECON, FXEINTPRIO, FXEPO, FXE2DSBOR, FXE2DLBOR, FXE2DMBOR, FXE2DENVOR, FXE2DPAKOR | Home Delivery |
| FXESPPS, FXEGRD        | Ground Economy   |
| FXESPPSL, FXSP         | Ground Economy   |
| Unknown codes          | Home Delivery (default) |

**What to validate:**
- [x] Confirm these PCS codes match the services we're actually shipping with
- [x] Confirm all FedEx service codes in PCS are covered

---

## Step 2: SmartPost Size/Weight Limit Enforcement

**What the calculator does:**
If a shipment is assigned to Ground Economy (SmartPost) AND any of the
following conditions are true, it is **overridden to Home Delivery**:

| Limit              | Threshold   |
|--------------------|-------------|
| Length + Girth     | > 84 inches |
| Actual weight      | > 20 lbs    |
| Longest dimension  | > 27 inches |
| 2nd longest dim    | > 17 inches |

Length + Girth = longest side + 2 × (2nd longest + 3rd longest).

**Impact:** This override affects a large portion of shipments. After
enforcement, FedEx HD handles 61% of FedEx shipments in S15 (151,819 HD
vs 98,858 SP). Before enforcement, SmartPost dominated.

**What to validate:**
- [x] Confirm these 4 limits match the FedEx SmartPost size/weight
      restrictions in the 2026 contract
- [x] Check if FedEx has additional SmartPost restrictions we haven't
      modeled (e.g., cylindrical items, fragile goods, non-machinable)
- [x] Compare our HD/SP split against FedEx invoice HD/SP split for
      the same shipments — do they agree on which packages are SmartPost?

---

## Step 3: Zone Lookup

**What the calculator does:**
Looks up the destination ZIP code in `zones.csv` to get a shipping zone.
The zone depends on the **origin** (production site):

| Production Site | Zone Column Used |
|-----------------|------------------|
| Phoenix (PHX)   | `phx_zone`       |
| Columbus (CMH)  | `cmh_zone`       |

Three-tier fallback:
1. Exact 5-digit ZIP match in `zones.csv`
2. State-level mode (most common zone for that state)
3. Default: zone 5

**Zone normalization for rate lookup:**
- Letter zones (A, H, M, P) are mapped to zone 9 (Hawaii rate)
- Null zones default to zone 5

**Reference data:** `zones.csv` — 58,772 rows (5-digit ZIP codes)

**What to validate:**
- [x] Confirm zone tables match the 2026 FedEx zone charts for both
      PHX and CMH origins
- [x] Verify that letter zones (A, H, M, P) should map to zone 9
- [x] Spot-check 10-20 ZIP codes: compare our zone vs FedEx's zone
      chart for both origins

---

## Step 4: DAS Zone Lookup

**What the calculator does:**
Looks up the destination ZIP code in `das_zones.csv` to determine if a
Delivery Area Surcharge applies. DAS tiers **differ by service**:

| DAS Tier       | Applies To |
|----------------|------------|
| DAS            | HD and/or SP (per ZIP) |
| DAS_EXTENDED   | HD and/or SP (per ZIP) |
| DAS_REMOTE     | HD only    |
| DAS_ALASKA     | HD and SP  |
| DAS_HAWAII     | HD and SP  |

A ZIP can have different DAS tiers for HD vs SP, or apply to one service
but not the other.

**Reference data:** `das_zones.csv` — 15,507 rows (only ZIPs with a DAS
surcharge). ZIPs not in this file have no DAS.

**What to validate:**
- [x] Confirm DAS zone list matches FedEx 2026 DAS zone tables
- [x] Confirm that HD and SP can have different DAS tiers for the
      same ZIP (the contract may specify this)
- [x] Spot-check 10 DAS ZIPs against FedEx's published DAS ZIP list

---

## Step 5: Dimensional Weight and Billable Weight

**What the calculator does:**

1. Compute dimensions (rounded to 1 decimal to avoid float issues):
   ```
   cubic_in         = length × width × height   (rounded to 0 decimals)
   longest_side_in  = max(L, W, H)              (rounded to 1 decimal)
   second_longest   = middle of (L, W, H)       (rounded to 1 decimal)
   length_plus_girth = longest + 2 × (sum of other two)  (rounded to 1 decimal)
   ```

2. Compute dimensional weight using service-specific DIM factors:

   | Service        | DIM Factor | Formula                        |
   |----------------|:----------:|--------------------------------|
   | Home Delivery  | 250        | dim_weight = cubic_in / 250    |
   | Ground Economy | 225        | dim_weight = cubic_in / 225    |

3. Billable weight:
   ```
   billable_weight = max(actual_weight, dim_weight)
   ```

   No minimum cubic inches threshold — DIM weight is always considered
   regardless of package size.

**What to validate:**
- [x] Confirm DIM factor 250 for Home Delivery (2026 contract)
- [x] Confirm DIM factor 225 for Ground Economy (2026 contract)
- [x] Confirm there is no minimum cubic inches threshold for DIM weight
      to apply (some carriers require packages to exceed a size before
      DIM pricing kicks in)
- [x] Confirm billable weight = max(actual, DIM) with no other rules

---

## Step 6: Base Rate Lookup (the "Baked" Rate)

**What the calculator does:**
Looks up the base rate from rate tables using:
- Service (HD or Ground Economy)
- Weight bracket = `ceil(billable_weight)`, minimum 1, integer
- Zone (from Step 3, normalized)

Weight is capped before lookup:
- HD: max 150 lbs
- Ground Economy: max 71 lbs

**Rate table structure:**

| Service        | Weight Range | Zones                                        | Rows |
|----------------|:------------:|----------------------------------------------|:----:|
| Home Delivery  | 1-150 lbs    | 2, 3, 4, 5, 6, 7, 8, 9, 14, 17, 22, 23, 25, 92, 96 | 150  |
| Ground Economy | 1-71 lbs     | 2, 3, 4, 5, 6, 7, 8, 9, 10, 17, 26, 99      | 71   |

**What "baked" means:**

The rate tables contain **net rates with Performance Pricing and Earned
Discount already applied**. The 4-part FedEx rate structure is:

```
Invoice breakdown:          What our rate table contains:
  Undiscounted list price     ─┐
  - Performance Pricing (PP)   │── All collapsed into one
  - Earned Discount            │   "baked" net rate
  - Grace Discount            ─┘
```

The separate PP, earned, and grace discount CSV files exist in the
reference data but are **all zeros**. The calculator outputs these columns
as $0.00 — the discounts are invisible because they're baked into the
base rate.

**Baked factors (what fraction of undiscounted list price the baked rate
represents):**

| Service        | PP Discount | Baked Earned | Baked Factor              |
|----------------|:-----------:|:------------:|---------------------------|
| Home Delivery  | 45%         | 18%          | 1 - 0.45 - 0.18 = **0.370** |
| Ground Economy | 45%         | 4.5%         | 1 - 0.45 - 0.045 = **0.505** |

This means:
- HD baked rate = 37.0% of the undiscounted list price
- SP baked rate = 50.5% of the undiscounted list price

To recover the undiscounted list price: `undiscounted = baked_rate / baked_factor`

**Sample rates (baked, from rate tables):**

| Weight | Zone 5 HD | Zone 5 SP | Zone 8 HD | Zone 8 SP |
|:------:|:---------:|:---------:|:---------:|:---------:|
| 1 lb   | $6.13     | $6.87     | $6.13     | $6.87     |
| 5 lb   | $7.04     | $8.23     | $8.37     | $9.49     |
| 10 lb  | $7.56     | $10.47    | $9.71     | $13.40    |
| 20 lb  | $10.35    | $14.99    | $14.14    | $21.03    |
| 50 lb  | $22.36    | $28.56    | $30.85    | $43.86    |

Note the SmartPost 10+ lb jump: SP zone 8 goes from $9.49 (9 lbs) to
$13.40 (10 lbs) — a 41% increase. This is the known "SmartPost 10+ lb
anomaly" where different rate tables apply.

**What to validate:**
- [x] **Critical:** Confirm the PP discount is 45% for both HD and SP
- [x] **Critical:** Confirm the baked earned discount is 18% for HD
- [x] **Critical:** Confirm the baked earned discount is 4.5% for SP
- [x] Confirm rate tables match the 2026 contract rate cards
      (spot-check 10-20 weight/zone combinations for each service)
- [x] Confirm the Grace Discount is 0% (not baked in) or that it IS
      baked and the baked factor should be different
- [x] Verify zones in rate tables match what FedEx uses (HD has 15
      zone columns, SP has 12 — are these the correct zone sets?)
- [x] Confirm HD max weight is 150 lbs and SP max weight is 70 lbs

**Risk:** The baked factors (0.370 HD, 0.505 SP) are the foundation of
the undiscounted spend calculation for the $5M threshold. If PP is not
45% or baked earned is not 18%/4.5%, the entire undiscounted math is
wrong.

We should get the list prices and compare once more against those.

---

## Step 7: Surcharges

Surcharges are applied in two phases. Phase 1 (BASE) surcharges are
evaluated independently. Phase 2 (DEPENDENT) surcharges reference flags
set in Phase 1.

Within Phase 1, the "dimensional" exclusivity group ensures that at most
ONE of Oversize, AHS Weight, or AHS is charged per shipment (the
highest-priority match wins).

### 7a. DAS — Delivery Area Surcharge

| Tier          | HD List | HD Discount | HD Net    | SP List | SP Discount | SP Net    |
|---------------|:-------:|:-----------:|:---------:|:-------:|:-----------:|:---------:|
| DAS           | $6.60   | 65%         | **$2.31** | $6.60   | 50%         | **$3.30** |
| DAS_EXTENDED  | $8.80   | 65%         | **$3.08** | $8.80   | 50%         | **$4.40** |
| DAS_REMOTE    | $16.75  | 65%         | **$5.86** | N/A     | N/A         | N/A       |
| DAS_ALASKA    | —       | —           | **$43.00**| $8.80   | 0%          | **$8.80** |
| DAS_HAWAII    | —       | —           | **$14.50**| $8.80   | 0%          | **$8.80** |

Alaska and Hawaii HD: net price stored directly (list price not broken
out). SP Alaska/Hawaii: no discount applied.

**Trigger:** `das_zone` is not null (ZIP is in `das_zones.csv`).

**What to validate:**
- [x] Confirm list prices: DAS $6.60, DAS_EXTENDED $8.80, DAS_REMOTE $16.75
- [x] Confirm HD discount is 65% for DAS/EXTENDED/REMOTE
- [x] Confirm SP discount is 50% for DAS/EXTENDED
- [x] Confirm Alaska HD net $43.00 and Hawaii HD net $14.50
- [x] Confirm SP Alaska/Hawaii rate $8.80 with 0% discount
- [x] Confirm DAS_REMOTE does not apply to SmartPost

### 7b. Residential Surcharge

| Service        | List Price | Discount | Net Cost    |
|----------------|:----------:|:--------:|:-----------:|
| Home Delivery  | $6.45      | 65%      | **$2.2575** |
| Ground Economy | N/A        | N/A      | $0.00       |

**Trigger:** `rate_service == "Home Delivery"` — applied to **100%** of
HD shipments. Ground Economy is exempt.

**What to validate:**
- [x] Confirm Residential list price $6.45
- [x] Confirm Residential discount 65%
- [x] Confirm Residential applies to ALL Home Delivery shipments
      (not conditionally based on address type)
- [x] Confirm Ground Economy is exempt from Residential

### 7c. Dimensional Surcharges (Exclusivity Group)

These three surcharges compete. Only the highest-priority match is
charged. Priority 1 (Oversize) beats Priority 2 (AHS Weight) beats
Priority 3 (AHS Dimensions).

#### Oversize — Priority 1

| | |
|---|---|
| List price | $275.00 |
| Discount   | 75% |
| **Net cost** | **$68.75** |
| Applies to | Home Delivery only (Ground Economy exempt) |

**Trigger (any of):**
- Longest side > 96 inches
- Length + Girth > 130 inches
- Cubic inches > 17,280
- Actual weight > 110 lbs

**What to validate:**
- [x] Confirm Oversize list $275.00 and discount 75%
- [x] Confirm all 4 trigger thresholds
- [x] Confirm Ground Economy is exempt

#### AHS Weight — Priority 2

| | |
|---|---|
| List price | $50.25 |
| Discount   | 50% |
| **Net cost** | **$25.125** |
| Applies to | Both HD and Ground Economy |

**Trigger:** Actual weight > 50 lbs

**What to validate:**
- [x] Confirm AHS Weight list $50.25 and discount 50%
- [x] Confirm threshold is 50 lbs (not 51 lbs, not billable weight)
- [x] Confirm it applies to both services

#### AHS Dimensions — Priority 3

| | |
|---|---|
| List price | $32.75 |
| Discount   | 75% |
| **Net cost** | **$8.1875** |
| Applies to | Home Delivery only (Ground Economy exempt) |

**Trigger (any of):**
- Longest side > 48 inches
- Second longest side > 30.3 inches (borderline 30.3" excluded)
- Length + Girth > 106 inches (borderline 105-106" excluded)

**Side effect:** When AHS Dimensions triggers, **billable weight is
raised to a minimum of 40 lbs** (Step 8). This causes a base rate
re-lookup at the higher weight.

**What to validate:**
- [x] Confirm AHS Dimensions list $32.75 and discount 75%
- [x] Confirm all 3 trigger thresholds (especially the 30.3" and 106"
      borderline handling)
- [x] Confirm 40 lb minimum billable weight when AHS triggers
- [x] Confirm Ground Economy is exempt

#### Exclusivity Example

| Package                              | Oversize? | AHS Wt? | AHS Dim? | Charged     |
|--------------------------------------|:---------:|:-------:|:--------:|-------------|
| Longest 100", weight 30 lbs         | Yes       | —       | —        | Oversize $68.75 |
| Weight 60 lbs, longest 40"          | No        | Yes     | —        | AHS Weight $25.13 |
| Longest 50", weight 10 lbs          | No        | No      | Yes      | AHS Dim $8.19 + 40lb min |
| Weight 60 lbs AND longest 50"       | No        | Yes     | blocked  | AHS Weight $25.13 (wins) |
| Longest 100" AND weight 120 lbs     | Yes       | blocked | blocked  | Oversize $68.75 (wins) |

**What to validate:**
- [x] Confirm only one dimensional surcharge can be charged per shipment
- [x] Confirm the priority order (Oversize > AHS Weight > AHS Dimensions)

### 7d. Demand Surcharges

Applied during peak periods. Phase 2 (DEPENDENT) surcharges reference
the dimensional surcharge flags from Phase 1.

#### Demand Base

| Period                  | Dates              | Cost     |
|-------------------------|--------------------|----------|
| Phase 1                 | Oct 27 — Nov 23    | **$0.40** |
| Phase 2                 | Nov 24 — Jan 18    | **$0.65** |

Applies to **Home Delivery only**. Ground Economy is exempt.

#### Demand AHS

| Period                  | Dates              | Cost     |
|-------------------------|--------------------|----------|
| Phase 1                 | Sep 29 — Nov 23    | **$4.13** |
| Phase 2                 | Nov 24 — Jan 18    | **$5.45** |

Applies when `surcharge_ahs = True` OR `surcharge_ahs_weight = True`.
(Only one can be true due to exclusivity, but DEM_AHS fires for either.)

#### Demand Oversize

| Period                  | Dates              | Cost      |
|-------------------------|--------------------|-----------|
| Phase 1                 | Sep 29 — Nov 23    | **$45.00** |
| Phase 2                 | Nov 24 — Jan 18    | **$54.25** |

Applies when `surcharge_oversize = True`.

**What to validate:**
- [x] Confirm all demand surcharge prices and date ranges
- [x] Confirm Ground Economy is exempt from Demand Base
- [x] Confirm Demand AHS fires for both AHS Dimensions and AHS Weight
- [x] Confirm Demand Oversize fires only for Oversize (not AHS)

#### Not Modeled: Demand Residential

FedEx invoices include a `Demand Residential` charge, but it is **not
implemented in the calculator**. This is a known gap — FedEx charges
this during peak periods on HD residential shipments.

**What to validate:**
- [x] Determine the Demand Residential surcharge price from the contract
- [x] Estimate impact: it would apply to all HD shipments in the demand
      period. Even a small per-shipment charge across 151K HD shipments
      adds up.

---

## Step 8: Minimum Billable Weight Adjustment

**What the calculator does:**
If `surcharge_ahs` (AHS Dimensions) triggered in Step 7c, the billable
weight is raised to a minimum of 40 lbs:

```
if surcharge_ahs == True:
    billable_weight = max(billable_weight, 40)
```

This causes the base rate to be re-looked up at the higher weight bracket
in Step 9. For a package that originally weighed 5 lbs, triggering AHS
means it's now rated at 40 lbs — a significant cost increase on top of
the $8.19 surcharge.

**What to validate:**
- [x] Confirm AHS minimum billable weight is 40 lbs (not 50, not 30)
- [x] Confirm this applies only to AHS Dimensions, not AHS Weight or
      Oversize

---

## Step 9: Base Rate Re-lookup

If the billable weight changed in Step 8, the base rate is re-looked up
using the new weight bracket. The lookup uses the same rate table and
zone from Step 6, just with the updated weight.

This is handled implicitly — Step 8 modifies `billable_weight_lbs` before
the rate lookup in the calculate() flow. The rate lookup in Step 6
happens after the min billable weight adjustment.

*(Correction: in the actual code, the order is: surcharges → min billable
weight → rate lookup. So the rate lookup already uses the adjusted weight.
There is no separate "re-lookup" step — it's one lookup with the final
billable weight.)*

---

## Step 10: Fuel Surcharge

**What the calculator does:**

```
cost_fuel = cost_base_rate × FUEL_RATE
```

| Parameter  | Value                          |
|------------|--------------------------------|
| List rate  | 20% (FedEx published rate)     |
| Discount   | 30% off                        |
| **Effective rate** | **14%** (0.20 × 0.70) |

**Fuel base:** Applied to `cost_base_rate` only — the baked net rate
from the rate table. Surcharges, PP discounts, and earned discounts are
**excluded** from the fuel calculation base.

Last updated: 2026-01-27.

**What to validate:**
- [x] Confirm FedEx published fuel rate is 20%
- [x] Confirm our fuel discount is 30%
- [x] **Critical:** Confirm fuel is applied to base rate only (not to
      base + surcharges, not to undiscounted rate). This significantly
      affects the total. The fuel.py `APPLICATION` field says
      "BASE_PLUS_SURCHARGES" but the code applies it to base rate only.
- [x] Confirm the fuel rate is current (it changes weekly for FedEx
      standard, but our contract may have a fixed rate)

---

## Step 11: Total Assembly

**What the calculator does:**

```
cost_subtotal = cost_base_rate
              + cost_performance_pricing      ($0.00 — baked)
              + cost_earned_discount          ($0.00 — baked)
              + cost_grace_discount           ($0.00 — baked)
              + cost_das
              + cost_residential
              + cost_oversize
              + cost_ahs_weight
              + cost_ahs
              + cost_dem_base
              + cost_dem_ahs
              + cost_dem_oversize

cost_total = cost_subtotal + cost_fuel
```

Rounded to 2 decimal places.

**What to validate:**
- [x] Confirm all cost components are included (no missing invoice
      charge categories)
- [x] Known gap: Demand Residential is not included (see Step 7d)
- [x] Check if FedEx has any other charges not modeled (e.g., Address
      Correction, Unauthorized surcharges, technology fees)

---

## Step 12: S15 Earned Discount Adjustment

**What the calculator does (scenario-level, not in the base calculator):**

The rate tables have earned discounts baked in at 18% HD / 4.5% SP.
For S15, we target 16% HD / 4% SP earned. The adjustment:

```
HD multiplier = (1 - 0.45 - 0.16) / 0.370 = 0.39 / 0.37 = 1.0541
SP multiplier = (1 - 0.45 - 0.04) / 0.505 = 0.51 / 0.505 = 1.0099

delta = base_rate × (multiplier - 1) × (1 + fuel_rate)

new_cost_total = old_cost_total + delta
```

This makes HD costs 5.4% higher and SP costs 1.0% higher than the baked
rate, reflecting the less generous earned discount tier.

**Example:** A 5 lb HD shipment to zone 5 with baked rate $7.04:
```
delta = $7.04 × (1.0541 - 1) × (1 + 0.14) = $7.04 × 0.0541 × 1.14 = $0.43
adjusted_cost_total = original + $0.43
```

**What to validate:**
- [x] Confirm S15 targets 16% HD earned and 4% SP earned
- [x] Confirm these are the correct earned discount tiers for the
      expected FedEx undiscounted spend ($5.1M+)
- [x] Confirm the adjustment formula is mathematically correct
      (it preserves the relationship: adjusted_base = undiscounted ×
      (1 - PP) × (1 - target_earned))

---

## Summary: Complete Cost Formula

For a Home Delivery shipment (the majority in S15):

```
1. billable_weight = max(actual_weight, cubic_in / 250)
2. if AHS triggers: billable_weight = max(billable_weight, 40)
3. weight_bracket = ceil(billable_weight), capped at 150
4. base_rate = HD_rate_table[weight_bracket][zone]          (baked net rate)
5. surcharges = DAS + Residential($2.26) + dimensional_surcharge + demand
6. fuel = base_rate × 0.14
7. cost_total = base_rate + surcharges + fuel
8. S15 adjustment: cost_total += base_rate × 0.0541 × 1.14  (HD earned 16%)
```

For a Ground Economy (SmartPost) shipment:

```
1. if size/weight limits exceeded → reclassify as HD (go to HD formula)
2. billable_weight = max(actual_weight, cubic_in / 225)
3. weight_bracket = ceil(billable_weight), capped at 71
4. base_rate = SP_rate_table[weight_bracket][zone]          (baked net rate)
5. surcharges = DAS + AHS_Weight(if >50lbs)                 (no Res, no AHS Dim, no Oversize)
6. fuel = base_rate × 0.14
7. cost_total = base_rate + surcharges + fuel
8. S15 adjustment: cost_total += base_rate × 0.0099 × 1.14  (SP earned 4%)
```

---

## Validation Checklist Summary

### Critical (wrong = entire S15 cost model is off)

| # | Item                                        | Step  | Status |
|---|---------------------------------------------|:----: |:------:|
| 1 | PP discount = 45% for HD and SP             | 6     | [x]    |
| 2 | Baked earned = 18% for HD                   | 6     | [x]    |
| 3 | Baked earned = 4.5% for SP                  | 6     | [x]    |
| 4 | Rate tables match 2026 contract             | 6     | [x]    |
| 5 | SmartPost size/weight limits correct         | 2    | [x]    |
| 6 | Fuel rate 14% (20% list × 70%)             | 10     | [x]    |
| 7 | Fuel applied to base rate only              | 10    | [x]    |
| 8 | S15 earned tiers: 16% HD, 4% SP            | 12     | [x]    |

### Important (wrong = cost per shipment is off for affected packages)

| # | Item                                        | Step | Status |
|---|---------------------------------------------|:----:|:------:|
| 9 | DIM factor: 250 HD, 225 SP                 | 5    | [x]    |
| 10| Zone tables match FedEx 2026 zone charts    | 3    | [x]    |
| 11| DAS zone list and tier pricing correct       | 4,7a | [x]    |
| 12| Residential list $6.45, discount 65%        | 7b   | [x]    |
| 13| AHS Dimensions: $32.75 list, 75% off, thresholds | 7c | [x] |
| 14| AHS Weight: $50.25 list, 50% off, >50 lbs  | 7c   | [x]    |
| 15| Oversize: $275 list, 75% off, thresholds    | 7c   | [x]    |
| 16| AHS min billable weight = 40 lbs            | 8    | [x]    |
| 17| Demand surcharge prices and date ranges      | 7d   | [x]    |

### Gaps (known items not modeled)

| # | Item                                        | Impact |
|---|---------------------------------------------|--------|
| 18| Demand Residential surcharge not modeled     | All HD shipments in peak period |
| 19| Grace Discount assumed 0% (not baked)       | If grace exists, baked factor is wrong |
| 20| Residential applied to 100% of HD           | If some HD goes to commercial, cost overstated |

---

*Source: `carriers/fedex/calculate_costs.py` (v2026.02.18.1)*
*Reference data: `carriers/fedex/data/reference/`*
*S15 adjustment: `analysis/US_2026_tenders/optimization/fedex_adjustment.py`*
