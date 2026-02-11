# Scenario 5: Optimal with P2P

## Executive Summary

This analysis extends Scenario 4 by adding P2P US as an additional carrier. For each constraint combination, P2P improves the result - **S5 is guaranteed to be at least as cheap as S4** because P2P is purely additive (no minimum commitment).

**FedEx costs are adjusted to remove the 18% earned discount** (same as S4). When optimization reduces FedEx spend below $4.5M, the earned discount is lost, increasing FedEx costs by ~49% on the base rate portion.

**With both constraints enforced**, adding P2P saves **$99,705 (1.8%)** vs S4, bringing the total to **$5,393,088 (7.6% savings vs S1 baseline)**. P2P captures 43,856 shipments at $4.51/shipment average by cherry-picking the cheapest segments from USPS and FedEx.

**Without the OnTrac commitment**, the best result drops to **$4,931,056 (15.5% savings)** using USPS + FedEx + P2P.

## Carrier Serviceability

| Carrier   | Serviceable     | Coverage   | Minimum Required   |
|-----------|-----------------|------------|--------------------|
| OnTrac    | 360,151         | 64.5%      | 279,080            |
| USPS      | 558,013         | 100.0%     | 140,000            |
| FedEx     | 558,013         | 100.0%     | 0                  |
| P2P       | 289,272         | 51.8%      | 0                  |

P2P can service 289K shipments due to weight limits and geographic coverage.

## Methodology

### Dual-Method Approach

For each constraint combination, two methods are tested and the cheaper result is kept:

- **Method A**: Greedy assignment with all carriers (including P2P) + constraint adjustment
- **Method B**: Take Scenario 4's solution and improve by switching groups to P2P where cheaper

Method B guarantees S5 <= S4 because it only makes beneficial switches from S4's baseline. Switches respect carrier minimums:
- FedEx -> P2P: always safe (no FedEx minimum)
- USPS -> P2P: only up to USPS surplus above minimum
- OnTrac -> P2P: only up to OnTrac surplus above minimum

*Note: FedEx rates adjusted to remove 18% earned discount (same as S4). See S4 summary for adjustment methodology.*

### Constraint Combinations

Same as S4 but with P2P added to each variant:

| Variant             | Available Carriers            | Minimums Enforced               |
|---------------------|-------------------------------|---------------------------------|
| Both constraints    | OnTrac, USPS, FedEx, P2P     | OnTrac >= 279K, USPS >= 140K   |
| Drop OnTrac         | USPS, FedEx, P2P             | USPS >= 140K                    |
| Drop USPS           | OnTrac, FedEx, P2P           | OnTrac >= 279K                  |
| Drop both           | FedEx, P2P                   | None                            |

## Results

### Variant Comparison

| Variant                | S5 Cost        | S4 Cost        | P2P Benefit   | vs S1 Baseline  | Method   |
|------------------------|----------------|----------------|---------------|-----------------|----------|
| **Both constraints**   | **$5,393,088** | **$5,492,793** | **+$99,705**  | **7.6%**        | **B**    |
| Drop OnTrac            | $4,931,056     | $5,857,270     | +$926,214     | 15.5%           | A        |
| Drop USPS              | $6,371,922     | $6,645,023     | +$273,102     | 9.4%            | B        |
| Drop both              | $6,324,461     | $8,333,650     | +$2,009,188   | 8.5%            | A        |

**S5 <= S4 guarantee met for all variants.** P2P improves every scenario.

P2P's biggest impact is when OnTrac is dropped: the "Drop OnTrac" variant saves $903K (15.5%) vs S1 baseline - the cheapest scenario across all of S4 and S5. P2P absorbs enormous FedEx volume ($2.01M savings in "Drop both").

### Optimal Carrier Mix (Both Constraints)

| Carrier     | Shipments   | % of Total   | Total Cost          |
|-------------|-------------|--------------|---------------------|
| OnTrac      | 279,082     | 50.0%        | $2,563,751.70       |
| USPS        | 181,917     | 32.6%        | $1,471,242.69       |
| FedEx       | 53,158      | 9.5%         | $1,160,116.95       |
| P2P         | 43,856      | 7.9%         | $197,976.62         |
| **Total**   | **558,013** | **100%**     | **$5,393,087.95**   |

### How Method B Works (Both Constraints)

Starting from S4's solution ($5,492,793), Method B switches groups to P2P where cheaper:

| Switch         | Groups   | Shipments   | Savings       |
|----------------|----------|-------------|---------------|
| FedEx -> P2P   | 1,294    | 1,590       | $18,540       |
| USPS -> P2P    | 14,543   | 42,266      | $81,166       |
| **Total**      | **15,837** | **43,856** | **$99,705**   |

OnTrac -> P2P: 0 switches (OnTrac is at its minimum with no surplus to release).

### Constraint Satisfaction

| Carrier   | Actual      | Minimum     | Status      |
|-----------|-------------|-------------|-------------|
| OnTrac    | 279,082     | 279,080     | **MET**     |
| USPS      | 181,917     | 140,000     | **MET**     |
| FedEx     | 53,158      | 0           | N/A         |
| P2P       | 43,856      | 0           | N/A         |

### FedEx Service Breakdown

| Service          | Shipments   | Share    |
|------------------|-------------|----------|
| Home Delivery    | 12,206      | 23.0%    |
| SmartPost        | 40,952      | 77.0%    |

## The "Drop OnTrac" Finding

The most significant finding is that **USPS + FedEx + P2P without OnTrac** produces the cheapest result at $4,931,056 (15.5% savings vs S1 baseline). This is $462K cheaper than "Both constraints" with P2P.

| Metric                    | Both Constraints   | Drop OnTrac         |
|---------------------------|--------------------|---------------------|
| Total Cost                | $5,393,088         | $4,931,056          |
| Savings vs S1 Baseline    | 7.6%               | 15.5%               |
| USPS shipments            | 181,917            | ~450K*              |
| FedEx shipments           | 53,158             | ~108K*              |
| P2P shipments             | 43,856             | ~(remainder)*       |

*Approximate from Method A greedy assignment.

**Why dropping OnTrac helps:** OnTrac requires 279K minimum shipments, but the greedy optimizer (with adjusted FedEx costs) initially wants to send 183K to OnTrac. The remaining 96K must be shifted at a $174K penalty. Without this constraint, USPS and P2P naturally absorb OnTrac's former volume at lower cost.

**Caveat:** This requires terminating the OnTrac contract. The analysis assumes OnTrac's rates are unavailable without meeting the minimum commitment.

## Key Findings

1. **P2P helps under all constraint combinations**: The dual-method approach guarantees S5 <= S4. P2P absorbs up to $2.01M of FedEx volume when unconstrained ("Drop both").

2. **Both constraints + P2P saves $100K vs S4**: P2P cherry-picks 44K shipments from USPS and FedEx at $4.51/shipment average - an increase from 27K pre-adjustment as FedEx became less competitive.

3. **Drop OnTrac remains transformative**: Without OnTrac's 279K minimum, P2P + USPS + FedEx saves 15.5% ($903K) vs S1 baseline - the best result across all scenarios.

4. **P2P's coverage limits its impact under tight constraints**: Only 51.8% of shipments are serviceable by P2P. With OnTrac consuming its overlap area, only 44K shipments (7.9%) go to P2P under both constraints.

5. **Method B wins under tight constraints**: When OnTrac's minimum is enforced, Method A (greedy) over-assigns to P2P then pays heavy penalties shifting back. Method B avoids this by starting from S4's already-constrained solution.

6. **FedEx share drops dramatically**: Without the earned discount, FedEx receives only 9.5% of shipments (53K) under both constraints - down from 21.2% pre-adjustment. The cost penalty makes OnTrac/USPS/P2P heavily preferred.

## Recommendations

### Under Current Contracts

**Add P2P to the carrier mix**: Even with both commitments, P2P saves $100K/year with zero downside risk (no P2P volume commitment required).

### If Renegotiating Contracts

**Prioritize reducing OnTrac commitment**: The analysis shows the OnTrac minimum is the binding constraint. Reducing or eliminating it unlocks $462K in additional savings through P2P and USPS.

| OnTrac Minimum   | Best S5 Cost   | vs S1 Baseline   | P2P Shipments   |
|------------------|----------------|------------------|-----------------|
| 279K (current)   | $5,393,088     | 7.6%             | 44K             |
| 0 (dropped)      | $4,931,056     | 15.5%            | ~large          |

**Negotiate earned discount floor**: If FedEx would guarantee a minimum earned discount (e.g., 10%) even below $4.5M spend, FedEx becomes more competitive and the overall mix cost drops.

---

*Analysis generated: February 2026*
*Data source: shipments_unified.parquet (558,013 shipments), FedEx earned discount removed*
*Note: P2P US is not currently used - this is a future assessment*
*Baseline: $5,833,893.77 (Scenario 1 current mix, unadjusted)*
*FedEx adjustment: 1.4865x multiplier on base rate (PP 45%, earned 18% removed, fuel 14%)*
