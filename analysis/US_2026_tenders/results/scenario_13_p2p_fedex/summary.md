# Scenario 13: P2P + FedEx (No USPS, No OnTrac)

## Executive Summary

This scenario explores a simplified 2-carrier strategy using only P2P (both US and US2 contracts) and FedEx, eliminating both USPS and OnTrac. Per-shipment cheapest selection among P2P US, P2P US2, and FedEx.

**Critical constraint: FedEx at 0% earned discount.** With P2P handling 79% of shipments, FedEx undiscounted spend falls to ~$2.3M — far below the $4.5M threshold required for the 16% earned discount tier.

**Result: $4,942,666 (-17.2% vs S1 baseline)** — a meaningful improvement over the current mix, and the best 2-carrier scenario tested. However, it underperforms S7-S11 by $490K-$510K because losing the FedEx earned discount offsets the savings from carrier simplification.

## Carrier Configuration

| Carrier   | Coverage   | FedEx Earned | Max Weight | Notes                         |
|-----------|------------|--------------|------------|-------------------------------|
| P2P US    | ~10,430 ZIPs | —          | 30 lbs     | Best P2P rates where available|
| P2P US2   | ~93,100 ZIPs | —          | 70 lbs     | Full US fallback              |
| FedEx     | 100%       | **0%**       | 150 lbs    | HD + SmartPost, no earned     |

FedEx at 0% earned discount uses a 1.4865x multiplier on base rate + fuel (adjusting from the baked 18% to 0%). This increases FedEx cost by ~49% compared to the 16% tier.

## Results

| Metric                       | Value              |
|------------------------------|--------------------|
| Total shipments              | 558,013            |
| Current mix (S1)             | $5,971,748         |
| S13 P2P+FedEx                | $4,942,666         |
| Difference                   | -$1,029,082 (-17.2%) |
| Avg per shipment             | $8.86 (vs $10.70)  |
| No coverage                  | 0                  |

### Carrier Selection

| Carrier   | Shipments   | % of Total   | Total Cost     | Avg Cost   | Avg Wt  |
|-----------|-------------|--------------|----------------|------------|---------|
| P2P US    | 239,258     | 42.9%        | $1,127,837     | $4.71      | 2.6 lbs |
| P2P US2   | 199,433     | 35.7%        | $1,475,755     | $7.40      | 1.9 lbs |
| FedEx     | 119,322     | 21.4%        | $2,339,075     | $19.60     | 7.8 lbs |
| **Total** | **558,013** | **100%**     | **$4,942,666** |            |         |

P2P handles 78.6% of shipments (the lighter ones), while FedEx serves as the fallback for heavier packages. The natural split follows weight: P2P dominates below 5 lbs, FedEx takes over above 5 lbs.

### FedEx Threshold Analysis

| Metric                   | Value         |
|--------------------------|---------------|
| FedEx undiscounted spend | ~$2.34M       |
| Threshold for 16% tier   | $4.50M        |
| Shortfall                | ~$2.16M       |
| Earned discount applied  | **0%**        |

With only 21.4% of shipments going to FedEx, undiscounted spend is far below the 16% tier threshold. Even forcing all non-P2P-US shipments to FedEx wouldn't make the economics work — P2P US2 is cheaper than FedEx at 0% earned for lightweight packages, so rerouting them would increase total cost.

## Comparison to Alternative Carrier Mixes

| Carrier Mix                          | Total Cost     | vs S1     | # Carriers |
|--------------------------------------|----------------|-----------|:----------:|
| S1 Current mix                       | $5,971,748     | Baseline  | 4          |
| USPS+FedEx+OnTrac (optimal)          | $5,303,527     | -11.2%    | 3          |
| USPS+FedEx (2 carriers)              | $5,857,112     | -1.9%     | 2          |
| **P2P+FedEx [S13] (2 carriers)**     | **$4,942,666** | **-17.2%**| **2**      |
| S7 Drop OnTrac (USPS+FedEx+P2P)     | $4,433,040     | -25.8%    | 3          |

**Key comparisons:**

- **vs USPS+FedEx (same carrier count):** S13 saves $914K more. P2P is dramatically cheaper than USPS for lightweight packages, even without the FedEx earned discount.
- **vs USPS+FedEx+OnTrac:** S13 saves $361K more with fewer carriers, because P2P undercuts both USPS and OnTrac where it has coverage.
- **vs S7 Drop OnTrac:** S13 is $510K more expensive. The FedEx 16% earned discount (which S7 maintains via USPS volume) is worth approximately this amount.

### Per-Shipment: P2P+FedEx vs USPS+FedEx

| Outcome           | Shipments  | % Total | Savings     |
|-------------------|------------|---------|-------------|
| P2P+FedEx cheaper | 323,332    | 57.9%   | $1,082,760  |
| USPS+FedEx cheaper| 153,366    | 27.5%   | $168,315    |
| Tied              | 81,315     | 14.6%   | —           |

P2P+FedEx wins on 58% of shipments, generating $1.1M in gross savings. USPS+FedEx wins on 28% (mostly heavier packages where FedEx at 0% earned is expensive and USPS is cheaper), but only claws back $168K. Net: P2P+FedEx is $914K cheaper.

## Cost by Weight Bracket

| Bracket   | Ships    | Current Avg | S13 Avg  | Diff %   | P2P US   | P2P US2  | FedEx   |
|-----------|----------|-------------|----------|----------|----------|----------|---------|
| 0-1 lb    | 145,687  | $7.88       | $4.84    | -38.6%   | 76,854   | 68,828   | 5       |
| 1-2 lb    | 113,398  | $10.65      | $5.66    | -46.9%   | 55,684   | 57,043   | 671     |
| 2-3 lb    | 96,338   | $11.79      | $7.20    | -38.9%   | 45,903   | 41,048   | 9,387   |
| 3-4 lb    | 43,900   | $13.81      | $9.15    | -33.7%   | 15,878   | 15,165   | 12,857  |
| 4-5 lb    | 41,160   | $14.47      | $10.92   | -24.6%   | 16,123   | 8,552    | 16,485  |
| 5-6 lb    | 28,730   | $16.15      | $12.53   | -22.4%   | 11,138   | 4,935    | 12,657  |
| 6-7 lb    | 25,303   | $19.46      | $16.84   | -13.5%   | 5,396    | 1,920    | 17,987  |
| 8-9 lb    | 12,704   | $20.94      | $18.04   | -13.8%   | 2,595    | 433      | 9,676   |
| 10-11 lb  | 5,815    | $22.67      | $19.93   | -12.1%   | 1,010    | 136      | 4,669   |
| 15-16 lb  | 1,761    | $26.11      | $24.43   | -6.4%    | 327      | 17       | 1,417   |
| 25-26 lb  | 436      | $33.15      | $32.77   | -1.2%    | 52       | 0        | 384     |
| 30+ lb    | 1,563    | ~$33        | ~$33     | ~-1%     | ~100     | 0        | ~1,460  |

**S13 saves across all weight brackets**, though savings diminish with weight:
- **0-4 lbs** (72% of volume): -34% to -47% savings, P2P dominates
- **4-7 lbs** (17% of volume): -14% to -25% savings, mixed P2P/FedEx
- **7-25 lbs** (10% of volume): -6% to -16% savings, mostly FedEx
- **25+ lbs** (1% of volume): -1% savings, all FedEx

P2P US2 becomes irrelevant above 7 lbs — FedEx is cheaper even at 0% earned. P2P US remains competitive up to ~25 lbs where it has coverage, but its 10,430-ZIP footprint limits how many shipments it can serve.

## Cost by Package Type (Top 10)

| Package Type              | Ships    | Wt   | Current | S13    | Diff %  | Primary Carrier |
|---------------------------|----------|------|---------|--------|---------|-----------------|
| PIZZA BOX 20x16x1        | 117,206  | 1.3  | $10.65  | $5.43  | -49.1%  | P2P (99.99%)    |
| PIZZA BOX 12x8x1         | 55,898   | 0.7  | $6.54   | $4.58  | -30.0%  | P2P (99.99%)    |
| PIZZA BOX 16x12x2        | 43,674   | 2.2  | $10.32  | $5.37  | -48.0%  | P2P (99.99%)    |
| WRAP 16''x12''           | 42,298   | 1.3  | $9.04   | $5.11  | -43.4%  | P2P (99.99%)    |
| PIZZA BOX 24x20x2        | 40,950   | 4.3  | $12.16  | $9.15  | -24.7%  | P2P (85%)       |
| PIZZA BOX 36x24x2        | 37,143   | 6.0  | $14.69  | $12.74 | -13.3%  | FedEx (68%)     |
| PIZZA BOX 20x16x2        | 36,316   | 3.2  | $11.43  | $5.74  | -49.8%  | P2P (100%)      |
| PIZZA BOX 42x32x2        | 24,809   | 8.9  | $24.11  | $22.22 | -7.8%   | FedEx (99.7%)   |
| WRAP 24''x16''           | 23,432   | 2.6  | $11.27  | $7.89  | -30.0%  | P2P (87%)       |
| PIZZA BOX 40x30x1        | 21,002   | 3.3  | $20.23  | $14.10 | -30.3%  | FedEx (65%)     |

The pattern is clear: lightweight flat packages (pizza boxes, wraps) go to P2P at massive savings. Heavier/larger packages go to FedEx with modest savings. Every package type improves, but the biggest wins are on the highest-volume lightweight items.

## The Earned Discount Tradeoff

The central question of S13 is whether a simpler carrier setup (2 carriers vs 3) justifies losing the FedEx 16% earned discount:

| Scenario                  | Carriers | FedEx Earned | Total Cost   | vs S1    |
|---------------------------|:--------:|:------------:|--------------|----------|
| S13 P2P+FedEx             | 2        | 0%           | $4,942,666   | -17.2%   |
| S7 USPS+FedEx+P2P        | 3        | 16%          | $4,433,040   | -25.8%   |
| Difference                |          |              | +$509,626    |          |

**The FedEx earned discount costs $510K/year to give up.** S7 maintains the 16% tier by keeping USPS in the mix (USPS absorbs enough non-P2P volume to push FedEx above the $4.5M threshold). S13 loses this because P2P takes too much from FedEx.

However, S13 offers operational simplicity: only 2 carrier relationships to manage (P2P + FedEx) vs 3 (USPS + FedEx + P2P), no USPS volume commitment to monitor (140K/year), and no FedEx threshold to maintain.

## Key Findings

1. **P2P+FedEx is a viable 2-carrier strategy**: At $4.94M (-17.2%), it materially outperforms the current mix and every scenario that keeps all existing carriers with their volume constraints (S4/S5).

2. **It's the best 2-carrier option by far**: P2P+FedEx at $4.94M crushes USPS+FedEx at $5.86M (-$914K). P2P US and P2P US2 together provide enough coverage to replace USPS's role in lightweight routing.

3. **But it leaves $510K on the table vs S7**: The FedEx 0% earned discount penalty is substantial. Adding USPS as a third carrier (S7) maintains the 16% tier and saves an additional $510K/year.

4. **P2P US2 proves its value as a coverage extender**: Without P2P US2, P2P US alone covers only 51.8% of shipments. P2P US2 adds 35.7% of shipments (199K) at $7.40/ship — expensive by P2P US standards but still cheaper than FedEx at 0% earned for lightweight packages.

5. **FedEx serves as the heavyweight fallback**: At $19.60/shipment average (7.8 lbs average weight), FedEx handles the packages that P2P cannot serve economically — heavier items where FedEx's volume discounting and SmartPost rates still provide value, even without the earned discount.

## Recommendations

**Choose S13 if:**
- Operational simplicity is valued (2 carriers vs 3)
- USPS relationship is being terminated
- The $510K annual cost vs S7 is acceptable for reduced complexity

**Choose S7/S10/S11 instead if:**
- Maximum savings is the priority
- USPS relationship can be maintained
- FedEx 16% earned discount can be preserved

**Do not choose S13 if:**
- OnTrac can be maintained at reduced minimums (S7/S10/S11 are strictly better with OnTrac dropped)

---

*Analysis generated: February 2026*
*Data source: shipments_unified.parquet (558,013 shipments)*
*FedEx at 0% earned discount (1.4865x multiplier from baked 18%)*
*Baseline: $5,971,748 (Scenario 1 current mix, FedEx at 16% earned discount)*
