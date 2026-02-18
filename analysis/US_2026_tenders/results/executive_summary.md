# US 2026 Tenders: Executive Summary

## Overview

Analysis of 558,013 US shipments (2025 volumes) evaluated against 2026 rate cards across 6 carriers: OnTrac, USPS, FedEx, P2P (US + US2), and Maersk. Fourteen routing scenarios were modeled to identify the optimal carrier strategy while respecting contractual volume commitments.

**FedEx Earned Discount Tiers** determine each scenario's FedEx cost level:

| Tier   | Undiscounted Spend   | Earned Discount   | Scenarios                    |
|--------|----------------------|-------------------|------------------------------|
| None   | < $4.5M              | 0%                | S4, S5, S13                  |
| Tier 1 | $4.5–6.5M           | 16%               | S1, S6, S7, S8, S10, S11, S14 |
| Tier 2 | $6.5–9.5M           | 18% (baked)       | S3                           |
| n/a    | —                    | —                 | S2, S9 (Maersk), S12 (P2P)  |

FedEx 2026 rate tables are built with 18% earned discount baked in. Scenarios adjust from 18% to the applicable tier using a multiplier on base rate + fuel: 18%→16% = 1.0541x (S1/S6/S7/S14), 18%→0% = 1.4865x (S4/S5/S13).

## Scenario Comparison

| #    | Scenario                        | FedEx Earned   | Total Cost          | Savings vs S1       | %        |
|------|---------------------------------|----------------|---------------------|---------------------|----------|
| S1   | Current Carrier Mix             | 16%            | $5,971,748          | Baseline            | -        |
| S2   | 100% Maersk                     | n/a            | $6,041,478          | -$69,730            | -1.2%    |
| S3   | 100% FedEx                      | 18% (baked)    | $5,889,066          | $82,682             | 1.4%     |
| S4   | Constrained Optimal             | 0%             | $5,492,793          | $478,955            | 8.0%     |
| S5   | Constrained + P2P               | 0%             | $5,393,088          | $578,660            | 9.7%     |
| S6   | FedEx 16% Optimal†              | 16%            | $5,040,871          | $930,877            | 15.6%    |
| S7   | FedEx 16% + P2P†                | 16%            | $4,433,040          | $1,538,708          | 25.8%    |
| S8   | Conservative P2P ($5M buffer)†  | 16%            | $4,536,690          | $1,435,058          | 24.0%    |
| S9   | 100% Maersk (NSD $9)           | n/a            | $5,495,484          | $476,264            | 8.0%     |
| S10  | Static Rules (per-packagetype)† | 16%            | $4,450,862          | $1,520,886          | 25.5%    |
| S11  | Static Rules (3-group)†         | 16%            | $4,516,218          | $1,455,530          | 24.4%    |
| S12  | 100% P2P Combined               | n/a            | $6,788,506          | -$816,758           | -13.7%   |
| S13  | P2P + FedEx (no USPS/OnTrac)   | 0%             | $4,942,666          | $1,029,082          | 17.2%    |
| S14  | P2P + FedEx constrained        | 16%            | $4,858,916          | $1,112,832          | 18.6%    |

**Baseline**: Scenario 1 current carrier mix ($5.97M) at 16% FedEx earned discount.

*†S6–S11 use "Drop OnTrac" variant (USPS + FedEx + P2P). The "Both constraints" variant ($5,002,886) is INFEASIBLE — FedEx 16% tier cannot be met with both OnTrac and USPS commitments active.*

**Best theoretical scenario**: S7 "Drop OnTrac" saves **$1.54M (25.8%)** through per-shipment optimal USPS/FedEx/P2P routing while maintaining the FedEx 16% earned discount. Requires dropping the OnTrac contract but needs 353K per-shipment routing assignments.

**Best implementable scenario**: S10 per-packagetype static rules save **$1.52M (25.5%)** — 98.8% of S7's savings with ~50 configurable rules. S11 simplifies further to **3 group rules** at **$1.46M (24.4%)** savings with more FedEx threshold headroom.

## Comparison to 2025 Actuals

For 539,941 matched shipments (96.8% match rate) with 2025 invoice data, each scenario's 2026 calculated cost vs what was actually paid:

| #    | Scenario                    | 2026 Calculated     | 2025 Actuals        | vs Actuals              |
|------|-----------------------------|---------------------|---------------------|-------------------------|
| -    | **2025 Invoiced**           | -                   | **$6,541,323**      | -                       |
| S1   | Current Carrier Mix         | $5,731,467          | $6,541,323          | -$809,856 (-12.4%)      |
| S2   | 100% Maersk                 | $5,686,496          | $6,541,323          | -$854,827 (-13.1%)      |
| S3   | 100% FedEx                  | $5,671,838          | $6,541,323          | -$869,485 (-13.3%)      |
| S4   | Constrained Optimal         | $5,271,913          | $6,541,323          | -$1,269,410 (-19.4%)    |
| S5   | Constrained + P2P           | $5,175,158          | $6,541,323          | -$1,366,165 (-20.9%)    |
| S6   | FedEx 16% Optimal*          | $4,804,976          | $6,541,323          | -$1,736,347 (-26.5%)    |
| S7   | FedEx 16% + P2P†            | $4,254,429          | $6,541,323          | -$2,286,894 (-35.0%)    |

**Key takeaway**: All scenarios reduce cost vs 2025 actuals. S7 "Drop OnTrac" would save **$2.29M (-35.0%)** compared to what was actually invoiced in 2025.

*\*S6 actuals use the "Both constraints" assignment (infeasible for FedEx 16% tier). †S7 uses the "Drop OnTrac" assignment (cheapest feasible). DHL shipments use $6.00 estimated actual. 18,072 unmatched shipments (3.2%) excluded.*

### Monthly Breakdown (Matched Shipments, $K)

| Month     | Ships      | Actual   | S1     | S2     | S3     | S4     | S5     | S6*    | S7†    |
|-----------|------------|----------|--------|--------|--------|--------|--------|--------|--------|
| 2025-01   | 41,882     | $571     | $441   | $438   | $446   | $399   | $391   | $365   | $323   |
| 2025-02   | 40,741     | $579     | $425   | $431   | $424   | $384   | $377   | $348   | $310   |
| 2025-03   | 32,474     | $430     | $340   | $348   | $343   | $313   | $307   | $282   | $252   |
| 2025-04   | 35,369     | $430     | $370   | $372   | $372   | $352   | $346   | $317   | $279   |
| 2025-05   | 48,362     | $585     | $508   | $496   | $506   | $487   | $479   | $437   | $384   |
| 2025-06   | 37,256     | $449     | $392   | $392   | $394   | $382   | $377   | $342   | $301   |
| 2025-07   | 34,715     | $438     | $377   | $385   | $369   | $354   | $349   | $319   | $283   |
| 2025-08   | 33,203     | $422     | $362   | $377   | $352   | $329   | $324   | $301   | $268   |
| 2025-09   | 29,989     | $340     | $330   | $350   | $320   | $300   | $295   | $272   | $246   |
| 2025-10   | 30,337     | $350     | $340   | $338   | $323   | $301   | $296   | $273   | $248   |
| 2025-11   | 52,185     | $642     | $601   | $572   | $557   | $523   | $512   | $477   | $425   |
| 2025-12   | 119,881    | $1,264   | $1,205 | $1,147 | $1,228 | $1,112 | $1,088 | $1,037 | $906   |
| 2026-01   | 3,547      | $42      | $40    | $39    | $38    | $36    | $35    | $33    | $29    |
| **Total** | **539,941**| **$6,541**| **$5,731**| **$5,686**| **$5,672**| **$5,272**| **$5,175**| **$4,805**| **$4,254** |

S7 "Drop OnTrac" is the cheapest scenario in every month. Dec 2025 peak volume (120K shipments) shows the largest absolute savings: $358K vs actuals. S1–S3 are clustered tightly ($5.67–5.73M). S6/S7 show the dramatic impact of maintaining the FedEx 16% earned discount combined with optimization.

*\*S6 = "Both constraints" assignment (infeasible). †S7 = "Drop OnTrac" assignment (cheapest feasible).*

## Scenario Details

### S1: Current Carrier Mix (Baseline)

Reproduces 2025 routing decisions with 2026 rate cards, with FedEx adjusted from baked 18% to actual 16% earned discount tier (1.0541x multiplier). Total cost: **$5,971,748**. FedEx dominates at 49.1% of shipments (51.8% of cost), followed by OnTrac (24.7%), USPS (19.0%), and DHL (7.2%, estimated at $6/shipment). 2026 calculated rates are 12.4% lower than 2025 actuals for matched shipments, driven by the SmartPost pricing correction (SmartPost now uses Ground Economy rates), partially offset by the earned discount adjustment.

### S2: 100% Maersk

Maersk costs **$6,041,478 (-1.2% vs S1)**. With corrected SmartPost pricing, Maersk is no longer the cheapest full-coverage carrier. Strong savings on lightweight packages (0-4 lbs represent 72% of volume, saving 25-38%), but becomes expensive for heavier packages due to 30 lb rate jump and dimensional surcharges.

### S3: 100% FedEx

FedEx at full volume costs **$5,889,066 (+1.4% vs S1)** — nearly cost-neutral with the current mix. Uses the baked 18% earned discount rate (conservative; 100% FedEx would qualify for 19%). SmartPost handles 86.8% of shipments at lower cost than Home Delivery. Surcharges represent 25% of total cost ($1.48M).

### S4: Constrained Optimal (FedEx 0% earned)

Optimized 3-carrier mix with FedEx earned discount removed (18%→0%, 1.4865x multiplier):

| Carrier   | Shipments   | % of Total   | Cost           |
|-----------|-------------|--------------|----------------|
| OnTrac    | 279,082     | 50.0%        | $2,563,752     |
| USPS      | 224,183     | 40.2%        | $1,736,238     |
| FedEx     | 54,748      | 9.8%         | $1,192,804     |
| **Total** | **558,013** | **100%**     | **$5,492,793** |

Saves **$478,955 (8.0%)** vs S1. Constraints met: OnTrac 279,082 (min 279,080), USPS 224,183 (min 140,000). FedEx drops to 9.8% of volume as inflated rates push traffic to OnTrac and USPS.

### S5: Constrained + P2P (FedEx 0% earned)

Adding P2P as a 4th carrier saves **$100K** vs S4. P2P cherry-picks 43,856 shipments at $4.51/shipment from USPS and FedEx:

| Carrier   | Shipments   | % of Total   | Cost           |
|-----------|-------------|--------------|----------------|
| OnTrac    | 279,082     | 50.0%        | $2,563,752     |
| USPS      | 181,917     | 32.6%        | $1,471,243     |
| FedEx     | 53,158      | 9.5%         | $1,160,117     |
| P2P       | 43,856      | 7.9%         | $197,977       |
| **Total** | **558,013** | **100%**     | **$5,393,088** |

Saves **$578,660 (9.7%)** vs S1. Without the OnTrac commitment, S5 "Drop OnTrac" achieves $4,931,056 (17.4% savings).

### S6: FedEx 16% Optimal (Drop OnTrac)

Extends S4 with FedEx at 16% earned discount (1.0541x multiplier) and a $4.5M undiscounted FedEx threshold constraint. **FedEx 16% tier is INFEASIBLE with both commitments** — OnTrac's 279K + USPS's 140K minimum leaves only 139K shipments for FedEx, producing $3.67M undiscounted vs $4.5M required.

**Recommended variant — Drop OnTrac ($5,040,871, 15.6% savings):**

| Carrier   | Shipments   | % of Total   | Cost           |
|-----------|-------------|--------------|----------------|
| USPS      | 328,764     | 58.9%        | $2,330,826     |
| FedEx     | 229,249     | 41.1%        | $2,710,045     |
| **Total** | **558,013** | **100%**     | **$5,040,871** |

FedEx threshold met: $5.66M undiscounted. Dropping OnTrac saves $452K/year vs S4 "Both constraints" by enabling the FedEx 16% tier.

### S7: FedEx 16% + P2P (Drop OnTrac) — Recommended

Extends S6 by adding P2P. Uses a dual-method approach: Method A (greedy with P2P) vs Method B (improve S6 with P2P switches), keeps the cheaper result.

**"Drop OnTrac" ($4,433,040, 25.8% savings) — cheapest scenario across all 7:**

| Carrier   | Shipments   | % of Total   | Cost           |
|-----------|-------------|--------------|----------------|
| USPS      | 186,791     | 33.5%        | $1,280,195     |
| FedEx     | 173,170     | 31.0%        | $2,250,642     |
| P2P       | 198,052     | 35.5%        | $902,204       |
| **Total** | **558,013** | **100%**     | **$4,433,040** |

FedEx threshold met: $4,500,015 undiscounted (just barely). P2P captures 198K shipments at $4.56/shipment — 4.5x more than S5's 44K — because the FedEx 16% discount changes the cost landscape. "Both constraints" variant is unchanged from S6 ($5,002,886) — P2P has no room to improve when all carriers are at their minimums.

### S8: Conservative P2P + FedEx 16% ($5M buffer)

Same as S7 "Drop OnTrac" but with a **$5M** undiscounted FedEx threshold instead of $4.5M — building in $500K of safety buffer. S7's threshold was met by just $15, making it fragile to seasonal shifts.

| Carrier   | Shipments   | % of Total   | Cost           |
|-----------|-------------|--------------|----------------|
| USPS      | 186,791     | 33.5%        | $1,280,195     |
| FedEx     | 199,578     | 35.8%        | $2,473,076     |
| P2P       | 171,644     | 30.8%        | $783,419       |
| **Total** | **558,013** | **100%**     | **$4,536,690** |

Saves **$1,435,058 (24.0%)** vs S1. The $500K buffer costs $104K/year vs S7 by shifting 26K shipments from P2P to FedEx. FedEx undiscounted: ~$5.0M (comfortable margin).

### S9: 100% Maersk with Discounted NSD

Same as S2 but with NSD (non-standard dimensions) surcharge reduced from **$18 to $9**. Total: **$5,495,484 (8.0% savings vs S1)**. The NSD discount saves $546K vs S2's $6.04M. Still significantly more expensive than the optimized scenarios (S7–S11).

### S10: Static Rules — Per-Packagetype (Implementable in PCS)

Translates S7's optimal routing into **static rules configurable in the production shipping system (PCS)**. Instead of 353K per-shipment assignments, S10 uses **per-packagetype weight cutoffs** combined with a P2P zone list:

```
For each package type:
  IF P2P zone AND weight ≤ P2P_cutoff → P2P
  IF non-P2P zone AND weight ≤ USPS_cutoff → USPS
  ELSE → FedEx
```

| Carrier   | Shipments   | % of Total   | Cost           |
|-----------|-------------|--------------|----------------|
| USPS      | 158,753     | 28.4%        | $1,038,088     |
| FedEx     | 172,927     | 31.0%        | $2,387,391     |
| P2P       | 226,333     | 40.6%        | $1,025,383     |
| **Total** | **558,013** | **100%**     | **$4,450,862** |

Saves **$1,520,886 (25.5%)** vs S1 — capturing **98.8% of S7's savings** with ~50 rules + zip list. FedEx 16% tier met with $17K margin. The $18K gap vs S7 comes from within-weight-bracket variation by zip code that static rules can't capture.

### S11: Static Rules — 3-Group Simplified

Simplifies S10's ~50 rules into **3 group rules** by classifying package types as Light, Medium, or Heavy:

| Group    | P2P Zone Rule       | Non-P2P Zone Rule   | Pkg Types | Shipments |
|----------|---------------------|---------------------|:---------:|:---------:|
| Light    | P2P if wt ≤ 3 lbs  | USPS if wt ≤ 3 lbs | 20        | 360,367   |
| Medium   | P2P if wt ≤ 21 lbs | USPS if wt ≤ 2 lbs | 18        | 121,118   |
| Heavy    | FedEx always        | FedEx always        | 16        | 76,528    |

| Carrier   | Shipments   | % of Total   | Cost           |
|-----------|-------------|--------------|----------------|
| USPS      | 153,494     | 27.5%        | $1,021,208     |
| FedEx     | 181,517     | 32.5%        | $2,483,577     |
| P2P       | 223,002     | 40.0%        | $1,011,433     |
| **Total** | **558,013** | **100%**     | **$4,516,218** |

Saves **$1,455,530 (24.4%)** vs S1 — capturing **94.6% of S7's savings** with just 3 rules + zip list. FedEx 16% tier met with **$194K margin** (11x more comfortable than S10's $17K). Costs $65K/year more than S10 but is far simpler to implement and maintain.

### S12: 100% P2P Combined (P2P US + P2P US2)

Routes all shipments through P2P using both contracts: P2P US (better rates, ~10,430 ZIPs) and P2P US2 (full US coverage, ~93,100 ZIPs, higher rates). Per-shipment cheapest selection.

| Contract  | Shipments   | % of Total   | Cost           |
|-----------|-------------|--------------|----------------|
| P2P US    | 267,840     | 48.0%        | $2,257,974     |
| P2P US2   | 290,091     | 52.0%        | $4,530,532     |
| None      | 82          | 0.0%         | $0             |
| **Total** | **558,013** | **100%**     | **$6,788,506** |

Costs **$6,788,506 (-13.7% vs S1)**. P2P alone cannot match current mix cost — P2P US2 rates are significantly higher than existing carriers for most weight brackets above 2 lbs. Not a viable standalone strategy.

### S13: P2P + FedEx (No USPS, No OnTrac)

Per-shipment cheapest of P2P US, P2P US2, and FedEx. Only 2 carrier relationships. FedEx at **0% earned discount** — P2P takes most volume, pushing FedEx undiscounted spend to ~$2.3M (below $4.5M threshold for 16% tier).

| Carrier   | Shipments   | % of Total   | Cost           |
|-----------|-------------|--------------|----------------|
| P2P US    | 239,258     | 42.9%        | $1,127,837     |
| P2P US2   | 199,433     | 35.7%        | $1,475,755     |
| FedEx     | 119,322     | 21.4%        | $2,339,075     |
| **Total** | **558,013** | **100%**     | **$4,942,666** |

Saves **$1,029,082 (17.2%)** vs S1. P2P handles 78.6% of shipments (lighter packages), FedEx serves as fallback for heavy items. Compared to USPS+FedEx (2 carriers, $5.86M), P2P+FedEx saves **$914K more** — P2P is significantly cheaper than USPS for lightweight shipments even without the FedEx earned discount. However, this scenario is worse than S7–S11 which maintain the FedEx 16% tier by keeping USPS in the mix.

### S14: P2P + FedEx with 16% Earned Discount (Constrained)

Builds on S13's 2-carrier concept but forces enough FedEx volume to maintain the 16% earned discount. FedEx undiscounted spend constrained to >= $5.1M (safely above the $5M penalty threshold).

| Carrier   | Shipments   | % of Total   | Total Cost     | Forced  |
|-----------|-------------|--------------|----------------|---------|
| FedEx     | 337,754     | 60.5%        | $3,721,037     | 187,272 |
| P2P US    | 136,958     | 24.5%        | $642,441       | 0       |
| P2P US2   | 83,301      | 14.9%        | $495,438       | 0       |
| **Total** | **558,013** | **100%**     | **$4,858,916** |         |

Saves **$1,112,832 (18.6%)** vs S1. The constraint forces 187,272 P2P shipments to FedEx (avg $3.19/ship extra cost), but the 16% earned discount on all FedEx volume more than compensates — net $84K cheaper than S13's unconstrained 0% earned approach. FedEx undiscounted: $5.1M ($100K margin above $5M penalty). Best 2-carrier scenario, but trails S7-S11 by $322K-$426K because USPS handles forced-to-FedEx volume more cheaply than FedEx@16%.

## Key Insights

1. **S7 "Drop OnTrac" is the theoretical optimum**: $1.54M savings (25.8%) — the cheapest result across all 11 scenarios. Requires dropping the OnTrac contract to unlock the FedEx 16% tier + P2P cherry-picking. However, it requires 353K per-shipment routing assignments.

2. **S10/S11 are the implementable optima**: S10's per-packagetype rules capture 98.8% of S7's savings with ~50 rules. S11's 3-group rules capture 94.6% with just 3 rules. Both are configurable in PCS with static rules + a P2P zip list.

3. **FedEx 16% tier is infeasible with both commitments**: OnTrac's 279K + USPS's 140K = 419K committed shipments, leaving only 139K for FedEx. This produces $3.67M undiscounted — $830K short of the $4.5M threshold. The three constraints are mutually incompatible.

4. **Maintaining FedEx 16% earned discount is critical**: S7 "Drop OnTrac" ($4,433,040) saves $498K more than S5 "Drop OnTrac" ($4,931,056) — same carrier set but with the 16% discount preserved. The earned discount is worth approximately $500K/year.

5. **P2P amplifies savings dramatically at 16% earned**: P2P captures 198K–226K shipments in S7–S11 (35–41% of volume) vs only 44K in S5 (7.9%). The 16% FedEx discount changes the competitive landscape, creating more opportunities for P2P to undercut.

6. **OnTrac commitment is the binding constraint**: With both commitments, OnTrac absorbs 50% of all shipments and prevents FedEx from reaching its volume threshold. OnTrac's value is $38K/year at 16% earned (S6) vs $364K/year at 0% earned (S4) — it becomes much less valuable when FedEx is competitively priced.

7. **USPS remains the most valuable commitment**: Saves $518K/year in S6 and $1.15M/year in S4. The USPS commitment should be maintained in all scenarios.

8. **FedEx threshold headroom tradeoff**: S10 has $17K margin (fragile), S8 has $500K margin at $104K/year cost, S11 has $194K margin at $65K/year cost. S11 offers the best balance of simplicity, savings, and safety.

9. **P2P US2 extends coverage but not competitiveness**: P2P US2 covers 93,100 ZIPs (full US) vs P2P US's 10,430, but at significantly higher rates. 100% P2P Combined (S12) costs $6.79M (+13.7%) — worse than the current mix. P2P US2 is only competitive at very light weights (0-2 lbs).

10. **P2P+FedEx is a viable 2-carrier strategy**: S14 (constrained, $4.86M, -18.6%) is the best 2-carrier option — it maintains the 16% earned discount by forcing 187K P2P shipments to FedEx. S13 (unconstrained, $4.94M, -17.2%) is simpler but loses the earned discount. Both trail the 3-carrier scenarios by $322K-$426K because USPS absorbs lightweight volume more efficiently than FedEx@16%. The $5M FedEx penalty threshold requires $100K safety margin monitoring in S14.

11. **Carrier strengths by segment**:
   - **Lightweight (0-4 lbs)**: P2P US dominates where available; P2P US2 competitive at 0-2 lbs
   - **West region**: OnTrac is cost-effective ($11.10 avg, 64.5% coverage)
   - **Universal coverage**: USPS at $7.85 avg for lightweight; FedEx SmartPost at $9.46 avg
   - **Heavy/oversize**: FedEx most competitive (Maersk 30 lb rate jump, USPS oversize penalties)

## Strategic Options

### Implementable Scenarios (Static Rules in PCS)

| Strategy                                   | Cost         | Savings vs S1   | Rules      | FedEx Margin   |
|--------------------------------------------|--------------|-----------------|------------|----------------|
| S11 3-Group rules (USPS+FedEx+P2P)        | $4,516,218   | 24.4%           | 3 + zip list | $194K (safe)  |
| S10 Per-packagetype rules (USPS+FedEx+P2P) | $4,450,862   | 25.5%           | ~50 + zip list | $17K (tight) |
| S8 Conservative $5M buffer (USPS+FedEx+P2P) | $4,536,690 | 24.0%           | 353K       | $500K (safe)   |

### All Scenarios Ranked

| Strategy                          | Cost         | Savings vs S1   | Feasible?   | Key Requirement                    |
|-----------------------------------|--------------|-----------------|-------------|-------------------------------------|
| S7 Drop OnTrac (USPS+FedEx+P2P)  | $4,433,040   | 25.8%           | YES         | Terminate OnTrac, per-shipment routing |
| S10 Static per-packagetype        | $4,450,862   | 25.5%           | YES         | Terminate OnTrac, ~50 PCS rules    |
| S11 Static 3-group               | $4,516,218   | 24.4%           | YES         | Terminate OnTrac, 3 PCS rules      |
| S8 Conservative $5M buffer       | $4,536,690   | 24.0%           | YES         | Terminate OnTrac, per-shipment routing |
| S14 P2P+FedEx constrained (16%)  | $4,858,916   | 18.6%           | YES         | No USPS/OnTrac, 2 carriers, $5.1M FedEx floor |
| S13 P2P+FedEx (0% earned)        | $4,942,666   | 17.2%           | YES         | No USPS/OnTrac, 2 carriers only   |
| S5 Drop OnTrac (0% earned+P2P)   | $4,931,056   | 17.4%           | YES         | Terminate OnTrac, accept 0% earned |
| S6 Drop OnTrac (USPS+FedEx)      | $5,040,871   | 15.6%           | YES         | Terminate OnTrac, no P2P needed    |
| S5 Both (OnTrac+USPS+FedEx+P2P)  | $5,393,088   | 9.7%            | YES         | Accept FedEx 0% earned             |
| S4 Both (OnTrac+USPS+FedEx)      | $5,492,793   | 8.0%            | YES         | Accept FedEx 0% earned             |
| S9 Maersk discounted (NSD $9)    | $5,495,484   | 8.0%            | YES         | Negotiate NSD to $9                |
| S3 100% FedEx                     | $5,889,066   | 1.4%            | YES         | Single carrier simplicity          |
| S1 Current mix                    | $5,971,748   | —               | YES         | No change                          |
| S2 100% Maersk                    | $6,041,478   | -1.2%           | YES         | Not recommended                    |
| S12 100% P2P Combined             | $6,788,506   | -13.7%          | YES         | Not recommended (P2P US2 too expensive) |
| S6/S7 Both constraints            | $5,002,886   | 16.2%           | **NO**      | FedEx 16% tier not met             |

## Constraints Reference

| Carrier   | Minimum Volume      | Basis                         |
|-----------|---------------------|-------------------------------|
| OnTrac    | 279,080/year        | 5,365/week x 52 (contractual) |
| USPS      | 140,000/year        | 35,000/quarter x 4 (Tier 1)   |
| FedEx     | No minimum          | Earned discount tiers apply    |
| Maersk    | No minimum          | Not currently used             |
| P2P       | No minimum          | Not currently used             |

## FedEx Earned Discount Tiers

| Undiscounted Spend   | Earned Discount   | Multiplier (from 18% baked)   |
|----------------------|-------------------|-------------------------------|
| < $4.5M              | 0%                | 1.4865x                       |
| $4.5–6.5M           | 16%               | 1.0541x                       |
| $6.5–9.5M           | 18%               | 1.0000x (no adjustment)       |
| $9.5–12.5M          | 19%               | 0.9730x                       |

## Carrier Coverage

| Carrier   | Serviceable   | Coverage   |
|-----------|---------------|------------|
| FedEx     | 558,013       | 100.0%     |
| USPS      | 558,013       | 100.0%     |
| Maersk    | 558,013       | 100.0%     |
| P2P US2   | 557,931       | 99.99%     |
| OnTrac    | 360,151       | 64.5%      |
| P2P US    | 289,272       | 51.8%      |

---

*Generated: February 2026*
*Data Period: 2025 shipment volumes with 2026 calculated rates*
*Baseline: Scenario 1 current carrier mix ($5,971,748) at FedEx 16% earned discount*
*S4/S5/S13 FedEx adjustment: earned discount removed (18% → 0%), multiplier 1.4865x on base rate*
*S6/S7/S8/S10/S11/S14 FedEx adjustment: earned discount 18% → 16%, multiplier 1.0541x on base rate*
*S14 constraint: FedEx undiscounted spend >= $5.1M ($100K margin above $5M penalty threshold)*
