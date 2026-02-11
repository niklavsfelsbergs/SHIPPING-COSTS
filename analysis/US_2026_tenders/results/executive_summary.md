# US 2026 Tenders: Executive Summary

## Overview

Analysis of 558,013 US shipments (2025 volumes) evaluated against 2026 rate cards across 5 carriers: OnTrac, USPS, FedEx, P2P, and Maersk. Five routing scenarios were modeled to identify the optimal carrier strategy while respecting contractual volume commitments.

**S4 and S5 adjust FedEx costs to remove the 18% earned discount.** When optimization reduces FedEx spend below $4.5M, the earned discount is lost. This increases FedEx costs by ~49% on the base rate portion, making OnTrac and USPS more valuable in the optimized mix.

## Scenario Comparison

| #   | Scenario                  | Total Cost          | Savings vs Baseline   | Savings %   |
|-----|---------------------------|---------------------|-----------------------|-------------|
| S1  | Current Carrier Mix       | $5,833,894          | Baseline              | -           |
| S2  | 100% Maersk               | $6,041,478          | -$207,585             | -3.6%       |
| S3  | 100% FedEx                | $5,889,066          | -$55,172              | -0.9%       |
| S4  | Constrained Optimal*      | $5,492,793          | $341,101              | 5.8%        |
| S5  | Constrained + P2P*        | $5,393,088          | $440,806              | 7.6%        |

**Baseline**: Scenario 1 current carrier mix ($5.83M) using each shipment's actual 2025 carrier with 2026 calculated rates.

*\*S4 and S5 use FedEx rates with earned discount removed (18% -> 0%). This is the realistic cost when FedEx volume drops below the $4.5M earned discount threshold.*

**Best scenario**: Scenario 5 saves **$441K (7.6%)** through optimized 4-carrier routing (OnTrac/USPS/FedEx/P2P) while meeting all contractual commitments. P2P saves $100K vs S4 by cherry-picking 44K cheap shipments from USPS and FedEx.

## Comparison to 2025 Actuals

For 539,941 matched shipments (96.8% match rate) with 2025 invoice data, each scenario's 2026 calculated cost vs what was actually paid:

| #   | Scenario                  | 2026 Calculated     | 2025 Actuals        | vs Actuals          |
|-----|---------------------------|---------------------|---------------------|---------------------|
| -   | **2025 Invoiced**         | -                   | **$6,541,323**      | -                   |
| S1  | Current Carrier Mix       | $5,597,549          | $6,541,323          | -$943,774 (-14.4%)  |
| S2  | 100% Maersk               | $5,686,496          | $6,541,323          | -$854,827 (-13.1%)  |
| S3  | 100% FedEx                | $5,671,838          | $6,541,323          | -$869,485 (-13.3%)  |
| S4  | Constrained Optimal*      | $5,271,913          | $6,541,323          | -$1,269,410 (-19.4%)|
| S5  | Constrained + P2P*        | $5,175,158          | $6,541,323          | -$1,366,165 (-20.9%)|

**Key takeaway**: All scenarios reduce cost vs 2025 actuals. The optimized mix with P2P (S5) would save **$1.37M (-20.9%)** compared to what was actually invoiced in 2025.

*Note: Matched shipments exclude 18,072 unmatched shipments (3.2%). DHL shipments use $6.00 estimated actual. S4/S5 costs computed by joining optimized carrier assignments back to shipment-level data, with FedEx costs adjusted for earned discount removal.*

### Monthly Breakdown (Matched Shipments, $K)

| Month     | Ships    | 2025 Actual   | S1 Current   | S2 Maersk   | S3 FedEx   | S4 Optimal   | S5 +P2P   |
|-----------|----------|---------------|--------------|-------------|------------|--------------|-----------|
| 2025-01   | 41,882   | $571          | $424         | $438        | $446       | $399         | $391      |
| 2025-02   | 40,741   | $579          | $407         | $431        | $424       | $384         | $377      |
| 2025-03   | 32,474   | $430          | $327         | $348        | $343       | $313         | $307      |
| 2025-04   | 35,369   | $430          | $355         | $372        | $372       | $352         | $346      |
| 2025-05   | 48,362   | $585          | $487         | $496        | $506       | $487         | $479      |
| 2025-06   | 37,256   | $449          | $377         | $392        | $394       | $382         | $377      |
| 2025-07   | 34,715   | $438          | $364         | $385        | $369       | $354         | $349      |
| 2025-08   | 33,203   | $422          | $354         | $377        | $352       | $329         | $324      |
| 2025-09   | 29,989   | $340          | $328         | $350        | $320       | $300         | $295      |
| 2025-10   | 30,337   | $350          | $337         | $338        | $323       | $301         | $296      |
| 2025-11   | 52,185   | $642          | $596         | $572        | $557       | $523         | $512      |
| 2025-12   | 119,881  | $1,264        | $1,202       | $1,147      | $1,228     | $1,112       | $1,088    |
| 2026-01   | 3,547    | $42           | $40          | $39         | $38        | $36          | $35       |
| **Total** |**539,941**|**$6,541**    | **$5,598**   | **$5,686**  | **$5,672** | **$5,272**   | **$5,175**|

S5 (Constrained + P2P) is the cheapest scenario in every month. Dec 2025 peak volume (120K shipments) shows the largest absolute savings: $176K vs actuals. S1, S2, and S3 are clustered tightly ($5.6-5.7M) due to corrected SmartPost pricing. S4 and S5 are now closer to S1-S3 than before the earned discount adjustment.

## Scenario Details

### S1: Current Carrier Mix (Baseline)

Reproduces 2025 routing decisions with 2026 rate cards. FedEx dominates at 49.1% of shipments (51.8% of cost), followed by OnTrac (24.7%), USPS (19.0%), and DHL (7.2%, estimated at $6/shipment). 2026 calculated rates are 14.4% lower than 2025 actuals for matched shipments, driven largely by the SmartPost pricing correction.

### S2: 100% Maersk

Maersk costs $6.04M (+3.6% vs baseline). With corrected SmartPost pricing, Maersk is no longer the cheapest full-coverage carrier. Strong savings on lightweight packages (0-4 lbs represent 72% of volume, saving 25-38%), but becomes expensive for heavier packages due to 30 lb rate jump and dimensional surcharges. No fuel surcharge (included in base rates).

### S3: 100% FedEx

FedEx at full volume costs $5.89M (+0.9% vs baseline) - nearly cost-neutral with the current mix. SmartPost handles 86.8% of shipments at lower cost than Home Delivery. Transportation charges of $4.41M fall just $92K short of the $4.5M earned discount threshold. Surcharges represent 25% of total cost ($1.48M).

### S4: Constrained Optimal (FedEx earned discount removed)

Optimized 3-carrier mix meeting contractual commitments, with FedEx costs adjusted for earned discount loss:

| Carrier   | Shipments   | % of Total   | Cost           |
|-----------|-------------|--------------|----------------|
| OnTrac    | 279,082     | 50.0%        | $2,563,752     |
| USPS      | 224,183     | 40.2%        | $1,736,238     |
| FedEx     | 54,748      | 9.8%         | $1,192,804     |
| **Total** | **558,013** | **100%**     | **$5,492,793** |

Constraints satisfied: OnTrac 279,082 (min 279,080), USPS 224,183 (min 140,000). FedEx volume drops to just 9.8% as the inflated rates push traffic to OnTrac and USPS. Both commitments are strongly beneficial: OnTrac saves $364K, USPS saves $1.15M vs dropping either.

### S5: Constrained + P2P (Recommended)

Adding P2P as a 4th carrier **saves $100K** vs Scenario 4. P2P cherry-picks 43,856 shipments at $4.51/shipment from USPS and FedEx. Without the OnTrac commitment, savings increase to $903K (15.5% vs S1).

| Carrier   | Shipments   | % of Total   | Cost           |
|-----------|-------------|--------------|----------------|
| OnTrac    | 279,082     | 50.0%        | $2,563,752     |
| USPS      | 181,917     | 32.6%        | $1,471,243     |
| FedEx     | 53,158      | 9.5%         | $1,160,117     |
| P2P       | 43,856      | 7.9%         | $197,977       |
| **Total** | **558,013** | **100%**     | **$5,393,088** |

## Key Insights

1. **Scenario 5 is optimal**: $441K savings (7.6%) with all constraints met. P2P adds $100K of incremental savings over S4 with zero downside risk.

2. **Earned discount removal is significant**: Without the 18% earned discount, FedEx costs increase by $2.44M (41.5%). This makes S4/S5 savings smaller vs S1 baseline (7.6% vs 17.2% pre-adjustment) but the result is more realistic.

3. **OnTrac commitment is now clearly beneficial**: With adjusted FedEx costs, OnTrac saves $364K/year vs dropping it - a strong argument for maintaining the commitment (previously was marginal at $3K).

4. **USPS is the most valuable commitment**: Saves $1.15M/year. Dropping USPS forces volume to expensive FedEx, making it the most costly commitment to lose.

5. **Drop OnTrac remains transformative**: Without OnTrac's 279K minimum, S5 achieves $4.93M (15.5% savings) - the cheapest result. But the gap vs "Both constraints" narrowed from $598K to $462K.

6. **SmartPost changes everything**: Correcting SmartPost pricing reduced FedEx costs by ~$1.1M. FedEx ($5.89M) is now nearly cost-neutral with the current mix and cheaper than Maersk.

7. **Carrier strengths by segment**:
   - **Lightweight (0-4 lbs)**: Maersk dominates (25-38% cheaper)
   - **West region**: OnTrac is cost-effective ($11.10 avg, 64.5% coverage)
   - **Universal coverage**: USPS at $7.85 avg for lightweight; FedEx SmartPost at $9.46 avg
   - **Heavy/oversize**: FedEx most competitive (Maersk 30 lb rate jump, USPS oversize penalties)

## Constraints Reference

| Carrier   | Minimum Volume      | Basis                         |
|-----------|---------------------|-------------------------------|
| OnTrac    | 279,080/year        | 5,365/week x 52 (contractual) |
| USPS      | 140,000/year        | 35,000/quarter x 4 (Tier 1)   |
| FedEx     | No minimum          | Earned discount tiers apply    |
| Maersk    | No minimum          | Not currently used             |
| P2P       | No minimum          | Not currently used             |

## Carrier Coverage

| Carrier   | Serviceable   | Coverage   |
|-----------|---------------|------------|
| FedEx     | 558,013       | 100.0%     |
| USPS      | 558,013       | 100.0%     |
| Maersk    | 558,013       | 100.0%     |
| OnTrac    | 360,151       | 64.5%      |
| P2P       | 289,272       | 51.8%      |

---

*Generated: February 2026*
*Data Period: 2025 shipment volumes with 2026 calculated rates*
*Baseline: Scenario 1 current carrier mix ($5,833,893.77)*
*S4/S5 FedEx adjustment: earned discount removed (18% -> 0%), multiplier 1.4865x on base rate*
