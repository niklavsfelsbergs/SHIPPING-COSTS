# Maersk US Cost Calculation Logic

The entry point is `calculate_costs(df)` which runs two stages: **supplement** (enrich data) then **calculate** (apply costs).

**Status:** Early development. Used for carrier cost optimization analysis, not yet validated against invoices.

---

## Stage 1: Supplement Shipments

### 1. Calculated Dimensions
- `cubic_in` = L x W x H (rounded to whole number)
- `longest_side_in` = max(L, W, H) (rounded to 1 decimal)
- `second_longest_in` = middle dimension (rounded to 1 decimal)

Dimensions are rounded to 1 decimal place before threshold comparisons to prevent floating-point precision issues.

Note: No `length_plus_girth` calculation — Maersk US doesn't use girth-based thresholds.

### 2. Zone Lookup (single origin, 3-tier fallback)
- **Lookup key:** 3-digit ZIP prefix
- **Single origin:** Columbus only — no origin-dependent logic
- Zones: **1-9**
- Fallback: exact 3-digit ZIP prefix match -> mode zone (most common across all entries) -> default zone 5

### 3. Billable Weight
- Dimensional weight = `cubic_in` / **166** (industry standard DIM factor)
- DIM threshold: **1,728 cubic inches** (1 cubic foot) — DIM weight only considered above this
- `billable_weight_lbs` = max(actual weight, dim weight) when cubic_in > 1,728, otherwise just actual weight
- No rounding — continuous value used for rate bracket lookup
- **Overweight handling:** Packages > 70 lbs capped at 70 lbs during calculation, original weight restored after

---

## Stage 2: Calculate Costs

### Phase 1: Base Surcharges

Four surcharges across one exclusivity group plus two standalone:

**"length" exclusivity group** (only highest-priority match wins):

| Surcharge | Conditions | List | Discount | Net Cost | Priority |
|-----------|-----------|------|----------|----------|----------|
| **NSL2** | longest > 30" | $4.00 | 0% | **$4.00** | 1 (wins) |
| **NSL1** | longest > 21" | $4.00 | 0% | **$4.00** | 2 |

**Standalone (no exclusivity):**

| Surcharge | Conditions | List | Discount | Net Cost |
|-----------|-----------|------|----------|----------|
| **NSD** | cubic_in > 3,456 (2 cubic feet) | $18.00 | 0% | **$18.00** |
| **PICKUP** | Always applies (all packages) | $0.04/lb | 0% | **$0.04 x ceil(billable_weight)** |

NSD can stack with NSL surcharges. PICKUP applies to every shipment.

No min billable weight side effects on any surcharge.

### Phase 2: Dependent Surcharges

None for Maersk US.

### Phase 3: Base Rate Lookup

Rate card (`base_rates.csv`) is in long format with weight brackets x zones (1-9):
```
weight_lbs_lower, weight_lbs_upper, zone, rate
```

Lookup: match on `shipping_zone = zone` and `weight_lbs_lower < billable_weight_lbs <= weight_lbs_upper`.

Max weight: **70 lbs**.

### Phase 4: Subtotal & Total

```
cost_subtotal = cost_base
              + cost_nsl1 (or cost_nsl2)
              + cost_nsd
              + cost_pickup
```

**Maersk US has no fuel surcharge.** Rates are all-inclusive.

```
cost_total = cost_subtotal
```

---

## Summary Formulas

For a typical small package:

```
total = base_rate + pickup_fee
```

For a large, heavy package:

```
total = base_rate + NSL2 ($4.00) + NSD ($18.00) + pickup_fee
```

Pickup fee example for a 5 lb package: `ceil(5) x $0.04 = $0.20`

---

## Special Logic

### Pickup Fee (Per-Pound Surcharge)
PICKUP is weight-based: **$0.04 per billable pound** (ceiled to nearest whole pound). It applies to every shipment.

### All-US Optimization Analysis
Maersk US has a dual-loader structure:
- `load_pcs_shipments()` — Maersk US shipments only (for accuracy validation)
- `load_pcs_shipments_all_us()` — ALL US shipments from all carriers

This enables "what if" analysis: what would total shipping costs be if Maersk US handled all volume?

### Overweight Capping
Packages over 70 lbs are capped at 70 lbs during calculation (uses 70 lb rate as best estimate), then original weight is restored for reporting.

### No Demand/Peak Surcharges
Maersk US has no seasonal demand surcharges.

