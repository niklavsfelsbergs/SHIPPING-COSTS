# Scenario 1: Current Carrier Mix

## Executive Summary

This scenario establishes the baseline shipping cost using the current carrier routing strategy. Using calculated/expected costs from 2026 rate tables (not invoice actuals), the current carrier mix achieves a total cost of **$6,072,061.73** for 539,917 shipments.

**FedEx Earned Discount Adjustment:** The FedEx 2026 rate tables are built with an 18% earned discount baked in. However, at the current carrier mix volume (~$6.05M true undiscounted FedEx transportation), the actual earned discount tier is 16%, not 18%. A multiplier of 1.0541 (ratio of effective discount factors: 0.39/0.37) is applied to all FedEx costs to correct for this 2-percentage-point difference. This increases total FedEx costs by ~$137K (+4.6%) compared to the unadjusted rate tables.

## Calculator Validation: 2025 Actuals vs 2026 Calculated

This dataset is matched-only: all 539,917 shipments have both calculated costs and actual invoice data (100% match rate by construction).

| Carrier    | Matched     | 2025 Actual       | 2026 Calculated   | Difference   |
|------------|-------------|-------------------|-------------------|--------------|
| FedEx      | 267,614     | $4,040,460.17     | $3,406,253.99     | -15.7%       |
| OnTrac     | 128,982     | $1,447,346.40     | $1,618,560.51     | +11.8%       |
| USPS       | 103,164     | $812,301.21       | $806,305.23       | -0.7%        |
| DHL        | 40,157      | $240,942.00       | $240,942.00       | 0.0%         |
| **TOTAL**  | **539,917** | **$6,541,049.78** | **$6,072,061.73** | **-7.2%**    |

Overall 2026 calculated rates are **7.2% lower** than 2025 actuals. FedEx shows the largest decrease (-15.7%), driven by the SmartPost fix (SmartPost now correctly uses Ground Economy rates instead of Home Delivery) plus updated 2026 surcharge discounts, partially offset by the earned discount adjustment from 18% to 16%. OnTrac calculated is 11.8% higher than actuals (2026 rate increases). USPS is within 1% of actuals.

**Match rates:** This is a matched-only dataset -- all 539,917 shipments have corresponding actuals (100% match rate). DHL uses a flat $6.00 estimate.

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
| FXEINTECON              | FedEx     | FedEx International Economy      |
| DHL ECOMMERCE AMERICA   | DHL       | $6.00 estimated cost             |

## Results

### Total Cost

| Metric                      | Value                |
|-----------------------------|----------------------|
| **Total Expected Cost**     | **$6,072,061.73**    |
| Total Shipments             | 539,917              |
| Non-DHL Shipments           | 499,760 (92.6%)      |
| DHL Shipments               | 40,157 (7.4%)        |
| DHL Estimated Cost          | $240,942.00          |
| Average Cost per Shipment   | $11.25               |

### Breakdown by Carrier

| Carrier         | Shipments   | Share    | Total Cost        | Avg Cost   |
|-----------------|-------------|----------|-------------------|------------|
| FedEx           | 267,614     | 49.6%    | $3,406,253.99     | $12.73     |
| OnTrac          | 128,982     | 23.9%    | $1,618,560.51     | $12.55     |
| USPS            | 103,164     | 19.1%    | $806,305.23       | $7.82      |
| DHL             | 40,157      | 7.4%     | $240,942.00       | $6.00      |

### Breakdown by Provider (Detailed)

| Provider                  | Shipments   | Share    | Total Cost        | Avg Cost   |
|---------------------------|-------------|----------|-------------------|------------|
| FXEHD (Home Delivery)     | 161,635     | 29.9%    | $2,389,665.00     | $14.78     |
| ONTRAC                    | 128,982     | 23.9%    | $1,618,560.51     | $12.55     |
| FXESPPS (SmartPost)       | 104,847     | 19.4%    | $1,002,489.42     | $9.56      |
| USPS                      | 103,164     | 19.1%    | $806,305.23       | $7.82      |
| DHL ECOMMERCE AMERICA     | 40,157      | 7.4%     | $240,942.00       | $6.00      |
| FXEGRD (Ground)           | 816         | 0.2%     | $8,910.22         | $10.92     |
| FXE2D (2Day)              | 315         | 0.1%     | $5,165.15         | $16.40     |
| FXEINTECON                | 1           | 0.0%     | $24.21            | $24.21     |

### Breakdown by Weight

| Weight Bracket   | Shipments   | Share    | Total Cost        | Avg Cost   |
|------------------|-------------|----------|-------------------|------------|
| 0-1 lbs          | 102,705     | 19.0%    | $725,787.76       | $7.07      |
| 1-5 lbs          | 285,327     | 52.8%    | $2,894,128.23     | $10.14     |
| 5-10 lbs         | 84,938      | 15.7%    | $1,545,959.43     | $18.20     |
| 10-20 lbs        | 22,438      | 4.2%     | $543,026.43       | $24.20     |
| 20-30 lbs        | 3,009       | 0.6%     | $78,632.50        | $26.13     |
| 30+ lbs          | 1,343       | 0.2%     | $43,585.38        | $32.45     |

### Breakdown by Production Site

| Site       | Shipments   | Share    | Total Cost        | Avg Cost   |
|------------|-------------|----------|-------------------|------------|
| Phoenix    | 257,311     | 47.7%    | $3,201,279.74     | $12.44     |
| Miami      | 127,607     | 23.6%    | $1,489,536.50     | $11.67     |
| Columbus   | 114,842     | 21.3%    | $1,140,303.49     | $9.93      |

### Monthly Breakdown

| Month   | DHL    | FedEx  | USPS   | OnTrac | Total     | Total Cost   | Avg     |
|---------|--------|--------|--------|--------|-----------|--------------|---------|
| 2025-01 | 16.4%  | 83.6%  | 0.0%   | 0.0%   | 44,220    | $520,663     | $11.77  |
| 2025-02 | 13.0%  | 87.0%  | 0.0%   | 0.0%   | 40,635    | $457,391     | $11.26  |
| 2025-03 | 16.4%  | 83.6%  | 0.0%   | 0.0%   | 32,417    | $368,201     | $11.36  |
| 2025-04 | 15.0%  | 85.0%  | 0.0%   | 0.0%   | 36,514    | $412,614     | $11.30  |
| 2025-05 | 12.8%  | 87.2%  | 0.0%   | 0.0%   | 47,264    | $532,672     | $11.27  |
| 2025-06 | 15.3%  | 84.7%  | 0.0%   | 0.0%   | 37,288    | $424,613     | $11.39  |
| 2025-07 | 11.9%  | 73.3%  | 0.8%   | 14.0%  | 34,874    | $402,026     | $11.53  |
| 2025-08 | 2.7%   | 45.2%  | 16.2%  | 35.9%  | 32,954    | $375,747     | $11.40  |
| 2025-09 | 0.0%   | 12.4%  | 37.3%  | 50.3%  | 29,866    | $339,872     | $11.38  |
| 2025-10 | 0.0%   | 16.3%  | 43.6%  | 40.1%  | 30,674    | $359,762     | $11.73  |
| 2025-11 | 0.0%   | 16.6%  | 33.3%  | 50.1%  | 56,505    | $666,832     | $11.80  |
| 2025-12 | 0.0%   | 5.0%   | 46.5%  | 48.5%  | 116,706   | $1,211,668   | $10.38  |

**Key observations:**
- Jan-Jun 2025: DHL (~13-16%) + FedEx (~84-87%) only
- Jul 2025: USPS and OnTrac start ramping up
- Sep 2025 onwards: OnTrac becomes dominant (~40-50%), USPS grows to ~33-47%, FedEx drops to ~5-16%
- Dec 2025: Peak volume (117K) with lowest avg cost ($10.38) - shift to cheaper carriers
- USPS consistently cheapest at $7-8 avg; OnTrac and FedEx both around $12-13 avg

### Comparison: 100% Single Carrier Scenarios

| Carrier       | Serviceable   | Coverage   | Total Cost         | Avg Cost   |
|---------------|---------------|------------|--------------------|------------|
| **Current**   | **539,917**   | **100.0%** | **$6,072,061.73**  | **$11.25** |
| Maersk        | 539,917       | 100.0%     | $5,686,413.05      | $10.53     |
| FedEx         | 539,917       | 100.0%     | $6,417,722.16      | $11.89     |
| USPS          | 539,917       | 100.0%     | $14,016,877.51     | $25.96     |
| OnTrac        | 346,822       | 64.2%      | $3,817,595.32      | $11.01     |
| P2P           | 279,534       | 51.8%      | $2,972,918.40      | $10.64     |

**Note:** OnTrac and P2P have partial geographic coverage. Costs shown are only for shipments they can service.

**Note on Maersk:** Maersk is the cheapest full-coverage carrier at $5,686,413 -- $385,649 less than the current mix ($6,072,062). See other scenarios for Maersk-optimized analysis.

**Note on FedEx 100%:** The FedEx single-carrier cost ($6.42M) also reflects the 16% earned discount. At 100% FedEx volume, the earned discount tier would likely be higher (potentially 18-20%), which would reduce this cost. See Scenario 3 for FedEx-optimized analysis.

## Key Findings

1. **Current mix baseline**: $6.07M for 540K shipments ($11.25 avg)

2. **2026 rates are 7.2% lower** than 2025 actuals for matched shipments ($6.07M vs $6.54M), primarily driven by the SmartPost rate correction, partially offset by the earned discount adjustment

3. **FedEx dominates volume** at 49.6% of shipments, accounting for 56.1% of total cost

4. **SmartPost is significantly cheaper than Home Delivery**: FXESPPS shipments average $9.56 vs FXEHD at $14.78 - the corrected SmartPost pricing reduced the FedEx carrier total substantially

5. **Full-coverage carrier ranking** (can service all shipments):
   - Maersk: $10.53 avg (cheapest full-coverage)
   - Current Mix: $11.25 avg
   - FedEx: $11.89 avg
   - USPS: $25.96 avg (penalized by heavy/oversize packages)

6. **Partial-coverage carriers** (cannot service all shipments):
   - OnTrac: 64.2% coverage, $11.01 avg (West region only)
   - P2P: 51.8% coverage, $10.64 avg (limited ZIP coverage)

7. **Weight-based pricing impact**: Shipments 5-10 lbs cost 2.6x more than 0-1 lb shipments

8. **Phoenix is the largest cost center** at 47.7% of shipments and 52.7% of costs

9. **FedEx earned discount sensitivity**: The 2-point adjustment from 18% to 16% adds ~$137K to the baseline. Negotiating a higher earned discount tier would directly reduce the current mix cost.

## Cost Imputations

| Item                              | Count    | Method                              |
|-----------------------------------|----------|-------------------------------------|
| DHL eCommerce America             | 40,157   | $6.00/shipment flat estimate        |
| OnTrac OML/LPS excluded          | 197      | Removed from all calculations       |
| FedEx earned discount adjustment  | 267,614  | 1.0541x multiplier (16% vs 18%)    |

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
*Dataset: Matched-only (539,917 shipments with both calculated and actual invoice data)*
*FedEx earned discount: adjusted from 18% (baked in rate tables) to 16% (actual tier for current mix volume)*
