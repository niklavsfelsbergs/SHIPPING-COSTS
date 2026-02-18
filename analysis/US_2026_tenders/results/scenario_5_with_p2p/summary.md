# Scenario 5: Optimal with P2P

## Executive Summary

This analysis extends Scenario 4 by adding P2P US as an additional carrier. For each constraint combination, P2P improves the result - **S5 is guaranteed to be at least as cheap as S4** because P2P is purely additive (no minimum commitment).

**FedEx costs are adjusted to remove the 18% earned discount** (same as S4). When optimization reduces FedEx spend below $4.5M, the earned discount is lost, increasing FedEx costs by ~49% on the HD base rate portion.

**With both constraints enforced**, adding P2P saves **$118,009 (2.1%)** vs S4, bringing the total to **$5,437,180 (10.5% savings vs S1 baseline)**. P2P captures 46,690 shipments at $4.54/shipment average by cherry-picking the cheapest segments from USPS and FedEx.

**Without the OnTrac commitment**, the best result drops to **$5,117,820 (15.7% savings vs S1 baseline)** using USPS + FedEx + P2P.

## Carrier Serviceability

| Carrier   | Serviceable     | Coverage   | Minimum Required   |
|-----------|-----------------|------------|--------------------|
| OnTrac    | 346,822         | 64.2%      | 279,080            |
| USPS      | 539,917         | 100.0%     | 140,000            |
| FedEx     | 539,917         | 100.0%     | 0                  |
| P2P       | 279,534         | 51.8%      | 0                  |

P2P can service 280K shipments due to weight limits and geographic coverage.

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

| Variant                | S5 Cost        | S4 Cost        | P2P Benefit   | vs Adjusted Current | Method   |
|------------------------|----------------|----------------|---------------|---------------------|----------|
| **Both constraints**   | **$5,437,180** | **$5,555,189** | **+$118,009** | **18.5%**           | **B**    |
| Drop OnTrac            | $5,117,820     | $6,003,310     | +$885,490     | 23.3%               | A        |
| Drop USPS              | $6,115,208     | $6,401,278     | +$286,071     | 8.4%                | B        |
| Drop both              | $6,014,002     | $7,456,284     | +$1,442,282   | 9.9%                | A        |

**S5 <= S4 guarantee met for all variants.** P2P improves every scenario.

P2P's biggest impact is when OnTrac is dropped: the "Drop OnTrac" variant saves $1,556K (23.3%) vs adjusted current mix. P2P absorbs enormous FedEx volume ($1.44M savings in "Drop both").

### Optimal Carrier Mix (Both Constraints)

| Carrier     | Shipments   | % of Total   | Total Cost          |
|-------------|-------------|--------------|---------------------|
| OnTrac      | 279,084     | 51.7%        | $2,951,574.61       |
| USPS        | 177,623     | 32.9%        | $1,436,864.56       |
| FedEx       | 36,520      | 6.8%         | $836,642.69         |
| P2P         | 46,690      | 8.6%         | $212,098.16         |
| **Total**   | **539,917** | **100%**     | **$5,437,180.02**   |

### How Method B Works (Both Constraints)

Starting from S4's solution ($5,555,189), Method B switches groups to P2P where cheaper:

| Switch         | Groups   | Shipments   | Savings       |
|----------------|----------|-------------|---------------|
| FedEx -> P2P   | 1,904    | 2,864       | $33,370       |
| USPS -> P2P    | 14,865   | 43,826      | $84,639       |
| **Total**      | **16,769** | **46,690** | **$118,009**  |

OnTrac -> P2P: 0 switches (OnTrac is at its minimum with no surplus to release).

### Constraint Satisfaction

| Carrier   | Actual      | Minimum     | Status      |
|-----------|-------------|-------------|-------------|
| OnTrac    | 279,084     | 279,080     | **MET**     |
| USPS      | 177,623     | 140,000     | **MET**     |
| FedEx     | 36,520      | 0           | N/A         |
| P2P       | 46,690      | 0           | N/A         |

### FedEx Service Breakdown

| Service          | Shipments   | Share    |
|------------------|-------------|----------|
| Home Delivery    | 30,032      | 82.2%    |
| SmartPost        | 6,488       | 17.8%    |

## The "Drop OnTrac" Finding

The most significant finding is that **USPS + FedEx + P2P without OnTrac** produces the cheapest result at $5,117,820 (23.3% savings vs adjusted current mix). This is $319K cheaper than "Both constraints" with P2P.

| Metric                    | Both Constraints   | Drop OnTrac         |
|---------------------------|--------------------|---------------------|
| Total Cost                | $5,437,180         | $5,117,820          |
| Savings vs Adjusted Mix   | 18.5%              | 23.3%               |
| USPS shipments            | 177,623            | ~large              |
| FedEx shipments           | 36,520             | ~large              |
| P2P shipments             | 46,690             | ~large              |

**Why dropping OnTrac helps:** OnTrac requires 279K minimum shipments, but the greedy optimizer (with adjusted FedEx costs) initially wants to send 201K to OnTrac. The remaining 78K must be shifted at a $105K penalty. Without this constraint, USPS and P2P naturally absorb OnTrac's former volume at lower cost.

**Caveat:** This requires terminating the OnTrac contract. The analysis assumes OnTrac's rates are unavailable without meeting the minimum commitment.

## Key Findings

1. **P2P helps under all constraint combinations**: The dual-method approach guarantees S5 <= S4. P2P absorbs up to $1.44M of FedEx volume when unconstrained ("Drop both").

2. **Both constraints + P2P saves $118K vs S4**: P2P cherry-picks 47K shipments from USPS and FedEx at $4.54/shipment average.

3. **Drop OnTrac remains transformative**: Without OnTrac's 279K minimum, P2P + USPS + FedEx saves 23.3% ($1,556K) vs adjusted current mix - the best result across all S4/S5 scenarios.

4. **P2P's coverage limits its impact under tight constraints**: Only 51.8% of shipments are serviceable by P2P. With OnTrac consuming its overlap area, only 47K shipments (8.6%) go to P2P under both constraints.

5. **Method B wins under tight constraints**: When OnTrac's minimum is enforced, Method A (greedy) over-assigns to P2P then pays heavy penalties shifting back. Method B avoids this by starting from S4's already-constrained solution.

6. **FedEx share drops dramatically**: Without the earned discount, FedEx receives only 6.8% of shipments (37K) under both constraints - down from previous estimates. The cost penalty makes OnTrac/USPS/P2P heavily preferred.

## Recommendations

### Under Current Contracts

**Add P2P to the carrier mix**: Even with both commitments, P2P saves $118K/year with zero downside risk (no P2P volume commitment required).

### If Renegotiating Contracts

**Prioritize reducing OnTrac commitment**: The analysis shows the OnTrac minimum is the binding constraint. Reducing or eliminating it unlocks $319K in additional savings through P2P and USPS.

| OnTrac Minimum   | Best S5 Cost   | vs Adjusted Mix  | P2P Shipments   |
|------------------|----------------|------------------|-----------------|
| 279K (current)   | $5,437,180     | 18.5%            | 47K             |
| 0 (dropped)      | $5,117,820     | 23.3%            | ~large          |

**Negotiate earned discount floor**: If FedEx would guarantee a minimum earned discount (e.g., 10%) even below $4.5M spend, FedEx becomes more competitive and the overall mix cost drops.

---

*Analysis generated: February 2026*
*Data source: shipments_unified.parquet (539,917 matched shipments), FedEx earned discount removed*
*Note: P2P US is not currently used - this is a future assessment*
*Adjusted current mix: $6,673,697 (S1 baseline with FedEx earned discount removed)*
*S1 Baseline (with earned discount, FedEx at 16% tier): $6,072,062*
*FedEx adjustment: HD 1.4865x, SP 1.0891x multiplier on base rate (earned 18% removed, fuel applied)*
