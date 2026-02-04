# Scenario 3: 100% FedEx

## Executive Summary

This scenario calculates the total shipping cost if all 558,210 US shipments were routed through FedEx, including the impact of volume-based earned discounts. With transportation charges of $4.10M, we fall just short of the $4.5M threshold needed to qualify for any earned discount (currently at 0% tier). Without earned discounts, 100% FedEx costs $6.92M - an **8.3% increase ($531K)** over the current carrier mix baseline of $6.39M.

## Methodology

### FedEx 4-Part Rate Structure

FedEx invoice charges decompose into four components:
1. **Undiscounted Base Rate** - Published rate card price after contractual discounts
2. **Performance Pricing** - Volume-based adjustment (currently $0 in our calculations)
3. **Earned Discount** - Tiered discount based on annual transportation charges
4. **Grace Discount** - Transitional discount (currently $0)

### How Earned Discount Works

The Earned Discount is a volume-based incentive that applies to **transportation charges only** (base rates, not surcharges):
- Calculated on a 52-week rolling average
- Does **NOT** apply to special zones (9, 14, 17, 22, 23, 25, 92, 96) except Ground Economy
- Tier is determined by total annual transportation charges
- Currently at 0% tier due to reduced FedEx volume

### Tier Qualification

With transportation charges (undiscounted base rate) of **$4,104,708**, we qualify for:

| Tier   | Transportation Charges   | Earned Discount   | Our Status       |
|--------|--------------------------|-------------------|------------------|
| 0%     | < $4.5M                  | 0%                | **Current**      |
| 16%    | $4.5M - $6.5M            | 16%               | Gap: $395K       |
| 18%    | $6.5M - $9.5M            | 18%               |                  |
| 19%    | $9.5M - $12.5M           | 19%               |                  |
| 20%    | $12.5M - $15.5M          | 20%               |                  |
| 20.5%  | $15.5M - $24.5M          | 20.5%             |                  |
| 21%    | $24.5M+                  | 21%               |                  |

## Results

### Total Cost (Before Earned Discount)

| Component                   | Amount             |
|-----------------------------|--------------------|
| Undiscounted base rate      | $4,104,708.12      |
| Performance pricing         | $0.00              |
| Total surcharges            | $2,816,232.19      |
| **Total FedEx Cost**        | **$6,920,940.31**  |

#### Surcharge Breakdown

| Surcharge                           | Amount         |
|-------------------------------------|----------------|
| Residential                         | $936,339.04    |
| Fuel                                | $629,378.37    |
| DAS                                 | $564,666.55    |
| Additional Handling (dimension)     | $462,576.80    |
| Demand (base)                       | $117,328.95    |
| Demand (AHS)                        | $100,234.92    |
| Additional Handling (weight)        | $5,592.56      |
| Oversize                            | $115.00        |

### Earned Discount Tier Achieved

- **Tier**: < $4.5M (0% discount)
- **Gap to next tier**: $395,291.88

### Total Cost (After Earned Discount)

| Metric                                   | Amount             |
|------------------------------------------|--------------------|
| FedEx cost (0% earned discount)          | $6,920,940.31      |
| Less: Earned discount (0%)               | $0.00              |
| **Final Total**                          | **$6,920,940.31**  |

### Comparison to Baseline

| Scenario                              | Total Cost          | vs Baseline                |
|---------------------------------------|---------------------|----------------------------|
| Current carrier mix (baseline)        | $6,389,595.72       | -                          |
| 100% FedEx (0% earned discount)       | $6,920,940.31       | **+$531,345 (+8.3%)**      |

### What-If: Impact at Different Tiers

If we could reach different earned discount tiers (hypothetically):

| Tier              | Discount   | Savings     | Total Cost     | vs Baseline   |
|-------------------|------------|-------------|----------------|---------------|
| < $4.5M           | 0%         | $0          | $6,920,940     | +8.3%         |
| $4.5M - $6.5M     | 16%        | $656,753    | $6,264,187     | -2.0%         |
| $6.5M - $9.5M     | 18%        | $738,847    | $6,182,093     | -3.2%         |
| $9.5M - $12.5M    | 19%        | $779,895    | $6,141,046     | -3.9%         |
| $12.5M - $15.5M   | 20%        | $820,942    | $6,099,999     | -4.5%         |
| $15.5M - $24.5M   | 20.5%      | $841,465    | $6,079,475     | -4.9%         |
| $24.5M+           | 21%        | $861,989    | $6,058,952     | -5.2%         |

### Cost Breakdown by Zone

| Zone   | Shipments   | FedEx Total    |
|--------|-------------|----------------|
| 2      | 36,669      | $400,840       |
| 3      | 62,662      | $715,287       |
| 4      | 188,159     | $2,189,927     |
| 5      | 134,971     | $1,692,765     |
| 6      | 30,458      | $398,581       |
| 7      | 33,200      | $468,789       |
| 8      | 71,318      | $1,000,153     |
| 9      | 589         | $43,998        |
| 17     | 184         | $10,599        |

### Cost Breakdown by Weight (Top 10)

| Weight   | Shipments   | FedEx Total    |
|----------|-------------|----------------|
| 1 lb     | 145,692     | $1,480,770     |
| 2 lb     | 113,406     | $1,156,303     |
| 3 lb     | 96,358      | $1,020,233     |
| 5 lb     | 41,170      | $510,696       |
| 7 lb     | 25,349      | $490,309       |
| 4 lb     | 43,915      | $486,578       |
| 6 lb     | 28,743      | $422,521       |
| 9 lb     | 12,726      | $260,270       |
| 8 lb     | 14,100      | $232,057       |
| 10 lb    | 7,085       | $146,815       |

## Key Findings

1. **No earned discount at current volume**: Transportation charges of $4.10M fall short of the $4.5M threshold by ~$395K, meaning we qualify for 0% earned discount.

2. **High surcharge burden**: Surcharges total $2.82M (40.7% of total cost), with Residential ($936K) and Fuel ($629K) being the largest components.

3. **Premium over current mix**: Even with 100% volume consolidation, FedEx costs 8.3% more than the current carrier mix without earned discounts.

4. **Break-even requires 16% tier**: To beat the current carrier mix, we would need to reach the $4.5M+ tier (16% discount), which would bring total to $6.26M (-2.0% vs baseline).

5. **Zone 4 is dominant**: Zone 4 accounts for 33.7% of shipments and 31.6% of cost - the highest concentration.

## Caveats

1. **Earned discount calculation is simplified**: The earned discount has been applied to total transportation charges (base rates) as an approximation. In reality:
   - Earned discount does NOT apply to special zones (9, 14, 17, 22, 23, 25, 92, 96)
   - The exact interaction between Earned Discount and Performance Pricing needs clarification in FedEx meeting

2. **Data period**: This analysis uses 558,210 shipments from the analysis period. Annual totals may differ.

3. **Rate calculations**: All costs are calculated/expected costs using 2026 rate cards, not actual invoice data.

4. **Questions for FedEx meeting**:
   - How exactly does Earned Discount interact with Performance Pricing?
   - Is Earned Discount applied to base rate before or after Performance Pricing?
   - Confirm 52-week rolling calculation methodology

---

*Generated: February 2026*
*Script: `analysis/US_2026_tenders/optimization/scenario_3_fedex_100.py`*
