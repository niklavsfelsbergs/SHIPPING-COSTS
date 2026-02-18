# Scenario 15: P2P + FedEx 3-Group Static Routing

## Executive Summary

Scenario 15 replaces the current 4-carrier mix with a **2-relationship setup** (P2P + FedEx) using **3 static routing rules** configurable in SPE. It achieves **$4,537,889 (-24.0% vs S1)**, saving **$1,433,859/year** while reducing operational complexity.

Compared to S4 (the best scenario using the current carriers), S15 saves **$954,904 more per year** (-17.4% vs S4) despite using fewer carrier relationships — made possible by replacing OnTrac and USPS with P2P's cheaper lightweight rates and maintaining FedEx's 16% earned discount (which S4 loses).

| Metric                        | S4 Current Optimal   | S15 P2P+FedEx        | Difference          |
|-------------------------------|----------------------|----------------------|---------------------|
| Annual cost                   | $5,492,793           | $4,537,889           | **-$954,904**       |
| Savings vs S1                 | -8.0%                | -24.0%               | +16.0pp             |
| Carrier relationships         | 3 (OnTrac, USPS, FedEx) | 2 (P2P, FedEx)   | -1                  |
| FedEx earned discount         | 0% (lost)            | 16% (maintained)     | +16pp               |
| SPE complexity                | Per-shipment optimal | 3 rules + ZIP list   | Simpler             |
| Volume commitments            | OnTrac 279K, USPS 140K | None              | No constraints      |

---

## How S15 Works

### Carriers

| Carrier | Contract    | Service Area              | Max Weight | Avg Cost | Role                           |
|---------|-------------|---------------------------|:----------:|:--------:|--------------------------------|
| PFAP    | P2P US      | 38,599 ZIPs (~52% of US)  | 30 lbs     | $4.54    | Cheapest option, limited zones |
| PFA     | P2P US2     | 93,100 ZIPs (~100% of US) | 30 lbs     | $5.77    | Lightweight fallback           |
| PFS     | P2P US2     | 93,100 ZIPs (~100% of US) | 70 lbs     | $6.09    | Lightweight fallback           |
| FedEx   | FedEx       | 100% of US                | 150 lbs    | $13.24   | Heavy packages + threshold     |

P2P operates two contracts: **P2P US** (PFAP, better rates, limited ZIP coverage) and **P2P US2** (PFA/PFS, full US coverage, higher rates). PFA and PFS are two services within P2P US2 — the calculator selects the cheaper service at the (packagetype, weight) group level.

FedEx rates are adjusted from the baked 18% earned discount to 16% using a 1.0541x multiplier on base rate + fuel. This reflects the actual earned discount tier S15 qualifies for.

### Package Type Groups

All 54 package types are classified into 3 groups based on their physical characteristics and cost profiles. The classification reuses S10's per-packagetype analysis:

| Group    | Logic                                  | Pkg Types | Shipments   | Share  | Examples                                    |
|----------|----------------------------------------|:---------:|:-----------:|:------:|---------------------------------------------|
| Light    | Small/flat, P2P competitive up to ~7 lbs | 20      | 360,367     | 64.6%  | Pizza boxes up to 36x24, wraps, tubes, poly bags |
| Medium   | Mid-size, P2P competitive up to ~21 lbs  | 18      | 121,118     | 21.7%  | Pizza boxes 24x20+, cross packaging, strapped |
| Heavy    | Oversized, FedEx always cheapest         | 16      | 76,528      | 13.7%  | Pizza boxes 42x32+, 48x36, 40x30            |

### Routing Rules

```
LIGHT packages:
  IF destination ZIP in PFAP list AND ceil(weight) <= 3 lbs  -->  PFAP
  IF destination ZIP NOT in PFAP list AND ceil(weight) <= 2 lbs  -->  PFA or PFS
  ELSE  -->  FedEx

MEDIUM packages:
  IF destination ZIP in PFAP list AND ceil(weight) <= 21 lbs  -->  PFAP
  IF destination ZIP NOT in PFAP list AND ceil(weight) <= 2 lbs  -->  PFA or PFS
  ELSE  -->  FedEx

HEAVY packages:
  -->  FedEx always
```

**SPE requires:** 3 rules + 1 ZIP list (38,599 PFAP ZIPs) + 1 package type-to-group mapping. New/unknown package types default to Heavy (FedEx always) — the safe default that can never increase cost vs current routing.

### Why These Cutoffs

The cutoffs were found by brute-force search over all possible (PFAP_cutoff, PFA/PFS_cutoff) combinations per group, subject to the FedEx undiscounted spend threshold constraint.

**PFAP cutoff of 3 lbs (Light) / 21 lbs (Medium):** PFAP has the cheapest rates in the system ($4.54 avg). For Light packages, PFAP beats FedEx up to 3 lbs — above that, FedEx's dimensional weight advantage (small packages = low DIM weight) makes it competitive. For Medium packages, PFAP wins up to 21 lbs because FedEx's DIM weight penalty on these larger packages is severe.

**PFA/PFS cutoff of 2 lbs (both groups):** P2P US2 rates are only competitive at very light weights. Above 2 lbs, FedEx at 16% earned is cheaper for most zone/weight combinations. The constraint optimization confirmed 2 lbs as the optimal P2P US2 cutoff.

**Heavy always FedEx:** Oversized packages (42x32+, 48x36, etc.) are too large for P2P's competitive rates. FedEx handles them at $16.32 avg — still much cheaper than the current mix's $25.73 avg for these packages.

---

## How the Optimization Was Run

### Step 1: Precompute Cost Grids

For Light and Medium groups, compute total cost and FedEx base rate for every possible (PFAP_cutoff, PFA/PFS_cutoff) combination:
- PFAP cutoff: 0 to 30 (P2P US max weight)
- PFA/PFS cutoff: 0 to 10 (P2P US2 only competitive at low weights)
- 341 combinations per group

Heavy group is fixed at FedEx always (no cutoffs to search).

### Step 2: Exhaustive Search

Test all Light x Medium cutoff combinations (341 x 341 = 116,281 total). For each:
1. Sum total cost across Light + Medium + Heavy
2. Sum FedEx base rate across all three groups
3. Check if FedEx base rate >= $1,887,000 (= $5.1M undiscounted x 0.37 baked factor)

Track both the unconstrained best (cheapest total) and constrained best (cheapest total where threshold is met).

### Step 3: Results

| Variant        | Light Cutoffs      | Medium Cutoffs     | Total Cost   | FedEx Undiscounted | Threshold Met |
|----------------|--------------------|--------------------|--------------|--------------------|----|
| Unconstrained  | PFAP<=3, US2<=3    | PFAP<=21, US2<=4   | $4,468,986   | $4,119,560         | NO |
| **Constrained**| **PFAP<=3, US2<=2**| **PFAP<=21, US2<=2**| **$4,537,889** | **$5,222,850** | **YES** |

The only difference: PFA/PFS cutoff drops from 3 to 2 (Light) and 4 to 2 (Medium), shifting ~29K shipments from PFA/PFS to FedEx. This costs **$68,903/year** but secures the FedEx 16% earned discount and avoids the $500K penalty.

---

## Results

### Carrier Split

| Carrier | Shipments   | Share  | Total Cost     | Avg Cost | Avg Weight |
|---------|-------------|--------|----------------|----------|------------|
| PFAP    | 223,002     | 40.0%  | $1,011,433     | $4.54    | 2.2 lbs    |
| PFS     | 89,347      | 16.0%  | $543,634       | $6.09    | 1.1 lbs    |
| PFA     | 36,147      | 6.5%   | $208,660       | $5.77    | 1.1 lbs    |
| FedEx   | 209,517     | 37.5%  | $2,774,162     | $13.24   | 6.2 lbs    |
| **Total** | **558,013** | **100%** | **$4,537,889** | **$8.13** | |

P2P handles 62.5% of shipments (the lightweight ones), FedEx handles 37.5% (heavier packages and everything outside P2P cutoffs).

### Per-Group Carrier Split

| Group   | Shipments | PFAP          | PFA/PFS        | FedEx          |
|---------|-----------|---------------|----------------|----------------|
| Light   | 360,367   | 163,731 (45%) | 124,730 (35%)  | 71,906 (20%)   |
| Medium  | 121,118   | 59,271 (49%)  | 764 (1%)       | 61,083 (50%)   |
| Heavy   | 76,528    | —             | —              | 76,528 (100%)  |

**Light group** is the biggest cost saver: 80% of Light shipments go to P2P at $4.54-5.93/ship instead of the current mix's $8.50+ avg. The 20% that go to FedEx are heavier Light packages (4+ lbs) where FedEx's low DIM weight wins.

**Medium group** splits roughly evenly between PFAP (where P2P US delivers) and FedEx (everywhere else above 2 lbs). Only 764 Medium shipments use PFA/PFS — these are rare 1-2 lb Medium packages outside PFAP zones.

**Heavy group** is 100% FedEx at $16.32/ship avg — significantly cheaper than the current mix's $25.73 for these packages due to corrected SmartPost pricing in the 2026 rate tables.

### FedEx Threshold

| Metric                       | Value         |
|------------------------------|---------------|
| FedEx base rate total        | $1,932,455    |
| FedEx undiscounted equivalent | $5,222,850   |
| $5.0M penalty threshold      | $5,000,000    |
| $4.5M earned discount floor  | $4,500,000    |
| **Margin above $5M**         | **$222,850**  |
| **Margin above $4.5M**       | **$722,850**  |
| Earned discount              | **16%**       |

The undiscounted equivalent is computed as: `base_rate_total / 0.37`, where 0.37 = 1 - 0.45 (performance pricing) - 0.18 (baked earned discount). This formula needs to be validated against actual FedEx list prices (see V2 in validation plan).

### Cost of the Constraint

| Metric                          | Value         |
|---------------------------------|---------------|
| Unconstrained optimal           | $4,468,986    |
| Constrained (>= $5.1M undisc.) | $4,537,889    |
| **Constraint cost**             | **$68,903**   |

The constraint costs only $69K/year — far less than S14's $597K, because the weight cutoffs naturally route heavier (high-undiscounted-spend) shipments to FedEx. Only a small cutoff adjustment (PFA/PFS from 3 to 2 lbs) was needed to cross the threshold.

---

## S15 vs S4: Current Carrier Optimal

S4 represents the best possible outcome using the **current carriers** (OnTrac, USPS, FedEx) with their volume commitments honored. It is the "do nothing about carrier relationships, just optimize routing" baseline.

### Head-to-Head

| Metric                       | S4 Current Optimal     | S15 P2P+FedEx           |
|------------------------------|------------------------|-------------------------|
| **Annual cost**              | **$5,492,793**         | **$4,537,889**          |
| **Savings vs S1**            | $478,955 (8.0%)        | $1,433,859 (24.0%)      |
| **S15 advantage**            |                        | **$954,904/year**       |
| FedEx earned discount        | 0% (lost)              | 16% (maintained)        |
| FedEx undiscounted spend     | ~$1.6M                 | $5.2M                   |
| Carrier relationships        | 3                      | 2                       |
| Volume commitments           | OnTrac 279K, USPS 140K | None                    |
| SPE complexity               | Per-shipment optimal   | 3 rules + ZIP list      |

S15 saves nearly **$1M/year more** than S4 while being simpler to implement and operate.

### Why S15 Beats S4 by $955K

Three factors compound:

**1. FedEx earned discount: ~$680K**

S4 loses the FedEx earned discount entirely. When S4 optimizes routing, FedEx volume drops to 55K shipments (~$1.6M undiscounted) — far below the $4.5M threshold. FedEx rates inflate by 49% (1.4865x multiplier). S15 maintains the 16% tier ($5.2M undiscounted), keeping FedEx rates only 5.4% above the baked 18% level.

The earned discount is worth approximately $680K/year on S15's FedEx volume. S4's loss of this discount is its single biggest disadvantage.

**2. P2P replaces OnTrac and USPS: ~$200K**

S4 uses OnTrac ($9.19 avg) and USPS ($7.74 avg) for lightweight packages. S15 uses PFAP ($4.54 avg) and PFA/PFS ($5.93 avg). P2P is significantly cheaper than both incumbent carriers for packages under 3 lbs — which represent the majority of volume.

| Weight Range | S4 Avg Cost (OnTrac/USPS) | S15 Avg Cost (P2P) | S15 Cheaper By |
|:------------:|:-------------------------:|:-------------------:|:--------------:|
| 0-1 lbs      | $6.38                     | $4.87               | -$1.51         |
| 1-2 lbs      | $7.92                     | $5.12               | -$2.80         |
| 2-3 lbs      | $8.74                     | $5.47               | -$3.27         |

**3. No volume commitments: ~$75K**

S4 must route 279K shipments to OnTrac and 140K to USPS, even when those aren't the cheapest option. The constraint costs S4 $174K in suboptimal routing. S15 has no minimum volume requirements — every shipment goes to its cheapest eligible carrier within the group rules.

### What S4 Does Better

S4 has one advantage: **no carrier transition risk.** OnTrac, USPS, and FedEx are established relationships. S15 requires:
- Onboarding P2P (2 contracts)
- Terminating OnTrac (potential exit penalties, 279K/year minimum)
- Terminating USPS (potential exit penalties, 140K/year minimum)
- Validating P2P rates, coverage, and service levels

The $955K annual savings must be weighed against transition costs and risks.

---

## S15 in Full Scenario Context

| Rank | Scenario                          | Cost         | vs S1    | Carriers | FedEx Earned | SPE Complexity          |
|:----:|-----------------------------------|--------------|----------|:--------:|:------------:|-------------------------|
| 1    | S7 Optimal per-shipment           | $4,433,040   | -25.8%   | 3        | 16%          | 353K assignments        |
| 2    | S10 Per-packagetype rules         | $4,450,862   | -25.5%   | 3        | 16%          | ~50 rules + ZIP list    |
| 3    | S11 3-Group with USPS             | $4,516,218   | -24.4%   | 3        | 16%          | 3 rules + ZIP list      |
| **4** | **S15 3-Group P2P+FedEx**        | **$4,537,889** | **-24.0%** | **2** | **16%**    | **3 rules + ZIP list**  |
| 5    | S8 Conservative $5M buffer        | $4,536,690   | -24.0%   | 3        | 16%          | 353K assignments        |
| 6    | S14 P2P+FedEx constrained        | $4,858,916   | -18.6%   | 2        | 16%          | 187K forced switches    |
| 7    | S13 P2P+FedEx unconstrained      | $4,942,666   | -17.2%   | 2        | 0%           | Per-shipment cheapest   |
| 8    | S6 USPS+FedEx (Drop OnTrac)      | $5,040,871   | -15.6%   | 2        | 16%          | Per-shipment            |
| 9    | S5 Constrained + P2P             | $5,393,088   | -9.7%    | 4        | 0%           | Per-shipment            |
| 10   | **S4 Current carrier optimal**   | **$5,492,793** | **-8.0%** | **3** | **0%**     | **Per-shipment**        |
| 11   | S9 Maersk (NSD $9)               | $5,495,484   | -8.0%    | 1        | n/a          | None                    |
| 12   | S3 100% FedEx                     | $5,889,066   | -1.4%    | 1        | 18%          | None                    |
| 13   | S1 Current mix                    | $5,971,748   | —        | 4        | 16%          | As-is                   |
| 14   | S2 100% Maersk                    | $6,041,478   | +1.2%    | 1        | n/a          | None                    |
| 15   | S12 100% P2P Combined             | $6,788,506   | +13.7%   | 1        | n/a          | Per-shipment cheapest   |

S15 ranks 4th on pure cost but 1st on cost-adjusted-for-complexity: it achieves 93% of S7's savings with only 2 carrier relationships and 3 SPE rules. The $105K gap to S7 buys dramatically simpler operations.

### Key Comparisons

**vs S11 (+$22K, same SPE complexity, -1 carrier):**
S11 uses USPS as the non-PFAP lightweight fallback. S15 uses PFA/PFS instead. The $22K premium is the cost of eliminating the USPS relationship. S15 also has slightly less FedEx threshold margin ($223K vs $194K) — both are comfortable.

**vs S14 (-$321K, same carriers, simpler SPE):**
S14 uses per-shipment optimization then force-switches 187K P2P shipments to FedEx. S15's weight cutoffs naturally route the right shipments to FedEx through blunt thresholds, achieving the FedEx spend target at $69K constraint cost instead of S14's $597K. Static rules outperform per-shipment forcing because they select heavier (higher undiscounted spend per shipment) packages for FedEx.

**vs S4 (-$955K, fewer carriers, simpler SPE):**
See detailed comparison above. S15 wins on every dimension: cost, carrier count, complexity, and FedEx discount status.

---

## Implementation

### SPE Configuration

**1. Package Type to Group mapping** (one-time setup, update when new package types are added)

54 package types mapped to 3 groups. See `routing_rules.csv` for the full mapping. Default for unknown types: Heavy (FedEx always).

**2. PFAP ZIP list** (periodic refresh if P2P US coverage changes)

38,599 ZIP codes where P2P US (PFAP) delivers. See `p2p_us_zip_codes.csv`.

**3. Three routing rules**

| Group  | Condition                                       | Carrier  |
|--------|-------------------------------------------------|----------|
| Light  | ZIP in PFAP list AND ceil(weight) <= 3 lbs      | PFAP     |
| Light  | ZIP NOT in PFAP list AND ceil(weight) <= 2 lbs  | PFA/PFS  |
| Light  | Otherwise                                        | FedEx    |
| Medium | ZIP in PFAP list AND ceil(weight) <= 21 lbs     | PFAP     |
| Medium | ZIP NOT in PFAP list AND ceil(weight) <= 2 lbs  | PFA/PFS  |
| Medium | Otherwise                                        | FedEx    |
| Heavy  | Always                                           | FedEx    |

### Detailed Rules per Package Type

See `routing_rules_detailed.csv` for the complete (packagetype, weight_bracket, carrier) lookup table — 102 rows covering every combination. This file can be used directly for SPE configuration or as a validation reference.

---

## Data Files

| File                          | Location                                      | Contents                              |
|-------------------------------|-----------------------------------------------|---------------------------------------|
| Routing rules (summary)      | `results/scenario_15.../routing_rules.csv`    | 54 rows: packagetype, group, cutoffs  |
| Routing rules (detailed)     | `results/scenario_15.../routing_rules_detailed.csv` | 102 rows: packagetype, weight range, carrier per zone type |
| Carrier selection             | `results/scenario_15.../carrier_selection.csv`| 3 rows: carrier totals                |
| Group summary                 | `results/scenario_15.../group_summary.csv`    | 3 rows: group cutoffs                 |
| PFAP ZIP list                 | `results/scenario_15.../p2p_us_zip_codes.csv` | 38,599 ZIPs                          |
| December shipment detail      | `results/scenario_15.../december_2025_shipments.csv` | 124,451 rows: per-shipment assignment + cost breakdown |
| Actuals vs S15 by packagetype | `results/scenario_15.../actuals_vs_s15_by_packagetype.csv` | 52 rows: Nov+Dec avg cost comparison |
| Summary metrics               | `results/scenario_15.../summary_metrics.csv`  | Key metrics                           |

---

*Created: February 2026*
*Data basis: 558,013 shipments (2025 volumes), 2026 rate cards*
*FedEx at 16% earned discount (1.0541x multiplier from baked 18%)*
*FedEx threshold: undiscounted spend >= $5.1M ($222K margin above $5M penalty)*
*Baseline: $5,971,748 (Scenario 1 current mix, FedEx at 16% earned discount)*
*S4 baseline: $5,492,793 (current carrier optimal, FedEx at 0% earned discount)*
