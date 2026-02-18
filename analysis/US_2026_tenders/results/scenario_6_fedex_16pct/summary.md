# Scenario 6: Constrained Optimization with FedEx 16% Earned Discount

## Executive Summary

This analysis extends S4 (Constrained Optimization) by modeling FedEx at the 16% earned discount tier instead of 0%. The 16% tier requires $4.5-6.5M in true undiscounted FedEx transportation spend, so a volume constraint is added alongside the existing OnTrac and USPS commitments.

**FedEx costs are adjusted from the 18% earned discount baked into the rate tables to 16%.** The adjustment applies a 1.0541x multiplier to FedEx base rates (plus fuel): (1-0.45-0.16)/(1-0.45-0.18) = 0.39/0.37.

**CRITICAL FINDING: The FedEx 16% tier is INFEASIBLE when both OnTrac and USPS commitments are active.** OnTrac's 279K minimum + USPS's 140K minimum leave only 139K shipments for FedEx, producing $3.67M undiscounted spend versus the $4.5M threshold required. The "Both constraints" result uses 16% rates without qualifying for them and is therefore invalid.

**The recommended S6 result is the "Drop OnTrac" variant at $5,040,871**, which is the cheapest configuration where FedEx actually meets the 16% tier ($5.66M undiscounted). This represents $930,878 (15.6%) savings versus the S1 baseline.

## Carrier Serviceability

| Carrier   | Serviceable     | Coverage   | Minimum Required                 | Feasible?   |
|-----------|-----------------|------------|----------------------------------|-------------|
| OnTrac    | 360,151         | 64.5%      | 279,080                          | YES         |
| USPS      | 558,013         | 100.0%     | 140,000                          | YES         |
| FedEx     | 558,013         | 100.0%     | $4.5M undiscounted transportation | **SEE BELOW** |

FedEx feasibility depends on which other carrier commitments are active. With both OnTrac and USPS commitments, insufficient volume remains for FedEx to reach the $4.5M undiscounted threshold.

## Methodology

### Algorithm: Greedy + Adjustment (Null-Aware)

1. **Initial Assignment**: For each group, assign to cheapest carrier **that can service it** (non-null cost)
2. **Check Constraints**: Verify if volume minimums are met
3. **Adjust for Constraints**: Shift lowest-cost-penalty groups to underutilized carriers (only if target carrier can service)
4. **Check FedEx Threshold**: Verify if FedEx undiscounted spend meets the $4.5M tier requirement

*Note: FedEx rates adjusted from 18% earned discount to 16%. The multiplier is 1.0541x on FedEx base rates (plus fuel): (1-0.45-0.16)/(1-0.45-0.18) = 0.39/0.37.*

### Constraint Combinations

When a carrier commitment is dropped, the carrier is removed entirely from routing (without meeting minimums, contract rates wouldn't apply):

| Variant             | Available Carriers      | Minimums Enforced                                 |
|---------------------|-------------------------|---------------------------------------------------|
| Both constraints    | OnTrac, USPS, FedEx     | OnTrac >= 279K, USPS >= 140K, FedEx >= $4.5M UD  |
| Drop OnTrac         | USPS, FedEx             | USPS >= 140K, FedEx >= $4.5M UD                   |
| Drop USPS           | OnTrac, FedEx           | OnTrac >= 279K, FedEx >= $4.5M UD                 |
| Drop both           | FedEx only              | FedEx >= $4.5M UD                                  |

## Results

### Variant Comparison

| Variant                 | Carriers   | Total Cost          | FedEx 16% Tier         | vs S1 ($5,971,748) | Savings %   |
|-------------------------|------------|---------------------|------------------------|---------------------|-------------|
| Both constraints        | OUF        | $5,002,886          | **NOT MET** ($3.67M)   | $968,862            | 16.2%       |
| **Drop OnTrac**         | **UF**     | **$5,040,871**      | **MET ($5.66M)**       | **$930,878**        | **15.6%**   |
| Drop USPS               | OF         | $5,521,358          | MET ($6.43M)           | $450,390            | 7.5%        |
| Drop both (FedEx only)  | F          | $6,160,686          | MET ($11.9M)           | -$188,938           | -3.2%       |

**The "Both constraints" result ($5,002,886) is INVALID.** It uses FedEx 16% rates but only generates $3.67M undiscounted FedEx spend, falling short of the $4.5M threshold. In reality, FedEx would drop to 0% earned discount (see S4 for that scenario).

**"Drop OnTrac" ($5,040,871) is the recommended S6 result** - the cheapest variant where FedEx actually qualifies for the 16% tier. FedEx-only at $6.16M is 3.2% more expensive than the S1 baseline, confirming that the 16% discount alone cannot offset losing all alternative carriers.

### Cost of Commitment

Marginal cost of each carrier commitment (negative = the commitment saves money):

| Commitment          | Marginal Cost    | Interpretation                                          |
|---------------------|------------------|---------------------------------------------------------|
| OnTrac minimum      | -$37,985         | OnTrac saves $38K/year vs dropping it entirely           |
| USPS minimum        | -$518,473        | USPS saves $518K/year vs dropping it entirely            |

USPS remains the most valuable commitment ($518K savings). OnTrac's value is modest ($38K) - with FedEx at 16% earned discount, OnTrac's cost advantage narrows significantly compared to S4 where FedEx had 0% earned discount.

### Optimal Carrier Mix (Both Constraints - INFEASIBLE for 16% Tier)

| Carrier     | Shipments   | % of Total   | Total Cost          |
|-------------|-------------|--------------|---------------------|
| OnTrac      | 279,080     | 50.0%        | $2,274,111          |
| USPS        | 140,001     | 25.1%        | $871,842            |
| FedEx       | 138,932     | 24.9%        | $1,856,932          |
| **Total**   | **558,013** | **100%**     | **$5,002,886**      |

**WARNING**: This mix generates only $3.67M undiscounted FedEx spend, well below the $4.5M threshold for the 16% earned discount tier. These costs are calculated at 16% rates that would not actually apply.

### Constraint Satisfaction (Both Constraints)

| Carrier   | Actual      | Minimum           | Status                          |
|-----------|-------------|-------------------|---------------------------------|
| OnTrac    | 279,080     | 279,080           | **MET**                         |
| USPS      | 140,001     | 140,000           | **MET**                         |
| FedEx     | $3.67M UD   | $4.5M UD          | **NOT MET** (81.6% of target)  |

### FedEx Service Breakdown (Both Constraints)

| Service          | Shipments   | Share    |
|------------------|-------------|----------|
| Home Delivery    | 29,661      | 21.3%    |
| SmartPost        | 109,271     | 78.7%    |

### Groups Shifted

**Volume constraint shifts** (to meet OnTrac minimum):

| Metric                           | Value         |
|----------------------------------|---------------|
| Groups shifted to OnTrac         | 65,557        |
| Shipments shifted to OnTrac      | 109,381       |
| Total cost penalty               | $208,284      |

**FedEx threshold shifts** (attempting to meet $4.5M undiscounted):

| Metric                           | Value         |
|----------------------------------|---------------|
| Groups shifted from USPS to FedEx| 18,746        |
| Shipments shifted to FedEx       | 28,121        |
| Undiscounted contribution        | $536,685      |
| Total cost penalty               | $21,153       |

Despite shifting 28,121 additional shipments to FedEx, the undiscounted spend only reaches $3.67M - still $830K short of the $4.5M threshold. Further shifts are not possible because OnTrac's commitment absorbs most of the volume that could otherwise go to FedEx.

## Key Findings

1. **FedEx 16% tier is infeasible with both commitments**: OnTrac's 279K + USPS's 140K minimum leaves only 139K shipments for FedEx, producing just $3.67M undiscounted spend versus the $4.5M required. The three constraints are mutually incompatible.

2. **Dropping OnTrac unlocks the 16% tier**: Without the OnTrac commitment, enough volume shifts to FedEx to reach $5.66M undiscounted, comfortably above the $4.5M threshold. This variant costs $5,040,871 - only $38K more than the (invalid) "Both constraints" result.

3. **USPS remains highly valuable**: Dropping USPS costs an additional $518K compared to the recommended variant. The USPS commitment should be maintained in all scenarios.

4. **OnTrac's value diminishes at 16% earned**: OnTrac saves only $38K/year here versus $364K/year in S4 (0% earned). With FedEx at competitive 16% rates, OnTrac's cost advantage over FedEx narrows significantly.

5. **FedEx-only is slightly worse than current mix**: At $6,160,686, the FedEx-only variant is 3.2% more expensive than S1. The 16% discount is not enough to offset losing all alternative carriers.

6. **S4 vs S6 comparison**: S4's "Both constraints" result ($5,492,793 at 0% earned) is valid and implementable. S6's equivalent ($5,002,886 at 16% earned) is not. The practical choice is between S4's $5,492,793 (both commitments, 0% FedEx earned) and S6's $5,040,871 (drop OnTrac, 16% FedEx earned).

## Recommendations

1. **Use S4 "Both constraints" as the primary recommendation**: $5,492,793 with both carrier commitments is valid and achievable. S6's "Both constraints" is not implementable.

2. **Consider the OnTrac tradeoff carefully**: Dropping OnTrac saves $452K/year ($5,492,793 - $5,040,871) by enabling the FedEx 16% tier, but loses the OnTrac contract relationship. This decision involves strategic factors beyond cost.

3. **Negotiate FedEx threshold reduction**: If the 16% tier threshold could be lowered to ~$3.5M, the "Both constraints" variant would become feasible, yielding the best of all worlds at $5,002,886.

4. **Monitor FedEx volume closely**: The 16% tier has a narrow band ($4.5-6.5M). Routing decisions should be managed to stay within the qualifying range.

---

*Analysis generated: February 2026*
*Data source: shipments_unified.parquet (558,013 shipments), FedEx 16% earned discount*
*S1 Baseline: $5,971,748 (current mix at 16% earned discount)*
*USPS Constraint: Tier 1 (35K/quarter = 140K/year)*
*OnTrac serviceable: 360,151 shipments (64.5%)*
*FedEx adjustment: 1.0541x multiplier on base rate (PP 45%, earned 16% vs 18% baked in)*
