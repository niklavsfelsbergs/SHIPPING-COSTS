# OnTrac Cost Calculation Logic

The entry point is `calculate_costs(df)` which runs two stages: **supplement** (enrich data) then **calculate** (apply costs).

---

## Stage 1: Supplement Shipments

### 1. Calculated Dimensions
- `cubic_in` = L x W x H (rounded to whole number)
- `longest_side_in` = max(L, W, H) (rounded to 1 decimal)
- `second_longest_in` = middle dimension (rounded to 1 decimal)
- `length_plus_girth` = longest + 2 x (sum of other two) (rounded to 1 decimal)

Dimensions are rounded to 1 decimal place before threshold comparisons to prevent floating-point precision issues (e.g. 762mm -> 30.0000001980" incorrectly triggering >30" threshold).

### 2. Zone Lookup (origin-dependent, 3-tier fallback)
- `zones.csv` has separate `phx_zone` and `cmh_zone` columns — zone depends on whether origin is Phoenix or Columbus
- Also assigns `das_zone` ("NO", "DAS", or "EDAS") from the same file
- Fallback: exact 5-digit ZIP match -> state mode (most common zone for state) -> default zone 5

### 3. Billable Weight
- Dimensional weight = `cubic_in` / **250** (contract DIM factor)
- DIM threshold: **1,728 cubic inches** (1 cubic foot) — DIM weight only considered above this
- `billable_weight_lbs` = max(actual weight, dim weight) when cubic_in > 1,728, otherwise just actual weight
- No rounding — continuous value used for rate bracket lookup

---

## Stage 2: Calculate Costs

### Phase 1: Base Surcharges

Six surcharges across two exclusivity groups plus one standalone:

**"dimensional" exclusivity group** (only highest-priority match wins):

| Surcharge | Conditions | List | Discount | Net Cost | Priority |
|-----------|-----------|------|----------|----------|----------|
| **OML** | weight > 150 lbs OR longest > 108" OR L+G > 165" | $1,875.00 | 0% | **$1,875.00** | 1 (wins) |
| **LPS** | longest > 72" OR volume > 17,280 cu in | $285.00 | 60% | **$114.00** | 2 |
| **AHS** | weight > 50 lbs OR longest > 48" OR 2nd longest > 30" OR volume > 8,640 cu in | Zone-based (see below) | 70% | **$10.80-$12.60** | 3 (loses) |

**AHS zone-based pricing (after 70% discount):**

| Zones | List Price | Net |
|-------|-----------|-----|
| 2-4 | $36.00 | **$10.80** |
| 5-6 | $40.00 | **$12.00** |
| 7-8 | $42.00 | **$12.60** |

**AHS Borderline Allocation:** OnTrac inconsistently charges AHS for packages with `second_longest_in` in the range (30.0, 30.5] when no other AHS trigger applies (~50% charge rate observed). For these borderline-only cases, 50% of the surcharge cost is applied.

**"delivery" exclusivity group:**

| Surcharge | Conditions | List | Discount | Net Cost | Priority |
|-----------|-----------|------|----------|----------|----------|
| **EDAS** | das_zone == "EDAS" | $8.80 | 60% | **$3.52** | 1 (wins) |
| **DAS** | das_zone == "DAS" | $6.60 | 60% | **$2.64** | 2 |

**Standalone (allocated):**

| Surcharge | Conditions | List | Discount | Allocation | Net Cost |
|-----------|-----------|------|----------|------------|----------|
| **RES** | Always True (all shipments) | $6.60 | 90% | 95% | **$0.627** per shipment |

RES is allocated because residential vs commercial status can't be predicted per-shipment. The cost is spread across all shipments at 95% allocation rate so total expected matches total actual across the portfolio.

**Min billable weight side effects:**

| Surcharge | Min Billable Weight |
|-----------|-------------------|
| OML | 150 lbs |
| LPS | 90 lbs |
| AHS | 30 lbs |

When triggered, billable weight is raised to at least this value (affects base rate lookup).

### Phase 2: Dependent (Demand/Peak) Surcharges

All demand surcharges use a **5-day billing lag** — OnTrac applies demand surcharges based on billing date, not ship date, so `ship_date + 5 days` is used for period checks.

| Surcharge | Condition | Period | List | Discount | Net Cost |
|-----------|-----------|--------|------|----------|----------|
| **DEM_RES** | RES flagged | Oct 25 - Jan 16 | $1.00 | 50% | **$0.475** (x 95% allocation) |
| **DEM_AHS** | AHS flagged | Sep 27 - Jan 16 | $11.00 | 50% | **$5.50** (or $2.75 borderline) |
| **DEM_LPS** | LPS flagged | Sep 27 - Jan 16 | $105.00 | 50% | **$52.50** |
| **DEM_OML** | OML flagged | Sep 27 - Jan 16 | $550.00 | 50% | **$275.00** |

DEM_AHS mirrors the AHS borderline allocation logic — 50% cost for borderline-only cases.

### Phase 3: Minimum Billable Weight Adjustment

Billable weight is raised to the highest minimum from triggered surcharges:
```
billable_weight = max(billable_weight, 150 if OML, 90 if LPS, 30 if AHS)
```

### Phase 4: Base Rate Lookup

Rate card (`base_rates.csv`) has weight brackets x zones (2-8):
```
weight_lbs_lower, weight_lbs_upper, zone_2, zone_3, ..., zone_8
```

Lookup: match on `shipping_zone` and `weight_lbs_lower < billable_weight_lbs <= weight_lbs_upper`.

### Phase 5: Subtotal

```
cost_subtotal = cost_base
              + cost_oml (or cost_lps or cost_ahs)
              + cost_edas (or cost_das)
              + cost_res
              + cost_dem_res
              + cost_dem_ahs
              + cost_dem_lps
              + cost_dem_oml
```

### Phase 6: Fuel Surcharge

```
cost_fuel = cost_subtotal x 12.5125%
```
(List rate 19.25%, with 35% contract discount -> effective 12.5125%. Applied to **full subtotal** — base + all surcharges.)

### Phase 7: Total

```
cost_total = cost_subtotal + cost_fuel
```

---

## Summary Formulas

For a typical package with no surcharges:

```
total = (base_rate + residential) x 1.125125
```

For a large package during peak (Sep 27 - Jan 16):

```
total = (base_rate + AHS + DEM_AHS + residential + DEM_RES + DAS/EDAS) x 1.125125
```

