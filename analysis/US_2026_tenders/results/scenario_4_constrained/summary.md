# Scenario 4: Constrained Optimization

## Executive Summary

This analysis finds the optimal carrier mix for US shipments while respecting contractual volume commitments: OnTrac minimum of 279,080 shipments/year and USPS Tier 1 minimum of 140,000 shipments/year. **Both constraints can be satisfied.** The optimized mix achieves **$918,478 (14.4%) savings** versus current routing.

## Carrier Serviceability

Not all carriers can service all shipments. OnTrac has geographic limitations:

| Carrier   | Serviceable     | Coverage   | Minimum Required   | Feasible?   |
|-----------|-----------------|------------|--------------------|-------------|
| OnTrac    | 360,151         | 64.5%      | 279,080            | **YES**     |
| USPS      | 558,013         | 100.0%     | 140,000            | YES         |
| FedEx     | 558,013         | 100.0%     | 0                  | YES         |

OnTrac can only service 360K shipments (West region), but this exceeds their 279K minimum - constraint is feasible.

## Methodology

### Algorithm: Greedy + Adjustment (Null-Aware)

1. **Initial Assignment**: For each group, assign to cheapest carrier **that can service it** (non-null cost)
2. **Check Constraints**: Verify if volume minimums are met
3. **Adjust for Constraints**: Shift lowest-cost-penalty groups to underutilized carriers (only if target carrier can service)
4. **FedEx Earned Discount**: Apply discount tier based on final FedEx transportation charges

### Constraints

| Carrier   | Minimum Volume      | Calculation                   | Status        |
|-----------|---------------------|-------------------------------|---------------|
| OnTrac    | 279,080 shipments   | 5,365/week × 52               | Contractual   |
| USPS      | 140,000 shipments   | 35,000/quarter × 4 (Tier 1)   | Tier 1        |
| FedEx     | No minimum          | Earned discount tiers apply   | -             |

### Feasibility Analysis

- **Total shipments available**: 558,013
- **OnTrac serviceable**: 360,151 (64.5%)
- **Combined minimums (USPS + OnTrac)**: 419,080
- **Conclusion**: Both constraints CAN be satisfied

## Results

### Scenario Comparison

| Scenario                      | Total Cost          | vs Current          | Savings %   |
|-------------------------------|---------------------|---------------------|-------------|
| Current Mix                   | $6,389,595.72       | -                   | -           |
| Unconstrained Optimal         | $5,278,875.79       | $1,110,719.93       | 17.4%       |
| **Constrained Optimal**       | **$5,471,117.96**   | **$918,477.76**     | **14.4%**   |

### Optimal Carrier Mix

| Carrier     | Shipments   | % of Total   | Total Cost          |
|-------------|-------------|--------------|---------------------|
| OnTrac      | 279,085     | 50.0%        | $2,632,038.46       |
| USPS        | 188,240     | 33.7%        | $1,283,864.30       |
| FedEx       | 90,688      | 16.3%        | $1,555,215.20       |
| **Total**   | **558,013** | **100%**     | **$5,471,117.96**   |

### Constraint Satisfaction

| Carrier   | Actual      | Minimum     | Status      |
|-----------|-------------|-------------|-------------|
| OnTrac    | 279,085     | 279,080     | **MET**     |
| USPS      | 188,240     | 140,000     | **MET**     |
| FedEx     | 90,688      | 0           | **MET**     |

USPS exceeds its minimum by 48,240 shipments - these remain with USPS because they are cheaper than shifting to FedEx.

### FedEx Earned Discount

| Metric                    | Value            |
|---------------------------|------------------|
| Transportation Charges    | $1,555,215.20    |
| Tier                      | < $4.5M          |
| Discount Rate             | 0%               |
| Discount Amount           | $0.00            |

FedEx volume does not reach the $4.5M threshold needed for any earned discount tier.

### Groups Shifted

To meet the OnTrac minimum:

| Metric                           | Value         |
|----------------------------------|---------------|
| Groups shifted to OnTrac         | 74,216        |
| Shipments shifted to OnTrac      | 108,512       |
| Total cost penalty               | $192,242.17   |

The greedy assignment initially allocated only 170,573 shipments to OnTrac, requiring 108,512 additional shipments to be shifted from USPS and FedEx to meet the 279,080 minimum. Only shipments in OnTrac's serviceable area were shifted.

## Key Findings

1. **OnTrac constraint is feasible**: With 360K serviceable shipments vs 279K minimum, OnTrac can meet its commitment.

2. **Both constraints can be satisfied**: With 140K USPS + 279K OnTrac = 419K combined minimums, there's room for 139K FedEx shipments.

3. **OnTrac minimum drives the optimization**: 50% of all shipments go to OnTrac to meet the contractual minimum.

4. **USPS gets more than its minimum**: 188K shipments remain with USPS (vs 140K minimum) because they're cheaper there than alternatives.

5. **Shift penalty is modest**: $192K cost to shift 109K shipments to OnTrac (only $1.77/shipment average penalty).

6. **Significant savings**: 14.4% ($918K) savings achievable vs current routing even with constraints.

## Recommendations

1. **Implement optimized routing**: Route by (packagetype, zip, weight) based on the assignment results.

2. **Monitor OnTrac minimum**: At approximately 279,085 shipments, there's minimal buffer. Consider targeting 285-290K for safety margin.

3. **OnTrac geographic constraint is binding**: Only 64.5% of shipments can go to OnTrac - routing must respect service area.

4. **Consider FedEx volume increase**: If USPS minimum could be reduced further, shifting more to FedEx might unlock earned discount tiers.

---

*Analysis generated: February 2026*
*Data source: shipments_aggregated.parquet (558,013 shipments)*
*USPS Constraint: Tier 1 (35K/quarter = 140K/year)*
*OnTrac serviceable: 360,151 shipments (64.5%)*
