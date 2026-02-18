# Scenario 1: Current Carrier Mix

## Executive Summary

This scenario establishes the baseline shipping cost using the current carrier routing strategy. Using calculated/expected costs from 2026 rate tables (not invoice actuals), the current carrier mix achieves a total cost of **$5,971,748.12** for 558,013 shipments.

**FedEx Earned Discount Adjustment:** The FedEx 2026 rate tables are built with an 18% earned discount baked in. However, at the current carrier mix volume (~$6.05M true undiscounted FedEx transportation), the actual earned discount tier is 16%, not 18%. A multiplier of 1.0541 (ratio of effective discount factors: 0.39/0.37) is applied to all FedEx costs to correct for this 2-percentage-point difference. This increases total FedEx costs by $137,854 (+4.6%) compared to the unadjusted rate tables.

## Calculator Validation: 2025 Actuals vs 2026 Calculated

For 539,941 matched shipments (96.8% match rate), comparing what we actually paid in 2025 against what the 2026 calculator predicts:

| Carrier    | Matched     | 2025 Actual       | 2026 Calculated   | Difference   |
|------------|-------------|-------------------|-------------------|--------------|
| FedEx      | 267,638     | $4,040,733.33     | $3,065,659.16     | -24.1%       |
| OnTrac     | 128,982     | $1,447,346.40     | $1,618,560.51     | +11.8%       |
| USPS       | 103,164     | $812,301.21       | $806,305.23       | -0.7%        |
| DHL        | 40,157      | $240,942.00       | $240,942.00       | 0.0%         |
| **TOTAL**  | **539,941** | **$6,541,322.94** | **$5,731,466.90** | **-12.4%**   |

Overall 2026 calculated rates are **12.4% lower** than 2025 actuals. FedEx shows the largest decrease (-24.1%), driven by the SmartPost fix (SmartPost now correctly uses Ground Economy rates instead of Home Delivery) plus updated 2026 surcharge discounts, partially offset by the earned discount adjustment from 18% to 16%. OnTrac calculated is 11.8% higher than actuals (2026 rate increases). USPS is within 1% of actuals.

**Match rates:** FedEx 97.7% (SmartPost matched via customer reference), OnTrac 93.6%, USPS 97.2%, DHL 100.0% (flat $6.00 estimate).

**Exclusions:** 197 OnTrac shipments with OML (over max limits) or LPS (large package surcharge) in actuals were excluded from all calculations. These are outlier shipments averaging $1,964 (OML) and $175 (LPS) that cannot be predicted by the calculator.

## Methodology

**Data Source:** `shipments_unified.parquet` - shipment-level data with costs calculated for each carrier

**Cost Calculation:**
- Each shipment uses the cost from its actual carrier (recorded in `pcs_shipping_provider`)
- FedEx shipments use FedEx calculated costs (optimal of Home Delivery vs SmartPost)
- OnTrac shipments use OnTrac calculated costs
- USPS shipments use USPS calculated costs
- DHL shipments use **$6.00 estimated cost** (no DHL calculator available)

**FedEx Fuel Surcharge:** 14% effective rate (20% list, 30% contractual discount), applied to base rate only (not surcharges).

**FedEx Earned Discount Adjustment:** Rate tables are built with 18% earned discount baked in. At current mix volume, the actual tier is 16%. All FedEx costs are multiplied by 1.0541 (= (1 - 0.16 * discount_factor) / (1 - 0.18 * discount_factor)) to correct for this. This affects all FedEx line items (base rate, surcharges) uniformly.

**Carrier Mapping:**

| Provider Code           | Carrier   | Description                      |
|-------------------------|-----------|----------------------------------|
| ONTRAC                  | OnTrac    | OnTrac Ground                    |
| USPS                    | USPS      | USPS Ground Advantage            |
| FXEHD                   | FedEx     | FedEx Home Delivery              |
| FXESPPS                 | FedEx     | FedEx SmartPost Parcel Select    |
| FXEGRD                  | FedEx     | FedEx Ground                     |
| FXE2D                   | FedEx     | FedEx 2Day                       |
| DHL ECOMMERCE AMERICA   | DHL       | $6.00 estimated cost             |

## Results

### Total Cost

| Metric                      | Value                |
|-----------------------------|----------------------|
| **Total Expected Cost**     | **$5,971,748.12**    |
| Total Shipments             | 558,013              |
| Non-DHL Shipments           | 517,856 (92.8%)      |
| DHL Shipments               | 40,157 (7.2%)        |
| DHL Estimated Cost          | $240,942.00          |
| Average Cost per Shipment   | $10.70               |

### Breakdown by Carrier

| Carrier         | Shipments   | Share    | Total Cost        | Avg Cost   |
|-----------------|-------------|----------|-------------------|------------|
| FedEx           | 273,941     | 49.1%    | $3,160,979.99     | $11.54     |
| OnTrac          | 137,764     | 24.7%    | $1,736,637.92     | $12.61     |
| USPS            | 106,151     | 19.0%    | $833,188.21       | $7.85      |
| DHL             | 40,157      | 7.2%     | $240,942.00       | $6.00      |

### Breakdown by Provider (Detailed)

| Provider                  | Shipments   | Share    | Total Cost        | Avg Cost   |
|---------------------------|-------------|----------|-------------------|------------|
| FXEHD (Home Delivery)     | 165,565     | 29.7%    | $2,085,804.31     | $12.60     |
| ONTRAC                    | 137,764     | 24.7%    | $1,736,637.92     | $12.61     |
| FXESPPS (SmartPost)       | 107,197     | 19.2%    | $1,060,686.90     | $9.89      |
| USPS                      | 106,151     | 19.0%    | $833,188.21       | $7.85      |
| DHL ECOMMERCE AMERICA     | 40,157      | 7.2%     | $240,942.00       | $6.00      |
| FXEGRD (Ground)           | 850         | 0.2%     | $9,280.10         | $10.92     |
| FXE2D (2Day)              | 326         | 0.1%     | $5,158.78         | $15.82     |
| Other FedEx               | 3           | 0.0%     | $49.89            | $16.63     |

### Breakdown by Weight

| Weight Bracket   | Shipments   | Share    | Total Cost        | Avg Cost   |
|------------------|-------------|----------|-------------------|------------|
| 0-1 lbs          | 106,089     | 19.0%    | $762,678.68       | $7.19      |
| 1-5 lbs          | 294,376     | 52.8%    | $2,984,690.39     | $10.14     |
| 5-10 lbs         | 87,810      | 15.7%    | $1,358,007.19     | $15.47     |
| 10-20 lbs        | 24,007      | 4.3%     | $473,764.59       | $19.73     |
| 20-30 lbs        | 3,671       | 0.7%     | $90,183.18        | $24.57     |
| 30+ lbs          | 1,903       | 0.3%     | $61,482.08        | $32.31     |

### Breakdown by Production Site

| Site       | Shipments   | Share    | Total Cost        | Avg Cost   |
|------------|-------------|----------|-------------------|------------|
| Phoenix    | 269,059     | 48.2%    | $3,197,642.21     | $11.88     |
| Miami      | 129,396     | 23.2%    | $1,381,793.81     | $10.68     |
| Columbus   | 119,400     | 21.4%    | $1,151,361.85     | $9.64      |
| Szczecin   | 1           | 0.0%     | $8.25             | $8.25      |

### Monthly Breakdown

| Month   | DHL    | FedEx  | USPS   | OnTrac | Total     | Total Cost   | Avg     |
|---------|--------|--------|--------|--------|-----------|--------------|---------|
| 2025-01 | 16.1%  | 83.9%  | 0.0%   | 0.0%   | 45,019    | $478,213     | $10.62  |
| 2025-02 | 12.8%  | 87.2%  | 0.0%   | 0.0%   | 41,368    | $435,770     | $10.53  |
| 2025-03 | 16.0%  | 84.0%  | 0.0%   | 0.0%   | 33,249    | $353,166     | $10.62  |
| 2025-04 | 14.6%  | 85.4%  | 0.0%   | 0.0%   | 37,322    | $395,733     | $10.60  |
| 2025-05 | 12.6%  | 87.4%  | 0.0%   | 0.0%   | 48,154    | $510,424     | $10.60  |
| 2025-06 | 15.1%  | 84.9%  | 0.0%   | 0.0%   | 37,955    | $402,576     | $10.61  |
| 2025-07 | 11.5%  | 72.5%  | 2.1%   | 13.9%  | 36,242    | $393,607     | $10.86  |
| 2025-08 | 2.7%   | 44.9%  | 16.1%  | 36.4%  | 33,696    | $369,060     | $10.95  |
| 2025-09 | 0.0%   | 12.4%  | 37.1%  | 50.5%  | 30,399    | $338,326     | $11.13  |
| 2025-10 | 0.0%   | 14.3%  | 38.8%  | 46.9%  | 35,375    | $408,441     | $11.55  |
| 2025-11 | 0.0%   | 16.4%  | 33.9%  | 49.7%  | 58,007    | $660,850     | $11.39  |
| 2025-12 | 0.0%   | 5.1%   | 45.6%  | 49.3%  | 121,227   | $1,225,583   | $10.11  |

**Key observations:**
- Jan-Jun 2025: DHL (~15%) + FedEx (~85%) only
- Jul 2025: USPS and OnTrac start ramping up
- Sep 2025 onwards: OnTrac becomes dominant (~50%), USPS grows to ~37%, FedEx drops to ~12-16%
- Dec 2025: Peak volume (121K) with lowest avg cost ($10.11) - shift to cheaper carriers
- USPS consistently cheapest at $7-8 avg; OnTrac most expensive at $11-14 avg

### Comparison: 100% Single Carrier Scenarios

| Carrier       | Serviceable   | Coverage   | Total Cost        | Avg Cost   |
|---------------|---------------|------------|-------------------|------------|
| **Current**   | **558,013**   | **100.0%** | **$5,971,748.12** | **$10.70** |
| FedEx         | 558,013       | 100.0%     | $6,160,686.12     | $11.04     |
| Maersk        | 558,013       | 100.0%     | $6,041,478.28     | $10.83     |
| USPS          | 558,013       | 100.0%     | $14,835,549.16    | $26.59     |
| OnTrac        | 360,151       | 64.5%      | $3,998,470.55     | $11.10     |
| P2P           | 289,272       | 51.8%      | $3,098,915.03     | $10.71     |

**Note:** OnTrac and P2P have partial geographic coverage. Costs shown are only for shipments they can service.

**Note on FedEx 100%:** The FedEx single-carrier cost ($6.16M) also reflects the 16% earned discount. At 100% FedEx volume, the earned discount tier would likely be higher (potentially 18-20%), which would reduce this cost. See Scenario 3 for FedEx-optimized analysis.

## Key Findings

1. **Current mix baseline**: $5.97M for 558K shipments ($10.70 avg)

2. **2026 rates are 12.4% lower** than 2025 actuals for matched shipments ($5.73M vs $6.54M), primarily driven by the SmartPost rate correction, partially offset by the earned discount adjustment

3. **FedEx dominates volume** at 49.1% of shipments, accounting for 52.9% of total cost

4. **SmartPost is significantly cheaper than Home Delivery**: FXESPPS shipments average $9.89 vs FXEHD at $12.60 - the corrected SmartPost pricing reduced the FedEx carrier total by ~$558K

5. **Full-coverage carrier ranking** (can service all shipments):
   - Current Mix: $10.70 avg (cheapest)
   - Maersk: $10.83 avg
   - FedEx: $11.04 avg
   - USPS: $26.59 avg (penalized by heavy/oversize packages)

6. **Partial-coverage carriers** (cannot service all shipments):
   - OnTrac: 64.5% coverage, $11.10 avg (West region only)
   - P2P: 51.8% coverage, $10.71 avg (limited ZIP coverage)

7. **Weight-based pricing impact**: Shipments 5-10 lbs cost 2.2x more than 0-1 lb shipments

8. **Phoenix is the largest cost center** at 48.2% of shipments and 53.5% of costs

9. **FedEx earned discount sensitivity**: The 2-point adjustment from 18% to 16% adds $137,854 to the baseline. Negotiating a higher earned discount tier would directly reduce the current mix cost.

## Cost Imputations

| Item                              | Count    | Method                              |
|-----------------------------------|----------|-------------------------------------|
| DHL eCommerce America             | 40,157   | $6.00/shipment flat estimate        |
| OnTrac OML/LPS excluded          | 197      | Removed from all calculations       |
| FedEx earned discount adjustment  | 273,941  | 1.0541x multiplier (16% vs 18%)    |

## Files Generated

- `breakdown_by_carrier.csv` - Carrier-level summary
- `breakdown_by_provider.csv` - Provider-level detail (includes FedEx service types)
- `breakdown_by_packagetype.csv` - Full package type breakdown
- `breakdown_by_weight.csv` - Weight bracket analysis
- `breakdown_by_site.csv` - Production site summary
- `breakdown_by_month.csv` - Monthly carrier split with costs
- `comparison_single_carrier.csv` - Single carrier scenario costs
- `comparison_actuals_vs_calculated.csv` - 2025 actuals vs 2026 calculated by carrier

---
*Generated: February 2026*
*Data Period: 2025 shipment volumes with 2026 calculated rates*
*FedEx earned discount: adjusted from 18% (baked in rate tables) to 16% (actual tier for current mix volume)*
