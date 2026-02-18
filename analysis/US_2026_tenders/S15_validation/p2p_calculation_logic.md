# P2P Calculation Logic: Validation Checklist

Documents the calculation logic for P2P US (PFAP) and P2P US2 (PFA/PFS) so each step can be verified against the contract rate cards and sample invoices.

---

## P2P US — PFAP Service

**Calculator:** `carriers/p2p_us/calculate_costs.py`
**Version:** 2026.02.03
**Rate card source:** P2P rate card (PFAP2)
**ZIP coverage:** ~10,430 5-digit ZIPs (ORD origin)

### Zone Lookup

| Item | Rule | Status |
|------|------|--------|
| Lookup key | Full 5-digit ZIP code | [ ] |
| Zone range | 1–8 (PR zone 9 and HI zone 12 mapped to 8) | [ ] |
| Fallback 1 | Mode zone (most common across all ZIPs) | [ ] |
| Fallback 2 | Default zone 5 | [ ] |
| Coverage tracking | `zone_covered` flag for exact match | [ ] |

### Dimensional Weight

| Item | Rule | Status |
|------|------|--------|
| DIM factor | 250 | [ ] |
| DIM threshold | 0 (always compare actual vs DIM) | [ ] |
| DIM formula | `cubic_in / 250` | [ ] |
| Billable weight | `max(weight_lbs, dim_weight_lbs)` | [ ] |
| Rounding | Dimensions rounded to 1 decimal before threshold checks | [ ] |
| Cubic inches | L × W × H rounded to whole number | [ ] |

### AHS Side Effect

Before surcharges and rate lookup, if any dimensional AHS condition triggers (longest > 48", second longest > 30", L+G > 105"), billable weight is floored to **30 lbs**.

| Item | Rule | Status |
|------|------|--------|
| Dimensional triggers | longest > 48" OR second longest > 30" OR L+G > 105" | [ ] |
| Min billable weight | `max(billable_weight, 30)` when dimensional trigger fires | [ ] |
| Weight-only trigger | billable weight > 30 lbs — does NOT apply min (already above 30) | [ ] |

### Surcharges

**AHS — Additional Handling ($29.00)**

| Item | Rule | Status |
|------|------|--------|
| Trigger 1 | `longest_side_in > 48"` | [ ] |
| Trigger 2 | `second_longest_in > 30"` | [ ] |
| Trigger 3 | `length_plus_girth > 105"` | [ ] |
| Trigger 4 | `billable_weight_lbs > 30 lbs` | [ ] |
| Logic | Any one trigger = surcharge applies | [ ] |
| Cost | $29.00 (no discount) | [ ] |
| Stacking | Independent — can stack with Oversize | [ ] |

**Oversize ($125.00)**

| Item | Rule | Status |
|------|------|--------|
| Trigger | `billable_weight_lbs > 70 lbs` | [ ] |
| Cost | $125.00 (no discount) | [ ] |
| Stacking | Independent — can stack with AHS | [ ] |
| Note | Only triggers via DIM weight (actual max 50 lbs) | [ ] |

### Base Rate Lookup

| Item | Rule | Status |
|------|------|--------|
| Rate structure | 66 weight brackets × 8 zones = 528 rates | [ ] |
| Ounce brackets | 16 brackets, 1 oz increments (0–1 lb) | [ ] |
| Pound brackets | 50 brackets, 1 lb increments (1–50 lbs) | [ ] |
| Bracket matching | `weight_lower < billable_weight <= weight_upper` | [ ] |
| Max weight | 50 lbs | [ ] |

### Cost Totaling

| Item | Rule | Status |
|------|------|--------|
| Subtotal | `cost_base + cost_ahs + cost_oversize` | [ ] |
| Fuel surcharge | None — rates are all-inclusive | [ ] |
| Peak surcharge | None currently modeled | [ ] |
| Total | `= subtotal` | [ ] |

---

## P2P US2 — PFA and PFS Services

**Calculator:** `carriers/p2p_us2/calculate_costs.py`
**Version:** 2026.02.18
**Rate card source:** P2PG_PicaNova_DomesticRates_20260212.xlsx
**ZIP coverage:** ~93,100 5-digit ZIPs (ORD origin)

The calculator outputs **both** PFA and PFS costs for every shipment. Service selection (PFA vs PFS) happens downstream at the group level.

### Zone Lookup

| Item | Rule | Status |
|------|------|--------|
| Lookup key | Full 5-digit ZIP code | [ ] |
| Zone range | 1–9 (PFA uses 1–8, PFS uses 1–9) | [ ] |
| Remote flag | `is_remote` from zones.csv (parsed from "remote X" values) | [ ] |
| Fallback 1 | Mode zone (most common across all ZIPs) | [ ] |
| Fallback 2 | Default zone 5 | [ ] |
| Coverage tracking | `zone_covered` flag for exact match | [ ] |

### Dimensional Weight

PFA and PFS have separate billable weight calculations.

**PFA:**

| Item | Rule | Status |
|------|------|--------|
| DIM factor | 166 | [ ] |
| DIM threshold | 1,728 cu in (1 cu ft) | [ ] |
| Weight floor | DIM weight only applied when `weight_lbs > 1.0` | [ ] |
| DIM formula | `cubic_in / 166` (only when cubic > 1,728 AND weight > 1 lb) | [ ] |
| Billable weight | `max(weight_lbs, pfa_dim_weight_lbs)` | [ ] |

**PFS:**

| Item | Rule | Status |
|------|------|--------|
| DIM factor | 166 | [ ] |
| DIM threshold | 1,728 cu in (1 cu ft) | [ ] |
| Weight floor | None (no weight restriction for DIM) | [ ] |
| DIM formula | `cubic_in / 166` (only when cubic > 1,728) | [ ] |
| Billable weight | `max(weight_lbs, pfs_dim_weight_lbs)` | [ ] |

**Shared dimension calculations:**

| Item | Rule | Status |
|------|------|--------|
| Rounding | Dimensions rounded to 1 decimal before threshold checks | [ ] |
| Cubic inches | L × W × H rounded to whole number | [ ] |
| Shortest side | `min(L, W, H)` — used in PFA oversize | [ ] |

### Service Eligibility

| Item | PFA | PFS | Status |
|------|-----|-----|--------|
| Max billable weight | 30 lbs | 70 lbs | [ ] |
| Max zone | 8 | 9 | [ ] |
| Ineligible output | All PFA cost columns = null | All PFS cost columns = null | [ ] |

### PFA Surcharges

**PFA Oversize ($9.00)**

| Item | Rule | Status |
|------|------|--------|
| Trigger 1 | `longest_side_in > 21"` | [ ] |
| Trigger 2 | `second_longest_in > 17"` | [ ] |
| Trigger 3 | `shortest_side_in > 14"` | [ ] |
| Logic | Any one trigger = surcharge applies | [ ] |
| Cost | $9.00 (no discount) | [ ] |
| Interpretation | Package doesn't fit in 21" × 17" × 14" box | [ ] |

**PFA Oversize Volume ($16.00)**

| Item | Rule | Status |
|------|------|--------|
| Trigger | `cubic_in > 3,456` (2 cu ft) | [ ] |
| Cost | $16.00 (no discount) | [ ] |
| Stacking | Independent — can stack with PFA Oversize | [ ] |

### PFS Surcharges

**PFS Non-Standard Length ($4.50 / $10.00)**

| Item | Rule | Status |
|------|------|--------|
| Trigger | `longest_side_in > 22"` | [ ] |
| Tier 1 cost | $4.50 when `22" < longest_side_in <= 30"` | [ ] |
| Tier 2 cost | $10.00 when `longest_side_in > 30"` | [ ] |

**PFS Non-Standard Volume ($21.00)**

| Item | Rule | Status |
|------|------|--------|
| Trigger | `cubic_in > 3,456` (2 cu ft) | [ ] |
| Cost | $21.00 (no discount) | [ ] |
| Stacking | Independent — can stack with PFS NSL | [ ] |

### Peak Season Surcharge

Applies to **both** PFA and PFS during holiday periods.

**Periods:**

| Period | Start | End | Status |
|--------|-------|-----|--------|
| 2025-2026 Holiday | 2025-10-05 | 2026-01-18 | [ ] |
| 2026-2027 Holiday | 2026-10-05 | 2027-01-18 | [ ] |

**Rates by weight and zone group:**

| Weight Bracket | Zones 1–4 | Zones 5–9 | Status |
|----------------|-----------|-----------|--------|
| 0–3 lbs | $0.30 | $0.35 | [ ] |
| 4–10 lbs | $0.45 | $0.75 | [ ] |
| 11–25 lbs | $0.75 | $1.25 | [ ] |
| 26–70 lbs | $2.25 | $5.50 | [ ] |

| Item | Rule | Status |
|------|------|--------|
| Weight column | Uses billable weight (PFA or PFS respectively) | [ ] |
| Zone grouping | 1–4 vs 5–9 (not individual zones) | [ ] |
| Output columns | `pfa_cost_peak`, `pfs_cost_peak` | [ ] |

### Base Rate Lookup

**PFA rates:**

| Item | Rule | Status |
|------|------|--------|
| Rate structure | 45 weight brackets × 8 zones = 360 rates | [ ] |
| Ounce brackets | 15 brackets (0.0625–0.9375 lbs) | [ ] |
| Pound brackets | 30 brackets (1–30 lbs) | [ ] |
| Bracket matching | `weight_lower < billable_weight <= weight_upper` | [ ] |
| Max weight | 30 lbs | [ ] |

**PFS rates:**

| Item | Rule | Status |
|------|------|--------|
| Rate structure | 74 weight brackets × 9 zones = 666 rates | [ ] |
| Ounce brackets | 4 brackets (0.25 lb increments, 0–1 lb) | [ ] |
| Pound brackets | 70 brackets (1–70 lbs) | [ ] |
| Bracket matching | `weight_lower < billable_weight <= weight_upper` | [ ] |
| Max weight | 70 lbs | [ ] |

### Cost Totaling

**PFA:**

| Item | Rule | Status |
|------|------|--------|
| Subtotal | `pfa_cost_base + pfa_cost_peak + cost_pfa_oversize + cost_pfa_oversize_volume` | [ ] |
| Fuel surcharge | None — rates are all-inclusive | [ ] |
| Total | `= subtotal` (null if ineligible) | [ ] |

**PFS:**

| Item | Rule | Status |
|------|------|--------|
| Subtotal | `pfs_cost_base + pfs_cost_peak + cost_pfs_nsl + cost_pfs_nsv` | [ ] |
| Fuel surcharge | None — rates are all-inclusive | [ ] |
| Total | `= subtotal` (null if ineligible) | [ ] |

---

## Cross-Carrier Comparison

| Feature | P2P US (PFAP) | P2P US2 PFA | P2P US2 PFS |
|---------|---------------|-------------|-------------|
| ZIP coverage | ~10,430 | ~93,100 | ~93,100 |
| Zone range | 1–8 | 1–8 | 1–9 |
| DIM factor | 250 | 166 | 166 |
| DIM threshold | 0 (always) | 1,728 cu in + weight > 1 lb | 1,728 cu in |
| Max weight | 50 lbs | 30 lbs | 70 lbs |
| Ounce brackets | 16 (1 oz) | 15 (1 oz) | 4 (4 oz) |
| Pound brackets | 50 | 30 | 70 |
| Peak surcharge | No | Yes | Yes |
| Fuel surcharge | No | No | No |
| Surcharges | AHS, Oversize | Oversize, Oversize Vol | NSL, NSV |
| Remote flag | No | No (in zones.csv but unused in cost) | No |

---

## Open Questions

| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | P2P US (PFAP) peak surcharges — does PFAP charge peak during holiday periods? | Underestimated cost if yes | [ ] V3 in validation_plan |
| 2 | P2P US2 remote zone surcharge — is the waiver contractual or discretionary? | Remote ZIPs may cost more | [ ] V5 in validation_plan |
| 3 | P2P US2 `is_remote` flag — is it used in any cost calculation or only informational? | Currently unused in calculator | [ ] |
| 4 | P2P US zone origin — zones mapped from ORD but Columbus is production site. Correct? | Zone mismatch → wrong rates | [ ] |
| 5 | P2P US2 PFA weight > 1 lb DIM restriction — confirmed in contract? | Affects billable weight for light parcels | [ ] |

---

*Created: February 2026*
*P2P US calculator v2026.02.03 | P2P US2 calculator v2026.02.18*
