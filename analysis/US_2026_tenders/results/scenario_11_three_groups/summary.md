# Scenario 11: 3-Group Static Routing Rules (Simplified S10)

## Executive Summary

Scenario 11 simplifies S10's ~50 per-packagetype routing rules into **3 group rules** that achieve **94.6% of S7's theoretical savings** while requiring only **3 rules + a P2P zip list** to configure.

| Metric                    | S11 3-Group          | S10 Per-Packagetype  | S7 Optimal           |
|---------------------------|----------------------|----------------------|----------------------|
| Total cost                | **$4,516,218**       | $4,450,862           | $4,433,040           |
| Savings vs S1             | **24.4%**            | 25.5%                | 25.8%                |
| Gap vs S7                 | **+$83,178**         | +$17,822             | —                    |
| FedEx 16% tier            | **MET ($194K margin)** | MET ($17K margin)  | MET ($15 margin)     |
| Configuration complexity  | **3 rules + zip list** | ~50 rules + zip list | 353K cell assignments |

The tradeoff: **$65K/year more** than S10, but **far simpler to implement** and **$194K of FedEx threshold headroom** (vs S10's thin $17K).

## How It Works

### Package Type Groups

All package types are assigned to one of three groups based on their physical characteristics:

| Group    | Description                            | Pkg Types | Shipments   | Share  |
|----------|----------------------------------------|:---------:|:-----------:|:------:|
| Light    | Small, flat packages                   |    20     |   360,367   | 64.6%  |
| Medium   | Mid-size packages                      |    18     |   121,118   | 21.7%  |
| Heavy    | Oversized packages                     |    16     |    76,528   | 13.7%  |

### Routing Rules

```
IF package is in LIGHT group:
    IF destination is in P2P zone AND weight ≤ 3 lbs → P2P
    IF destination is NOT in P2P zone AND weight ≤ 3 lbs → USPS
    ELSE → FedEx

IF package is in MEDIUM group:
    IF destination is in P2P zone AND weight ≤ 21 lbs → P2P
    IF destination is NOT in P2P zone AND weight ≤ 2 lbs → USPS
    ELSE → FedEx

IF package is in HEAVY group:
    → FedEx always
```

### Why These Cutoffs

**Light group (P2P ≤ 3, USPS ≤ 3):** These are small/flat packages (pizza boxes up to 36x24, wraps, poly bags, mug boxes, tubes). P2P and USPS are significantly cheaper than FedEx at 1-3 lbs, but FedEx becomes competitive above 3 lbs due to the packages' small dimensions keeping FedEx's dimensional weight low.

**Medium group (P2P ≤ 21, USPS ≤ 2):** These are mid-size packages (24x20, 20x16x2, 30x20x3, cross packaging, strapped variants). P2P wins up to high weights because FedEx's dimensional weight penalty is severe for these dimensions. USPS loses competitiveness fast — only cheapest at 1-2 lbs.

**Heavy group (always FedEx):** Oversized packages (42x32, 48x36, 40x30, cross 49x30/40x40). P2P and USPS either can't handle them or are more expensive at all weights.

## Group Definitions

### Light (20 package types, 360,367 shipments)

| Package Type               | Shipments |
|----------------------------|-----------|
| PIZZA BOX 20x16x1          | 117,206   |
| PIZZA BOX 12x8x1           | 55,898    |
| PIZZA BOX 16x12x2          | 43,674    |
| WRAP 16''x12''             | 42,298    |
| PIZZA BOX 36x24x2          | 37,143    |
| WRAP 24''x16''             | 23,432    |
| 21" Tube                   | 12,376    |
| POLY BAG 9x12              | 5,471     |
| 26" Tube                   | 4,717     |
| MUG BOX 5x5x5              | 4,464     |
| MIXPIX BOX                 | 3,239     |
| (blank)                    | 2,685     |
| BUBBLE MAILER 9x14         | 2,053     |
| MUG BOX 9x7x5              | 1,493     |
| MUG BOX 16x6x4             | 1,130     |
| Carpet Box 22x4x4          | 1,112     |
| POLY BAG 12x15             | 824       |
| MIXPIX BOX_(2)             | 504       |
| MIXPIX BOX_(4)             | 329       |
| Carpet Box 37x5x5          | 319       |

### Medium (18 package types, 121,118 shipments)

| Package Type                      | Shipments |
|-----------------------------------|-----------|
| PIZZA BOX 24x20x2                 | 40,950    |
| PIZZA BOX 20x16x2                 | 36,316    |
| CROSS PACKAGING 30X24"            | 15,128    |
| PIZZA BOX 30x20x3                 | 10,152    |
| MUG BOX 16x12x8                   | 4,962     |
| PIZZA BOX 27x23x2                 | 2,427     |
| POLY BAG 14,5x19                  | 2,043     |
| PIZZA BOX 24x20x2 (2x strapped)  | 1,846     |
| PIZZA BOX 30x20x3 (2x strapped)  | 1,519     |
| PIZZA BOX 36x24x2 (2x strapped)  | 1,479     |
| BOX 16x24x12                      | 1,666     |
| PIZZA BOX 36x24x2 (3x strapped)  | 777       |
| WRAP 36''x24'' [x2]               | 632       |
| PIZZA BOX 24x20x2 (3x strapped)  | 329       |
| WRAP 36''x24''                    | 307       |
| WRAP 27''x23''                    | 243       |
| PIZZA BOX 27x23x2 (2x strapped)  | 200       |
| PIZZA BOX 30x20x3 (3x strapped)  | 142       |

### Heavy (16 package types, 76,528 shipments)

| Package Type                      | Shipments |
|-----------------------------------|-----------|
| PIZZA BOX 42x32x2                 | 24,809    |
| PIZZA BOX 40x30x1                 | 21,002    |
| PIZZA BOX 48X36X1                 | 19,768    |
| PIZZA BOX 42x32x2 (2x strapped)  | 2,910     |
| CROSS PACKAGING 49X30"            | 2,254     |
| PIZZA BOX 40x30x2                 | 1,692     |
| CROSS PACKAGING 40X30"            | 1,483     |
| PIZZA BOX 42x32x2 (3x strapped)  | 1,133     |
| PIZZA BOX 40x30x2 (2x strapped)  | 441       |
| CROSS PACKAGING 40X40"            | 444       |
| PIZZA BOX 40x30x2 (3x strapped)  | 433       |
| + 5 rare types                    | 112       |

## Results

### Carrier Mix

| Carrier     | Shipments   | Share    | Total Cost     | Avg Cost    |
|-------------|-------------|---------|----------------|-------------|
| USPS        | 153,494     | 27.5%   | $1,021,208     | $6.65       |
| FedEx       | 181,517     | 32.5%   | $2,483,577     | $13.68      |
| P2P         | 223,002     | 40.0%   | $1,011,433     | $4.54       |
| **Total**   | **558,013** | **100%**| **$4,516,218** |             |

### Per-Group Carrier Split

| Group   | FedEx      | P2P        | USPS       |
|---------|------------|------------|------------|
| Light   | 43,906 (12%) | 163,731 (45%) | 152,730 (42%) |
| Medium  | 61,083 (50%) | 59,271 (49%)  | 764 (1%)      |
| Heavy   | 76,528 (100%) | —          | —          |

### FedEx Earned Discount

| Metric                  | Value           |
|-------------------------|-----------------|
| Base rate total         | $1,736,678      |
| Undiscounted equivalent | $4,693,725      |
| Threshold               | $4,500,000      |
| Margin                  | **+$193,725**   |
| 16% tier                | **MET**         |

The $194K margin is **11x more comfortable** than S10's $17K margin. This makes S11 much more resilient to seasonal volume shifts and future changes.

### P2P Zone Coverage

| Metric                  | Value           |
|-------------------------|-----------------|
| P2P zip codes           | 38,599          |
| Eligible shipments      | 289,272 (51.8%) |
| Actually routed to P2P  | 223,002 (77.1% of eligible) |

## Cutoff Optimization

### How the Cutoffs Were Found

For each group, a brute-force search tested all (P2P_cutoff, USPS_cutoff) combinations:
- P2P cutoff: 0 to 30
- USPS cutoff: 0 to 10

The search found the combination that minimizes total cost while keeping FedEx undiscounted spend ≥ $4.5M.

### Unconstrained vs Constrained

| Variant          | Light         | Medium          | Cost       | FedEx Threshold |
|------------------|---------------|-----------------|------------|-----------------|
| Unconstrained    | P2P≤3, USPS≤3 | P2P≤21, USPS≤4 | $4,493,988 | NOT MET         |
| **Constrained**  | **P2P≤3, USPS≤3** | **P2P≤21, USPS≤2** | **$4,516,218** | **MET** |

The only change: Medium USPS cutoff drops from 4 to 2, shifting ~764 shipments from USPS to FedEx. This costs $22,230/year but secures the FedEx threshold with ample margin.

## Missed Opportunities

| Scenario                              | Ships   | Overpay    |
|---------------------------------------|---------|------------|
| FedEx assigned, but P2P is cheaper    | 15,575  | $98,592    |
| FedEx assigned, but USPS is cheaper   | 40,129  | $85,846    |
| P2P assigned, but USPS is cheaper     | 13,645  | $3,181     |

The missed opportunities are larger than S10's ($184K vs $134K) because the 3-group cutoffs can't capture per-packagetype variation. For example, PIZZA BOX 20x16x2 has an S10 P2P cutoff of 11 but gets the Light group's cutoff of 3 — leaving 8 weight brackets of P2P savings on the table.

## Comparison to Other Approaches

| Approach                              | Cost           | Savings | Rules Needed             | S7 Captured |
|---------------------------------------|----------------|---------|--------------------------|:-----------:|
| S1 Current mix                        | $5,971,748     | —       | As-is                    | —           |
| **S11 3-Group rules**                 | **$4,516,218** | **24.4%** | **3 rules + zip list** | **94.6%**   |
| S10 Per-packagetype rules             | $4,450,862     | 25.5%   | ~50 rules + zip list     | 98.8%       |
| S7 Per-shipment optimal               | $4,433,040     | 25.8%   | 353K cell assignments    | 100%        |

## Implementation Guide

### What Needs to Be Configured in PCS

**1. P2P Zone List (one-time)**
- Upload 38,599 zip codes from `p2p_zip_codes.csv`
- Same as S10

**2. Package Type → Group Mapping**
- Assign each package type to Light, Medium, or Heavy
- See `group_definitions.csv` for the full mapping
- Any new/unknown package types default to Heavy (FedEx always)

**3. Three Routing Rules**

| Group  | P2P Zone Destination        | Non-P2P Zone Destination    |
|--------|-----------------------------|-----------------------------|
| Light  | P2P if ceil(weight) ≤ 3 lbs | USPS if ceil(weight) ≤ 3 lbs |
| Medium | P2P if ceil(weight) ≤ 21 lbs | USPS if ceil(weight) ≤ 2 lbs |
| Heavy  | FedEx                       | FedEx                       |

**4. Priority Logic**
```
IF destination zip is in P2P zone AND ceil(weight) <= group P2P cutoff:
    → Ship with P2P
ELSE IF destination zip is NOT in P2P zone AND ceil(weight) <= group USPS cutoff:
    → Ship with USPS
ELSE:
    → Ship with FedEx
```

### S11 vs S10 Implementation Tradeoff

| Factor                  | S11 (3-Group)          | S10 (Per-Packagetype)   |
|-------------------------|------------------------|-------------------------|
| Rules to configure      | 3                      | ~50                     |
| Annual cost             | $4,516,218             | $4,450,862              |
| Extra cost              | +$65,356/year          | —                       |
| FedEx threshold margin  | $194K (safe)           | $17K (fragile)          |
| Maintenance effort      | Low                    | Medium                  |
| New package type        | Assign to group        | Compute new cutoffs     |

## Risks

### FedEx Threshold

With $194K margin, S11 is resilient. The threshold would only be at risk if:
- Light packages shift dramatically toward heavier weights (unlikely — these are small/flat)
- P2P coverage expands significantly (more volume diverted from FedEx)

### Group Misassignment

If a new package type is assigned to the wrong group, costs may be suboptimal. The safe default is Heavy (FedEx always), which can never cause a loss vs the current mix.

### Rate Changes

If carrier rates change materially, the cutoffs should be recomputed. The script can be re-run to find new optimal group cutoffs.

## Output Files

| File                      | Description                                          |
|---------------------------|------------------------------------------------------|
| `assignments.parquet`     | Per-(packagetype, zip, weight_bracket) carrier assignment |
| `routing_rules.csv`       | Per-packagetype: group, cutoffs, shipment counts     |
| `group_summary.csv`       | 3-row summary: group cutoffs and package type counts |
| `p2p_zip_codes.csv`       | List of 38,599 zip codes where P2P delivers          |
| `summary.md`              | This file                                            |

---

*Analysis generated: February 2026*
*Data source: shipments_unified.parquet (558,013 shipments), FedEx at 16% earned discount*
*Baseline: $5,971,748 (Scenario 1 current mix, FedEx at 16% earned discount)*
*FedEx threshold: $4.5M undiscounted spend required for 16% earned discount tier*
*Group definitions derived from Scenario 10 per-packagetype cutoffs*
