# US 2026 Tenders: Executive Summary

## Overview

Analysis of 539,917 matched US shipments (2025 volumes with invoice data) evaluated against 2026 rate cards across 6 carriers: OnTrac, USPS, FedEx, P2P (US + US2), and Maersk. Fifteen routing scenarios were modeled to identify the optimal carrier strategy while respecting contractual volume commitments.

**FedEx Earned Discount Tiers** determine each scenario's FedEx cost level:

| Tier   | Undiscounted Spend   | Earned Discount   | Scenarios                         |
|--------|----------------------|-------------------|-----------------------------------|
| None   | < $4.5M              | 0%                | S4, S5, S13                       |
| Tier 1 | $4.5-6.5M            | 16%               | S1, S6, S7, S8, S10, S11, S14, S15 |
| Tier 2 | $6.5-9.5M            | 18% (baked)       | S3                                |
| n/a    | --                   | --                | S2, S9 (Maersk), S12 (P2P)       |

FedEx 2026 rate tables are built with 18% earned discount baked in. Scenarios adjust from 18% to the applicable tier using a multiplier on base rate + fuel: 18%->16% = 1.0541x (S1/S6/S7/S8/S10/S11/S14/S15), 18%->0% = 1.4865x (S4/S5/S13).

## Scenario Comparison

| #    | Scenario                        | FedEx Earned   | Total Cost          | Savings vs S1       | %        |
|------|---------------------------------|----------------|---------------------|---------------------|----------|
| S1   | Current Carrier Mix             | 16%            | $6,072,062          | Baseline            | --       |
| S2   | 100% Maersk                     | n/a            | $5,686,413          | $385,649            | 6.4%     |
| S3   | 100% FedEx                      | 18% (baked)    | $6,287,902          | -$215,840           | -3.6%    |
| S4   | Constrained Optimal             | 0%             | $5,555,189          | $516,873            | 8.5%     |
| S5   | Constrained + P2P               | 0%             | $5,437,180          | $634,882            | 10.5%    |
| S6   | FedEx 16% Optimal               | 16%            | $5,354,844          | $717,218            | 11.8%    |
| S7   | FedEx 16% + P2P                 | 16%            | $5,000,952          | $1,071,110          | 17.6%    |
| S8   | Conservative P2P ($5M buffer)   | 16%            | $5,136,088          | $935,974            | 15.4%    |
| S9   | 100% Maersk (NSD $9)            | n/a            | $5,176,959          | $895,103            | 14.7%    |
| S10  | Static Rules (per-packagetype)  | 16%            | $4,942,173          | $1,129,889          | 18.6%    |
| S11  | Static Rules (3-group)          | 16%            | $4,962,119          | $1,109,943          | 18.3%    |
| S12  | 100% P2P Combined               | n/a            | $6,519,851          | -$447,790           | -7.4%    |
| S13  | P2P + FedEx (no USPS/OnTrac)    | 0%             | $5,178,926          | $893,136            | 14.7%    |
| S14  | P2P + FedEx constrained          | 16%            | $4,944,680          | $1,127,382          | 18.6%    |
| S15  | P2P + FedEx 3-Group             | 16%            | $5,099,099          | $972,963            | 16.0%    |

**Baseline**: Scenario 1 current carrier mix ($6,072,062) at 16% FedEx earned discount.

**Best implementable scenario (USPS+FedEx+P2P)**: S10 per-packagetype static rules save **$1.13M (18.6%)** with ~50 configurable rules. S11 simplifies further to **3 group rules** at **$1.11M (18.3%)** savings with more FedEx threshold headroom.

**Best P2P+FedEx scenario (2-carrier)**: S14 constrained saves **$1.13M (18.6%)** with per-shipment routing, matching S10's savings. S15 simplifies to 3 group rules at **$973K (16.0%)** savings.

## Comparison to 2025 Actuals

For the 539,917 matched shipments, each scenario's 2026 calculated cost vs what was actually invoiced in 2025:

| #    | Scenario                        | 2026 Calculated     | 2025 Actuals        | vs Actuals              |
|------|---------------------------------|---------------------|---------------------|-------------------------|
| --   | **2025 Invoiced**               | --                  | **$6,541,050**      | --                      |
| S1   | Current Carrier Mix             | $6,072,062          | $6,541,050          | -$468,988 (-7.2%)       |
| S2   | 100% Maersk                     | $5,686,413          | $6,541,050          | -$854,637 (-13.1%)      |
| S3   | 100% FedEx                      | $6,287,902          | $6,541,050          | -$253,148 (-3.9%)       |
| S4   | Constrained Optimal             | $5,555,189          | $6,541,050          | -$985,861 (-15.1%)      |
| S5   | Constrained + P2P               | $5,437,180          | $6,541,050          | -$1,103,870 (-16.9%)    |
| S6   | FedEx 16% Optimal               | $5,354,844          | $6,541,050          | -$1,186,206 (-18.1%)    |
| S7   | FedEx 16% + P2P                 | $5,000,952          | $6,541,050          | -$1,540,098 (-23.5%)    |
| S8   | Conservative P2P ($5M buffer)   | $5,136,088          | $6,541,050          | -$1,404,962 (-21.5%)    |
| S9   | 100% Maersk (NSD $9)            | $5,176,959          | $6,541,050          | -$1,364,091 (-20.9%)    |
| S10  | Static Rules (per-packagetype)  | $4,942,173          | $6,541,050          | -$1,598,877 (-24.4%)    |
| S11  | Static Rules (3-group)          | $4,962,119          | $6,541,050          | -$1,578,931 (-24.1%)    |
| S12  | 100% P2P Combined               | $6,519,851          | $6,541,050          | -$21,199 (-0.3%)        |
| S13  | P2P + FedEx (no USPS/OnTrac)    | $5,178,926          | $6,541,050          | -$1,362,124 (-20.8%)    |
| S14  | P2P + FedEx constrained          | $4,944,680          | $6,541,050          | -$1,596,370 (-24.4%)    |
| S15  | P2P + FedEx 3-Group             | $5,099,099          | $6,541,050          | -$1,441,951 (-22.0%)    |

**Key takeaway**: All 15 scenarios reduce cost vs 2025 actuals. S10/S14 offer the deepest savings at **$1.60M (-24.4%)** compared to what was actually invoiced in 2025. Even S12 (the worst scenario) saves $21K vs actuals.

## Scenario Details

### S1: Current Carrier Mix (Baseline)

Reproduces 2025 routing decisions with 2026 rate cards, with FedEx adjusted from baked 18% to actual 16% earned discount tier (1.0541x multiplier). Total cost: **$6,072,062**. Carrier split: 267,614 FedEx + 128,982 OnTrac + 103,164 USPS + 40,157 DHL ($6/shipment estimate). FedEx dominates at 49.6% of shipments (56.1% of cost), followed by OnTrac (23.9%), USPS (19.1%), and DHL (7.4%). 2026 calculated rates are 7.2% lower than 2025 actuals for matched shipments, driven by the SmartPost pricing correction (SmartPost now uses Ground Economy rates), partially offset by the earned discount adjustment.

### S2: 100% Maersk

Maersk is the cheapest full-coverage carrier at **$5,686,413 (6.4% savings vs S1)**. Strong savings on lightweight packages (0-4 lbs represent 72% of volume, saving 25-38%), but becomes expensive for heavier packages due to 30 lb rate jump and dimensional surcharges.

### S3: 100% FedEx

FedEx at full volume costs **$6,287,902 (-3.6% vs S1)** -- more expensive than the current mix. Uses the baked 18% earned discount rate (true undiscounted $9.3M qualifies for 18% tier). SmartPost handles the majority of shipments at lower cost than Home Delivery. Surcharges represent ~25% of total cost.

### S4: Constrained Optimal (FedEx 0% earned)

Optimized 3-carrier mix with FedEx earned discount removed (18%->0%, 1.4865x multiplier):

| Carrier   | Shipments   | % of Total   | Cost           |
|-----------|-------------|--------------|----------------|
| OnTrac    | 279,082     | 51.7%        | $2,563,752     |
| USPS      | 221,000     | 40.9%        | $1,736,238     |
| FedEx     | 39,835      | 7.4%         | $1,255,199     |
| **Total** | **539,917** | **100%**     | **$5,555,189** |

Saves **$516,873 (8.5%)** vs S1. Both OnTrac and USPS constraints met. FedEx drops to 7.4% of volume as inflated rates push traffic to OnTrac and USPS.

### S5: Constrained + P2P (FedEx 0% earned)

Adding P2P as a 4th carrier saves **$118K** vs S4. Total: **$5,437,180 (10.5% savings vs S1)**.

### S6: FedEx 16% Optimal

FedEx at 16% earned discount (1.0541x multiplier). Total: **$5,354,844 (11.8% savings vs S1)**. Carriers: USPS + FedEx + P2P (or OnTrac variants depending on constraints). The 16% earned tier enables better FedEx pricing across the mix.

### S7: FedEx 16% + P2P -- Best 3-Carrier Constrained

Extends S6 by adding P2P. Best 3-carrier constrained result at **$5,000,952 (17.6% savings vs S1)**. Carriers: USPS + FedEx + P2P. FedEx threshold met.

### S8: Conservative P2P + FedEx 16% ($5M buffer)

Same carrier set as S7 but with a **$5M** undiscounted FedEx threshold instead of $4.5M -- building in $500K of safety buffer. No OnTrac.

| Carrier   | Shipments   | % of Total   | Cost           |
|-----------|-------------|--------------|----------------|
| USPS      | 186,791     | 34.6%        | $1,280,195     |
| FedEx     | 199,578     | 37.0%        | $2,473,076     |
| P2P       | 153,548     | 28.4%        | $1,382,817     |
| **Total** | **539,917** | **100%**     | **$5,136,088** |

Saves **$935,974 (15.4%)** vs S1. FedEx undiscounted: ~$5.0M (comfortable margin).

### S9: 100% Maersk with Discounted NSD

Same as S2 but with NSD (non-standard dimensions) surcharge reduced from **$18 to $9**. Total: **$5,176,959 (14.7% savings vs S1)**. The NSD discount saves $509K vs S2's $5.69M. Still more expensive than the best optimized scenarios (S10/S11/S14).

### S10: Static Rules -- Per-Packagetype (Implementable in PCS)

Translates optimal routing into **static rules configurable in the production shipping system (PCS)**. Uses **per-packagetype weight cutoffs** combined with a P2P zone list:

```
For each package type:
  IF P2P zone AND weight <= P2P_cutoff -> P2P
  IF non-P2P zone AND weight <= USPS_cutoff -> USPS
  ELSE -> FedEx
```

| Carrier   | Shipments   | % of Total   | Cost           |
|-----------|-------------|--------------|----------------|
| USPS      | 104,181     | 19.3%        | $604,574       |
| FedEx     | 216,585     | 40.1%        | $3,346,797     |
| P2P       | 219,151     | 40.6%        | $990,801       |
| **Total** | **539,917** | **100%**     | **$4,942,173** |

Saves **$1,129,889 (18.6%)** vs S1 with ~50 rules + zip list. FedEx 16% tier met. Best overall USPS+FedEx+P2P scenario.

### S11: Static Rules -- 3-Group Simplified

Simplifies S10's ~50 rules into **3 group rules** by classifying package types as Light, Medium, or Heavy:

| Group    | P2P Zone Rule         | Non-P2P Zone Rule      | Pkg Types   | Shipments   |
|----------|-----------------------|------------------------|:-----------:|:-----------:|
| Light    | P2P if wt <= 3 lbs   | USPS if wt <= 2 lbs   | 20          | 350,835     |
| Medium   | P2P if wt <= 7 lbs   | USPS if wt <= 2 lbs   | 18          | 116,561     |
| Heavy    | FedEx always          | FedEx always           | 15          | 72,521      |

| Carrier   | Shipments   | % of Total   | Cost           |
|-----------|-------------|--------------|----------------|
| USPS      | 122,404     | 22.7%        | $741,415       |
| FedEx     | 208,808     | 38.7%        | $3,287,062     |
| P2P       | 208,705     | 38.7%        | $933,642       |
| **Total** | **539,917** | **100%**     | **$4,962,119** |

Saves **$1,109,943 (18.3%)** vs S1 with just 3 rules + zip list. FedEx 16% tier met with comfortable margin. Costs $20K/year more than S10 but is far simpler to implement and maintain.

### S12: 100% P2P Combined (P2P US + P2P US2)

Routes all shipments through P2P using both contracts: P2P US (better rates, ~10,430 ZIPs) and P2P US2 (full US coverage, ~93,100 ZIPs, higher rates). Per-shipment cheapest selection.

| Contract   | Shipments   | % of Total   | Cost           |
|------------|-------------|--------------|----------------|
| P2P US     | 258,796     | 47.9%        | $2,158,573     |
| P2P US2    | 281,081     | 52.1%        | $4,361,278     |
| None       | 40          | 0.0%         | $0             |
| **Total**  | **539,917** | **100%**     | **$6,519,851** |

Costs **$6,519,851 (+7.4% vs S1)**. P2P alone cannot match current mix cost -- P2P US2 rates are significantly higher than existing carriers for most weight brackets above 2 lbs. Not a viable standalone strategy.

### S13: P2P + FedEx (No USPS, No OnTrac)

Per-shipment cheapest of P2P US, P2P US2, and FedEx. Only 2 carrier relationships. FedEx at **0% earned discount** -- P2P takes most volume, pushing FedEx undiscounted spend to ~$2.7M (below $4.5M threshold for 16% tier).

| Carrier   | Shipments   | % of Total   | Cost           |
|-----------|-------------|--------------|----------------|
| P2P US    | 236,225     | 43.8%        | $1,270,346     |
| P2P US2   | 188,937     | 35.0%        | $1,422,042     |
| FedEx     | 114,755     | 21.3%        | $2,486,538     |
| **Total** | **539,917** | **100%**     | **$5,178,926** |

Saves **$893,136 (14.7%)** vs S1. P2P handles 78.7% of shipments (lighter packages), FedEx serves as fallback for heavy items. Even without earned discount, this beats the current mix by nearly $900K.

### S14: P2P + FedEx with 16% Earned Discount (Constrained)

Builds on S13's 2-carrier concept but forces enough FedEx volume to maintain the 16% earned discount. FedEx undiscounted spend constrained to >= $5.1M (safely above the $5M penalty threshold).

| Carrier   | Shipments   | % of Total   | Cost           | Forced    |
|-----------|-------------|--------------|----------------|-----------|
| FedEx     | 266,062     | 49.3%        | $3,557,049     | 120,915   |
| P2P US    | 190,037     | 35.2%        | $872,462       | 0         |
| P2P US2   | 83,818      | 15.5%        | $515,169       | 0         |
| **Total** | **539,917** | **100%**     | **$4,944,680** |           |

Saves **$1,127,382 (18.6%)** vs S1. The constraint forces 120,915 P2P shipments to FedEx, but the 16% earned discount on all FedEx volume more than compensates -- net $234K cheaper than S13's unconstrained 0% earned approach. FedEx undiscounted: $5.1M ($100K margin above $5M penalty). Best 2-carrier scenario.

### S15: P2P + FedEx 3-Group (Implementable Static Rules)

Implementable version of S14 using 3 static weight-group rules for P2P + FedEx routing:

| Group    | Weight      | P2P US Zone                             | Other Zone                         |
|----------|-------------|----------------------------------------|------------------------------------|
| Light    | <= 3 lbs    | P2P US if wt <= 3 lbs                  | P2P US2 if wt <= 1 lbs, else FedEx |
| Medium   | 3-21 lbs    | P2P US if wt <= 21 lbs                 | P2P US2 if wt <= 2 lbs, else FedEx |
| Heavy    | > 21 lbs    | FedEx always                           | FedEx always                       |

| Carrier   | Shipments   | % of Total   | Cost           |
|-----------|-------------|--------------|----------------|
| FedEx     | 255,971     | 47.4%        | $3,745,234     |
| P2P US    | 216,075     | 40.0%        | $978,249       |
| P2P US2   | 67,871      | 12.6%        | $375,616       |
| **Total** | **539,917** | **100%**     | **$5,099,099** |

Saves **$972,963 (16.0%)** vs S1. FedEx undiscounted spend of $5.13M meets the $5.1M threshold with $33K margin. Simplification cost vs S14 (per-shipment optimal) is $154K/year. Best implementable P2P+FedEx scenario with just 3 rules.

## Key Insights

1. **S10/S14 are tied for cheapest at 18.6% savings**: S10 (USPS+FedEx+P2P, $4,942,173) and S14 (P2P+FedEx, $4,944,680) both save ~$1.13M vs the current mix. S10 uses 3 carrier relationships with ~50 static rules; S14 uses 2 carrier relationships with per-shipment routing.

2. **S10/S11 are the best implementable USPS+FedEx+P2P options**: S10's per-packagetype rules capture 18.6% savings with ~50 rules. S11's 3-group rules capture 18.3% with just 3 rules. Both are configurable in PCS with static rules + a P2P zip list.

3. **S14/S15 offer a viable 2-carrier alternative**: For operations wanting to simplify to just P2P+FedEx, S14 (per-shipment optimal, -18.6%) matches S10's savings. S15 (3-group static rules, -16.0%) is the implementable version, trading $154K/year for simplicity.

4. **Maersk is the cheapest full-coverage single carrier**: S2 (100% Maersk, $5,686,413) saves 6.4% vs the current mix. With NSD discounted to $9, S9 saves 14.7%. Both are simpler than multi-carrier optimization but leave significant savings on the table.

5. **Maintaining FedEx 16% earned discount is critical**: S7 ($5,001K at 16% earned) saves $437K more than S5 ($5,437K at 0% earned) -- same concept but with the 16% discount preserved. The earned discount is worth approximately $400-500K/year.

6. **P2P amplifies savings dramatically at 16% earned**: P2P captures 200-220K shipments in S10/S11 (38-41% of volume) vs much smaller volumes when FedEx is at 0% earned (S5). The 16% FedEx discount changes the competitive landscape, creating more opportunities for P2P to undercut.

7. **100% P2P (S12) is not viable standalone**: At $6,519,851 (+7.4% vs S1), P2P US2's high rates for packages above 2 lbs make it more expensive than the current mix. P2P only works as a complement to FedEx/USPS.

8. **100% FedEx (S3) is 3.6% more expensive**: At $6,287,902, even with the 18% earned discount baked in, FedEx alone costs more than the current mix. Multi-carrier routing consistently outperforms single-carrier approaches.

9. **FedEx threshold headroom tradeoff**: S10 has tight margin, S8 has $500K margin at $104K/year cost, S11 has comfortable margin. S15 has $33K margin above $5.1M floor. Monitor FedEx undiscounted spend quarterly in any scenario.

10. **Carrier strengths by segment**:
    - **Lightweight (0-4 lbs)**: P2P US dominates where available; P2P US2 competitive at 0-2 lbs
    - **West region**: OnTrac is cost-effective (64.2% coverage)
    - **Universal coverage**: USPS at ~$7-8 avg for lightweight; FedEx SmartPost for moderate weights
    - **Heavy/oversize**: FedEx most competitive (Maersk 30 lb rate jump, USPS oversize penalties)

## Strategic Options

### USPS + FedEx + P2P (3-Carrier, Drop OnTrac)

| Strategy                                    | Cost           | Savings vs S1   | Rules              | FedEx Margin   |
|---------------------------------------------|----------------|-----------------|---------------------|----------------|
| S10 Per-packagetype rules                   | $4,942,173     | 18.6%           | ~50 + zip list      | Tight          |
| S11 3-Group rules                           | $4,962,119     | 18.3%           | 3 + zip list        | Comfortable    |
| S7 Per-shipment optimal                     | $5,000,952     | 17.6%           | Per-shipment        | Met            |
| S8 Conservative $5M buffer                  | $5,136,088     | 15.4%           | Per-shipment        | $500K (safe)   |

### P2P + FedEx (2-Carrier, Drop OnTrac + USPS)

| Strategy                                    | Cost           | Savings vs S1   | Rules              | FedEx Margin   |
|---------------------------------------------|----------------|-----------------|---------------------|----------------|
| S14 Per-shipment constrained                | $4,944,680     | 18.6%           | Per-shipment        | $100K          |
| S15 3-Group static rules                    | $5,099,099     | 16.0%           | 3 + zip list        | $33K           |
| S13 Unconstrained (0% earned)               | $5,178,926     | 14.7%           | Per-shipment        | n/a (0%)       |

### All Scenarios Ranked

| Strategy                          | Cost           | Savings vs S1   | vs Actuals   | Key Requirement                    |
|-----------------------------------|----------------|-----------------|-------------|-------------------------------------|
| S10 Static per-packagetype        | $4,942,173     | 18.6%           | -24.4%      | Drop OnTrac, ~50 PCS rules         |
| S14 P2P+FedEx constrained (16%)  | $4,944,680     | 18.6%           | -24.4%      | No USPS/OnTrac, $5.1M FedEx floor  |
| S11 Static 3-group               | $4,962,119     | 18.3%           | -24.1%      | Drop OnTrac, 3 PCS rules           |
| S7 Drop OnTrac (USPS+FedEx+P2P)  | $5,000,952     | 17.6%           | -23.5%      | Drop OnTrac, per-shipment routing   |
| S15 P2P+FedEx 3-group            | $5,099,099     | 16.0%           | -22.0%      | No USPS/OnTrac, 3 rules            |
| S8 Conservative $5M buffer       | $5,136,088     | 15.4%           | -21.5%      | Drop OnTrac, per-shipment routing   |
| S9 Maersk discounted (NSD $9)    | $5,176,959     | 14.7%           | -20.9%      | Negotiate NSD to $9                 |
| S13 P2P+FedEx (0% earned)        | $5,178,926     | 14.7%           | -20.8%      | No USPS/OnTrac, 2 carriers only    |
| S6 FedEx 16% Optimal             | $5,354,844     | 11.8%           | -18.1%      | Drop OnTrac, USPS+FedEx+P2P        |
| S5 Constrained + P2P (0% earned) | $5,437,180     | 10.5%           | -16.9%      | Accept FedEx 0% earned              |
| S4 Constrained Optimal (0%)      | $5,555,189     | 8.5%            | -15.1%      | Accept FedEx 0% earned              |
| S2 100% Maersk                   | $5,686,413     | 6.4%            | -13.1%      | Single carrier simplicity           |
| S1 Current mix                   | $6,072,062     | --              | -7.2%       | No change                           |
| S3 100% FedEx                    | $6,287,902     | -3.6%           | -3.9%       | Single carrier, 18% earned baked    |
| S12 100% P2P Combined            | $6,519,851     | -7.4%           | -0.3%       | Not recommended (P2P US2 expensive) |

## Constraints Reference

| Carrier   | Minimum Volume      | Basis                          |
|-----------|---------------------|--------------------------------|
| OnTrac    | 279,080/year        | 5,365/week x 52 (contractual) |
| USPS      | 140,000/year        | 35,000/quarter x 4 (Tier 1)   |
| FedEx     | No minimum          | Earned discount tiers apply    |
| Maersk    | No minimum          | Not currently used             |
| P2P       | No minimum          | Not currently used             |

## FedEx Earned Discount Tiers

| Undiscounted Spend   | Earned Discount   | Multiplier (from 18% baked)   |
|----------------------|-------------------|-------------------------------|
| < $4.5M              | 0%                | 1.4865x                       |
| $4.5-6.5M            | 16%               | 1.0541x                       |
| $6.5-9.5M            | 18%               | 1.0000x (no adjustment)       |
| $9.5-12.5M           | 19%               | 0.9730x                       |

## Carrier Coverage

| Carrier   | Serviceable   | Coverage   |
|-----------|---------------|------------|
| FedEx     | 539,917       | 100.0%     |
| USPS      | 539,917       | 100.0%     |
| Maersk    | 539,917       | 100.0%     |
| P2P US2   | 539,877       | 99.99%     |
| OnTrac    | 346,822       | 64.2%      |
| P2P US    | 279,534       | 51.8%      |

---

*Generated: February 2026*
*Data Period: 2025 shipment volumes with 2026 calculated rates*
*Dataset: Matched-only (539,917 shipments with both calculated and actual invoice data)*
*2025 Actuals Total: $6,541,050*
*Baseline: Scenario 1 current carrier mix ($6,072,062) at FedEx 16% earned discount*
*S4/S5/S13 FedEx adjustment: earned discount removed (18% -> 0%), multiplier 1.4865x on base rate*
*S6/S7/S8/S10/S11/S14/S15 FedEx adjustment: earned discount 18% -> 16%, multiplier 1.0541x on base rate*
*S14 constraint: FedEx undiscounted spend >= $5.1M ($100K margin above $5M penalty threshold)*
*S15 constraint: FedEx undiscounted spend >= $5.1M ($33K margin above threshold)*
