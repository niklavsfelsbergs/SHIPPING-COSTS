# Scenario 12: 100% P2P Combined (P2P US + P2P US2)

## Executive Summary

This scenario tests whether P2P can serve as the sole carrier for all US shipments by combining both P2P contracts: P2P US (better rates, ~10,430 ZIPs) and P2P US2 (full US coverage, ~93,100 ZIPs, higher rates). Per-shipment cheapest selection where both have coverage.

**Result: $6,788,506 (+13.7% vs S1 baseline)** — P2P alone is **not viable**. P2P US2's rates are too high to compensate for expanded coverage. This is the most expensive scenario after USPS 100%.

## Contract Coverage

| Contract  | ZIPs     | Max Weight | Services    |
|-----------|----------|------------|-------------|
| P2P US    | ~10,430  | 30 lbs     | Single      |
| P2P US2   | ~93,100  | 70 lbs     | PFA + PFS   |
| Combined  | ~93,100  | 70 lbs     | Full US     |

P2P US2 covers nearly every US ZIP, making full-US P2P routing feasible. 82 shipments (0.01%) have no P2P coverage at all.

## Results

| Metric                   | Value              |
|--------------------------|--------------------|
| Total shipments          | 558,013            |
| Current mix (S1)         | $5,971,748         |
| P2P Combined             | $6,788,506         |
| Difference               | +$816,758 (+13.7%) |
| Avg per shipment         | $12.17 (vs $10.70) |
| No coverage              | 82 (0.01%)         |

### Contract Selection

| Contract  | Shipments   | % of Total   | Total Cost     | Avg Cost   | Avg Wt  |
|-----------|-------------|--------------|----------------|------------|---------|
| P2P US    | 267,840     | 48.0%        | $2,257,974     | $8.43      | 3.4 lbs |
| P2P US2   | 290,091     | 52.0%        | $4,530,532     | $15.62     | 3.5 lbs |
| None      | 82          | 0.0%         | $0             | —          | 57.5 lbs|

P2P US wins 48% of shipments despite covering only 19% of ZIPs — its rates are substantially better where it has coverage. P2P US2 costs nearly twice as much per shipment ($15.62 vs $8.43).

### For Reference

| Scenario           | Total Cost     | vs S1     |
|--------------------|----------------|-----------|
| 100% P2P US only   | $3,098,915     | -48.1%    |
| 100% P2P US2 only  | $8,884,351     | +48.8%    |
| P2P Combined       | $6,788,506     | +13.7%    |
| S1 Current mix     | $5,971,748     | Baseline  |

P2P US alone would be extraordinary (-48.1%) but only covers 51.8% of shipments. P2P US2 alone is catastrophic (+48.8%). Combined, P2P US2 drags the average up significantly.

## Cost by Weight Bracket

P2P Combined is only competitive at the lightest weights:

| Bracket   | Ships    | Current Avg | P2P Avg  | Diff %   | P2P US   | P2P US2  |
|-----------|----------|-------------|----------|----------|----------|----------|
| 0-1 lb    | 145,687  | $6.74       | $4.84    | -28.2%   | 76,854   | 68,829   |
| 1-2 lb    | 113,398  | $8.61       | $5.67    | -34.2%   | 55,684   | 57,706   |
| 2-3 lb    | 96,338   | $9.78       | $7.43    | -24.1%   | 45,903   | 50,430   |
| 3-4 lb    | 43,900   | $11.82      | $10.21   | -13.6%   | 15,878   | 28,020   |
| 4-5 lb    | 41,160   | $11.67      | $14.59   | **+25.1%** | 17,495 | 23,664   |
| 5-6 lb    | 28,730   | $13.41      | $18.28   | +36.2%   | 13,900   | 14,828   |
| 6-7 lb    | 25,303   | $15.48      | $29.55   | +90.9%   | 12,228   | 13,074   |
| 10-11 lb  | 5,815    | $18.19      | $37.44   | +105.9%  | 2,912    | 2,903    |
| 20-21 lb  | 634      | $21.84      | $56.27   | +157.6%  | 358      | 276      |
| 30-31 lb  | 182      | $24.66      | $72.00   | +192.0%  | 104      | 78       |

**The crossover point is at ~4 lbs.** Below 4 lbs (72% of volume), P2P Combined saves 13-34%. Above 4 lbs (28% of volume), P2P becomes progressively more expensive — reaching 2-3x the current cost at 10+ lbs. P2P US2 rates escalate dramatically with weight, making it unsuitable for heavier shipments.

## Key Findings

1. **P2P cannot replace the current carrier mix**: At +13.7%, 100% P2P is more expensive than the status quo. P2P US2's rates are fundamentally uncompetitive for packages above 4 lbs.

2. **P2P US rates are excellent but coverage is limited**: P2P US at $8.43/shipment is competitive, but its 10,430-ZIP coverage means 48-52% of shipments must fall back to the much more expensive P2P US2.

3. **The weight problem is structural**: P2P US2 rates grow roughly linearly with weight, while FedEx/OnTrac benefit from economies of scale on heavier packages. At 10+ lbs, P2P US2 costs 2-3x what FedEx charges.

4. **P2P's value is as a complement, not a replacement**: The data confirms P2P's role in S7-S11 — cherry-picking lightweight shipments in P2P US coverage areas while leaving heavier and non-covered shipments to FedEx and USPS.

## Conclusion

100% P2P is not feasible. P2P US2's expanded coverage comes at rates that are uncompetitive for most weight brackets. P2P's optimal role remains as a supplementary carrier for lightweight shipments within its coverage area, as demonstrated in S7-S11 where it contributes $600K-900K in savings by handling 35-41% of shipments at $4.56/shipment.

---

*Analysis generated: February 2026*
*Data source: shipments_unified.parquet (558,013 shipments)*
*Baseline: $5,971,748 (Scenario 1 current mix, FedEx at 16% earned discount)*
