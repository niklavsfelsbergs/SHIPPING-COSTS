# Scenario 3: 100% FedEx

## Executive Summary

This scenario calculates the total shipping cost if all 558,013 US shipments were routed through FedEx, optimizing between Home Delivery and SmartPost per shipment. With transportation charges of $4.41M, we fall short of the $4.5M threshold by just $92K. Without earned discounts, 100% FedEx costs $5.89M - a **0.9% increase ($55K)** over the current carrier mix baseline of $5.83M. FedEx is now nearly cost-neutral vs the current mix thanks to corrected SmartPost pricing.

## Methodology

### FedEx Service Selection

For each shipment, the calculator picks the cheaper of Home Delivery vs SmartPost (Ground Economy). SmartPost uses different rate tables, a higher DIM factor (225 vs 139), and a weight ceiling of 71 lbs.

| Service              | Shipments   | Share    | Cost             |
|----------------------|-------------|----------|------------------|
| Home Delivery (FXEHD)| 73,907     | 13.2%    | $937,208.96      |
| SmartPost (FXSP)     | 484,106    | 86.8%    | $4,951,856.72    |

SmartPost is cheaper for 86.8% of shipments. For reference:
- 100% Home Delivery: $7,037,555
- 100% SmartPost: $6,059,158
- Optimal (best of each): $5,889,066

### Earned Discount Tiers

FedEx base rates already include the earned discount. For reference, the tier table based on annual transportation charges:

| Tier   | Transportation Charges   | Earned Discount   | Our Status       |
|--------|--------------------------|-------------------|------------------|
| 0%     | < $4.5M                  | 0%                | **Current**      |
| 16%    | $4.5M - $6.5M            | 16%               | Gap: $92K        |
| 18%    | $6.5M - $9.5M            | 18%               |                  |

## Results

### Cost Component Breakdown

| Component                          | Amount             |
|------------------------------------|--------------------|
| Undiscounted base rate             | $4,407,875.55      |
| Performance pricing                | $0.00              |
| Additional Handling (dimension)    | $20,771.69         |
| Additional Handling (weight)       | $5,326.50          |
| Oversize                           | $68.75             |
| DAS                                | $655,673.35        |
| Residential                        | $166,845.05        |
| Demand (base)                      | $12,427.95         |
| Demand (AHS)                       | $3,313.06          |
| Fuel                               | $616,586.32        |
| **Total surcharges**               | **$1,481,012.67**  |
| **Total FedEx Cost**               | **$5,889,065.68**  |

### Comparison to Baseline

| Scenario                              | Total Cost          | vs Baseline                |
|---------------------------------------|---------------------|----------------------------|
| Current carrier mix (baseline)        | $5,833,893.77       | -                          |
| 100% FedEx (optimal HD/SP)            | $5,889,065.68       | **+$55,172 (+0.9%)**       |

### What-If: Impact at Different Earned Discount Tiers

| Tier              | Discount   | Savings       | Total Cost     | vs Baseline   |
|-------------------|------------|---------------|----------------|---------------|
| < $4.5M           | 0%         | $0            | $5,889,066     | +0.9%         |
| $4.5M - $6.5M     | 16%        | $705,260      | $5,183,806     | -11.1%        |
| $6.5M - $9.5M     | 18%        | $793,418      | $5,095,648     | -12.7%        |

### Cost Breakdown by Zone

| Zone   | Shipments   | FedEx Total    |
|--------|-------------|----------------|
| 2      | 36,645      | $340,317       |
| 3      | 62,638      | $613,954       |
| 4      | 188,070     | $1,863,238     |
| 5      | 134,923     | $1,425,242     |
| 6      | 30,457      | $341,612       |
| 7      | 33,197      | $404,077       |
| 8      | 71,310      | $875,724       |
| 9      | 589         | $19,161        |
| 17     | 184         | $5,741         |

### Cost Breakdown by Weight (Top 10)

| Weight   | Shipments   | FedEx Total    |
|----------|-------------|----------------|
| 1 lb     | 145,687     | $1,329,799     |
| 2 lb     | 113,398     | $1,059,998     |
| 3 lb     | 96,338      | $921,354       |
| 5 lb     | 41,160      | $458,267       |
| 4 lb     | 43,900      | $448,209       |
| 7 lb     | 25,303      | $340,974       |
| 6 lb     | 28,730      | $337,588       |
| 9 lb     | 12,704      | $181,102       |
| 8 lb     | 14,087      | $183,476       |
| 10 lb    | 7,074       | $101,608       |

## Key Findings

1. **FedEx is nearly cost-neutral**: At $5.89M, 100% FedEx is only $55K (+0.9%) more than the current mix. SmartPost pricing makes FedEx highly competitive.

2. **SmartPost handles 87% of volume**: SmartPost (Ground Economy) is cheaper for the vast majority of shipments, saving $1.15M vs using only Home Delivery.

3. **Surcharge burden reduced**: Total surcharges are $1.48M (25.1% of total cost), down significantly from the Home Delivery-only scenario where surcharges were 43% of cost.

4. **Close to the 16% earned discount tier**: Transportation charges of $4.41M are only $92K short of the $4.5M threshold. If reached, the 16% tier would save $705K, bringing total to $5.18M (-11.1% vs baseline).

5. **Zone 4 is dominant**: Zone 4 accounts for 33.7% of shipments and 31.7% of cost.

## Caveats

1. **Earned discount already in base rates**: The base rates used include any applicable earned discount. The tier table is shown for reference only.

2. **Service selection is per-shipment optimal**: The calculator picks the cheaper of HD vs SmartPost for each shipment. In practice, routing decisions may also consider service level and delivery speed.

3. **Rate calculations**: All costs use 2026 rate cards. Surcharges updated to 2026 proposed contract terms (AHS 75% off, Oversize 75% off, Residential 65% off, DAS 65% off, Fuel 14% effective rate applied to base rate only).

---

*Generated: February 2026*
*Script: `analysis/US_2026_tenders/optimization/scenario_3_fedex_100.py`*
