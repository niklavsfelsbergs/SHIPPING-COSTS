# USPS Cost Calculation Logic

The entry point is `calculate_costs(df)` which runs two stages: **supplement** (enrich data) then **calculate** (apply costs).

---

## Stage 1: Supplement Shipments

### 1. Calculated Dimensions
- `cubic_in` = L x W x H (rounded to whole number)
- `longest_side_in` = max(L, W, H) (rounded to 1 decimal)
- `second_longest_in` = middle dimension (rounded to 1 decimal)
- `length_plus_girth` = longest + 2 x (sum of other two) (rounded to 1 decimal)

Dimensions are rounded to 1 decimal place before threshold comparisons to prevent floating-point precision issues.

### 2. Zone Lookup (origin-dependent, 3-tier fallback)
- **Lookup key:** 3-digit ZIP prefix (first 3 digits of shipping_zip_code)
- `zones.csv` has separate `phx_zone` and `cmh_zone` columns — zone depends on whether origin is Phoenix or Columbus
- Some zones have asterisk variants (1\*, 2\*, 3\*) indicating local delivery
  - `shipping_zone` preserves the asterisk for reference
  - `rate_zone` strips the asterisk and casts to Int64 for rate table lookup
- Fallback: exact 3-digit ZIP prefix match -> mode zone (most common across all entries) -> default zone 5

### 3. Billable Weight
- Dimensional weight = `cubic_in` / **200** (contract DIM factor)
- DIM threshold: **1,728 cubic inches** (1 cubic foot) — DIM weight only considered above this
- `billable_weight_lbs` = max(actual weight, dim weight) when cubic_in > 1,728, otherwise just actual weight
- No rounding — continuous value used for rate bracket lookup

---

## Stage 2: Calculate Costs

### Phase 1: Base Surcharges

Three surcharges across one exclusivity group plus one standalone:

**"length" exclusivity group** (only highest-priority match wins):

| Surcharge | Conditions | List | Discount | Net Cost | Priority |
|-----------|-----------|------|----------|----------|----------|
| **NSL2** | longest > 30" | $3.00 | 0% | **$3.00** | 1 (wins) |
| **NSL1** | longest > 22" AND longest <= 30" | $3.00 | 0% | **$3.00** | 2 |

**Standalone (no exclusivity):**

| Surcharge | Conditions | List | Discount | Net Cost |
|-----------|-----------|------|----------|----------|
| **NSV** | cubic_in > 3,456 (2 cubic feet) | $10.00 | 0% | **$10.00** |

NSV can stack with NSL1 or NSL2 since it has no exclusivity group.

No min billable weight side effects on any surcharge.

### Phase 2: Dependent Surcharges

None for USPS. All surcharges are BASE (don't reference other surcharge flags).

### Phase 3: Base Rate Lookup

Rate card (`base_rates.csv`) has weight brackets x zones (1-9):
```
weight_lbs_lower, weight_lbs_upper, zone_1, zone_2, ..., zone_9
```

Lookup: match on `rate_zone` and `weight_lbs_lower < billable_weight_lbs <= weight_lbs_upper`.

Max weight: **20 lbs** (USPS Ground Advantage limit).

### Phase 3b: Oversize Rate Override

**Trigger:** `length_plus_girth > 108"`.

When triggered, the normal weight-based `cost_base` is **replaced** with a flat zone-based oversize rate from `oversize_rates.csv`. Also sets `surcharge_oversize = True`.

**Oversize rates by zone:**

| Zone | Rate |
|------|------|
| 1 | $91.43 |
| 2 | $101.36 |
| 3 | $116.24 |
| 4 | $141.09 |
| 5 | $165.62 |
| 6 | $190.41 |
| 7 | $215.15 |
| 8 | $240.01 |
| 9 | $240.01 |

### Phase 4: Peak Season Surcharge

**Periods:**
- 2025-2026 Holiday: Oct 5, 2025 - Jan 18, 2026
- 2026-2027 Holiday: Oct 5, 2026 - Jan 18, 2027

**Rates by weight tier and zone group:**

| Weight Tier | Zones 1-4 | Zones 5-9 |
|-------------|-----------|-----------|
| 0-3 lbs | $0.30 | $0.35 |
| 4-10 lbs | $0.45 | $0.75 |
| 11-25 lbs | $0.75 | $1.25 |
| 26-70 lbs | $2.25 | $5.50 |

Sets `surcharge_peak = True` and adds `cost_peak`.

### Phase 5: Subtotal

```
cost_subtotal = cost_base (or oversize rate)
              + cost_nsl1 (or cost_nsl2)
              + cost_nsv
              + cost_peak
```

### Phase 6: Fuel & Total

**USPS has no fuel surcharge.**

```
cost_total = cost_subtotal
```

---

## Summary Formulas

For a typical small package (no surcharges, outside peak):

```
total = base_rate
```

For a long package during peak:

```
total = base_rate + NSL2 ($3.00) + peak ($0.30-$5.50)
```

For an oversize package (L+G > 108") during peak:

```
total = oversize_rate ($91.43-$240.01) + NSL2 ($3.00) + NSV ($10.00) + peak
```

---

## Special Logic

### Peak in Base (Comparison Reports Only)
USPS includes the peak surcharge in their base rate on invoices. In comparison reports, `cost_base + cost_peak` is combined as "Base" for proper comparison against actuals. This does **not** affect the calculator itself.

### Oversize Replaces Base Rate
USPS oversize is a complete replacement of the base rate — it's a flat zone-based price that replaces the normal weight-based lookup.

### No Allocated or Demand Surcharges
All USPS surcharges are deterministic — they trigger based purely on package attributes. No allocation patterns or seasonal demand surcharges that depend on other surcharge flags.
