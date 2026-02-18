# Scenario 13: P2P + FedEx (No USPS, No OnTrac)

## Overview
Per-shipment cheapest selection among P2P US, P2P US2, and FedEx.
Only 2 carrier relationships (P2P + FedEx).
FedEx at 0% earned discount (below $4.5M undiscounted threshold).

## Results
- Total shipments: 539,917
- Current mix (S1): $6,072,061.73
- S13 P2P+FedEx: $5,178,925.65
- **Difference: -$893,136.08 (-14.7%)**
- Avg per shipment: $9.59 (vs $11.25 current)

## FedEx Earned Discount
- FedEx undiscounted spend: $2,670,489.00
- FedEx undiscounted threshold: $5,100,000
- **FedEx earned discount: 0%** (below $4.5M threshold)
- At unconstrained per-shipment cheapest, too few shipments go to FedEx to qualify for any earned discount

## Carrier Selection
- P2P_US: 236,225 shipments (43.8%), $1,270,346.17 (avg $5.38)
- P2P_US2: 188,937 shipments (35.0%), $1,422,041.81 (avg $7.53)
- FEDEX: 114,755 shipments (21.3%), $2,486,537.67 (avg $21.67)

## vs Alternative Mixes
- S1 Current mix (4 carriers): $6,072,061.73
- USPS+FedEx+OnTrac (3 carriers): $5,434,307.07
- USPS+FedEx (2 carriers): $6,002,917.63
- **P2P+FedEx [S13] (2 carriers): $5,178,925.65**

**P2P+FedEx saves $824K vs USPS+FedEx** ($6,002,918 - $5,178,926 = $823,992) with the same number of carrier relationships.

## Key Findings
1. P2P+FedEx at 0% earned is already **14.7% cheaper** than the current mix
2. P2P wins 78.7% of shipments (43.8% P2P US + 35.0% P2P US2), FedEx wins 21.3%
3. FedEx handles the heavy/oversize shipments where P2P rates are less competitive (avg weight 7.22 lbs vs P2P US 2.63 lbs)
4. The 0% earned discount is a disadvantage -- see S14 for constrained version that achieves 16% earned
5. Even without earned discount, this beats the current mix by nearly $900K

---
*Generated: February 2026*
*Data Period: 2025 shipment volumes with 2026 calculated rates*
*Dataset: Matched-only (539,917 shipments)*
