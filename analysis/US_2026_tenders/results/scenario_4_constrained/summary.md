# Scenario 4: Constrained Optimization

## Executive Summary

This analysis finds the optimal carrier mix for US shipments while respecting contractual volume commitments. It also tests what happens when carrier commitments are dropped entirely (removing the carrier from routing, since contract rates wouldn't apply without meeting minimums).

**FedEx costs are adjusted to remove the 18% earned discount.** When optimization reduces FedEx spend below $4.5M, the earned discount is lost. The adjustment increases FedEx costs by ~49% on the base rate portion (multiplier 1.4865x), making OnTrac and USPS significantly more valuable.

**Both constraints can be satisfied.** The optimized mix with both OnTrac and USPS commitments achieves **$341,101 (5.8%) savings** versus current routing (also adjusted). Both commitments are strongly beneficial - OnTrac saves $364K/year and USPS saves $1.15M/year compared to dropping either carrier.

## Carrier Serviceability

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

*Note: FedEx rates adjusted to remove 18% earned discount. When optimization shifts volume away from FedEx, the $4.5M earned discount threshold is no longer met. The adjustment applies a 1.4865x multiplier to FedEx base rates (plus fuel) to reflect true cost without the discount.*

### Constraint Combinations

When a carrier commitment is dropped, the carrier is removed entirely from routing (without meeting minimums, contract rates wouldn't apply):

| Variant             | Available Carriers      | Minimums Enforced               |
|---------------------|-------------------------|---------------------------------|
| Both constraints    | OnTrac, USPS, FedEx     | OnTrac >= 279K, USPS >= 140K   |
| Drop OnTrac         | USPS, FedEx             | USPS >= 140K                    |
| Drop USPS           | OnTrac, FedEx           | OnTrac >= 279K                  |
| Drop both           | FedEx only              | None                            |

## Results

### Variant Comparison

| Variant                 | Carriers   | Total Cost          | vs Current          | Savings %   |
|-------------------------|------------|---------------------|---------------------|-------------|
| Current Mix (adjusted)  | -          | $7,074,583          | -                   | -           |
| **Both constraints**    | **OUF**    | **$5,492,793**      | **$1,581,789**      | **22.4%**   |
| Drop OnTrac             | UF         | $5,857,270          | $1,217,313          | 17.2%       |
| Drop USPS               | OF         | $6,645,023          | $429,559            | 6.1%        |
| Drop both (FedEx only)  | F          | $8,333,650          | -$1,259,067         | -17.8%      |

**Both constraints is the cheapest variant** by a significant margin ($365K cheaper than Drop OnTrac). FedEx-only at $8.33M is extremely expensive without the earned discount - 18% more than the adjusted current mix.

*Note: "Current Mix (adjusted)" reflects the S1 baseline with FedEx earned discount removed from FedEx shipments in the current routing. The universal S1 baseline (with earned discount) is $5,833,894.*

### Cost of Commitment

Marginal cost of each carrier commitment (negative = the commitment saves money):

| Commitment          | Marginal Cost    | Interpretation                                          |
|---------------------|------------------|---------------------------------------------------------|
| OnTrac minimum      | -$364,476        | OnTrac saves $364K/year vs dropping it entirely          |
| USPS minimum        | -$1,152,230      | USPS saves $1.15M/year vs dropping it entirely           |
| Both commitments    | -$2,840,856      | Both together save $2.84M/year vs FedEx only             |

Both carrier commitments are strongly beneficial. USPS is the most valuable ($1.15M savings), and OnTrac is also clearly worthwhile ($364K savings). Without the earned discount, FedEx is expensive enough that every alternative carrier provides meaningful savings.

### Optimal Carrier Mix (Both Constraints)

| Carrier     | Shipments   | % of Total   | Total Cost          |
|-------------|-------------|--------------|---------------------|
| OnTrac      | 279,082     | 50.0%        | $2,563,751.70       |
| USPS        | 224,183     | 40.2%        | $1,736,237.50       |
| FedEx       | 54,748      | 9.8%         | $1,192,804.24       |
| **Total**   | **558,013** | **100%**     | **$5,492,793.43**   |

### Constraint Satisfaction

| Carrier   | Actual      | Minimum     | Status      |
|-----------|-------------|-------------|-------------|
| OnTrac    | 279,082     | 279,080     | **MET**     |
| USPS      | 224,183     | 140,000     | **MET**     |
| FedEx     | 54,748      | 0           | **MET**     |

USPS exceeds its minimum by 84,183 shipments - these remain with USPS because they are cheaper than shifting to FedEx (which is expensive without the earned discount).

### FedEx Service Breakdown

| Service          | Shipments   | Share    |
|------------------|-------------|----------|
| Home Delivery    | 13,050      | 23.8%    |
| SmartPost        | 41,698      | 76.2%    |

### Groups Shifted

To meet the OnTrac minimum:

| Metric                           | Value         |
|----------------------------------|---------------|
| Groups shifted to OnTrac         | 64,501        |
| Shipments shifted to OnTrac      | 96,314        |
| Total cost penalty               | $173,979.01   |

The greedy assignment initially allocated only 182,768 shipments to OnTrac, requiring 96,314 additional shipments to be shifted from USPS and FedEx to meet the 279,080 minimum. Only shipments in OnTrac's serviceable area were shifted.

## Key Findings

1. **Both commitments are strongly beneficial**: With FedEx costs inflated by the earned discount loss, OnTrac saves $364K and USPS saves $1.15M - both are clearly worth maintaining.

2. **USPS is the most valuable commitment**: Dropping USPS and relying on OnTrac + FedEx would cost $1.15M more. USPS absorbs 40% of shipments, providing cost-effective routing nationwide.

3. **OnTrac commitment is clearly beneficial**: Unlike the pre-adjustment analysis where OnTrac barely broke even, removing the earned discount makes OnTrac's $364K savings significant and unambiguous.

4. **FedEx-only is very expensive**: "Drop both" costs $8.33M - 18% more than the adjusted current mix. Without the earned discount, 100% FedEx is the worst option by far.

5. **FedEx volume drops to 9.8%**: The optimizer heavily favors OnTrac and USPS over the more expensive (unadjusted) FedEx rates, sending only 55K shipments to FedEx.

6. **Shift penalty is modest**: $174K cost to shift 96K shipments to OnTrac ($1.81/shipment average penalty) - lower than pre-adjustment because more volume naturally gravitates to OnTrac.

## Recommendations

1. **Maintain both carrier commitments**: Both OnTrac and USPS commitments provide significant cost savings and should be kept.

2. **Implement optimized routing**: Route by (packagetype, zip, weight) based on the assignment results.

3. **Monitor OnTrac minimum**: At 279,082 shipments, there's minimal buffer. Consider targeting 285-290K for safety margin.

4. **Negotiate earned discount floor**: If possible, negotiate a minimum earned discount that persists even below $4.5M FedEx spend. This would make FedEx more competitive in the mix.

---

*Analysis generated: February 2026*
*Data source: shipments_unified.parquet (558,013 shipments), FedEx earned discount removed*
*USPS Constraint: Tier 1 (35K/quarter = 140K/year)*
*OnTrac serviceable: 360,151 shipments (64.5%)*
*FedEx adjustment: 1.4865x multiplier on base rate (PP 45%, earned 18% removed, fuel 14%)*
