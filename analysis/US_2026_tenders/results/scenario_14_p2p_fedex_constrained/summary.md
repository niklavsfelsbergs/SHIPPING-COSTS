# Scenario 14: P2P + FedEx with 16% Earned Discount (Constrained)

## Overview
Per-shipment cheapest of P2P US, P2P US2, and FedEx at 16% earned discount,
with FedEx undiscounted spend constrained to >= $5.1M
(safely above $5M penalty threshold).

## Results
- Total shipments: 539,917
- Current mix (S1): $6,072,061.73
- S14 P2P+FedEx@16%: $4,944,679.84
- **Difference vs S1: -$1,127,381.88 (-18.6%)**
- Avg per shipment: $9.16 (vs $11.25 current)

## FedEx Earned Discount
- FedEx earned discount: **16%**
- FedEx undiscounted spend: $5,100,006.72
- FedEx undiscounted threshold: $5,100,000
- **Margin above $5M: $100,006.72**

## Constraint Analysis
- Unconstrained total (P2P+FedEx@16%, no floor): $4,647,086.65
- Constrained total: $4,944,679.84
- **Cost of constraint: $297,593.20** (forcing cheaper P2P shipments to FedEx to meet $5.1M floor)
- Forced shipments: 120,915 (shipments moved from P2P to FedEx to meet threshold)

## vs S13 (0% Earned)
- S13 P2P+FedEx@0%: $5,178,925.65
- S14 P2P+FedEx@16%: $4,944,679.84
- **S14 saves $234,245.81 vs S13** by achieving the 16% earned discount

The 16% earned discount more than pays for the constraint cost. Even though we force 120,915 shipments away from cheaper P2P rates, the earned discount on all FedEx volume saves more than it costs.

## Carrier Selection
| Carrier  | Shipments | Share  | Total Cost     | Avg Cost | Forced |
|----------|-----------|--------|----------------|----------|--------|
| FEDEX    | 266,062   | 49.3%  | $3,557,048.68  | $13.37   | 120,915|
| P2P_US   | 190,037   | 35.2%  | $872,462.47    | $4.59    | 0      |
| P2P_US2  | 83,818    | 15.5%  | $515,168.69    | $6.15    | 0      |

## Key Findings
1. Best P2P+FedEx scenario at **-18.6% vs current mix** ($1.13M savings)
2. FedEx takes 49.3% of shipments (up from 21.3% in S13) to meet the undiscounted floor
3. 120,915 shipments are forced from P2P to FedEx -- these are shipments where P2P was cheaper but FedEx is needed for volume
4. The constraint costs $297,593 but the earned discount saves $531,839 ($297,593 + $234,246), net benefit $234,246
5. $100K margin above $5M threshold provides safety buffer for volume fluctuations
6. P2P still handles 50.7% of shipments (35.2% P2P US + 15.5% P2P US2)
7. See S15 for an implementable version with static routing rules

---
*Generated: February 2026*
*Data Period: 2025 shipment volumes with 2026 calculated rates*
*Dataset: Matched-only (539,917 shipments)*
