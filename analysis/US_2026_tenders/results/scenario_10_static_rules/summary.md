# Scenario 10: Static Routing Rules (Implementable in PCS)

## Executive Summary

Scenario 10 translates Scenario 7's optimal carrier routing into **simple, static rules that can be configured in the production shipping system (PCS)**. Instead of S7's 353,000 unique per-shipment routing decisions, S10 uses **per-package-type weight cutoffs** combined with a **P2P zone list** — achieving **98.8% of S7's theoretical savings**.

| Metric                    | S10 Static Rules     | S7 Optimal           |
|---------------------------|----------------------|----------------------|
| Total cost                | **$4,450,862**       | $4,433,040           |
| Savings vs S1             | **25.5%**            | 25.8%                |
| Gap                       | **+$17,822**         | —                    |
| FedEx 16% tier            | **MET ($17K margin)**| MET ($15 margin)     |
| Configuration complexity  | **~50 rules + zip list** | 353K cell assignments |

## How It Works

### The Problem

S7 assigns carriers at the **(packagetype, zip_code, weight_bracket)** granularity — 353,000 unique cells. This cannot be configured in PCS, which supports static routing rules only: no real-time rate comparison between carriers.

### The Solution

S10 reduces the routing decision to two dimensions per package type:

```
For each package type:
  1. If destination is in P2P zone AND weight ≤ P2P_cutoff → ship with P2P
  2. If destination is NOT in P2P zone AND weight ≤ USPS_cutoff → ship with USPS
  3. Otherwise → ship with FedEx
```

This requires:
- **A P2P zone list**: 38,599 zip codes where P2P can deliver (one-time configuration)
- **Per package type**: a P2P weight cutoff and a USPS weight cutoff (39 active rules, rest default to FedEx)

### Why This Works

The S7 optimization showed that carrier choice is driven by three factors:
1. **P2P geographic availability** — P2P only serves ~52% of zip codes
2. **Weight** — lighter packages favor P2P/USPS, heavier packages favor FedEx
3. **Package dimensions** — larger boxes hit FedEx's crossover point at lower weights

The static rule captures factors 1 and 2 directly, and factor 3 through per-packagetype cutoffs. The only thing lost is **within-weight-bracket variation by zip code** (e.g., at 5 lbs, P2P might be cheaper in zone 2 but FedEx might be cheaper in zone 8 for the same package type). This costs $18K/year — a 0.4% gap.

## Cutoff Optimization

### Step 1: Find Optimal Cutoffs Per Package Type

For each of the 54 package types with meaningful volume (≥50 shipments):
- **P2P cutoff**: Find the highest weight where P2P average cost < FedEx average cost, across all P2P-zone shipments for that package type
- **USPS cutoff**: Find the highest weight where USPS average cost < FedEx average cost, across all non-P2P-zone shipments for that package type

The "break at first loss" approach stops raising the cutoff as soon as FedEx becomes cheaper on average at a given weight bracket. This prevents routing heavy packages to USPS/P2P where FedEx is the better carrier.

### Step 2: Check FedEx 16% Earned Discount Threshold

The unconstrained cutoffs produce $4,439,369 total cost but FedEx undiscounted spend is $4,337,684 — **below the $4,500,000 threshold** needed for the 16% earned discount tier. Without the discount, all FedEx rates increase by ~49% (see S4/S5).

### Step 3: Tighten USPS Cutoffs to Meet Threshold

To push more volume to FedEx, the optimizer iteratively **lowers USPS cutoffs** for the package types where shifting to FedEx is cheapest. Each shift is ranked by **cost efficiency** (cost penalty per dollar of FedEx base rate gained). The cheapest shifts go first.

34 shifts were needed, costing a total of **$11,493** in additional spend to meet the FedEx threshold. Notably:
- **Only USPS cutoffs were lowered** — P2P cutoffs were left untouched because shifting P2P volume to FedEx is more expensive
- The biggest single shift: PIZZA BOX 20x16x2 USPS cutoff from 5→4 ($3,753 penalty, $18,017 FedEx base rate gain)
- Many shifts cost under $100 (e.g., lowering cutoffs for rare weight brackets)

## Final Routing Rules

### Top Package Types (by shipment volume)

| Package Type                       | Ships   | P2P Zone Rule         | Non-P2P Rule          |
|------------------------------------|---------|----------------------|-----------------------|
| PIZZA BOX 20x16x1                 | 117,206 | P2P if wt ≤ 7        | USPS if wt ≤ 3       |
| PIZZA BOX 12x8x1                  |  55,898 | P2P if wt ≤ 6        | USPS if wt ≤ 3       |
| PIZZA BOX 16x12x2                 |  43,674 | P2P if wt ≤ 5        | USPS if wt ≤ 3       |
| WRAP 16''x12''                    |  42,298 | P2P if wt ≤ 4        | USPS if wt ≤ 3       |
| PIZZA BOX 24x20x2                 |  40,950 | P2P if wt ≤ 11       | USPS if wt ≤ 1       |
| PIZZA BOX 36x24x2                 |  37,143 | P2P if wt ≤ 3        | FedEx always          |
| PIZZA BOX 20x16x2                 |  36,316 | P2P if wt ≤ 11       | USPS if wt ≤ 4       |
| PIZZA BOX 42x32x2                 |  24,809 | FedEx always          | FedEx always          |
| WRAP 24''x16''                    |  23,432 | P2P if wt ≤ 4        | USPS if wt ≤ 1       |
| PIZZA BOX 40x30x1                 |  21,002 | FedEx always          | USPS if wt ≤ 1       |
| PIZZA BOX 48X36X1                 |  19,768 | FedEx always          | FedEx always          |
| CROSS PACKAGING 30X24"            |  15,128 | P2P if wt ≤ 16       | USPS if wt ≤ 2       |
| 21" Tube                          |  12,376 | P2P if wt ≤ 6        | USPS if wt ≤ 1       |
| PIZZA BOX 30x20x3                 |  10,152 | P2P if wt ≤ 22       | FedEx always          |
| POLY BAG 9x12                     |   5,471 | P2P if wt ≤ 3        | USPS if wt ≤ 3       |
| MUG BOX 16x12x8                   |   4,962 | P2P if wt ≤ 13       | USPS if wt ≤ 4       |

**Pattern:** The P2P cutoff varies from 0 (large boxes like 42x32 go straight to FedEx) to 30 (BOX 16x24x12 — compact dimensions, P2P wins across all weights). The USPS cutoff is generally lower (1-4 lbs) because USPS loses competitiveness faster as weight increases.

### Package Type Groups

For implementation convenience, packages fall into three natural groups:

**Always FedEx (8 package types, 52K ships):** PIZZA BOX 42x32x2, 48X36X1, 40x30x2, CROSS PACKAGING 49X30", 40X30", 40X40", and strapped variants. These are large, heavy packages where FedEx is always cheapest.

**P2P only, no USPS (13 package types, 23K ships):** PIZZA BOX 36x24x2, 30x20x3, 27x23x2, and various strapped/specialty variants. P2P wins at low weights in P2P zones, but USPS is never competitive due to package dimensions.

**P2P + USPS (18 package types, 483K ships):** The main volume drivers. P2P serves the P2P zone below a weight cutoff, USPS serves non-P2P zones below a (usually lower) cutoff, FedEx handles everything else.

### Default Rule

Any package type not explicitly configured defaults to **FedEx always**. This is conservative and safe.

## Results

### Carrier Mix

| Carrier     | Shipments   | Share    | Total Cost     | Avg Cost    |
|-------------|-------------|---------|----------------|-------------|
| USPS        | 158,753     | 28.4%   | $1,038,088     | $6.54       |
| FedEx       | 172,927     | 31.0%   | $2,387,391     | $13.81      |
| P2P         | 226,333     | 40.6%   | $1,025,383     | $4.53       |
| **Total**   | **558,013** | **100%**| **$4,450,862** |             |

### FedEx Earned Discount

| Metric                  | Value           |
|-------------------------|-----------------|
| Base rate total         | $1,671,430      |
| Undiscounted equivalent | $4,517,378      |
| Threshold               | $4,500,000      |
| Margin                  | **+$17,378**    |
| 16% tier                | **MET**         |

### P2P Zone Coverage

| Metric                  | Value           |
|-------------------------|-----------------|
| P2P zip codes           | 38,599          |
| Eligible shipments      | 289,272 (51.8%) |
| Actually routed to P2P  | 226,333 (78.2% of eligible) |

78% of P2P-eligible shipments are routed to P2P. The remaining 22% are above the P2P weight cutoff for their package type, so they go to FedEx.

## Verification

### Every Rule Saves Money

All 39 active routing rules were validated: each one reduces cost compared to the "always FedEx" alternative. The total savings from all rules combined: **$1,709,824** vs all-FedEx routing.

### Missed Opportunities (Inherent to Static Rules)

| Scenario                              | Ships   | Overpay    | Why                                          |
|---------------------------------------|---------|------------|----------------------------------------------|
| FedEx assigned, but P2P is cheaper    | 12,215  | $82,482    | P2P wins for some zips but not on average     |
| FedEx assigned, but USPS is cheaper   | 28,813  | $48,723    | USPS wins for some zips but not on average    |
| P2P assigned, but USPS is cheaper     | 13,645  | $3,181     | Negligible — P2P and USPS are close in cost   |

**Total theoretical overpay: ~$134K.** This is the cost of static rules vs per-shipment rate shopping. However, only $18K of this gap shows up in the S10 vs S7 comparison because S7 itself doesn't capture all per-shipment optimality (it also uses weight-bracket aggregation).

The $82K "FedEx assigned but P2P cheaper" overpay comes from **within-weight-bracket variation**: at the same weight and package type, P2P might be cheaper in zone 2 but not zone 8. A weight-only cutoff can't distinguish between these. This would require zone-level rules per package type — 400+ rules instead of 50.

## Comparison to Other Approaches

### Static Rule Complexity vs Savings

| Approach                              | Cost       | Savings | Rules Needed             |
|---------------------------------------|------------|---------|--------------------------|
| S1 Current mix                        | $5,971,748 | —       | As-is                    |
| Flat rule (all P2P≤3, USPS≤3)        | $4,870,938 | 18.4%   | 1 rule + zip list        |
| 3-group rule (small/medium/large)     | $4,516,757 | 24.4%   | 3 groups + zip list      |
| **S10 per-packagetype rules**         | **$4,450,862** | **25.5%** | **~50 rules + zip list** |
| S7 per-shipment optimal              | $4,433,040 | 25.8%   | 353K cell assignments    |

The per-packagetype approach captures 98.8% of S7's savings. The 3-group simplification captures 93.5% — still good but leaves $66K on the table. The flat rule captures only 71.1%.

### Comparison to Other Scenarios

| Scenario                              | Cost           | vs S1     |
|---------------------------------------|----------------|-----------|
| **S10 Static Rules**                  | **$4,450,862** | **25.5%** |
| S7 Drop OnTrac (optimal)             | $4,433,040     | 25.8%     |
| S8 Drop OnTrac ($5M conservative)    | $4,536,690     | 24.0%     |
| S5 Drop OnTrac (0% earned + P2P)     | $4,931,056     | 17.4%     |
| S4 Both constraints (0% earned)       | $5,492,793     | 8.0%      |
| S1 Baseline                          | $5,971,748     | —         |

S10 is cheaper than S8 (the conservative $5M threshold variant) by $86K — because S10 uses the $4.5M threshold, giving it more room for P2P/USPS routing. The FedEx margin is thin ($17K) but more comfortable than S7's $15.

## Implementation Guide

### What Needs to Be Configured in PCS

**1. P2P Zone List (one-time)**
- Upload the 38,599 zip codes from `p2p_zip_codes.csv`
- These are the destinations where P2P can deliver
- This list comes from P2P's coverage data and should be updated if P2P expands/contracts

**2. Routing Rules (per package type)**
- For each of the ~50 package types, set:
  - **P2P weight limit**: max weight (in lbs, rounded up) to route to P2P when destination is in P2P zone
  - **USPS weight limit**: max weight to route to USPS when destination is NOT in P2P zone
- If a shipment doesn't match either rule, it goes to FedEx (default)
- The full rule table is in `routing_rules.csv`

**3. Priority Logic**
```
IF destination zip is in P2P zone AND ceiling(weight) <= P2P_cutoff:
    → Ship with P2P
ELSE IF destination zip is NOT in P2P zone AND ceiling(weight) <= USPS_cutoff:
    → Ship with USPS
ELSE:
    → Ship with FedEx
```

Note: P2P is only checked for P2P-zone destinations. USPS is only checked for non-P2P-zone destinations. This prevents routing to USPS in P2P zones (where P2P is cheaper) or to P2P in non-P2P zones (where P2P can't deliver).

### What This Does NOT Handle

- **In-P2P-zone USPS routing**: The rule never sends P2P-zone packages to USPS, even when USPS would be cheaper. This costs ~$3K/year — negligible.
- **Zone-level optimization**: Different zones within the same weight bracket may have different optimal carriers. Capturing this would require ~400+ rules instead of ~50.
- **Seasonal volume shifts**: If shipment volumes change significantly, the FedEx threshold margin ($17K) could be at risk. Monitor FedEx undiscounted spend quarterly.

## Risks

### FedEx Threshold Fragility

The $17,378 margin above the $4.5M threshold is thin. Scenarios that could push below:
- **Seasonal demand shifts** — fewer heavy packages in summer could reduce FedEx volume
- **P2P coverage expansion** — if P2P adds more zip codes, more volume shifts away from FedEx
- **New package types** — lightweight products that route to P2P/USPS instead of FedEx

**Mitigation**: Use S8's $5M threshold instead. This costs $86K more but provides $500K of headroom. Alternatively, lower 2-3 USPS cutoffs by 1 lb each to shift ~$50K more base rate to FedEx.

### P2P Availability

P2P coverage is zip-code-level. If P2P exits certain markets, those shipments automatically fall to FedEx (the default). No configuration change needed, but cost increases.

### Rate Changes

If any carrier's rates change materially, the cutoffs should be recomputed. The scenario script can be re-run with updated rate data to generate new cutoffs.

## Output Files

| File                      | Description                                          |
|---------------------------|------------------------------------------------------|
| `assignments.parquet`     | Per-(packagetype, zip, weight_bracket) carrier assignment |
| `routing_rules.csv`       | Per-packagetype P2P and USPS weight cutoffs          |
| `p2p_zip_codes.csv`       | List of 38,599 zip codes where P2P delivers          |
| `summary.md`              | This file                                            |

---

*Analysis generated: February 2026*
*Data source: shipments_unified.parquet (558,013 shipments), FedEx at 16% earned discount*
*Baseline: $5,971,748 (Scenario 1 current mix, FedEx at 16% earned discount)*
*FedEx threshold: $4.5M undiscounted spend required for 16% earned discount tier*
*Methodology: Per-packagetype weight cutoff optimization with greedy FedEx threshold enforcement*
