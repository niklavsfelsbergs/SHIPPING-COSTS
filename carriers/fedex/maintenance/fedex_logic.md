# FedEx Cost Calculation Logic

The entry point is `calculate_costs(df)` which runs two stages: **supplement** (enrich data) then **calculate** (apply costs).

---

## Stage 1: Supplement Shipments

### 1. Service Type Mapping (`service_mapping.py`)
- Maps PCS shipping provider codes to one of two services:
  - **Home Delivery** — standard residential (codes like `FXEHD`, `FXE2D`, etc.)
  - **Ground Economy** — SmartPost (codes `FXESPPS`, `FXEGRD`, `FXESPPSL`)
- Unknown codes default to Home Delivery

### 2. Calculated Dimensions
- `cubic_in` = L x W x H (rounded to whole number)
- `longest_side_in` = max(L, W, H) (rounded to 1 decimal)
- `second_longest_in` = middle dimension (rounded to 1 decimal)
- `length_plus_girth` = longest + 2 x (sum of other two) (rounded to 1 decimal)

### 3. Zone Lookup (origin-dependent, 3-tier fallback)
- `zones.csv` has separate `phx_zone` and `cmh_zone` columns — zone depends on whether origin is Phoenix or Columbus
- Fallback: exact 5-digit ZIP match → state mode (most common zone for state) → default zone 5

### 4. DAS Zone Lookup (destination-only)
- `das_zones.csv` maps ZIP codes to DAS tiers (`DAS`, `DAS_EXTENDED`, `DAS_REMOTE`, `DAS_ALASKA`, `DAS_HAWAII`)
- Separate columns for Home Delivery vs SmartPost (tiers can differ by service)

### 5. Billable Weight
- Dimensional weight = `cubic_in` / dim factor
  - Home Delivery dim factor: **250**
  - Ground Economy dim factor: **225**
- `billable_weight_lbs` = max(actual weight, dim weight)
- No threshold — dim weight is always considered

---

## Stage 2: Calculate Costs

### Phase 1: Base Surcharges (applied in parallel, with exclusivity)

Five standalone/exclusive surcharges, processed in this order:

| Surcharge | Conditions | Net Cost | Exclusivity |
|-----------|-----------|----------|-------------|
| **DAS** | ZIP in DAS zone | Varies by tier and service (see below) | Standalone |
| **Residential** | All Home Delivery shipments | $6.45 x (1 - 0.65) = **$2.26** | Standalone |
| **Oversize** | HD only: longest > 96" OR L+G > 130" OR volume > 17,280 cu in OR weight > 110 lbs | $275.00 x (1 - 0.75) = **$68.75** | `dimensional` group, priority **1** (wins) |
| **AHS Weight** | Actual weight > 50 lbs | $50.25 x (1 - 0.50) = **$25.13** | `dimensional` group, priority **2** |
| **AHS Dimensions** | HD only: longest > 48" OR 2nd longest > 30.3" OR L+G > 106" | $32.75 x (1 - 0.75) = **$8.19** | `dimensional` group, priority **3** |

**Exclusivity rule**: Within the `dimensional` group, only the highest-priority (lowest number) surcharge that matches wins. So Oversize beats AHS Weight beats AHS Dimensions.

**DAS pricing:**

| Tier | Home Delivery (65% off) | Ground Economy |
|------|------------------------|----------------|
| DAS | $6.60 x 0.35 = **$2.31** | $6.60 x 0.50 = **$3.30** |
| DAS Extended | $8.80 x 0.35 = **$3.08** | $8.80 x 0.50 = **$4.40** |
| DAS Remote | $16.75 x 0.35 = **$5.86** | N/A |
| DAS Alaska | **$43.00** (net) | **$8.80** (no discount) |
| DAS Hawaii | **$14.50** (net) | **$8.80** (no discount) |

### Phase 2: Dependent (Demand/Peak) Surcharges

These reference flags set in Phase 1:

| Surcharge | Condition | Phase 1 | Phase 2 |
|-----------|-----------|---------|---------|
| **DEM_Base** | HD only, Oct 27 - Jan 18 | **$0.40** (Oct 27 - Nov 23) | **$0.65** (Nov 24 - Jan 18) |
| **DEM_AHS** | AHS or AHS_Weight flagged, Sep 29 - Jan 18 | **$4.13** (Sep 29 - Nov 23) | **$5.45** (Nov 24 - Jan 18) |
| **DEM_Oversize** | Oversize flagged, Sep 29 - Jan 18 | **$45.00** (Sep 29 - Nov 23) | **$54.25** (Nov 24 - Jan 18) |

### Phase 3: Minimum Billable Weight Adjustment

If AHS Dimensions triggered → billable weight is at least **40 lbs** (bumps up if actual/dim weight was lower).

### Phase 4: Base Rate Lookup

Rate tables are looked up by `(service, weight_bracket, zone)`:
- Weight is ceiled to the next whole pound (1 lb minimum)
- Capped at **150 lbs** (HD) or **71 lbs** (SmartPost)
- Zone fallback: null → zone 5, letter zones (A/H/M/P) → zone 9
- Four rate components are joined from separate CSV tables:
  1. **`cost_base_rate`** — undiscounted list price (positive)
  2. **`cost_performance_pricing`** — volume discount (negative)
  3. **`cost_earned_discount`** — negotiated discount (currently $0.00)
  4. **`cost_grace_discount`** — promotional discount (currently $0.00)

SmartPost has **separate** undiscounted rate tables — packages 10+ lbs use higher rates (~26% more).

### Phase 5: Subtotal

```
cost_subtotal = cost_base_rate
              + cost_performance_pricing  (negative)
              + cost_earned_discount      (currently $0)
              + cost_grace_discount       (currently $0)
              + cost_das
              + cost_residential
              + cost_oversize (or cost_ahs_weight or cost_ahs)
              + cost_dem_base
              + cost_dem_ahs
              + cost_dem_oversize
```

### Phase 6: Fuel Surcharge

```
cost_fuel = cost_base_rate x 14%
```
(List rate 20%, with 30% discount → effective 14%. Applied to **base rate only**, not surcharges or discounts.)

### Phase 7: Total

```
cost_total = cost_subtotal + cost_fuel
```

---

## Summary Formulas

For a typical Home Delivery package with no surcharges:

```
total = (undiscounted_rate + performance_pricing) + residential + (undiscounted_rate x 0.14)
```

For a large Home Delivery package during peak (Nov 24 - Jan 18):

```
total = (undiscounted_rate + performance_pricing)
      + residential ($2.26)
      + AHS ($8.19) or Oversize ($68.75)
      + DEM_Base ($0.65)
      + DEM_AHS ($5.45) or DEM_Oversize ($54.25)
      + DAS (if applicable)
      + fuel (undiscounted_rate x 14%)
```
