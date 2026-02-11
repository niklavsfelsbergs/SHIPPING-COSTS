# Scenario 5: Optimal with P2P

## Executive Summary

This analysis evaluates adding P2P US as a fourth carrier option. **Key finding: P2P is cheaper where it can service, but the OnTrac contractual minimum negates most of P2P's benefit.** With constraints enforced, Scenario 5 costs **$5,629,197** - which is **$158,079 (2.9%) more expensive** than Scenario 4 without P2P.

**Recommendation:** P2P offers attractive pricing ($4.59/shipment avg) but has limited coverage (51.8%). The OnTrac minimum forces expensive shifts that negate P2P's advantage. Consider P2P only if OnTrac commitment can be reduced.

## Carrier Serviceability

Not all carriers can service all shipments. OnTrac and P2P have geographic/weight limitations:

| Carrier   | Serviceable     | Coverage   | Minimum Required   | Feasible?   |
|-----------|-----------------|------------|--------------------|-------------|
| OnTrac    | 360,151         | 64.5%      | 279,080            | **YES**     |
| USPS      | 558,013         | 100.0%     | 140,000            | YES         |
| FedEx     | 558,013         | 100.0%     | 0                  | YES         |
| P2P       | 289,272         | 51.8%      | 0                  | YES         |

P2P can only service 289K shipments due to weight limits and geographic coverage.

## Methodology

### Algorithm: Greedy + Adjustment (4 Carriers, Null-Aware)

1. **Initial Assignment**: For each group, assign to cheapest carrier **that can service it** (non-null cost)
2. **Check Constraints**: Verify if OnTrac and USPS volume minimums are met
3. **Adjust for Constraints**: Shift lowest-penalty groups to underutilized carriers (only where target carrier can service)
4. **FedEx Earned Discount**: Apply discount tier based on final FedEx transportation charges

### Constraints

| Carrier   | Minimum             | Notes                               |
|-----------|---------------------|-------------------------------------|
| OnTrac    | 279,080 shipments   | Contractual (5,365/week × 52)       |
| USPS      | 140,000 shipments   | Tier 1 (35K/quarter × 4)            |
| P2P       | None                | No volume commitment                |
| FedEx     | None                | Earned discount tiers apply         |

## Results

### Initial Greedy Assignment (Before Constraints)

| Carrier   | Shipments   | % of Total   | Notes                           |
|-----------|-------------|--------------|----------------------------------|
| P2P       | 226,360     | 40.6%        | Cheapest where it can service    |
| USPS      | 174,613     | 31.3%        | Universal coverage               |
| FedEx     | 114,281     | 20.5%        | -                                |
| OnTrac    | 42,759      | 7.7%         | Limited to serviceable area      |

P2P captures a significant portion but less than in unconstrained scenarios due to 51.8% coverage limit.

### After Constraint Enforcement

To meet the OnTrac minimum of 279,080:
- Shifted 69,302 groups (108,904 shipments) from USPS/FedEx to OnTrac (cost penalty: $551,310)
- Shifted 100,239 groups (127,417 shipments) from P2P to OnTrac

To meet the USPS minimum of 140,000:
- Shifted 9,210 groups (10,337 shipments) to USPS (cost penalty: $6,082)

| Carrier     | Shipments   | % of Total   | Total Cost          |
|-------------|-------------|--------------|---------------------|
| OnTrac      | 279,080     | 50.0%        | $3,378,601.76       |
| USPS        | 140,000     | 25.1%        | $1,057,602.97       |
| P2P         | 98,943      | 17.7%        | $454,275.33         |
| FedEx       | 39,990      | 7.2%         | $738,716.98         |
| **Total**   | **558,013** | **100%**     | **$5,629,197.04**   |

### Constraint Satisfaction

| Carrier   | Actual      | Minimum     | Status      |
|-----------|-------------|-------------|-------------|
| OnTrac    | 279,080     | 279,080     | **MET**     |
| USPS      | 140,000     | 140,000     | **MET**     |
| P2P       | 98,943      | 0           | N/A         |
| FedEx     | 39,990      | 0           | N/A         |

### FedEx Earned Discount

| Metric                    | Value            |
|---------------------------|------------------|
| Transportation Charges    | $738,716.98      |
| Tier                      | < $4.5M          |
| Discount Rate             | 0%               |
| Discount Amount           | $0.00            |

### Scenario Comparison

| Scenario                      | Total Cost          | vs Current          | Savings %   |
|-------------------------------|---------------------|---------------------|-------------|
| Current Mix                   | $6,389,595.72       | -                   | -           |
| Scenario 4 (without P2P)      | $5,471,117.96       | $918,477.76         | 14.4%       |
| **Scenario 5 (with P2P)**     | **$5,629,197.04**   | **$760,398.68**     | **11.9%**   |

**P2P adds $158,079 in cost vs Scenario 4** due to the constraint adjustments required.

## Analysis: Why P2P Doesn't Help Under Current Constraints

### The OnTrac Constraint Problem

1. **P2P captures volume that OnTrac needs**: P2P's serviceable area (289K) heavily overlaps with OnTrac's (360K)
2. **OnTrac minimum requires 279K**: Most of P2P's "wins" must be shifted to OnTrac
3. **Shift penalty is significant**: Moving 127K shipments from P2P to OnTrac costs more than keeping them with P2P

### Volume Flow

| Stage                 | OnTrac    | USPS      | FedEx     | P2P       |
|-----------------------|-----------|-----------|-----------|-----------|
| Greedy Assignment     | 42,759    | 174,613   | 114,281   | 226,360   |
| After Adjustment      | 279,080   | 140,000   | 39,990    | 98,943    |
| Net Change            | +236,321  | -34,613   | -74,291   | -127,417  |

### P2P Value Where It Remains

For the 98,943 shipments P2P captures in the final mix:

| Metric                    | P2P           | Alternative (OnTrac)   | Savings     |
|---------------------------|---------------|------------------------|-------------|
| Total Cost                | $454,275      | $619,869               | $165,594    |
| Avg Cost/Shipment         | $4.59         | $6.26                  | $1.67       |

P2P saves $166K on the 99K shipments it retains, but this is offset by the constraint adjustment penalties.

### P2P vs Other Carriers (on P2P's assigned volume)

| Carrier   | Would Cost      | Avg/Shipment   | vs P2P        |
|-----------|-----------------|----------------|---------------|
| P2P       | $454,275        | $4.59          | -             |
| OnTrac    | $619,869        | $6.26          | +$165,594     |
| USPS      | $924,873        | $9.35          | +$470,598     |
| FedEx     | $1,074,789      | $10.86         | +$620,514     |

P2P is genuinely the cheapest carrier for its serviceable shipments.

### P2P by Weight Bracket

| Weight     | Shipments   | % of P2P Volume   |
|------------|-------------|-------------------|
| 1 lb       | 32,766      | 33.1%             |
| 2 lbs      | 31,396      | 31.7%             |
| 3 lbs      | 18,210      | 18.4%             |
| 4 lbs      | 4,690       | 4.7%              |
| 5 lbs      | 4,626       | 4.7%              |
| 6+ lbs     | 7,255       | 7.3%              |

P2P is most competitive for lightweight packages (1-3 lbs = 83% of P2P volume).

## Key Findings

1. **P2P adds cost under current constraints**: The OnTrac minimum forces expensive shifts that negate P2P's advantage. Scenario 5 costs $158K more than Scenario 4.

2. **P2P is genuinely cheap where it operates**: At $4.59/shipment average, P2P beats all other carriers in its serviceable area.

3. **Coverage limitation matters**: P2P can only service 51.8% of shipments (289K of 558K) due to weight limits and geographic restrictions.

4. **Constraint interaction is critical**: P2P and OnTrac compete for the same volume. With OnTrac's 279K minimum, P2P can only retain 99K shipments.

5. **Both constraints are still met**: Even with P2P added, we can satisfy OnTrac (279K) and USPS (140K) minimums.

## Recommendations

### Do Not Add P2P Under Current Constraints

Adding P2P to the carrier mix would cost **$158,079 more** than the current optimized mix (Scenario 4).

### Scenario 4 Remains Optimal

Without renegotiating the OnTrac commitment, Scenario 4 (3-carrier mix without P2P) delivers the best results:
- **$918,478 savings** vs current routing (14.4%)
- Meets all contractual commitments

### If Considering P2P in the Future

| OnTrac Min   | P2P Viability   | Expected Outcome                    |
|--------------|-----------------|-------------------------------------|
| 279K         | Not viable      | Current situation (+$158K vs S4)    |
| ~200K        | Marginal        | P2P can retain ~180K shipments      |
| ~100K        | Viable          | P2P captures significant volume     |
| 0            | Optimal         | Unconstrained optimization          |

### Alternative: Negotiate Lower OnTrac Minimum

If the OnTrac minimum could be reduced to ~100-150K shipments:
- P2P could capture its natural volume (~200K shipments)
- Combined savings could exceed Scenario 4
- OnTrac would focus on its core West region where it's most competitive

---

*Analysis generated: February 2026*
*Data source: shipments_aggregated.parquet (558,013 shipments)*
*Note: P2P US is not currently used - this is a future assessment*
*Baseline: $6,389,595.72 (Scenario 1 current mix)*
