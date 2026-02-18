# Scenario 11: 3-Group Static Routing Rules (Simplified S10)

## Executive Summary

Scenario 11 simplifies S10's ~50 per-packagetype routing rules into **3 group rules** that require only **3 rules + a P2P zip list** to configure.

| Metric                    | S11 3-Group          | S10 Per-Packagetype  |
|---------------------------|----------------------|----------------------|
| Total cost                | **$4,962,119**       | $4,942,173           |
| Savings vs S1             | **$1,109,943 (18.3%)** | $1,129,889 (18.6%) |
| Gap vs S10                | **+$19,946**         | --                   |
| FedEx 16% tier            | **MET**              | MET                  |
| Configuration complexity  | **3 rules + zip list** | ~50 rules + zip list |

The tradeoff: **$20K/year more** than S10, but **far simpler to implement**.

## How It Works

### Package Type Groups

All package types are assigned to one of three groups based on their physical characteristics:

| Group    | Description                            | Pkg Types | Shipments   | Share  |
|----------|----------------------------------------|:---------:|:-----------:|:------:|
| Light    | Small, flat packages                   |    20     |   350,835   | 65.0%  |
| Medium   | Mid-size packages                      |    18     |   116,561   | 21.6%  |
| Heavy    | Oversized packages                     |    15     |    72,521   | 13.4%  |

### Routing Rules

```
IF package is in LIGHT group:
    IF destination is in P2P zone AND weight <= 3 lbs -> P2P
    IF destination is NOT in P2P zone AND weight <= 2 lbs -> USPS
    ELSE -> FedEx

IF package is in MEDIUM group:
    IF destination is in P2P zone AND weight <= 7 lbs -> P2P
    IF destination is NOT in P2P zone AND weight <= 2 lbs -> USPS
    ELSE -> FedEx

IF package is in HEAVY group:
    -> FedEx always
```

### Why These Cutoffs

**Light group (P2P <= 3, USPS <= 2):** These are small/flat packages (pizza boxes up to 36x24, wraps, poly bags, mug boxes, tubes). P2P and USPS are significantly cheaper than FedEx at low weights, but FedEx becomes competitive above these cutoffs due to the packages' small dimensions keeping FedEx's dimensional weight low.

**Medium group (P2P <= 7, USPS <= 2):** These are mid-size packages (24x20, 20x16x2, 30x20x3, cross packaging, strapped variants). P2P wins up to moderate weights because FedEx's dimensional weight penalty is more severe for these dimensions. USPS loses competitiveness fast -- only cheapest at 1-2 lbs.

**Heavy group (always FedEx):** Oversized packages (42x32, 48x36, 40x30, cross 49x30/40x40). P2P and USPS either can't handle them or are more expensive at all weights.

## Group Definitions

### Light (20 package types, 350,835 shipments)

| Package Type               | Shipments |
|----------------------------|-----------|
| PIZZA BOX 20x16x1          | 113,896   |
| PIZZA BOX 12x8x1           | 54,637    |
| PIZZA BOX 16x12x2          | 42,377    |
| WRAP 16''x12''             | 41,536    |
| PIZZA BOX 36x24x2          | 36,438    |
| WRAP 24''x16''             | 22,638    |
| 21" Tube                   | 12,032    |
| POLY BAG 9x12              | 5,340     |
| 26" Tube                   | 4,555     |
| MUG BOX 5x5x5              | 4,342     |
| MIXPIX BOX                 | 3,082     |
| (blank)                    | 2,656     |
| BUBBLE MAILER 9x14         | 2,000     |
| MUG BOX 9x7x5              | 1,345     |
| Carpet Box 22x4x4          | 1,058     |
| MUG BOX 16x6x4             | 1,009     |
| POLY BAG 12x15             | 808       |
| MIXPIX BOX_(2)             | 483       |
| MIXPIX BOX_(4)             | 315       |
| Carpet Box 37x5x5          | 288       |

### Medium (18 package types, 116,561 shipments)

| Package Type                      | Shipments |
|-----------------------------------|-----------|
| PIZZA BOX 24x20x2                 | 39,950    |
| PIZZA BOX 20x16x2                 | 35,114    |
| CROSS PACKAGING 30X24"            | 14,740    |
| PIZZA BOX 30x20x3                 | 9,920     |
| MUG BOX 16x12x8                   | 4,610     |
| PIZZA BOX 27x23x2                 | 2,325     |
| POLY BAG 14,5x19                  | 1,953     |
| PIZZA BOX 24x20x2 (2x strapped)  | 1,749     |
| PIZZA BOX 30x20x3 (2x strapped)  | 1,359     |
| PIZZA BOX 36x24x2 (2x strapped)  | 1,289     |
| BOX 16x24x12                      | 1,238     |
| PIZZA BOX 36x24x2 (3x strapped)  | 613       |
| WRAP 36''x24'' [x2]               | 601       |
| PIZZA BOX 24x20x2 (3x strapped)  | 294       |
| WRAP 36''x24''                    | 294       |
| WRAP 27''x23''                    | 228       |
| PIZZA BOX 27x23x2 (2x strapped)  | 184       |
| PIZZA BOX 30x20x3 (3x strapped)  | 100       |

### Heavy (15 package types, 72,521 shipments)

| Package Type                      | Shipments |
|-----------------------------------|-----------|
| PIZZA BOX 42x32x2                 | 24,261    |
| PIZZA BOX 40x30x1                 | 20,091    |
| PIZZA BOX 48X36X1                 | 18,697    |
| PIZZA BOX 42x32x2 (2x strapped)  | 2,532     |
| CROSS PACKAGING 49X30"            | 1,990     |
| PIZZA BOX 40x30x2                 | 1,597     |
| CROSS PACKAGING 40X30"            | 1,383     |
| PIZZA BOX 42x32x2 (3x strapped)  | 877       |
| CROSS PACKAGING 40X40"            | 397       |
| PIZZA BOX 40x30x2 (2x strapped)  | 331       |
| PIZZA BOX 40x30x2 (3x strapped)  | 239       |
| WRAP 40''x30''                    | 65        |
| PIZZA BOX 27x23x2 (3x strapped)  | 36        |
| WRAP 36''x24'' [x3]               | 20        |
| WRAP 40''x30'' [x3]               | 5         |

## Results

### Carrier Mix

| Carrier     | Shipments   | Share    | Total Cost     | Avg Cost    |
|-------------|-------------|---------|----------------|-------------|
| USPS        | 122,404     | 22.7%   | $741,415       | $6.06       |
| FedEx       | 208,808     | 38.7%   | $3,287,062     | $15.74      |
| P2P         | 208,705     | 38.7%   | $933,642       | $4.47       |
| **Total**   | **539,917** | **100%**| **$4,962,119** |             |

### FedEx Earned Discount

| Metric                  | Value           |
|-------------------------|-----------------|
| Threshold               | $4,500,000      |
| 16% tier                | **MET**         |

### P2P Zone Coverage

P2P-eligible shipments are routed to P2P when below the weight cutoff for their group. The remaining shipments above the cutoff go to FedEx.

## Cutoff Optimization

### How the Cutoffs Were Found

For each group, a brute-force search tested all (P2P_cutoff, USPS_cutoff) combinations:
- P2P cutoff: 0 to 30
- USPS cutoff: 0 to 10

The search found the combination that minimizes total cost while keeping FedEx undiscounted spend >= $4.5M.

## Comparison to Other Approaches

| Approach                              | Cost           | Savings vs S1   | Rules Needed             |
|---------------------------------------|----------------|-----------------|--------------------------|
| S1 Current mix                        | $6,072,062     | --              | As-is                    |
| S8 Conservative P2P ($5M buffer)      | $5,136,088     | 15.4%           | Greedy optimization      |
| S10 Per-packagetype rules             | $4,942,173     | 18.6%           | ~50 rules + zip list     |
| **S11 3-Group rules**                 | **$4,962,119** | **18.3%**       | **3 rules + zip list**   |

## Implementation Guide

### What Needs to Be Configured in PCS

**1. P2P Zone List (one-time)**
- Upload zip codes from `p2p_zip_codes.csv`
- Same as S10

**2. Package Type -> Group Mapping**
- Assign each package type to Light, Medium, or Heavy
- See `routing_rules.csv` for the full mapping
- Any new/unknown package types default to Heavy (FedEx always)

**3. Three Routing Rules**

| Group  | P2P Zone Destination         | Non-P2P Zone Destination     |
|--------|------------------------------|------------------------------|
| Light  | P2P if ceil(weight) <= 3 lbs | USPS if ceil(weight) <= 2 lbs |
| Medium | P2P if ceil(weight) <= 7 lbs | USPS if ceil(weight) <= 2 lbs |
| Heavy  | FedEx                        | FedEx                        |

**4. Priority Logic**
```
IF destination zip is in P2P zone AND ceil(weight) <= group P2P cutoff:
    -> Ship with P2P
ELSE IF destination zip is NOT in P2P zone AND ceil(weight) <= group USPS cutoff:
    -> Ship with USPS
ELSE:
    -> Ship with FedEx
```

### S11 vs S10 Implementation Tradeoff

| Factor                  | S11 (3-Group)          | S10 (Per-Packagetype)   |
|-------------------------|------------------------|-------------------------|
| Rules to configure      | 3                      | ~50                     |
| Annual cost             | $4,962,119             | $4,942,173              |
| Extra cost              | +$19,946/year          | --                      |
| Maintenance effort      | Low                    | Medium                  |
| New package type        | Assign to group        | Compute new cutoffs     |

## Risks

### FedEx Threshold

The FedEx 16% earned discount threshold ($4.5M undiscounted) must be monitored. The threshold would be at risk if:
- Light packages shift dramatically toward heavier weights (unlikely -- these are small/flat)
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
| `p2p_zip_codes.csv`       | Zip codes where P2P delivers                         |
| `summary.md`              | This file                                            |

---

*Analysis generated: February 2026*
*Data source: shipments_unified.parquet (539,917 matched shipments), FedEx at 16% earned discount*
*Baseline: $6,072,062 (Scenario 1 current mix, FedEx at 16% earned discount)*
*FedEx threshold: $4.5M undiscounted spend required for 16% earned discount tier*
*Group definitions derived from Scenario 10 per-packagetype cutoffs*
