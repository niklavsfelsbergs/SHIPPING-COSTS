# Scenario 7: Optimal with P2P + FedEx 16% Earned Discount

## Executive Summary

This analysis extends Scenario 6 by adding P2P US as a fourth carrier. For each constraint combination, P2P improves the result - **S7 is guaranteed to be at least as cheap as S6** because P2P is purely additive (no minimum commitment).

**FedEx costs use the 16% earned discount** (same as S6), but with a **$4.5M undiscounted threshold constraint** - carrier mixes must generate at least $4.5M in FedEx undiscounted spend to maintain the 16% tier.

**With both constraints enforced**, adding P2P provides **no improvement** vs S6 - the total remains **$5,002,886 (16.2% savings vs S1 baseline)** because P2P cannot find cheaper assignments when OnTrac is at its minimum, USPS groups are locked at minimum, and FedEx is below the threshold.

**Without the OnTrac commitment**, the result drops to **$4,433,040 (25.8% savings vs S1 baseline)** - the **cheapest feasible scenario across all 7 scenarios**.

## Carrier Serviceability

| Carrier   | Serviceable     | Coverage   | Minimum Required           |
|-----------|-----------------|------------|----------------------------|
| OnTrac    | 360,151         | 64.5%      | 279,080                    |
| USPS      | 558,013         | 100.0%     | 140,000                    |
| FedEx     | 558,013         | 100.0%     | $4.5M undiscounted         |
| P2P       | 289,272         | 51.8%      | 0                          |

P2P can service 289K shipments due to weight limits and geographic coverage.

## Methodology

### Dual-Method Approach

For each constraint combination, two methods are tested and the cheaper result is kept:

- **Method A**: Greedy assignment with all carriers (including P2P) + constraint adjustment
- **Method B**: Take Scenario 6's solution and improve by switching groups to P2P where cheaper

Method B guarantees S7 <= S6 because it only makes beneficial switches from S6's baseline. Switches respect carrier minimums and the FedEx undiscounted threshold:
- FedEx -> P2P: only if FedEx stays above $4.5M undiscounted threshold
- USPS -> P2P: only up to USPS surplus above minimum
- OnTrac -> P2P: only up to OnTrac surplus above minimum

*Note: FedEx rates use the 16% earned discount (same as S6). The $4.5M undiscounted threshold must be maintained to keep this discount tier.*

### Constraint Combinations

Same as S6 but with P2P added to each variant:

| Variant             | Available Carriers            | Minimums Enforced                                      |
|---------------------|-------------------------------|--------------------------------------------------------|
| Both constraints    | OnTrac, USPS, FedEx, P2P     | OnTrac >= 279K, USPS >= 140K, FedEx >= $4.5M undisc.  |
| Drop OnTrac         | USPS, FedEx, P2P             | USPS >= 140K, FedEx >= $4.5M undisc.                   |
| Drop USPS           | OnTrac, FedEx, P2P           | OnTrac >= 279K, FedEx >= $4.5M undisc.                 |
| Drop both           | FedEx, P2P                   | FedEx >= $4.5M undisc.                                 |

## Results

### Variant Comparison

| Variant                | S7 Cost        | S6 Cost        | P2P Benefit   | vs S1 Baseline  | FedEx Tier  | Method   |
|------------------------|----------------|----------------|---------------|-----------------|-------------|----------|
| **Both constraints**   | **$5,002,886** | **$5,002,886** | **$0**        | **16.2%**       | **NOT MET** | **B**    |
| Drop OnTrac            | $4,433,040     | $5,040,871     | +$607,831     | 25.8%           | MET         | A        |
| Drop USPS              | $5,363,152     | $5,521,358     | +$158,206     | 10.2%           | MET         | B        |
| Drop both              | $4,999,206     | $6,160,686     | +$1,161,480   | 16.3%           | MET         | A        |

**S7 <= S6 guarantee met for all variants.** P2P improves every scenario except "Both constraints" (where it has no room to improve).

P2P's biggest impact is when OnTrac is dropped: the "Drop OnTrac" variant at **$4,433,040 is the cheapest feasible scenario across all 7 scenarios** - 25.8% savings vs S1 baseline. P2P captures 198K shipments, far more than the 44K in S5.

### FedEx Threshold Status

| Variant             | FedEx Undiscounted   | Threshold ($4.5M)   | Status       |
|---------------------|----------------------|----------------------|--------------|
| Both constraints    | Below threshold      | -                    | **NOT MET**  |
| Drop OnTrac         | $4,500,015           | $4,500,000           | **MET**      |
| Drop USPS           | Above threshold      | $4,500,000           | **MET**      |
| Drop both           | Above threshold      | $4,500,000           | **MET**      |

The "Both constraints" variant cannot meet the FedEx threshold because OnTrac and USPS minimums absorb too much volume. The "Drop OnTrac" variant just barely meets the threshold ($4,500,015 vs $4,500,000 required).

### Optimal Carrier Mix - Drop OnTrac (Recommended)

| Carrier     | Shipments   | % of Total   | Total Cost        |
|-------------|-------------|--------------|-------------------|
| USPS        | 186,791     | 33.5%        | $1,280,195        |
| FedEx       | 173,170     | 31.0%        | $2,250,642        |
| P2P         | 198,052     | 35.5%        | $902,204          |
| **Total**   | **558,013** | **100%**     | **$4,433,040**    |

### Carrier Mix - Both Constraints (Infeasible for 16% Tier)

| Carrier     | Shipments   | % of Total   | Total Cost        |
|-------------|-------------|--------------|-------------------|
| OnTrac      | 279,080     | 50.0%        | $2,274,111        |
| USPS        | 140,001     | 25.1%        | $871,842          |
| FedEx       | 138,932     | 24.9%        | $1,856,932        |
| P2P         | 0           | 0.0%         | $0                |
| **Total**   | **558,013** | **100%**     | **$5,002,886**    |

P2P captures zero shipments here because all USPS groups are locked at their minimum, OnTrac is at its minimum, and FedEx is already below the threshold - no groups can be released to P2P.

### Constraint Satisfaction (Drop OnTrac)

| Carrier   | Actual         | Minimum          | Status      |
|-----------|----------------|------------------|-------------|
| USPS      | 186,791        | 140,000          | **MET**     |
| FedEx     | $4,500,015     | $4,500,000       | **MET**     |
| P2P       | 198,052        | 0                | N/A         |

### FedEx Service Breakdown (Drop OnTrac)

| Service          | Shipments   | Share    |
|------------------|-------------|----------|
| Home Delivery    | 41,184      | 23.8%    |
| SmartPost        | 131,986     | 76.2%    |

### P2P Analysis (Drop OnTrac)

| Metric                    | Value           |
|---------------------------|-----------------|
| P2P shipments             | 198,052         |
| P2P total cost            | $902,204        |
| P2P average cost          | $4.56/shipment  |
| Winning method            | A (greedy)      |

P2P captures 198K shipments - dramatically more than S5's 44K. With FedEx at the 16% discounted rate, the cost landscape changes significantly: FedEx is more competitive, pushing more volume to FedEx to meet the threshold, but P2P cherry-picks the segments where it undercuts both USPS and FedEx.

## The "Drop OnTrac" Finding

The most significant finding across the entire analysis: **USPS + FedEx + P2P without OnTrac at the 16% earned discount** produces the **cheapest result across all 7 scenarios** at $4,433,040 (25.8% savings vs S1 baseline).

| Metric                    | Both Constraints   | Drop OnTrac         |
|---------------------------|--------------------|---------------------|
| Total Cost                | $5,002,886         | $4,433,040          |
| Savings vs S1 Baseline    | 16.2%              | 25.8%               |
| USPS shipments            | 140,001            | 186,791             |
| FedEx shipments           | 138,932            | 173,170             |
| P2P shipments             | 0                  | 198,052             |
| FedEx 16% threshold       | NOT MET            | MET                 |

**Why dropping OnTrac is transformative:** OnTrac's 279K minimum consumes 50% of all shipments, leaving insufficient FedEx volume to reach the $4.5M undiscounted threshold. Without OnTrac, USPS + FedEx + P2P can be balanced so FedEx just barely meets the threshold while P2P cherry-picks 198K cheap shipments.

**Caveat:** This requires terminating the OnTrac contract. The analysis assumes OnTrac's rates are unavailable without meeting the minimum commitment.

## Comparison to Other Scenarios

| Scenario                              | Cost           | vs S1 Baseline   |
|---------------------------------------|----------------|------------------|
| S7 Drop OnTrac (16% + P2P)           | $4,433,040     | 25.8%            |
| S5 Drop OnTrac (0% earned + P2P)     | $4,931,056     | 17.4%            |
| S4 Both constraints (0% earned)       | $5,492,793     | 8.0%             |
| S7 Both constraints (16% + P2P)      | $5,002,886     | 16.2%            |
| **S1 Baseline (16% earned)**          | **$5,971,748** | **-**            |

**Key insight:** Maintaining the FedEx 16% earned discount combined with P2P cherry-picking is far more valuable than losing the earned discount entirely. S7 "Drop OnTrac" saves $498K more than S5 "Drop OnTrac" and $1,060K more than S4 "Both constraints".

## Key Findings

1. **S7 "Drop OnTrac" is the cheapest scenario across all 7**: At $4,433,040 (25.8% savings), this is the optimal carrier strategy if the OnTrac contract can be terminated. No other constraint combination in any scenario comes close.

2. **FedEx 16% + P2P is a powerful combination**: The 16% earned discount makes FedEx competitive enough to carry 31% of volume, while P2P cherry-picks 35.5% at $4.56/shipment - together they dramatically outperform either alone.

3. **"Both constraints" cannot reach the FedEx 16% tier**: With OnTrac consuming 50% of shipments and USPS locked at its minimum, there is not enough FedEx volume to reach the $4.5M undiscounted threshold. The result is identical to S6 ($5,002,886).

4. **P2P captures 4.5x more shipments than S5**: S7 "Drop OnTrac" routes 198K to P2P vs 44K in S5 "Both constraints". The 16% earned discount changes the competitive landscape, and P2P exploits the resulting opportunities.

5. **The FedEx threshold is met by $15**: "Drop OnTrac" generates exactly $4,500,015 in FedEx undiscounted spend. This razor-thin margin suggests the optimizer is perfectly calibrating FedEx volume to minimize cost while just meeting the threshold.

6. **Method A wins for unconstrained variants**: When OnTrac's minimum is removed, the greedy approach (Method A) outperforms the incremental improvement approach (Method B), suggesting the optimal solution differs significantly from S6's constrained baseline.

## Recommendations

### Strategic Recommendation

**Drop OnTrac and implement the USPS + FedEx + P2P carrier mix**: This achieves $4,433,040/year - 25.8% savings vs the current mix - the best result across all scenarios analyzed.

### If OnTrac Contract Must Be Maintained

**Add P2P to the carrier mix**: Under both constraints, P2P provides no savings (identical to S6). The binding constraint is the OnTrac minimum, which prevents any volume from being released to P2P. Focus instead on negotiating a lower OnTrac minimum to unlock P2P's potential.

### If Renegotiating Contracts

| Priority   | Action                                       | Impact                                    |
|------------|----------------------------------------------|-------------------------------------------|
| 1          | Terminate/reduce OnTrac commitment            | Unlocks $570K+ in P2P savings             |
| 2          | Maintain FedEx 16% earned discount            | Worth $498K vs losing the discount (S5)   |
| 3          | Add P2P with no minimum commitment            | $608K savings when OnTrac is dropped      |

### Critical Dependency

The 16% earned discount is essential. The $4,500,015 undiscounted FedEx spend in "Drop OnTrac" just barely qualifies. Any volume reduction (seasonality, demand changes) could push FedEx below the threshold. **Build in a safety buffer** by targeting $4.6-4.7M undiscounted FedEx spend.

---

*Analysis generated: February 2026*
*Data source: shipments_unified.parquet (558,013 shipments), FedEx at 16% earned discount*
*Note: P2P US is not currently used - this is a future assessment*
*Baseline: $5,971,748 (Scenario 1 current mix, FedEx at 16% earned discount)*
*FedEx threshold: $4.5M undiscounted spend required for 16% earned discount tier*
