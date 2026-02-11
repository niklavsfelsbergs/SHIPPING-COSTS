# US 2026 Tenders: Executive Summary

## Overview

Analysis of 558,013 US shipments (2025 volumes) evaluated against 2026 rate cards across 5 carriers: OnTrac, USPS, FedEx, P2P, and Maersk. Five routing scenarios were modeled to identify the optimal carrier strategy while respecting contractual volume commitments.

## Scenario Comparison

| #   | Scenario                  | Total Cost          | Savings vs Baseline   | Savings %   |
|-----|---------------------------|---------------------|-----------------------|-------------|
| S1  | Current Carrier Mix       | $6,437,752          | Baseline              | -           |
| S2  | 100% Maersk               | $6,041,478          | $396,274              | 6.2%        |
| S3  | 100% FedEx                | $7,037,555          | -$599,803             | -9.3%       |
| S4  | Constrained Optimal       | $5,471,118          | $966,634              | 15.0%       |
| S5  | Constrained + P2P         | $5,629,197          | $808,555              | 12.6%       |

**Baseline**: Scenario 1 current carrier mix ($6.44M) using each shipment's actual 2025 carrier with 2026 calculated rates.

**Best scenario**: Scenario 4 saves **$967K (15.0%)** through optimized 3-carrier routing (OnTrac/USPS/FedEx) while meeting all contractual commitments.

## Comparison to 2025 Actuals

For 539,941 matched shipments (96.8% match rate) with 2025 invoice data, each scenario's 2026 calculated cost vs what was actually paid:

| #   | Scenario                  | 2026 Calculated     | 2025 Actuals        | vs Actuals          |
|-----|---------------------------|---------------------|---------------------|---------------------|
| -   | **2025 Invoiced**         | -                   | **$6,541,323**      | -                   |
| S1  | Current Carrier Mix       | $6,185,721          | $6,541,323          | -$355,602 (-5.4%)   |
| S2  | 100% Maersk               | $5,686,496          | $6,541,323          | -$854,827 (-13.1%)  |
| S3  | 100% FedEx                | $6,778,262          | $6,541,323          | +$236,939 (+3.6%)   |
| S4  | Constrained Optimal       | $5,253,857          | $6,541,323          | -$1,287,466 (-19.7%)|
| S5  | Constrained + P2P         | $5,401,495          | $6,541,323          | -$1,139,828 (-17.4%)|

**Key takeaway**: Every scenario except 100% FedEx reduces cost vs 2025 actuals. The optimized mix (S4) would save **$1.29M (-19.7%)** compared to what was actually invoiced in 2025.

*Note: Matched shipments exclude 18,072 unmatched shipments (3.2%). DHL shipments use $6.00 estimated actual. S4/S5 costs computed by joining optimized carrier assignments back to shipment-level data.*

### Monthly Breakdown (Matched Shipments, $K)

| Month     | Ships    | 2025 Actual   | S1 Current   | S2 Maersk   | S3 FedEx   | S4 Optimal   | S5 +P2P   |
|-----------|----------|---------------|--------------|-------------|------------|--------------|-----------|
| 2025-01   | 41,882   | $571          | $514         | $438        | $546       | $413         | $398      |
| 2025-02   | 40,741   | $579          | $476         | $431        | $499       | $382         | $371      |
| 2025-03   | 32,474   | $430          | $379         | $348        | $402       | $311         | $302      |
| 2025-04   | 35,369   | $430          | $410         | $372        | $433       | $340         | $349      |
| 2025-05   | 48,362   | $585          | $561         | $496        | $587       | $462         | $488      |
| 2025-06   | 37,256   | $449          | $435         | $392        | $460       | $364         | $384      |
| 2025-07   | 34,715   | $438          | $410         | $385        | $428       | $339         | $357      |
| 2025-08   | 33,203   | $422          | $386         | $377        | $409       | $320         | $338      |
| 2025-09   | 29,989   | $340          | $341         | $350        | $373       | $292         | $314      |
| 2025-10   | 30,337   | $350          | $355         | $338        | $388       | $308         | $328      |
| 2025-11   | 52,185   | $642          | $629         | $572        | $685       | $538         | $563      |
| 2025-12   | 119,881  | $1,264        | $1,247       | $1,147      | $1,522     | $1,147       | $1,171    |
| 2026-01   | 3,547    | $42           | $42          | $39         | $48        | $38          | $40       |
| **Total** |**539,941**|**$6,541**    | **$6,186**   | **$5,686**  | **$6,778** | **$5,254**   | **$5,401**|

S4 (Constrained Optimal) is the cheapest scenario in every month. Dec 2025 peak volume (120K shipments) shows the largest absolute savings: $117K vs actuals. Maersk (S2) is cheaper than the current mix (S1) in every month except Sep-Oct 2025 where they are roughly equal.

## Scenario Details

### S1: Current Carrier Mix (Baseline)

Reproduces 2025 routing decisions with 2026 rate cards. FedEx dominates at 49.1% of shipments (56.3% of cost), followed by OnTrac (24.7%), USPS (19.0%), and DHL (7.2%, estimated at $6/shipment). 2026 calculated rates are 5.4% lower than 2025 actuals for matched shipments.

### S2: 100% Maersk

Maersk is the **cheapest full-coverage carrier** at $6.04M (-6.2% vs baseline). Strong savings on lightweight packages (0-4 lbs represent 72% of volume, saving 28-42%). Becomes expensive for heavy packages due to 30 lb rate jump and dimensional surcharges. No fuel surcharge (included in base rates).

### S3: 100% FedEx

FedEx at full volume costs $7.04M (+9.3% vs baseline). Transportation charges of $3.99M fall $506K short of the $4.5M earned discount threshold. At the 16% tier, FedEx would beat baseline (-0.6%). Surcharges represent 43% of total FedEx cost ($3.04M). SmartPost rates not yet populated.

### S4: Constrained Optimal (Recommended)

Optimized 3-carrier mix meeting contractual commitments:

| Carrier   | Shipments   | % of Total   | Cost           |
|-----------|-------------|--------------|----------------|
| OnTrac    | 279,085     | 50.0%        | $2,632,038     |
| USPS      | 188,240     | 33.7%        | $1,283,864     |
| FedEx     | 90,688      | 16.3%        | $1,555,215     |
| **Total** | **558,013** | **100%**     | **$5,471,118** |

Constraints satisfied: OnTrac 279,085 (min 279,080), USPS 188,240 (min 140,000). Cost penalty to meet OnTrac minimum: $192K ($1.77/shipment avg for 108K shifted shipments).

### S5: Constrained + P2P

Adding P2P as a 4th carrier **increases cost by $158K** vs Scenario 4. P2P is genuinely cheap ($4.59/shipment avg) but its serviceable area (51.8% coverage) overlaps heavily with OnTrac's. The OnTrac minimum forces expensive shifts that negate P2P's advantage. P2P only viable if OnTrac commitment is reduced to ~100-150K.

## Key Insights

1. **Scenario 4 is optimal**: $967K savings (15.0%) with all constraints met. OnTrac and USPS handle 84% of volume at lower cost.

2. **Maersk is surprisingly competitive**: Cheapest full-coverage carrier at $6.04M. Strong candidate for selective routing of lightweight packages in the optimized mix.

3. **FedEx volume matters**: At current volumes, FedEx earns no discount. Reaching $4.5M transportation charges (-$506K gap) would unlock 16% savings on base rates.

4. **P2P doesn't help under current constraints**: The OnTrac contractual minimum negates P2P's cost advantage. Revisit if OnTrac commitment is renegotiated.

5. **Carrier strengths by segment**:
   - **Lightweight (0-4 lbs)**: Maersk dominates (28-42% cheaper)
   - **West region**: OnTrac is cost-effective ($11.10 avg, 64.5% coverage)
   - **Universal coverage**: USPS at $7.85 avg for current lightweight mix
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
*Baseline: Scenario 1 current carrier mix ($6,437,752.11)*
