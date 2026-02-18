# Scenario 14: P2P + FedEx with 16% Earned Discount (Constrained)

## Executive Summary

This scenario builds on S13's 2-carrier concept (P2P + FedEx, no USPS, no OnTrac) but solves S13's critical weakness: the lost FedEx earned discount. By constraining FedEx undiscounted spend above $5.1M (safely clearing the $5M penalty threshold), S14 qualifies for the 16% earned discount tier — making FedEx significantly cheaper per shipment.

The tradeoff: 187,272 shipments that would naturally go to P2P are forced to FedEx to meet the volume threshold. These shipments cost an average of $3.19 more each at FedEx vs P2P, but the 16% earned discount on ALL FedEx shipments more than compensates.

**Result: $4,858,916 (-18.6% vs S1 baseline)** — $84K better than S13 and the best 2-carrier scenario. However, it trails the 3-carrier scenarios (S7-S11) by $322K-$426K because forcing lightweight P2P shipments to FedEx is inherently less efficient than routing them through USPS.

## Carrier Configuration

| Carrier   | Coverage     | Earned | Max Weight | Notes                              |
|-----------|--------------|--------|------------|-------------------------------------|
| P2P US    | ~10,430 ZIPs | —      | 30 lbs     | Best P2P rates, limited coverage    |
| P2P US2   | ~93,100 ZIPs | —      | 70 lbs     | Full US coverage, higher rates      |
| FedEx     | 100%         | **16%**| 150 lbs    | HD + SmartPost, 16% earned discount |

FedEx at 16% earned uses a 1.0541x multiplier on base rate + fuel (adjusting from the baked 18% to 16%). This is far cheaper than S13's 0% earned (1.4865x multiplier).

## How the Constraint Works

1. **Start unconstrained**: For each shipment, pick cheapest of P2P US, P2P US2, FedEx@16%
2. **Check FedEx undiscounted spend**: Unconstrained result yields only $2.83M — far below $5M
3. **Force cheapest-to-switch P2P shipments to FedEx**: Sort P2P winners by "switch pain" (FedEx@16% cost minus P2P cost), switch the cheapest ones first until undiscounted spend reaches $5.1M
4. **Result**: 187,272 P2P shipments forced to FedEx, achieving $5.1M undiscounted with $100K safety margin

## Results

| Metric                            | Value              |
|-----------------------------------|--------------------|
| Total shipments                   | 558,013            |
| Current mix (S1)                  | $5,971,748         |
| S14 P2P+FedEx@16% constrained    | $4,858,916         |
| Difference                        | -$1,112,832 (-18.6%) |
| Avg per shipment                  | $8.71 (vs $10.70)  |
| No coverage                       | 0                  |

### Carrier Selection

| Carrier   | Shipments   | % of Total   | Total Cost     | Avg Cost   | Avg Wt  | Forced  |
|-----------|-------------|--------------|----------------|------------|---------|---------|
| FedEx     | 337,754     | 60.5%        | $3,721,037     | $11.02     | 4.2 lbs | 187,272 |
| P2P US    | 136,958     | 24.5%        | $642,441       | $4.69      | 2.9 lbs | 0       |
| P2P US2   | 83,301      | 14.9%        | $495,438       | $5.95      | 1.6 lbs | 0       |
| **Total** | **558,013** | **100%**     | **$4,858,916** |            |         |         |

FedEx handles 60.5% of shipments — far more than S13's 21.4% — because 187K P2P shipments are rerouted to meet the volume threshold. P2P retains 39.5% of shipments (the ones where switching to FedEx would be most expensive).

### FedEx Breakdown: Natural vs Forced

| FedEx Type          | Shipments  | Total Cost    | Avg Cost  | Avg Wt  |
|---------------------|------------|---------------|-----------|---------|
| Natural (cheapest)  | 150,482    | $2,095,806    | $13.93    | 7.3 lbs |
| Forced (threshold)  | 187,272    | $1,625,231    | $8.68     | 1.9 lbs |
| **Total FedEx**     | **337,754**| **$3,721,037**| **$11.02**|         |

The forced shipments are lightweight (avg 1.9 lbs) — these are the packages P2P handles cheaply ($5.49/ship avg) but that get rerouted to FedEx ($8.68/ship) to meet the threshold. Natural FedEx shipments are heavier (7.3 lbs avg) where FedEx genuinely wins on cost.

### FedEx Threshold Analysis

| Metric                       | Value         |
|------------------------------|---------------|
| FedEx undiscounted spend     | $5,100,007    |
| $5M penalty threshold        | $5,000,000    |
| Safety margin                | **$100,007**  |
| Earned discount applied      | **16%**       |
| Earned discount tier minimum | $4,500,000    |

The $5.1M undiscounted spend provides $100K of margin above the $5M penalty line and $600K above the 16% earned discount threshold ($4.5M). Seasonal volume fluctuations should be monitored — if a low-volume quarter reduces FedEx spend below $5M, the $500K penalty applies.

## Cost of the Constraint

| Metric                          | Value              |
|---------------------------------|--------------------|
| Unconstrained P2P+FedEx@16%     | $4,262,074         |
| Constrained (>=$5.1M undiscounted) | $4,858,916      |
| **Cost of meeting constraint**  | **$596,842**       |

Without the constraint, free per-shipment selection would yield $4,262,074 — cheaper than even S7. But FedEx undiscounted spend would be only $2.83M, triggering the $500K penalty and losing the 16% earned discount. The constraint costs $597K to avoid a $500K penalty + lost earned discount.

### Where the Forced Shipments Come From

| Originally Assigned | Forced Count | Avg Switch Pain |
|---------------------|:------------:|:---------------:|
| P2P US              | 101,490      | ~$3.20/ship     |
| P2P US2             | 85,782       | ~$3.17/ship     |

The forced switches are split roughly evenly between P2P US and P2P US2. P2P US shipments are forced despite having better rates because those happen to be the cheapest to reroute (smallest cost difference vs FedEx@16%).

## Comparison to Other Scenarios

| Scenario                              | Cost         | vs S1    | Carriers | FedEx Earned |
|---------------------------------------|--------------|----------|:--------:|:------------:|
| S7 USPS+FedEx+P2P (optimal)          | $4,433,040   | -25.8%   | 3        | 16%          |
| S10 Static per-packagetype            | $4,450,862   | -25.5%   | 3        | 16%          |
| S11 Static 3-group                    | $4,516,218   | -24.4%   | 3        | 16%          |
| S8 Conservative $5M buffer            | $4,536,690   | -24.0%   | 3        | 16%          |
| **S14 P2P+FedEx constrained**         | **$4,858,916**| **-18.6%** | **2** | **16%**      |
| S13 P2P+FedEx unconstrained          | $4,942,666   | -17.2%   | 2        | 0%           |
| S6 USPS+FedEx (Drop OnTrac)          | $5,040,871   | -15.6%   | 3        | 16%          |

**Key comparisons:**

- **vs S13 (same carriers, 0% earned):** S14 saves $84K by gaining the 16% earned discount. The constraint costs $597K but the earned discount saves $681K — net benefit of $84K.
- **vs S7 (3 carriers, optimal):** S14 is $426K more expensive. S7 uses USPS to naturally absorb volume that S14 must force to FedEx, and USPS is cheaper than FedEx@16% for lightweight packages ($7.85/ship vs $8.68/ship forced).
- **vs S11 (3 carriers, simplest implementable):** S14 is $342K more expensive. The 2-carrier simplicity of S14 costs about $342K/year vs the simplest 3-carrier alternative.

## Cost by Weight Bracket

| Bracket   | Ships    | Current Avg | S14 Avg  | Diff %   | P2P US   | P2P US2  | FedEx   | Forced  |
|-----------|----------|-------------|----------|----------|----------|----------|---------|---------|
| 0-1 lb    | 145,687  | $6.87       | $6.41    | -6.7%    | 42,884   | 34,370   | 68,433  | 64,947  |
| 1-2 lb    | 113,398  | $8.83       | $7.19    | -18.6%   | 24,468   | 27,453   | 61,477  | 59,467  |
| 2-3 lb    | 96,338   | $10.01      | $7.82    | -21.8%   | 23,089   | 13,277   | 59,972  | 38,954  |
| 3-4 lb    | 43,900   | $12.04      | $8.49    | -29.4%   | 10,955   | 5,335    | 27,610  | 10,437  |
| 4-5 lb    | 41,160   | $11.98      | $9.47    | -20.9%   | 12,632   | 2,016    | 26,512  | 6,441   |
| 5-6 lb    | 28,730   | $13.72      | $10.49   | -23.5%   | 7,992    | 545      | 20,193  | 4,355   |
| 6-7 lb    | 25,303   | $15.92      | $12.91   | -18.9%   | 4,533    | 178      | 20,592  | 1,278   |
| 8-9 lb    | 12,704   | $17.49      | $13.62   | -22.1%   | 2,459    | 28       | 10,217  | 185     |
| 10-11 lb  | 5,815    | $18.69      | $14.99   | -19.8%   | 964      | 5        | 4,846   | 61      |
| 15-16 lb  | 1,761    | $21.77      | $18.64   | -14.3%   | 173      | 1        | 1,587   | 54      |
| 25-26 lb  | 436      | $27.78      | $25.35   | -8.7%    | 4        | 0        | 432     | 14      |

**All weight brackets improve vs S1.** The forced assignments are concentrated in the 0-3 lb range (163K of 187K forced), where the switch pain is lowest. Above 5 lbs, almost all FedEx assignments are natural wins, and forced switches are rare.

Compared to S13 (which saves 34-47% on 0-4 lbs), S14's savings are smaller on lightweight packages (7-29%) because many are forced to FedEx. But S14 saves more on 5+ lb packages (14-24% vs 13-16%) because FedEx@16% is significantly cheaper than FedEx@0%.

## Key Findings

1. **The 16% earned discount is worth pursuing even with 2 carriers**: S14 saves $84K vs S13 by forcing enough FedEx volume. The constraint costs $597K but avoids the $500K penalty and secures the earned discount worth ~$681K.

2. **The $100K safety margin is thin**: With $5.1M undiscounted vs $5M threshold, seasonal variations could push below the line. Monthly monitoring of FedEx undiscounted spend is essential. Consider increasing the threshold to $5.3M for more headroom (at additional constraint cost).

3. **187K forced switches is operationally complex**: Unlike S13's clean "cheapest wins" logic, S14 requires maintaining a list of which shipments get forced to FedEx. This is implementable via static rules (similar to S10/S11) but adds complexity to the 2-carrier simplicity story.

4. **Some package types get more expensive**: 21" Tubes (+17.3%) and Poly Bags (+26.3%) — lightweight items where P2P is dramatically cheaper — become more expensive when forced to FedEx. This is the cost of meeting the threshold.

5. **The 3-carrier alternative remains superior**: S7-S11 save $322K-$426K more than S14 because USPS naturally absorbs volume that S14 must force to FedEx at higher cost. The only advantage of S14 is eliminating the USPS relationship.

## Recommendations

**Choose S14 if:**
- 2-carrier simplicity is required (no USPS relationship)
- The $342K annual cost vs S11 is acceptable
- FedEx undiscounted spend can be monitored monthly
- The forced-switching rules can be implemented in PCS

**Choose S7/S10/S11 instead if:**
- Maximum savings is the priority
- USPS relationship can be maintained
- $322K-$426K annual savings justify the third carrier

**Choose S13 instead if:**
- The $5M FedEx penalty threshold doesn't apply or can be waived
- Clean per-shipment cheapest routing is preferred over constrained optimization
- $84K annual difference is immaterial

---

*Analysis generated: February 2026*
*Data source: shipments_unified.parquet (558,013 shipments)*
*FedEx at 16% earned discount (1.0541x multiplier from baked 18%)*
*Constraint: FedEx undiscounted spend >= $5.1M ($100K margin above $5M penalty)*
*Baseline: $5,971,748 (Scenario 1 current mix, FedEx at 16% earned discount)*
