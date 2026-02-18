# Scenario 3: 100% FedEx

## Executive Summary

This scenario calculates the total shipping cost if all 539,917 US shipments were routed through FedEx, optimizing between Home Delivery and SmartPost per shipment. With true undiscounted transportation charges of $9.32M, we fall in the $6.5M-$9.5M tier (18% earned discount). The rate tables already have this 18% discount baked in, so no additional discount applies. 100% FedEx costs $6.29M - a **3.6% increase ($216K)** over the current carrier mix baseline of $6.07M.

## Methodology

### FedEx Service Selection

For each shipment, the calculator picks the cheaper of Home Delivery vs SmartPost (Ground Economy). SmartPost uses different rate tables, a higher DIM factor (225 vs 139), and a weight ceiling of 71 lbs.

| Service              | Shipments   | Share    | Cost             |
|----------------------|-------------|----------|------------------|
| Home Delivery (FXEHD)| 193,908    | 35.9%    | $3,076,215.29    |
| SmartPost (FXSP)     | 346,009    | 64.1%    | $3,211,686.64    |

SmartPost is cheaper for 64.1% of shipments. For reference:
- 100% Home Delivery: $6,777,880
- 100% SmartPost: $6,311,568
- Optimal (best of each): $6,287,902

### Earned Discount Tiers

FedEx base rates already include the 18% earned discount baked in. The true undiscounted transportation charges of $9.32M place us firmly in the $6.5M-$9.5M tier.

| Tier   | Transportation Charges   | Earned Discount   | Our Status       |
|--------|--------------------------|-------------------|------------------|
| 0%     | < $4.5M                  | 0%                |                  |
| 16%    | $4.5M - $6.5M            | 16%               |                  |
| 18%    | $6.5M - $9.5M            | 18%               | **Current**      |
| 19%    | $9.5M - $12.5M           | 19%               |                  |

## Results

### Cost Component Breakdown

| Component                          | Amount             |
|------------------------------------|--------------------|
| Base rate (baked 18% earned)       | $4,098,539.06      |
| Performance pricing                | $0.00              |
| Additional Handling (dimension)    | $415,965.94        |
| Additional Handling (weight)       | $2,788.88          |
| Oversize                           | $0.00              |
| DAS                                | $625,093.69        |
| Residential                        | $437,747.31        |
| Demand (base)                      | $40,380.30         |
| Demand (AHS)                       | $93,745.22         |
| Fuel                               | $573,258.63        |
| **Total surcharges**               | **$2,188,979.96**  |
| **Total FedEx Cost**               | **$6,287,901.93**  |

### Comparison to Baseline

| Scenario                              | Total Cost          | vs Baseline                |
|---------------------------------------|---------------------|----------------------------|
| Current carrier mix (baseline)        | $6,072,061.73       | -                          |
| 100% FedEx (baked 18% earned)         | $6,287,901.93       | **+$215,840 (+3.6%)**      |

### Earned Discount Tier

| Metric                                      | Value                     |
|---------------------------------------------|---------------------------|
| True undiscounted transportation charges     | $9,315,338                |
| Baked base rate total (after discounts)      | $4,098,539                |
| Earned discount tier                         | $6.5M - $9.5M (18%)      |
| Rate tables bake in                          | 18% HD / 4.5% SP earned  |

The rate tables already reflect the 18% earned discount for Home Delivery and 4.5% for SmartPost. The baked rate is the final cost -- no re-application or additional discount is needed.

### Cost Breakdown by Zone

| Zone   | Shipments   | FedEx Total    |
|--------|-------------|----------------|
| 2      | 35,369      | $361,242       |
| 3      | 60,830      | $652,999       |
| 4      | 182,793     | $2,002,804     |
| 5      | 131,012     | $1,537,910     |
| 6      | 29,398      | $362,753       |
| 7      | 31,744      | $422,241       |
| 8      | 68,044      | $900,956       |
| 9      | 560         | $38,744        |
| 17     | 167         | $8,253         |

### Cost Breakdown by Weight (Top 10)

| Weight   | Shipments   | FedEx Total    |
|----------|-------------|----------------|
| 1 lb     | 142,303     | $1,299,388     |
| 2 lb     | 109,943     | $1,029,802     |
| 3 lb     | 93,314      | $915,827       |
| 5 lb     | 40,112      | $492,562       |
| 7 lb     | 24,421      | $459,339       |
| 4 lb     | 42,378      | $457,148       |
| 6 lb     | 27,885      | $405,298       |
| 9 lb     | 12,272      | $245,086       |
| 8 lb     | 13,611      | $220,838       |
| 10 lb    | 6,837       | $138,776       |

### Surcharge Breakdown

| Surcharge                    | Total Cost     | Shipments Affected   | % of Total Cost |
|------------------------------|----------------|----------------------|-----------------|
| DAS                          | $625,094       | 186,879 (34.6%)      | 9.9%            |
| Fuel                         | $573,259       | 539,917 (100%)       | 9.1%            |
| Residential                  | $437,747       | 193,908 (35.9%)      | 7.0%            |
| Additional Handling (dim)    | $415,966       | 50,805 (9.4%)        | 6.6%            |
| Demand (AHS)                 | $93,745        | 18,838 (3.5%)        | 1.5%            |
| Demand (base)                | $40,380        | 68,042 (12.6%)       | 0.6%            |
| Additional Handling (weight) | $2,789         | 111 (0.0%)           | 0.0%            |
| **Total Surcharges**         | **$2,188,980** |                      | **34.8%**       |

## Key Findings

1. **FedEx is 3.6% more expensive than baseline**: At $6.29M, 100% FedEx costs $216K more than the current carrier mix of $6.07M.

2. **Home Delivery handles 36% of volume**: Unlike previous analysis, the matched-only dataset shifts the HD/SP split from 13%/87% to 36%/64%, with HD handling a larger share and costing $3.08M vs SmartPost's $3.21M.

3. **Surcharge burden is significant**: Total surcharges are $2.19M (34.8% of total cost). DAS ($625K) is the largest surcharge, followed by fuel ($573K), residential ($438K), and additional handling ($416K).

4. **Well above the 18% earned discount tier**: True undiscounted transportation charges of $9.32M place us firmly in the $6.5M-$9.5M tier. The rate tables already have 18% baked in, so the calculated cost reflects this discount.

5. **Zone 4 is dominant**: Zone 4 accounts for 33.9% of shipments and 31.9% of cost ($2.00M).

## Caveats

1. **Earned discount already in base rates**: The base rates used include the 18% earned discount (HD) and 4.5% earned discount (SP). The tier table is shown for reference only.

2. **Service selection is per-shipment optimal**: The calculator picks the cheaper of HD vs SmartPost for each shipment. In practice, routing decisions may also consider service level and delivery speed.

3. **Rate calculations**: All costs use 2026 rate cards. Surcharges updated to 2026 proposed contract terms (AHS 75% off, Oversize 75% off, Residential 65% off, DAS 65% off, Fuel 14% effective rate applied to base rate only).

---

*Generated: February 2026*
*Script: `analysis/US_2026_tenders/optimization/scenario_3_fedex_100.py`*
