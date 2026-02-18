# P2P US Cost Calculation Logic

The entry point is `calculate_costs(df)` which runs two stages: **supplement** (enrich data) then **calculate** (apply costs).

**Status:** Early development. Used for carrier cost optimization analysis, not yet validated against invoices.

**Service:** Parcel Flex Advantage Plus (PFAP2), single service, max 50 lbs.

---

## Stage 1: Supplement Shipments

### 1. Calculated Dimensions
- `cubic_in` = L x W x H (rounded to whole number)
- `longest_side_in` = max(L, W, H) (rounded to 1 decimal)
- `second_longest_in` = middle dimension (rounded to 1 decimal)
- `length_plus_girth` = longest + 2 x (sum of other two) (rounded to 1 decimal)

Dimensions are rounded to 1 decimal place before threshold comparisons to prevent floating-point precision issues.

### 2. Zone Lookup (5-digit ZIP, 3-tier fallback)
- **Lookup key:** Full 5-digit ZIP code (unique among carriers — others use 3-digit prefix or 5-digit)
- **Single origin:** Columbus only — zones mapped from ORD (Chicago)
- Zones: **1-8** (Puerto Rico zone 9 and Hawaii zone 12 mapped to zone 8)
- `zone_covered` flag tracks whether ZIP was found in zones file
- Fallback: exact 5-digit ZIP match -> mode zone (most common across all ~10,430 ZIPs) -> default zone 5

### 3. Billable Weight
- Dimensional weight = `cubic_in` / **250**
- DIM threshold: **0** (no threshold — DIM weight always compared against actual)
- `billable_weight_lbs` = max(actual weight, dim weight) — always
- No rounding — continuous value used for rate bracket lookup

---

## Stage 2: Calculate Costs

### Phase 1: AHS Minimum Billable Weight Side Effect

Before surcharges are applied, packages that meet AHS **dimensional** conditions (not weight) get their billable weight raised to at least **30 lbs**. This ensures the correct rate bracket is used.

The dimensional conditions are:
- longest > 48" OR second longest > 30" OR L+G > 105"

This is applied separately from the surcharge itself because it must happen before rate lookup.

### Phase 2: Base Surcharges

Two standalone surcharges (no exclusivity groups):

| Surcharge | Conditions | List | Discount | Net Cost |
|-----------|-----------|------|----------|----------|
| **AHS** | longest > 48" OR 2nd longest > 30" OR L+G > 105" OR billable weight > 30 lbs | $29.00 | 0% | **$29.00** |
| **Oversize** | billable_weight > 70 lbs | $125.00 | 0% | **$125.00** |

Both are standalone — they can stack (a package can get both AHS and Oversize).

**AHS conditions detail:** Four triggers, any one is sufficient:
1. `longest_side_in > 48"`
2. `second_longest_in > 30"`
3. `length_plus_girth > 105"`
4. `billable_weight_lbs > 30 lbs`

**AHS side effect:** Min billable weight of 30 lbs, but only enforced when dimensional conditions (1-3) trigger, not when weight condition (4) triggers alone.

**Oversize note:** Since P2P US max actual weight is 50 lbs, Oversize only triggers when dimensional weight exceeds 70 lbs.

### Phase 3: Dependent Surcharges

None for P2P US.

### Phase 4: Base Rate Lookup

Rate card (`base_rates.csv`) is in long format with weight brackets x zones (1-8):
```
weight_lbs_lower, weight_lbs_upper, zone, rate
```

**66 weight brackets:**
- First 16: Ounce-level brackets (0.0625 lb increments up to 1 lb)
- Remaining 50: Pound-level brackets (1 lb increments from 1-50 lbs)

Lookup: match on `shipping_zone = zone` and `weight_lbs_lower < billable_weight_lbs <= weight_lbs_upper`.

### Phase 5: Subtotal & Total

```
cost_subtotal = cost_base + cost_ahs + cost_oversize
```

**P2P US has no fuel surcharge.** Rates are all-inclusive.

```
cost_total = cost_subtotal
```

---

## Summary Formulas

For a typical small package:

```
total = base_rate
```

For a dimensionally large package (e.g. longest > 48"):

```
total = base_rate (at 30 lb minimum) + AHS ($29.00)
```

For an extremely large package (dim weight > 70 lbs):

```
total = base_rate + AHS ($29.00) + Oversize ($125.00)
```

---

## Special Logic

### Ounce-Level Rate Brackets
P2P US has sub-pound weight brackets (16 brackets for 0-1 lb in 1-ounce increments).

### AHS Two-Part Condition Logic
AHS has a unique split between dimensional and weight conditions:
- **Dimensional triggers** (longest > 48", 2nd longest > 30", L+G > 105") enforce a 30 lb min billable weight side effect
- **Weight trigger** (billable weight > 30 lbs) does NOT enforce the minimum (it's already above 30)
- Both paths result in the $29.00 surcharge

### All-US Optimization Analysis
P2P US has a dual-loader structure for "what if" carrier cost optimization across all US shipments.

### Multi-Shipment Handling
Upload script calculates `cost_total_multishipment = cost_total x trackingnumber_count` for orders split across multiple packages. Also applies penalty costs: $200 for overweight and $200 for out-of-coverage shipments.

### No Demand/Peak Surcharges
P2P US has no seasonal demand or peak surcharges.

