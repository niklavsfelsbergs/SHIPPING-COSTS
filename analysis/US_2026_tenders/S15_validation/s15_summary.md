# Scenario 15: P2P + FedEx 3-Group Static Routing

## Executive Summary

Scenario 15 replaces the current 4-carrier mix with a **2-relationship setup** (P2P + FedEx) using **3 static routing rules** configurable in SPE. It achieves **$5,099,099 (-16.0% vs S1)**, saving **$972,963/year** while reducing operational complexity.

Compared to S4 (the best scenario using the current carriers at 0% earned), S15 saves **$456,090 more per year** — made possible by replacing OnTrac and USPS with P2P's cheaper lightweight rates and maintaining FedEx's 16% earned discount (which S4 loses).

| Metric                | S4 Current Optimal         | S14 Per-shipment       | S15 3-Group            | S13 Unconstrained      |
|-----------------------|----------------------------|------------------------|------------------------|------------------------|
| Annual cost           | $5,555,189                 | **$4,944,680**         | $5,099,099             | $5,178,926             |
| Savings vs S1         | -8.5%                      | **-18.6%**             | -16.0%                 | -14.7%                 |
| FedEx earned discount | 0% (lost)                  | 16% HD / 4% SP         | 16% HD / 4% SP         | 0% (lost)              |
| Carrier relationships | 3 (OnTrac, USPS, FedEx)    | 2 (P2P, FedEx)         | 2 (P2P, FedEx)         | 2 (P2P, FedEx)         |
| SPE complexity        | Per-shipment optimal       | 108K forced switches   | **3 rules + ZIP list** | Per-shipment cheapest  |
| Volume commitments    | OnTrac 279K, USPS 140K     | None                   | None                   | None                   |

**Key finding:** SmartPost size/weight limits (implemented 2026-02-18) shift many FedEx packages from SmartPost to Home Delivery. Because HD generates 2.70x undiscounted spend per dollar of base rate (vs SP's 1.98x), the $5.1M threshold is now easier to meet. This allows S15 to use generous Medium cutoffs (PFAP≤21 lbs) while clearing the threshold with $33K margin.

---

## How S15 Works

### Carriers

| Carrier  | Contract | Service Area              | Max Weight | Avg Cost | Role                           |
|----------|----------|---------------------------|:----------:|:--------:|--------------------------------|
| PFAP     | P2P US   | 38,599 ZIPs (~52% of US)  | 30 lbs     | $4.53    | Cheapest option, limited zones |
| PFA/PFS  | P2P US2  | 93,100 ZIPs (~100% of US) | 70 lbs     | $5.53    | Lightweight fallback           |
| FedEx HD | FedEx    | 100% of US                | 150 lbs    | $17.69   | Heavier packages (selected)    |
| FedEx SP | FedEx    | 100% of US                | 70 lbs     | $10.12   | Lighter packages (selected)    |

P2P operates two contracts: **P2P US** (PFAP, better rates, limited ZIP coverage) and **P2P US2** (PFA/PFS, full US coverage, higher rates). PFA and PFS are two services within P2P US2 — the calculator selects the cheaper service at the (packagetype, weight) group level.

FedEx rates are adjusted from baked earned discounts to target earned discount tiers using service-specific multipliers:
- **HD**: baked 18% → target 16%, multiplier 1.0541x on base rate + fuel
- **SP**: baked 4.5% → target 4.0%, multiplier 1.0099x on base rate + fuel

The FedEx calculator selects the cheaper of HD and SP per shipment, subject to SmartPost size/weight limits. **Packages exceeding SmartPost limits (L+G >84", weight >20 lbs, any dimension >27", second longest >17") are automatically routed to Home Delivery.** This affects a large portion of shipments — FedEx HD now handles 59.5% of FedEx shipments (vs 24% before SmartPost limit enforcement).

### Package Type Groups

All 54 package types are classified into 3 groups based on their physical characteristics and cost profiles. The classification reuses S10's per-packagetype analysis:

| Group  | Logic                                     | Pkg Types | Shipments | Share | Examples                                          |
|--------|-------------------------------------------|:---------:|:---------:|:-----:|---------------------------------------------------|
| Light  | Small/flat, P2P competitive up to ~3 lbs  | 20        | 350,835   | 65.0% | Pizza boxes up to 36x24, wraps, tubes, poly bags  |
| Medium | Mid-size, P2P competitive up to ~21 lbs   | 18        | 116,561   | 21.6% | Pizza boxes 24x20+, cross packaging, strapped     |
| Heavy  | Oversized, FedEx always cheapest          | 15        | 72,521    | 13.4% | Pizza boxes 42x32+, 48x36, 40x30                 |

### Routing Rules

```
LIGHT packages:
  IF destination ZIP in PFAP list AND ceil(weight) <= 3 lbs  -->  PFAP
  IF destination ZIP NOT in PFAP list AND ceil(weight) <= 1 lbs  -->  PFA or PFS
  ELSE  -->  FedEx

MEDIUM packages:
  IF destination ZIP in PFAP list AND ceil(weight) <= 21 lbs  -->  PFAP
  IF destination ZIP NOT in PFAP list AND ceil(weight) <= 2 lbs  -->  PFA or PFS
  ELSE  -->  FedEx

HEAVY packages:
  -->  FedEx always
```

**SPE requires:** 5 prioritized rules + 1 ZIP list (38,599 PFAP ZIPs) + 1 package type-to-group mapping. See the [Implementation](#implementation) section for the exact SPE rule setup.

### Why These Cutoffs

The cutoffs were found by brute-force search over all possible (PFAP_cutoff, PFA/PFS_cutoff) combinations per group, subject to the FedEx undiscounted spend threshold constraint.

**PFAP cutoff of 3 lbs (Light) / 21 lbs (Medium):** PFAP has the cheapest rates in the system ($4.53 avg). For Light packages, PFAP beats FedEx up to 3 lbs — above that, FedEx's dimensional weight advantage (small packages = low DIM weight) makes it competitive. For Medium packages, PFAP wins up to 21 lbs because FedEx's DIM weight penalty on these larger packages is severe. **The Medium PFAP cutoff of 21 lbs is at the unconstrained optimum** — the FedEx threshold constraint does not reduce it.

**PFA/PFS cutoff of 1 lb (Light) / 2 lbs (Medium):** P2P US2 rates are competitive at lighter weights. The constraint reduces these from the unconstrained optimum to push enough undiscounted spend to FedEx. The constraint cost is modest because only PFA/PFS cutoffs are reduced — PFAP cutoffs remain at the unconstrained optimum.

**Heavy always FedEx:** Oversized packages (42x32+, 48x36, etc.) are too large for P2P's competitive rates.

**Why the constraint is loose:** SmartPost size/weight limits force many packages from SP to HD. HD generates 2.70x undiscounted spend per dollar of base rate (1/0.370) vs SP's 1.98x (1/0.505). With HD now handling 59.5% of FedEx shipments, each dollar of FedEx base rate generates more undiscounted spend, making the $5.1M threshold easier to clear.

---

## How the Optimization Was Run

### Step 1: Precompute Cost Grids

For Light and Medium groups, compute total cost and FedEx HD/SP base rates for every possible (PFAP_cutoff, PFA/PFS_cutoff) combination:
- PFAP cutoff: 0 to 30 (P2P US max weight)
- PFA/PFS cutoff: 0 to 10 (P2P US2 only competitive at low weights)
- 341 combinations per group

Heavy group is fixed at FedEx always (no cutoffs to search).

### Step 2: Exhaustive Search

Test all Light x Medium cutoff combinations (341 x 341 = 116,281 total). For each:
1. Sum total cost across Light + Medium + Heavy
2. Sum FedEx HD and SP base rates across all three groups
3. Compute undiscounted: `HD_base / 0.370 + SP_base / 0.505`
4. Check if undiscounted >= $5,100,000

Track both the unconstrained best (cheapest total) and constrained best (cheapest total where threshold is met).

### Step 3: Results

| Variant         | Light Cutoffs        | Medium Cutoffs        | Total Cost     | FedEx Undiscounted | Threshold Met |
|-----------------|----------------------|-----------------------|----------------|--------------------|----|
| **Constrained** | **PFAP<=3, US2<=1**  | **PFAP<=21, US2<=2**  | **$5,099,099** | **$5,133,406**     | **YES** |

The constraint enforcement secures the FedEx 16% HD / 4% SP earned discount and avoids the $500K penalty. The constraint only reduces PFA/PFS (P2P US2) cutoffs. **PFAP cutoffs remain at the unconstrained optimum** for both groups.

---

## Results

### Carrier Split

| Carrier         | Shipments   | Share    | Total Cost     | Avg Cost  |
|-----------------|-------------|----------|----------------|-----------|
| PFAP            | 216,075     | 40.0%    | $978,249       | $4.53     |
| PFA/PFS         | 67,871      | 12.6%    | $375,615       | $5.53     |
| FedEx (total)   | 255,971     | 47.4%    | $3,745,234     | $14.63    |
|   FedEx HD      | 152,438     | 28.2%    | $2,697,192     | $17.69    |
|   FedEx SP      | 103,533     | 19.2%    | $1,048,042     | $10.12    |
| **Total**       | **539,917** | **100%** | **$5,099,099** | **$9.44** |

P2P handles 52.6% of shipments (the lightweight ones), FedEx handles 47.4% (heavier packages and everything outside P2P cutoffs). P2P US2 costs include USPS-equivalent peak surcharges (Oct 5 - Jan 18).

### FedEx HD / SP Breakdown

| Service   | Base Rate   | Undiscounted     | Share of Undiscounted |
|-----------|-------------|------------------|-----------------------|
| FedEx HD  | $1,361,838  | $3,680,643       | 71.7%                 |
| FedEx SP  | $733,645    | $1,452,762       | 28.3%                 |
| **Total** |             | **$5,133,406**   | **100%**              |

**Home Delivery now dominates undiscounted spend (71.7%)** because SmartPost size/weight limits force many packages to HD. Before SmartPost limit enforcement, SmartPost dominated at 73% — the ratio has completely reversed. HD handles the majority of FedEx shipments: 152,438 (59.5%) vs SP's 103,533 (40.5%).

**Undiscounted computation:**
- HD: `$1,361,838 / 0.370` = $3,680,643 (where 0.370 = 1 - 0.45 PP - 0.18 baked earned)
- SP: `$733,645 / 0.505` = $1,452,762 (where 0.505 = 1 - 0.45 PP - 0.045 baked earned)
- Total: $5,133,406

### Per-Group Carrier Split

| Group  | Shipments | PFAP        | PFA/PFS      | FedEx            |
|--------|-----------|-------------|--------------|------------------|
| Light  | 350,835   | ~46%        | ~19%         | ~35%             |
| Medium | 116,561   | ~49%        | ~1%          | ~50%             |
| Heavy  | 72,521    | —           | —            | 72,521 (100%)    |

**Light group** is the biggest cost saver: ~65% of Light shipments go to P2P at $4.53-5.53/ship instead of the current mix's higher avg. The ~35% that go to FedEx are heavier Light packages (4+ lbs) or 2+ lb packages outside PFAP zones.

**Medium group** splits between PFAP (where P2P US delivers at <=21 lbs) and PFA/PFS (packages outside PFAP zones at <=2 lbs) and FedEx (everything else). With PFAP cutoff at 21 lbs, nearly half of Medium shipments go to PFAP. With the PFA/PFS cutoff reduced to 2 lbs, very few Medium shipments go to P2P US2.

**Heavy group** is 100% FedEx.

### FedEx Threshold

| Metric                           | Value            |
|----------------------------------|------------------|
| FedEx HD base rate               | $1,361,838       |
| FedEx SP base rate               | $733,645         |
| HD undiscounted (/ 0.370)        | $3,680,643       |
| SP undiscounted (/ 0.505)        | $1,452,762       |
| **Total undiscounted**           | **$5,133,406**   |
| $5.1M constraint threshold       | $5,100,000       |
| $5.0M penalty threshold          | $5,000,000       |
| $4.5M earned discount floor      | $4,500,000       |
| **Margin above $5.1M**           | **$33,406**      |
| **Margin above $5M**             | **$133,406**     |
| **Margin above $4.5M**           | **$633,406**     |
| Earned discount                  | **16% HD / 4% SP** |

The undiscounted equivalent uses split baked factors because HD and SP have different baked earned discounts:
- HD: baked earned = 18%, so baked factor = 1 - 0.45 - 0.18 = 0.370
- SP: baked earned = 4.5%, so baked factor = 1 - 0.45 - 0.045 = 0.505

**HD now contributes 71.7% of undiscounted spend** (vs 28.3% SP). This shift is driven by SmartPost size/weight limits forcing oversized packages from SP to HD. Because HD generates more undiscounted per dollar (2.70x vs 1.98x), the threshold is now significantly easier to meet.

**The $33K margin above the $5.1M constraint is improved** from the pre-matched-only dataset. The $133K margin above the $5M penalty threshold provides reasonable safety.

### Cost of the Constraint

| Metric                          | Value         |
|---------------------------------|---------------|
| Constrained (>= $5.1M undisc.) | $5,099,099    |

The constraint only reduces PFA/PFS cutoffs (Light US2 reduced to 1, Medium US2 reduced to 2). **PFAP cutoffs are not constrained** — both groups use their unconstrained optimum (Light PFAP=3, Medium PFAP=21). The constraint shifts PFA/PFS-eligible shipments (lightweight packages outside PFAP zones) to FedEx.

---

## S15 vs Other 2-Carrier Scenarios

S15 competes against S13 and S14 — all three use only P2P + FedEx (2 carrier relationships).

### Head-to-Head

| Metric                   | S14 Constrained        | S15 3-Group            | S13 Unconstrained      |
|--------------------------|------------------------|------------------------|------------------------|
| **Annual cost**          | **$4,944,680**         | $5,099,099             | $5,178,926             |
| **Savings vs S1**        | $1,127,382 (18.6%)     | $972,963 (16.0%)       | $893,136 (14.7%)       |
| FedEx earned discount    | 16% HD / 4% SP         | 16% HD / 4% SP         | 0% (lost)              |
| FedEx undiscounted spend | >=5,100,000            | $5,133,406             | Below $5M              |
| SPE complexity           | 108K forced switches   | **3 rules + ZIP list** | Per-shipment cheapest  |
| Constraint cost          | See S14 summary        | See above              | None                   |

### S14 vs S15: Per-Shipment vs Group Rules

S14 is $154K/year cheaper because per-shipment optimization is strictly more flexible than group-based cutoffs. S14 can assign each shipment to its cheapest carrier individually, while S15 applies uniform weight cutoffs within each group.

**S15's advantage is implementability.** S14 requires 108K individual shipment overrides from P2P to FedEx — these are specific (packagetype, ZIP, weight) combinations that would need per-shipment routing in SPE. S15 achieves 86% of S14's savings with just 5 rules + a ZIP list.

| Metric                          | S14              | S15              |
|---------------------------------|------------------|------------------|
| Constrained total               | $4,944,680       | $5,099,099       |
| **Simplification cost (vs S14)**|                  | **$154,419**     |
| SPE rules needed                | 108K overrides   | 5 rules          |

### Why S15 (and S14) Beat S13

With SmartPost size/weight limits, losing the FedEx earned discount (S13's approach) is **more expensive than maintaining it**. SmartPost limits force many packages from SP to HD. At 0% earned, the HD multiplier is 1.4865x (devastating). At 16% earned, it's only 1.0541x. The large HD population amplifies this difference.

S13's FedEx undiscounted spend is far below any threshold at 0% earned. The 0% earned assumption is confirmed self-consistent but costly. **Maintaining the earned discount saves $234K/year** (S14 vs S13) or **$80K/year** (S15 vs S13).

---

## S15 in Full Scenario Context

| Rank  | Scenario                       | Cost           | vs S1      | Carriers | FedEx Earned     | SPE Complexity        |
|:-----:|--------------------------------|----------------|------------|:--------:|:----------------:|-----------------------|
| 1     | S14 P2P+FedEx per-shipment     | $4,944,680     | -18.6%     | 2        | 16% HD / 4% SP   | 108K forced switches  |
| **2** | **S15 3-Group P2P+FedEx**      | **$5,099,099** | **-16.0%** | **2**    | **16% HD / 4% SP** | **3 rules + ZIP list**|
| 3     | S13 P2P+FedEx unconstrained    | $5,178,926     | -14.7%     | 2        | 0%               | Per-shipment cheapest |

*3-carrier scenarios (S7, S10, S11) may achieve different savings — their summaries need updating after SmartPost limit enforcement. S4 (current carrier optimal at 0% earned) is also affected.*

S15 ranks **1st among implementable 2-carrier scenarios**. S14 is $154K cheaper but requires 108K per-shipment routing overrides — not configurable through simple SPE rules. S13 at 0% earned is confirmed self-consistent but $80K more expensive than S15.

---

## Implementation

### SPE Configuration

SPE needs 3 data inputs and a set of prioritized rules that are evaluated top-to-bottom per shipment.

#### Input 1: Package Type to Group mapping

Each package type is assigned to exactly one group. This mapping is stored in SPE as a lookup table or attribute on the package type.

| Group  | Package types (20)                                                                                                                                                                    |
|--------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Light  | PIZZA BOX 20x16x1, 12x8x1, 16x12x2, 36x24x2; WRAP 16''x12'', 24''x16''; 21'' Tube, 26'' Tube; POLY BAG 9x12, 12x15; BUBBLE MAILER 9x14; MUG BOX 5x5x5, 9x7x5, 16x6x4; MIXPIX BOX, MIXPIX BOX\_(2), MIXPIX BOX\_(4); Carpet Box 22x4x4, 37x5x5 |
| Medium | PIZZA BOX 24x20x2, 20x16x2, 27x23x2, 30x20x3; CROSS PACKAGING 30X24''; MUG BOX 16x12x8; POLY BAG 14,5x19; BOX 16x24x12; all "(2x strapped)" and "(3x strapped)" variants of 24x20x2, 30x20x3, 36x24x2, 27x23x2; WRAP 36''x24'', 27''x23'', 36''x24'' [x2] |
| Heavy  | PIZZA BOX 42x32x2, 48X36X1, 40x30x1, 40x30x2; CROSS PACKAGING 49X30'', 40X30'', 40X40''; all 42x32x2 strapped, 40x30x2 strapped; WRAP 40''x30'', 36''x24'' [x3], 40''x30'' [x3]; PIZZA BOX 27x23x2 (3x strapped); PAPIER-VERSANDTASCHE klein 250x353x50 |

See `routing_rules.csv` for the complete 54-row mapping. **Default for unknown/new package types: Heavy** — this routes to FedEx always, which is the safe default that can never increase cost vs current routing.

#### Input 2: PFAP ZIP list

A list of 38,599 5-digit ZIP codes where P2P US (PFAP) delivers. Stored as a ZIP list or zone file in SPE. See `p2p_us_zip_codes.csv`.

This list determines whether a shipment is eligible for PFAP (cheapest carrier) or falls to PFA/PFS (second cheapest) or FedEx.

#### Input 3: Weight rounding

All weight comparisons use `ceil(weight_lbs)` — the actual weight rounded up to the next whole pound. A 1.2 lb package counts as 2 lbs. A 3.0 lb package counts as 3 lbs.

SPE must apply this ceiling before evaluating the rules below.

#### Rule evaluation

Rules are evaluated **in priority order** per shipment. The first matching rule wins. If no rule matches, the shipment goes to FedEx (the fallback).

```
RULE 1 — Light packages to PFAP
  IF group = "Light"
  AND destination_zip IN pfap_zip_list
  AND ceil(weight_lbs) <= 3
  THEN carrier = PFAP

RULE 2 — Light packages to PFA/PFS
  IF group = "Light"
  AND destination_zip NOT IN pfap_zip_list
  AND ceil(weight_lbs) <= 1
  THEN carrier = PFA/PFS

RULE 3 — Medium packages to PFAP
  IF group = "Medium"
  AND destination_zip IN pfap_zip_list
  AND ceil(weight_lbs) <= 21
  THEN carrier = PFAP

RULE 4 — Medium packages to PFA/PFS
  IF group = "Medium"
  AND destination_zip NOT IN pfap_zip_list
  AND ceil(weight_lbs) <= 2
  THEN carrier = PFA/PFS

RULE 5 — Everything else to FedEx
  ELSE carrier = FedEx (HD or SP, selected by FedEx)
```

Rule 5 catches: all Heavy packages, Light packages above the weight cutoff, Medium packages above the weight cutoff, and any edge cases. FedEx selects HD or SP per shipment based on which is cheaper (subject to SmartPost size/weight limits).

#### PFA vs PFS service selection

When a shipment is routed to "PFA/PFS", the specific service (PFA or PFS) is selected by P2P based on the package type and weight. This selection happens on P2P's side — SPE only needs to route to the P2P US2 contract. The calculator pre-determines the cheaper service at the (packagetype, weight_bracket) group level.

#### What each rule handles

| Rule | Group  | Carrier | Shipments | Share  | Approx Cost  |
|:----:|--------|---------|----------:|-------:|-------------:|
| 1    | Light  | PFAP    | ~46% of Light | ~30%  | —           |
| 2    | Light  | PFA/PFS | ~19% of Light | ~12%  | —           |
| 3    | Medium | PFAP    | ~49% of Med   | ~11%  | —           |
| 4    | Medium | PFA/PFS | ~1% of Med    | ~0.3% | —           |
| 5    | All    | FedEx   | 255,971   | 47.4%  | $3,745,234   |
|      |        | **Total** | **539,917** | **100%** | **$5,099,099** |

Rules 1 and 2 handle ~65% of Light packages. Rule 3 handles ~49% of Medium. Rule 4 handles a small share of Medium shipments (PFA/PFS cutoff at 2 lbs limits eligibility). Rule 5 is the catch-all for everything heavy or above cutoff — this includes both FedEx HD and SP, with FedEx selecting the cheaper service per shipment (subject to SmartPost limits).

#### Maintenance

- **New package types**: Assign to a group (default Heavy if unsure). No rule changes needed.
- **PFAP ZIP changes**: Update the ZIP list. No rule changes needed.
- **Weight cutoff changes**: Requires rule modification (only if re-optimizing).

### Detailed Rules per Package Type

See `routing_rules_detailed.csv` for the complete (packagetype, weight_bracket, carrier) lookup table. This file can be used as a validation reference to verify SPE is routing correctly, or as an alternative SPE configuration if the rule-based approach above isn't feasible (i.e., configure SPE with explicit package-type + weight-bracket rules instead of 5 group-based rules).

---

## Data Files

| File                          | Location                                              | Contents                                                   |
|-------------------------------|-------------------------------------------------------|------------------------------------------------------------|
| Routing rules (summary)       | `results/scenario_15.../routing_rules.csv`            | 54 rows: packagetype, group, cutoffs                       |
| Routing rules (detailed)      | `results/scenario_15.../routing_rules_detailed.csv`   | Per packagetype, weight range, carrier per zone type       |
| Carrier selection              | `results/scenario_15.../carrier_selection.csv`        | 5 rows: carrier totals + FedEx HD/SP                       |
| Group summary                  | `results/scenario_15.../group_summary.csv`            | 3 rows: group cutoffs                                      |
| PFAP ZIP list                  | `results/scenario_15.../p2p_us_zip_codes.csv`         | 38,599 ZIPs                                                |
| December shipment detail       | `results/scenario_15.../december_2025_shipments.csv`  | 124,451 rows: per-shipment assignment + cost breakdown     |
| Actuals vs S15 by packagetype  | `results/scenario_15.../actuals_vs_s15_by_packagetype.csv` | 52 rows: Nov+Dec avg cost comparison                  |
| Summary metrics                | `results/scenario_15.../summary_metrics.csv`          | Key metrics including HD/SP split                          |

---

*Updated: February 2026*
*Data basis: 539,917 matched-only shipments (2025 volumes), 2026 rate cards*
*FedEx calculator v2026.02.18.1 — SmartPost size/weight limits enforced (L+G >84", wt >20 lbs, dim >27", 2nd dim >17" → override to HD)*
*FedEx HD at 16% earned discount (1.0541x), SP at 4% earned discount (1.0099x)*
*P2P US2 costs include USPS-equivalent peak surcharges (Oct 5 - Jan 18)*
*FedEx threshold: undiscounted spend >= $5.1M ($33K margin — HD $3.68M + SP $1.45M)*
*Baseline: $6,072,062 (Scenario 1 current mix)*
