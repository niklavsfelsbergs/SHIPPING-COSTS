# Scenario 6: Constrained Optimization with FedEx 16% Earned Discount

## Executive Summary

This analysis extends S4 (Constrained Optimization) by modeling FedEx at the 16% earned discount tier instead of 0%. The 16% tier requires $4.5-6.5M in true undiscounted FedEx transportation spend, so a volume constraint is added alongside the existing OnTrac and USPS commitments.

**FedEx costs are adjusted from the 18% earned discount baked into the rate tables to 16%.** The adjustment applies a 1.0541x multiplier to FedEx HD base rates and 1.0099x to SP base rates (plus fuel): ratio of effective discount factors for each service type.

**CRITICAL FINDING: The FedEx 16% tier is INFEASIBLE when both OnTrac and USPS commitments are active.** OnTrac's 279K minimum + USPS's 140K minimum leave only 121K shipments for FedEx, producing $2.50M undiscounted spend versus the $4.5M threshold required. The "Both constraints" result uses 16% rates without qualifying for them and is therefore invalid.

**The recommended S6 result is the "Drop OnTrac" variant at $5,396,055**, which is the cheapest configuration where FedEx actually meets the 16% tier ($4.66M undiscounted). This represents $676,006 (11.1%) savings versus the S1 baseline.

## Carrier Serviceability

| Carrier   | Serviceable     | Coverage   | Minimum Required                 | Feasible?   |
|-----------|-----------------|------------|----------------------------------|-------------|
| OnTrac    | 346,822         | 64.2%      | 279,080                          | YES         |
| USPS      | 539,917         | 100.0%     | 140,000                          | YES         |
| FedEx     | 539,917         | 100.0%     | $4.5M undiscounted transportation | **SEE BELOW** |

FedEx feasibility depends on which other carrier commitments are active. With both OnTrac and USPS commitments, insufficient volume remains for FedEx to reach the $4.5M undiscounted threshold.

## Methodology

### Algorithm: Greedy + Adjustment (Null-Aware)

1. **Initial Assignment**: For each group, assign to cheapest carrier **that can service it** (non-null cost)
2. **Check Constraints**: Verify if volume minimums are met
3. **Adjust for Constraints**: Shift lowest-cost-penalty groups to underutilized carriers (only if target carrier can service)
4. **Check FedEx Threshold**: Verify if FedEx undiscounted spend meets the $4.5M tier requirement

*Note: FedEx rates adjusted from 18% earned discount to 16%. The multiplier is 1.0541x on FedEx HD base rates and 1.0099x on SP base rates (plus fuel).*

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

| Variant                 | Carriers   | Total Cost          | FedEx 16% Tier         | vs S1 ($6,072,062) | Savings %   |
|-------------------------|------------|---------------------|------------------------|---------------------|-------------|
| Both constraints        | OUF        | $5,354,844          | **NOT MET** ($2.50M)   | $717,218            | 11.8%       |
| **Drop OnTrac**         | **UF**     | **$5,396,055**      | **MET ($4.66M)**       | **$676,006**        | **11.1%**   |
| Drop USPS               | OF         | $5,838,099          | MET ($4.93M)           | $233,962            | 3.9%        |
| Drop both (FedEx only)  | F          | $6,417,722          | MET ($9.32M)           | -$345,660           | -5.7%       |

**The "Both constraints" result ($5,354,844) is INVALID.** It uses FedEx 16% rates but only generates $2.50M undiscounted FedEx spend, falling short of the $4.5M threshold. In reality, FedEx would drop to 0% earned discount (see S4 for that scenario).

**"Drop OnTrac" ($5,396,055) is the recommended S6 result** - the cheapest variant where FedEx actually qualifies for the 16% tier. FedEx-only at $6.42M is 5.7% more expensive than the S1 baseline, confirming that the 16% discount alone cannot offset losing all alternative carriers.

### Cost of Commitment

Marginal cost of each carrier commitment (negative = the commitment saves money):

| Commitment          | Marginal Cost    | Interpretation                                          |
|---------------------|------------------|---------------------------------------------------------|
| OnTrac minimum      | -$41,211         | OnTrac saves $41K/year vs dropping it entirely           |
| USPS minimum        | -$483,255        | USPS saves $483K/year vs dropping it entirely            |
| Both commitments    | -$1,062,878      | Both together save $1.06M/year vs FedEx only             |

USPS remains the most valuable commitment ($483K savings). OnTrac's value is modest ($41K) - with FedEx at 16% earned discount, OnTrac's cost advantage narrows significantly compared to S4 where FedEx had 0% earned discount.

### Optimal Carrier Mix (Both Constraints - INFEASIBLE for 16% Tier)

| Carrier     | Shipments   | % of Total   | Total Cost          |
|-------------|-------------|--------------|---------------------|
| OnTrac      | 279,080     | 51.7%        | $2,731,153.71       |
| USPS        | 140,002     | 25.9%        | $865,423.67         |
| FedEx       | 120,835     | 22.4%        | $1,758,266.84       |
| **Total**   | **539,917** | **100%**     | **$5,354,844.22**   |

**WARNING**: This mix generates only $2.50M undiscounted FedEx spend, well below the $4.5M threshold for the 16% earned discount tier. These costs are calculated at 16% rates that would not actually apply.

### Constraint Satisfaction (Both Constraints)

| Carrier   | Actual      | Minimum           | Status                          |
|-----------|-------------|-------------------|---------------------------------|
| OnTrac    | 279,080     | 279,080           | **MET**                         |
| USPS      | 140,002     | 140,000           | **MET**                         |
| FedEx     | $2.50M UD   | $4.5M UD          | **NOT MET** (55.6% of target)  |

### FedEx Service Breakdown (Both Constraints)

| Service          | Shipments   | Share    |
|------------------|-------------|----------|
| Home Delivery    | 85,082      | 70.4%    |
| SmartPost        | 35,753      | 29.6%    |

### Groups Shifted

**Volume constraint shifts** (to meet OnTrac minimum):

| Metric                           | Value         |
|----------------------------------|---------------|
| Groups shifted to OnTrac         | 77,128        |
| Shipments shifted to OnTrac      | 113,046       |
| Total cost penalty               | $211,403.33   |

**FedEx threshold shifts** (attempting to meet $4.5M undiscounted):

| Metric                           | Value         |
|----------------------------------|---------------|
| Groups shifted from USPS to FedEx| 24,733        |
| Shipments shifted to FedEx       | 37,396        |
| Undiscounted contribution        | $593,096      |
| Total cost penalty               | $30,715       |

Despite shifting 37,396 additional shipments to FedEx, the undiscounted spend only reaches $2.50M - still $2.0M short of the $4.5M threshold. Further shifts are not possible because OnTrac's commitment absorbs most of the volume that could otherwise go to FedEx.

## Key Findings

1. **FedEx 16% tier is infeasible with both commitments**: OnTrac's 279K + USPS's 140K minimum leaves only 121K shipments for FedEx, producing just $2.50M undiscounted spend versus the $4.5M required. The three constraints are mutually incompatible.

2. **Dropping OnTrac unlocks the 16% tier**: Without the OnTrac commitment, enough volume shifts to FedEx to reach $4.66M undiscounted, comfortably above the $4.5M threshold. This variant costs $5,396,055 - only $41K more than the (invalid) "Both constraints" result.

3. **USPS remains highly valuable**: Dropping USPS costs an additional $483K compared to the recommended variant. The USPS commitment should be maintained in all scenarios.

4. **OnTrac's value diminishes at 16% earned**: OnTrac saves only $41K/year here versus $448K/year in S4 (0% earned). With FedEx at competitive 16% rates, OnTrac's cost advantage over FedEx narrows significantly.

5. **FedEx-only is worse than current mix**: At $6,417,722, the FedEx-only variant is 5.7% more expensive than S1. The 16% discount is not enough to offset losing all alternative carriers.

6. **S4 vs S6 comparison**: S4's "Both constraints" result ($5,555,189 at 0% earned) is valid and implementable. S6's equivalent ($5,354,844 at 16% earned) is not. The practical choice is between S4's $5,555,189 (both commitments, 0% FedEx earned) and S6's $5,396,055 (drop OnTrac, 16% FedEx earned).

## Recommendations

1. **Use S4 "Both constraints" as the primary recommendation**: $5,555,189 with both carrier commitments is valid and achievable. S6's "Both constraints" is not implementable.

2. **Consider the OnTrac tradeoff carefully**: Dropping OnTrac saves $159K/year ($5,555,189 - $5,396,055) by enabling the FedEx 16% tier, but loses the OnTrac contract relationship. This decision involves strategic factors beyond cost.

3. **Negotiate FedEx threshold reduction**: If the 16% tier threshold could be lowered to ~$2.5M, the "Both constraints" variant would become feasible, yielding the best of all worlds at $5,354,844.

4. **Monitor FedEx volume closely**: The 16% tier has a narrow band ($4.5-6.5M). Routing decisions should be managed to stay within the qualifying range.

---

*Analysis generated: February 2026*
*Data source: shipments_unified.parquet (539,917 matched shipments), FedEx 16% earned discount*
*S1 Baseline: $6,072,062 (current mix at 16% earned discount)*
*USPS Constraint: Tier 1 (35K/quarter = 140K/year)*
*OnTrac serviceable: 346,822 shipments (64.2%)*
*FedEx adjustment: HD 1.0541x, SP 1.0099x multiplier on base rate (PP baked, earned 16% vs 18% baked in)*
