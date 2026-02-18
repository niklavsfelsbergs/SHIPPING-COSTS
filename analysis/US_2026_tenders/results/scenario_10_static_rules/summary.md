# Scenario 10: Static Routing Rules (Implementable in PCS)

## Executive Summary

Scenario 10 translates Scenario 7's optimal carrier routing into **simple, static rules that can be configured in the production shipping system (PCS)**. Instead of S7's per-shipment routing decisions, S10 uses **per-package-type weight cutoffs** combined with a **P2P zone list**.

| Metric                    | S10 Static Rules         |
|---------------------------|--------------------------|
| Total cost                | **$4,942,173**           |
| Savings vs S1             | **$1,129,889 (18.6%)**   |
| FedEx 16% tier            | **MET**                  |
| Configuration complexity  | **~50 rules + zip list** |

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
- **A P2P zone list**: zip codes where P2P can deliver (one-time configuration)
- **Per package type**: a P2P weight cutoff and a USPS weight cutoff (active rules, rest default to FedEx)

### Why This Works

The S7 optimization showed that carrier choice is driven by three factors:
1. **P2P geographic availability** — P2P only serves ~52% of zip codes
2. **Weight** — lighter packages favor P2P/USPS, heavier packages favor FedEx
3. **Package dimensions** — larger boxes hit FedEx's crossover point at lower weights

The static rule captures factors 1 and 2 directly, and factor 3 through per-packagetype cutoffs. The only thing lost is **within-weight-bracket variation by zip code** (e.g., at 5 lbs, P2P might be cheaper in zone 2 but FedEx might be cheaper in zone 8 for the same package type).

## Cutoff Optimization

### Step 1: Find Optimal Cutoffs Per Package Type

For each of the 54 package types with meaningful volume (≥50 shipments):
- **P2P cutoff**: Find the highest weight where P2P average cost < FedEx average cost, across all P2P-zone shipments for that package type
- **USPS cutoff**: Find the highest weight where USPS average cost < FedEx average cost, across all non-P2P-zone shipments for that package type

The "break at first loss" approach stops raising the cutoff as soon as FedEx becomes cheaper on average at a given weight bracket. This prevents routing heavy packages to USPS/P2P where FedEx is the better carrier.

### Step 2: Check FedEx 16% Earned Discount Threshold

The unconstrained cutoffs may produce a total cost where FedEx undiscounted spend is below the **$4,500,000 threshold** needed for the 16% earned discount tier. Without the discount, all FedEx rates increase by ~49% (see S4/S5).

### Step 3: Tighten USPS Cutoffs to Meet Threshold

If the threshold is not met, the optimizer iteratively **lowers USPS cutoffs** for the package types where shifting to FedEx is cheapest. Each shift is ranked by **cost efficiency** (cost penalty per dollar of FedEx base rate gained). The cheapest shifts go first.

Key design choices:
- **Only USPS cutoffs are lowered** — P2P cutoffs are left untouched because shifting P2P volume to FedEx is more expensive
- Many shifts cost very little (e.g., lowering cutoffs for rare weight brackets)

## Final Routing Rules

### Top Package Types (by shipment volume)

| Package Type                       | Ships   | P2P Zone Rule         | Non-P2P Rule          |
|------------------------------------|---------|----------------------|-----------------------|
| PIZZA BOX 20x16x1                 | 113,896 | P2P if wt ≤ 7        | USPS if wt ≤ 2       |
| PIZZA BOX 12x8x1                  |  54,637 | P2P if wt ≤ 6        | USPS if wt ≤ 1       |
| PIZZA BOX 16x12x2                 |  42,377 | P2P if wt ≤ 5        | USPS if wt ≤ 2       |
| WRAP 16''x12''                    |  41,536 | P2P if wt ≤ 4        | USPS if wt ≤ 1       |
| PIZZA BOX 24x20x2                 |  39,950 | P2P if wt ≤ 11       | USPS if wt ≤ 1       |
| PIZZA BOX 36x24x2                 |  36,438 | P2P if wt ≤ 3        | FedEx always          |
| PIZZA BOX 20x16x2                 |  35,114 | P2P if wt ≤ 11       | USPS if wt ≤ 2       |
| PIZZA BOX 42x32x2                 |  24,261 | FedEx always          | FedEx always          |
| WRAP 24''x16''                    |  22,638 | P2P if wt ≤ 4        | FedEx always          |
| PIZZA BOX 40x30x1                 |  20,091 | FedEx always          | USPS if wt ≤ 1       |
| PIZZA BOX 48X36X1                 |  18,697 | FedEx always          | FedEx always          |
| CROSS PACKAGING 30X24"            |  14,740 | P2P if wt ≤ 16       | USPS if wt ≤ 2       |
| 21" Tube                          |  12,032 | P2P if wt ≤ 6        | FedEx always          |
| PIZZA BOX 30x20x3                 |   9,920 | P2P if wt ≤ 22       | FedEx always          |
| POLY BAG 9x12                     |   5,340 | P2P if wt ≤ 3        | USPS if wt ≤ 1       |
| MUG BOX 16x12x8                   |   4,610 | P2P if wt ≤ 13       | USPS if wt ≤ 2       |

**Pattern:** The P2P cutoff varies from 0 (large boxes like 42x32 go straight to FedEx) to 30 (BOX 16x24x12 — compact dimensions, P2P wins across all weights). The USPS cutoff is generally lower (1-4 lbs) because USPS loses competitiveness faster as weight increases.

### Package Type Groups

For implementation convenience, packages fall into three natural groups:

**Always FedEx (11 package types):** PIZZA BOX 42x32x2, 48X36X1, 40x30x2, CROSS PACKAGING 49X30", 40X30", 40X40", WRAP 40''x30'', and strapped variants. These are large, heavy packages where FedEx is always cheapest.

**P2P only, no USPS (15 package types):** PIZZA BOX 36x24x2, 30x20x3, 27x23x2, WRAP 24''x16'', 21" Tube, and various strapped/specialty variants. P2P wins at low weights in P2P zones, but USPS is never competitive due to package dimensions.

**P2P + USPS (remaining package types):** The main volume drivers. P2P serves the P2P zone below a weight cutoff, USPS serves non-P2P zones below a (usually lower) cutoff, FedEx handles everything else.

### Default Rule

Any package type not explicitly configured defaults to **FedEx always**. This is conservative and safe.

## Results

### Carrier Mix

| Carrier     | Shipments   | Share    | Total Cost     | Avg Cost    |
|-------------|-------------|---------|----------------|-------------|
| USPS        | 104,181     | 19.3%   | $604,574       | $5.80       |
| FedEx       | 216,585     | 40.1%   | $3,346,797     | $15.45      |
| P2P         | 219,151     | 40.6%   | $990,801       | $4.52       |
| **Total**   | **539,917** | **100%**| **$4,942,173** |             |

### FedEx Earned Discount

| Metric                  | Value           |
|-------------------------|-----------------|
| Threshold               | $4,500,000      |
| 16% tier                | **MET**         |

### P2P Zone Coverage

P2P-eligible shipments are routed to P2P when below the weight cutoff for their package type. The remaining shipments above the cutoff go to FedEx.

## Verification

### Every Rule Saves Money

All active routing rules were validated: each one reduces cost compared to the "always FedEx" alternative.

### Missed Opportunities (Inherent to Static Rules)

Static rules cannot capture within-weight-bracket variation by zip code (e.g., at 5 lbs, P2P might be cheaper in zone 2 but FedEx might be cheaper in zone 8 for the same package type). This would require zone-level rules per package type — 400+ rules instead of ~50.

## Comparison to Other Approaches

### Static Rule Complexity vs Savings

| Approach                              | Cost           | Savings vs S1   | Rules Needed             |
|---------------------------------------|----------------|-----------------|--------------------------|
| S1 Current mix                        | $6,072,062     | —               | As-is                    |
| S11 3-group rule (small/medium/large) | $4,962,119     | 18.3%           | 3 groups + zip list      |
| **S10 per-packagetype rules**         | **$4,942,173** | **18.6%**       | **~50 rules + zip list** |

### Comparison to Other Scenarios

| Scenario                              | Cost           | vs S1     |
|---------------------------------------|----------------|-----------|
| S8 Drop OnTrac ($5M conservative)    | $5,136,088     | 15.4%     |
| **S10 Static Rules**                  | **$4,942,173** | **18.6%** |
| S11 3-Group Rules                    | $4,962,119     | 18.3%     |
| S1 Baseline                          | $6,072,062     | —         |

S10 is $19,946 cheaper than S11 (3-group simplification) — the per-packagetype cutoffs capture additional savings through finer-grained routing.

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
- **Seasonal volume shifts**: If shipment volumes change significantly, the FedEx threshold margin could be at risk. Monitor FedEx undiscounted spend quarterly.

## Risks

### FedEx Threshold

The FedEx 16% earned discount requires meeting the $4.5M undiscounted spend threshold. Scenarios that could push below:
- **Seasonal demand shifts** — fewer heavy packages in summer could reduce FedEx volume
- **P2P coverage expansion** — if P2P adds more zip codes, more volume shifts away from FedEx
- **New package types** — lightweight products that route to P2P/USPS instead of FedEx

**Mitigation**: Use S8's $5M threshold instead for more headroom. Alternatively, lower USPS cutoffs by 1 lb each for select package types to shift more base rate to FedEx.

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
*Data source: shipments_unified.parquet (539,917 matched shipments), FedEx at 16% earned discount*
*Baseline: $6,072,062 (Scenario 1 current mix, FedEx at 16% earned discount)*
*FedEx threshold: $4.5M undiscounted spend required for 16% earned discount tier*
*Methodology: Per-packagetype weight cutoff optimization with greedy FedEx threshold enforcement*
