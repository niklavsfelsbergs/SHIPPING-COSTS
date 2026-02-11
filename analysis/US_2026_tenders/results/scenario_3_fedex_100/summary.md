# Scenario 3: 100% FedEx

## Executive Summary

This scenario calculates the total shipping cost if all 558,013 US shipments were routed through FedEx, including the impact of volume-based earned discounts. With transportation charges of $3.99M, we fall short of the $4.5M threshold needed to qualify for any earned discount (currently at 0% tier). Without earned discounts, 100% FedEx costs $7.04M - a **9.3% increase ($600K)** over the current carrier mix baseline of $6.44M.

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

With transportation charges (undiscounted base rate) of **$3,994,408**, we qualify for:

| Tier   | Transportation Charges   | Earned Discount   | Our Status       |
|--------|--------------------------|-------------------|------------------|
| 0%     | < $4.5M                  | 0%                | **Current**      |
| 16%    | $4.5M - $6.5M            | 16%               | Gap: $506K       |
| 18%    | $6.5M - $9.5M            | 18%               |                  |
| 19%    | $9.5M - $12.5M           | 19%               |                  |
| 20%    | $12.5M - $15.5M          | 20%               |                  |
| 20.5%  | $15.5M - $24.5M          | 20.5%             |                  |
| 21%    | $24.5M+                  | 21%               |                  |

## Results

### Total Cost (Before Earned Discount)

| Component                   | Amount             |
|-----------------------------|--------------------|
| Undiscounted base rate      | $3,994,407.80      |
| Performance pricing         | $0.00              |
| Total surcharges            | $3,041,860.41      |
| **Total FedEx Cost**        | **$7,037,554.62**  |

#### Surcharge Breakdown

| Surcharge                           | Amount         |
|-------------------------------------|----------------|
| Residential                         | $1,259,714.35  |
| Fuel                                | $559,788.26    |
| DAS                                 | $549,246.04    |
| Additional Handling (dimension)     | $440,086.31    |
| Demand (base)                       | $127,735.90    |
| Demand (AHS)                        | $99,894.30     |
| Additional Handling (weight)        | $5,326.50      |
| Oversize                            | $68.75         |

### Earned Discount Tier Achieved

- **Tier**: < $4.5M (0% discount)
- **Gap to next tier**: $505,592.20

### Total Cost (After Earned Discount)

| Metric                                   | Amount             |
|------------------------------------------|--------------------|
| FedEx cost (0% earned discount)          | $7,037,554.62      |
| Less: Earned discount (0%)               | $0.00              |
| **Final Total**                          | **$7,037,554.62**  |

### Comparison to Baseline

| Scenario                              | Total Cost          | vs Baseline                |
|---------------------------------------|---------------------|----------------------------|
| Current carrier mix (baseline)        | $6,437,752.11       | -                          |
| 100% FedEx (0% earned discount)       | $7,037,554.62       | **+$599,803 (+9.3%)**      |

### What-If: Impact at Different Tiers

If we could reach different earned discount tiers (hypothetically):

| Tier              | Discount   | Savings     | Total Cost     | vs Baseline   |
|-------------------|------------|-------------|----------------|---------------|
| < $4.5M           | 0%         | $0          | $7,037,555     | +9.3%         |
| $4.5M - $6.5M     | 16%        | $639,105    | $6,398,449     | -0.6%         |
| $6.5M - $9.5M     | 18%        | $718,993    | $6,318,561     | -1.9%         |
| $9.5M - $12.5M    | 19%        | $758,937    | $6,278,617     | -2.5%         |
| $12.5M - $15.5M   | 20%        | $798,882    | $6,238,673     | -3.1%         |
| $15.5M - $24.5M   | 20.5%      | $818,854    | $6,218,701     | -3.4%         |
| $24.5M+           | 21%        | $838,826    | $6,198,729     | -3.7%         |

### Cost Breakdown by Zone

| Zone   | Shipments   | FedEx Total    |
|--------|-------------|----------------|
| 2      | 36,645      | $409,878       |
| 3      | 62,638      | $729,719       |
| 4      | 188,070     | $2,232,706     |
| 5      | 134,923     | $1,714,714     |
| 6      | 30,457      | $404,113       |
| 7      | 33,197      | $473,882       |
| 8      | 71,310      | $1,013,384     |
| 9      | 589         | $47,608        |
| 17     | 184         | $11,551        |

### Cost Breakdown by Weight (Top 10)

| Weight   | Shipments   | FedEx Total    |
|----------|-------------|----------------|
| 1 lb     | 145,687     | $1,533,091     |
| 2 lb     | 113,398     | $1,214,138     |
| 3 lb     | 96,338      | $1,052,851     |
| 5 lb     | 41,160      | $517,228       |
| 4 lb     | 43,900      | $498,299       |
| 7 lb     | 25,303      | $479,178       |
| 6 lb     | 28,730      | $421,634       |
| 9 lb     | 12,704      | $253,975       |
| 8 lb     | 14,087      | $229,984       |
| 10 lb    | 7,074       | $143,303       |

### FedEx Service Selection

| Service              | Shipments   | Share    | Cost           |
|----------------------|-------------|----------|----------------|
| Home Delivery (FXEHD)| 558,013    | 100.0%   | $7,037,554.62  |
| SmartPost (FXSP)     | 0          | 0.0%     | $0.00          |

**Note:** SmartPost shows 0 shipments because the current rate tables have no SmartPost-specific rates populated (performance_pricing and undiscounted_rates are zeroed out for SmartPost), so all shipments default to Home Delivery as the cheaper option.

## Key Findings

1. **No earned discount at current volume**: Transportation charges of $3.99M fall short of the $4.5M threshold by ~$506K, meaning we qualify for 0% earned discount.

2. **Surcharge burden is significant**: Surcharges total $3.04M (43.2% of total cost), with Residential ($1.26M), Fuel ($560K), and DAS ($549K) being the largest components.

3. **Premium over current mix**: 100% FedEx costs 9.3% more than the current carrier mix without earned discounts.

4. **At 16% tier, FedEx beats baseline**: If we could reach the $4.5M threshold, the 16% earned discount would bring FedEx cost to $6.40M - slightly cheaper than the current mix baseline (-0.6%).

5. **At higher tiers, FedEx savings grow**: At 18%+ earned discount ($6.5M+ transportation charges), FedEx would save 1.9-3.7% vs the current carrier mix.

6. **Zone 4 is dominant**: Zone 4 accounts for 33.7% of shipments and 31.7% of cost - the highest concentration.

7. **SmartPost not contributing**: All shipments route to Home Delivery because SmartPost rate tables are not yet populated with 2026 rates. Populating SmartPost rates could significantly reduce costs for lighter shipments.

## Caveats

1. **Earned discount calculation is simplified**: The earned discount has been applied to total transportation charges (base rates) as an approximation. In reality:
   - Earned discount does NOT apply to special zones (9, 14, 17, 22, 23, 25, 92, 96)
   - The exact interaction between Earned Discount and Performance Pricing needs clarification in FedEx meeting

2. **SmartPost rates missing**: SmartPost undiscounted_rates.csv and performance_pricing.csv are zeroed out, so all shipments default to Home Delivery. This overstates the 100% FedEx cost.

3. **Data period**: This analysis uses 558,013 shipments from the analysis period. Annual totals may differ.

4. **Rate calculations**: All costs are calculated/expected costs using 2026 rate cards, not actual invoice data. Surcharges updated to 2026 proposed contract terms (AHS 75% off, Oversize 75% off, Residential 65% off, DAS 65% off, Fuel 14% effective rate applied to base rate only).

5. **Questions for FedEx meeting**:
   - How exactly does Earned Discount interact with Performance Pricing?
   - Is Earned Discount applied to base rate before or after Performance Pricing?
   - Confirm 52-week rolling calculation methodology

---

*Generated: February 2026*
*Script: `analysis/US_2026_tenders/optimization/scenario_3_fedex_100.py`*
