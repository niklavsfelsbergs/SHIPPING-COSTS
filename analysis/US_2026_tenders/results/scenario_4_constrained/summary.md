# Scenario 4: Constrained Optimization

## Executive Summary

This analysis finds the optimal carrier mix for US shipments while respecting contractual volume commitments. It also tests what happens when carrier commitments are dropped entirely (removing the carrier from routing, since contract rates wouldn't apply without meeting minimums).

**FedEx costs are adjusted to remove the 18% earned discount.** When optimization reduces FedEx spend below $4.5M, the earned discount is lost. The adjustment increases FedEx costs by ~49% on the HD base rate portion (HD multiplier 1.4865x, SP multiplier 1.0891x), making OnTrac and USPS significantly more valuable.

**Both constraints can be satisfied.** The optimized mix with both OnTrac and USPS commitments achieves **$516,873 (8.5%) savings** versus the S1 baseline ($6,072,062), or **$1,118,508 (16.8%) savings** versus the adjusted current mix ($6,673,697 with FedEx earned discount removed). Both commitments are strongly beneficial - OnTrac saves $448K/year and USPS saves $846K/year compared to dropping either carrier.

## Carrier Serviceability

| Carrier   | Serviceable     | Coverage   | Minimum Required   | Feasible?   |
|-----------|-----------------|------------|--------------------|-------------|
| OnTrac    | 346,822         | 64.2%      | 279,080            | **YES**     |
| USPS      | 539,917         | 100.0%     | 140,000            | YES         |
| FedEx     | 539,917         | 100.0%     | 0                  | YES         |

OnTrac can only service 347K shipments (West region), but this exceeds their 279K minimum - constraint is feasible.

## Methodology

### Algorithm: Greedy + Adjustment (Null-Aware)

1. **Initial Assignment**: For each group, assign to cheapest carrier **that can service it** (non-null cost)
2. **Check Constraints**: Verify if volume minimums are met
3. **Adjust for Constraints**: Shift lowest-cost-penalty groups to underutilized carriers (only if target carrier can service)

*Note: FedEx rates adjusted to remove 18% earned discount. When optimization shifts volume away from FedEx, the $4.5M earned discount threshold is no longer met. The adjustment applies a 1.4865x multiplier to FedEx HD base rates and 1.0891x to SP base rates (plus fuel) to reflect true cost without the discount.*

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
| Current Mix (adjusted)  | -          | $6,673,697          | -                   | -           |
| **Both constraints**    | **OUF**    | **$5,555,189**      | **$1,118,508**      | **16.8%**   |
| Drop OnTrac             | UF         | $6,003,310          | $670,388            | 10.0%       |
| Drop USPS               | OF         | $6,401,278          | $272,419            | 4.1%        |
| Drop both (FedEx only)  | F          | $7,456,284          | -$782,587           | -11.7%      |

**Both constraints is the cheapest variant** by a significant margin ($448K cheaper than Drop OnTrac). FedEx-only at $7.46M is extremely expensive without the earned discount - 11.7% more than the adjusted current mix.

*Note: "Current Mix (adjusted)" reflects the S1 baseline with FedEx earned discount removed from FedEx shipments in the current routing. The universal S1 baseline (with earned discount, FedEx at actual 16% tier) is $6,072,062.*

### Cost of Commitment

Marginal cost of each carrier commitment (negative = the commitment saves money):

| Commitment          | Marginal Cost    | Interpretation                                          |
|---------------------|------------------|---------------------------------------------------------|
| OnTrac minimum      | -$448,121        | OnTrac saves $448K/year vs dropping it entirely          |
| USPS minimum        | -$846,090        | USPS saves $846K/year vs dropping it entirely            |
| Both commitments    | -$1,901,095      | Both together save $1.90M/year vs FedEx only             |

Both carrier commitments are strongly beneficial. USPS is the most valuable ($846K savings), and OnTrac is also clearly worthwhile ($448K savings). Without the earned discount, FedEx is expensive enough that every alternative carrier provides meaningful savings.

### Optimal Carrier Mix (Both Constraints)

| Carrier     | Shipments   | % of Total   | Total Cost          |
|-------------|-------------|--------------|---------------------|
| OnTrac      | 279,084     | 51.7%        | $2,951,574.61       |
| USPS        | 221,449     | 41.0%        | $1,713,684.68       |
| FedEx       | 39,384      | 7.3%         | $889,929.61         |
| **Total**   | **539,917** | **100%**     | **$5,555,188.90**   |

### Constraint Satisfaction

| Carrier   | Actual      | Minimum     | Status      |
|-----------|-------------|-------------|-------------|
| OnTrac    | 279,084     | 279,080     | **MET**     |
| USPS      | 221,449     | 140,000     | **MET**     |
| FedEx     | 39,384      | 0           | **MET**     |

USPS exceeds its minimum by 81,449 shipments - these remain with USPS because they are cheaper than shifting to FedEx (which is expensive without the earned discount).

### FedEx Service Breakdown

| Service          | Shipments   | Share    |
|------------------|-------------|----------|
| Home Delivery    | 31,181      | 79.2%    |
| SmartPost        | 8,203       | 20.8%    |

### Groups Shifted

To meet the OnTrac minimum:

| Metric                           | Value         |
|----------------------------------|---------------|
| Groups shifted to OnTrac         | 51,480        |
| Shipments shifted to OnTrac      | 78,053        |
| Total cost penalty               | $105,498.45   |

The greedy assignment initially allocated only 201,031 shipments to OnTrac, requiring 78,053 additional shipments to be shifted from USPS and FedEx to meet the 279,080 minimum. Only shipments in OnTrac's serviceable area were shifted.

## Key Findings

1. **Both commitments are strongly beneficial**: With FedEx costs inflated by the earned discount loss, OnTrac saves $448K and USPS saves $846K - both are clearly worth maintaining.

2. **USPS is the most valuable commitment**: Dropping USPS and relying on OnTrac + FedEx would cost $846K more. USPS absorbs 41% of shipments, providing cost-effective routing nationwide.

3. **OnTrac commitment is clearly beneficial**: Removing the earned discount makes OnTrac's $448K savings significant and unambiguous.

4. **FedEx-only is very expensive**: "Drop both" costs $7.46M - 11.7% more than the adjusted current mix. Without the earned discount, 100% FedEx is the worst option by far.

5. **FedEx volume drops to 7.3%**: The optimizer heavily favors OnTrac and USPS over the more expensive (unadjusted) FedEx rates, sending only 39K shipments to FedEx.

6. **Shift penalty is modest**: $105K cost to shift 78K shipments to OnTrac ($1.35/shipment average penalty) - lower than pre-adjustment because more volume naturally gravitates to OnTrac.

## Recommendations

1. **Maintain both carrier commitments**: Both OnTrac and USPS commitments provide significant cost savings and should be kept.

2. **Implement optimized routing**: Route by (packagetype, zip, weight) based on the assignment results.

3. **Monitor OnTrac minimum**: At 279,084 shipments, there's minimal buffer. Consider targeting 285-290K for safety margin.

4. **Negotiate earned discount floor**: If possible, negotiate a minimum earned discount that persists even below $4.5M FedEx spend. This would make FedEx more competitive in the mix.

---

*Analysis generated: February 2026*
*Data source: shipments_unified.parquet (539,917 matched shipments), FedEx earned discount removed*
*USPS Constraint: Tier 1 (35K/quarter = 140K/year)*
*OnTrac serviceable: 346,822 shipments (64.2%)*
*FedEx adjustment: HD 1.4865x, SP 1.0891x multiplier on base rate (earned 18% removed, fuel applied)*
