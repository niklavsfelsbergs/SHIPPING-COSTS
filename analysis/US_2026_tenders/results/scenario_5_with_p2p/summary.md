# Scenario 5: Optimal with P2P

## Executive Summary

This analysis evaluates adding P2P US as a fourth carrier option. **Key finding: P2P is cheaper where it can service, but the OnTrac contractual minimum negates most of P2P's benefit.** With constraints enforced, Scenario 5 costs **$5,633,582** - which is **$243,608 (4.5%) more expensive** than Scenario 4 without P2P.

**Recommendation:** P2P offers attractive pricing ($4.65/shipment avg) but has limited coverage (51.8%). The OnTrac minimum forces expensive shifts that negate P2P's advantage. Consider P2P only if OnTrac commitment can be reduced.

## Carrier Serviceability

Not all carriers can service all shipments. OnTrac and P2P have geographic/weight limitations:

| Carrier   | Serviceable     | Coverage   | Minimum Required   | Feasible?   |
|-----------|-----------------|------------|--------------------|-------------|
| OnTrac    | 360,348         | 64.6%      | 279,080            | **YES**     |
| USPS      | 558,210         | 100.0%     | 140,000            | YES         |
| FedEx     | 558,210         | 100.0%     | 0                  | YES         |
| P2P       | 289,429         | 51.8%      | 0                  | YES         |

P2P can only service 289K shipments due to weight limits and geographic coverage.

## Methodology

### Algorithm: Greedy + Adjustment (4 Carriers, Null-Aware)

1. **Initial Assignment**: For each group, assign to cheapest carrier **that can service it** (non-null cost)
2. **Check Constraints**: Verify if OnTrac and USPS volume minimums are met
3. **Adjust for Constraints**: Shift lowest-penalty groups to underutilized carriers (only where target carrier can service)
4. **FedEx Earned Discount**: Apply discount tier based on final FedEx transportation charges

### Constraints

| Carrier   | Minimum             | Notes                               |
|-----------|---------------------|-------------------------------------|
| OnTrac    | 279,080 shipments   | Contractual (5,365/week × 52)       |
| USPS      | 140,000 shipments   | Tier 1 (35K/quarter × 4)            |
| P2P       | None                | No volume commitment                |
| FedEx     | None                | Earned discount tiers apply         |

## Results

### Initial Greedy Assignment (Before Constraints)

| Carrier   | Shipments   | % of Total   | Notes                           |
|-----------|-------------|--------------|----------------------------------|
| P2P       | 215,240     | 38.6%        | Cheapest where it can service    |
| USPS      | 203,846     | 36.5%        | Universal coverage               |
| FedEx     | 99,795      | 17.9%        | -                                |
| OnTrac    | 39,329      | 7.0%         | Limited to serviceable area      |

P2P captures a significant portion but less than in unconstrained scenarios due to 51.8% coverage limit.

### After Constraint Enforcement

To meet the OnTrac minimum of 279,080:
- Shifted 122,915 shipments from USPS/FedEx to OnTrac (cost penalty: $634,643)
- Shifted 116,836 shipments from P2P to OnTrac

To meet the USPS minimum of 140,000:
- Shifted 2,263 shipments to USPS (cost penalty: $329)

| Carrier     | Shipments   | % of Total   | Total Cost          |
|-------------|-------------|--------------|---------------------|
| OnTrac      | 279,080     | 50.0%        | $3,427,591.27       |
| USPS        | 140,000     | 25.1%        | $1,074,896.51       |
| P2P         | 98,404      | 17.6%        | $457,316.71         |
| FedEx       | 40,726      | 7.3%         | $673,777.03         |
| **Total**   | **558,210** | **100%**     | **$5,633,581.52**   |

### Constraint Satisfaction

| Carrier   | Actual      | Minimum     | Status      |
|-----------|-------------|-------------|-------------|
| OnTrac    | 279,080     | 279,080     | **MET**     |
| USPS      | 140,000     | 140,000     | **MET**     |
| P2P       | 98,404      | 0           | N/A         |
| FedEx     | 40,726      | 0           | N/A         |

### FedEx Earned Discount

| Metric                    | Value            |
|---------------------------|------------------|
| Transportation Charges    | $673,777.03      |
| Tier                      | < $4.5M          |
| Discount Rate             | 0%               |
| Discount Amount           | $0.00            |

### Scenario Comparison

| Scenario                      | Total Cost          | vs Current          | Savings %   |
|-------------------------------|---------------------|---------------------|-------------|
| Current Mix                   | $6,389,595.72       | -                   | -           |
| Scenario 4 (without P2P)      | $5,389,973.56       | $999,622.16         | 15.6%       |
| **Scenario 5 (with P2P)**     | **$5,633,581.52**   | **$756,014.20**     | **11.8%**   |

**P2P adds $243,608 in cost vs Scenario 4** due to the constraint adjustments required.

## Analysis: Why P2P Doesn't Help Under Current Constraints

### The OnTrac Constraint Problem

1. **P2P captures volume that OnTrac needs**: P2P's serviceable area (289K) heavily overlaps with OnTrac's (360K)
2. **OnTrac minimum requires 279K**: Most of P2P's "wins" must be shifted to OnTrac
3. **Shift penalty is significant**: Moving 116,836 shipments from P2P to OnTrac costs more than keeping them with P2P

### Volume Flow

| Stage                 | OnTrac    | USPS      | FedEx     | P2P       |
|-----------------------|-----------|-----------|-----------|-----------|
| Greedy Assignment     | 39,329    | 203,846   | 99,795    | 215,240   |
| After OnTrac Adj      | 279,080   | ~140,000  | ~40,726   | 98,404    |
| Net Change            | +239,751  | -63,846   | -59,069   | -116,836  |

### P2P Value Where It Remains

For the 98,404 shipments P2P captures in the final mix:

| Metric                    | P2P           | Alternative (OnTrac)   | Savings     |
|---------------------------|---------------|------------------------|-------------|
| Total Cost                | $457,317      | $631,263               | $173,946    |
| Avg Cost/Shipment         | $4.65         | $6.42                  | $1.77       |

P2P saves $173,946 on the 98K shipments it retains, but this is offset by the constraint adjustment penalties.

### P2P vs Other Carriers (on P2P's assigned volume)

| Carrier   | Would Cost      | Avg/Shipment   | vs P2P        |
|-----------|-----------------|----------------|---------------|
| P2P       | $457,317        | $4.65          | -             |
| OnTrac    | $631,263        | $6.42          | +$173,946     |
| USPS      | $905,078        | $9.20          | +$447,761     |
| FedEx     | $1,025,888      | $10.43         | +$568,571     |

P2P is genuinely the cheapest carrier for its serviceable shipments.

### P2P by Weight Bracket

| Weight     | Shipments   | % of P2P Volume   |
|------------|-------------|-------------------|
| 1 lb       | 27,397      | 27.8%             |
| 2 lbs      | 32,880      | 33.4%             |
| 3 lbs      | 19,582      | 19.9%             |
| 4 lbs      | 5,228       | 5.3%              |
| 5 lbs      | 5,102       | 5.2%              |
| 6+ lbs     | 8,215       | 8.4%              |

P2P is most competitive for lightweight packages (1-3 lbs = 81% of P2P volume).

## Key Findings

1. **P2P adds cost under current constraints**: The OnTrac minimum forces expensive shifts that negate P2P's advantage. Scenario 5 costs $243K more than Scenario 4.

2. **P2P is genuinely cheap where it operates**: At $4.65/shipment average, P2P beats all other carriers in its serviceable area.

3. **Coverage limitation matters**: P2P can only service 51.8% of shipments (289K of 558K) due to weight limits and geographic restrictions.

4. **Constraint interaction is critical**: P2P and OnTrac compete for the same volume. With OnTrac's 279K minimum, P2P can only retain 98K shipments.

5. **Both constraints are still met**: Even with P2P added, we can satisfy OnTrac (279K) and USPS (140K) minimums.

## Recommendations

### Do Not Add P2P Under Current Constraints

Adding P2P to the carrier mix would cost **$243,608 more** than the current optimized mix (Scenario 4).

### Scenario 4 Remains Optimal

Without renegotiating the OnTrac commitment, Scenario 4 (3-carrier mix without P2P) delivers the best results:
- **$999,622 savings** vs current routing (15.6%)
- Meets all contractual commitments

### If Considering P2P in the Future

| OnTrac Min   | P2P Viability   | Expected Outcome                    |
|--------------|-----------------|-------------------------------------|
| 279K         | Not viable      | Current situation (+$243K vs S4)    |
| ~200K        | Marginal        | P2P can retain ~180K shipments      |
| ~100K        | Viable          | P2P captures significant volume     |
| 0            | Optimal         | Unconstrained optimization          |

### Alternative: Negotiate Lower OnTrac Minimum

If the OnTrac minimum could be reduced to ~100-150K shipments:
- P2P could capture its natural volume (~200K shipments)
- Combined savings could exceed Scenario 4
- OnTrac would focus on its core West region where it's most competitive

---

*Analysis generated: February 2026*
*Data source: shipments_aggregated.parquet (558,210 shipments)*
*Note: P2P US is not currently used - this is a future assessment*
*Baseline: $6,389,595.72 (Scenario 1 current mix)*
