# Scenario 4: Constrained Optimization

## Executive Summary

This analysis finds the optimal carrier mix for US shipments while respecting contractual volume commitments: OnTrac minimum of 279,080 shipments/year and USPS Tier 1 minimum of 140,000 shipments/year. **Both constraints can be satisfied.** The optimized mix achieves **$828,631 (13.3%) savings** versus current routing.

## Methodology

### Algorithm: Greedy + Adjustment

1. **Initial Assignment**: For each (packagetype, zip_code, weight_bracket) group, assign to cheapest carrier among OnTrac, USPS, and FedEx
2. **Check Constraints**: Verify if volume minimums are met
3. **Adjust for Constraints**: Shift lowest-cost-penalty groups to underutilized carriers until constraints are met
4. **FedEx Earned Discount**: Apply discount tier based on final FedEx transportation charges

### Constraints

| Carrier | Minimum Volume    | Calculation                  | Status      |
|---------|-------------------|------------------------------|-------------|
| OnTrac  | 279,080 shipments | 5,365/week × 52              | Contractual |
| USPS    | 140,000 shipments | 35,000/quarter × 4 (Tier 1)  | Tier 1      |
| FedEx   | No minimum        | Earned discount tiers apply  | -           |

### Feasibility Analysis

- **Total shipments available**: 558,210
- **Combined minimums (USPS + OnTrac)**: 419,080
- **Remaining for FedEx**: 139,130
- **Conclusion**: Both constraints CAN be satisfied

## Results

### Scenario Comparison

| Scenario                      | Total Cost       | vs Current       | Savings % |
|-------------------------------|------------------|------------------|-----------|
| Current Mix                   | $6,218,604.91    | -                | -         |
| Unconstrained Optimal         | $5,192,509.49    | $1,026,095.42    | 16.5%     |
| **Constrained Optimal**       | **$5,389,973.56**| **$828,631.35**  | **13.3%** |

### Optimal Carrier Mix

| Carrier   | Shipments | % of Total | Total Cost       |
|-----------|-----------|------------|------------------|
| OnTrac    | 279,080   | 50.0%      | $2,584,393.79    |
| USPS      | 200,310   | 35.9%      | $1,490,422.13    |
| FedEx     | 78,820    | 14.1%      | $1,315,157.64    |
| **Total** | **558,210** | **100%** | **$5,389,973.56** |

### Constraint Satisfaction

| Carrier | Actual    | Minimum   | Status  |
|---------|-----------|-----------|---------|
| OnTrac  | 279,080   | 279,080   | **MET** |
| USPS    | 200,310   | 140,000   | **MET** |
| FedEx   | 78,820    | 0         | **MET** |

USPS exceeds its minimum by 60,310 shipments - these remain with USPS because they are cheaper than shifting to FedEx.

### FedEx Earned Discount

| Metric                  | Value          |
|-------------------------|----------------|
| Transportation Charges  | $1,315,157.64  |
| Tier                    | < $4.5M        |
| Discount Rate           | 0%             |
| Discount Amount         | $0.00          |

FedEx volume does not reach the $4.5M threshold needed for any earned discount tier.

### Groups Shifted

To meet the OnTrac minimum:

| Metric                         | Value      |
|--------------------------------|------------|
| Groups shifted to OnTrac       | 81,347     |
| Shipments shifted to OnTrac    | 125,123    |
| Total cost penalty             | $197,464.07|

The greedy assignment initially allocated only 153,957 shipments to OnTrac, requiring 125,123 additional shipments to be shifted from USPS and FedEx to meet the 279,080 minimum.

## Key Findings

- **Both constraints can be satisfied**: With 140K USPS + 279K OnTrac = 419K combined minimums, there's room for 139K FedEx shipments.

- **OnTrac minimum drives the optimization**: 50% of all shipments go to OnTrac to meet the contractual minimum.

- **USPS gets more than its minimum**: 200K shipments remain with USPS (vs 140K minimum) because they're cheaper there than alternatives.

- **Shift penalty is modest**: $197K cost to shift 125K shipments to OnTrac (only $1.58/shipment average penalty).

- **Significant savings**: 13.3% ($828K) savings achievable vs current routing even with constraints.

## Recommendations

1. **Implement optimized routing**: Route by (packagetype, zip, weight) based on the assignment results.

2. **Monitor OnTrac minimum**: At exactly 279,080 shipments, there's no buffer. Consider targeting 285-290K for safety margin.

3. **Consider FedEx volume increase**: If USPS minimum could be reduced further, shifting more to FedEx might unlock earned discount tiers.

4. **Review OnTrac service area**: Many shipments shifted to OnTrac may be at penalty pricing outside their core service area. Validate delivery performance.

---

*Analysis generated: February 2026*
*Data source: shipments_aggregated.parquet (558,210 shipments)*
*USPS Constraint: Tier 1 (35K/quarter = 140K/year)*
