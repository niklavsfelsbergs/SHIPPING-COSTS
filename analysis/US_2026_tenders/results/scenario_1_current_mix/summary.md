# Scenario 1: Current Carrier Mix

## Executive Summary

This scenario establishes the baseline shipping cost using the current carrier routing strategy. Using calculated/expected costs from 2026 rate tables (not invoice actuals), the current carrier mix achieves a total cost of **$5,833,893.77** for 558,013 shipments.

## Calculator Validation: 2025 Actuals vs 2026 Calculated

For 539,941 matched shipments (96.8% match rate), comparing what we actually paid in 2025 against what the 2026 calculator predicts:

| Carrier    | Matched     | 2025 Actual       | 2026 Calculated   | Difference   |
|------------|-------------|-------------------|-------------------|--------------|
| FedEx      | 267,638     | $4,040,733.33     | $2,931,741.21     | -27.4%       |
| OnTrac     | 128,982     | $1,447,346.40     | $1,618,560.51     | +11.8%       |
| USPS       | 103,164     | $812,301.21       | $806,305.23       | -0.7%        |
| DHL        | 40,157      | $240,942.00       | $240,942.00       | 0.0%         |
| **TOTAL**  | **539,941** | **$6,541,322.94** | **$5,597,548.95** | **-14.4%**   |

Overall 2026 calculated rates are **14.4% lower** than 2025 actuals. FedEx shows the largest decrease (-27.4%), driven by the SmartPost fix (SmartPost now correctly uses Ground Economy rates instead of Home Delivery) plus updated 2026 surcharge discounts. OnTrac calculated is 11.8% higher than actuals (2026 rate increases). USPS is within 1% of actuals.

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
| **Total Expected Cost**     | **$5,833,893.77**    |
| Total Shipments             | 558,013              |
| Non-DHL Shipments           | 517,856 (92.8%)      |
| DHL Shipments               | 40,157 (7.2%)        |
| DHL Estimated Cost          | $240,942.00          |
| Average Cost per Shipment   | $10.45               |

### Breakdown by Carrier

| Carrier         | Shipments   | Share    | Total Cost        | Avg Cost   |
|-----------------|-------------|----------|-------------------|------------|
| FedEx           | 273,941     | 49.1%    | $3,023,125.64     | $11.04     |
| OnTrac          | 137,764     | 24.7%    | $1,736,637.92     | $12.61     |
| USPS            | 106,151     | 19.0%    | $833,188.21       | $7.85      |
| DHL             | 40,157      | 7.2%     | $240,942.00       | $6.00      |

### Breakdown by Provider (Detailed)

| Provider                  | Shipments   | Share    | Total Cost        | Avg Cost   |
|---------------------------|-------------|----------|-------------------|------------|
| FXEHD (Home Delivery)     | 165,565     | 29.7%    | $1,995,041.05     | $12.05     |
| ONTRAC                    | 137,764     | 24.7%    | $1,736,637.92     | $12.61     |
| FXESPPS (SmartPost)       | 107,197     | 19.2%    | $1,014,190.74     | $9.46      |
| USPS                      | 106,151     | 19.0%    | $833,188.21       | $7.85      |
| DHL ECOMMERCE AMERICA     | 40,157      | 7.2%     | $240,942.00       | $6.00      |
| FXEGRD (Ground)           | 850         | 0.2%     | $8,873.39         | $10.44     |
| FXE2D (2Day)              | 326         | 0.1%     | $4,973.01         | $15.25     |
| Other FedEx               | 3           | 0.0%     | $47.45            | $15.82     |

### Breakdown by Weight

| Weight Bracket   | Shipments   | Share    | Total Cost        | Avg Cost   |
|------------------|-------------|----------|-------------------|------------|
| 0-1 lbs          | 106,089     | 19.0%    | $744,299.23       | $7.02      |
| 1-5 lbs          | 294,376     | 52.8%    | $2,915,031.48     | $9.90      |
| 5-10 lbs         | 87,810      | 15.7%    | $1,324,074.08     | $15.08     |
| 10-20 lbs        | 24,007      | 4.3%     | $461,491.68       | $19.22     |
| 20-30 lbs        | 3,671       | 0.7%     | $87,815.77        | $23.92     |
| 30+ lbs          | 1,903       | 0.3%     | $60,239.53        | $31.66     |

### Breakdown by Production Site

| Site       | Shipments   | Share    | Total Cost        | Avg Cost   |
|------------|-------------|----------|-------------------|------------|
| Phoenix    | 269,059     | 48.2%    | $3,128,352.91     | $11.63     |
| Miami      | 129,396     | 23.2%    | $1,321,119.45     | $10.21     |
| Columbus   | 119,400     | 21.4%    | $1,143,471.59     | $9.58      |
| Szczecin   | 1           | 0.0%     | $7.83             | $7.83      |

### Monthly Breakdown

| Month   | DHL    | FedEx  | USPS   | OnTrac | Total     | Total Cost   | Avg     |
|---------|--------|--------|--------|--------|-----------|--------------|---------|
| 2025-01 | 16.1%  | 83.9%  | 0.0%   | 0.0%   | 45,019    | $459,357     | $10.20  |
| 2025-02 | 12.8%  | 87.2%  | 0.0%   | 0.0%   | 41,368    | $417,833     | $10.10  |
| 2025-03 | 16.0%  | 84.0%  | 0.0%   | 0.0%   | 33,249    | $339,061     | $10.20  |
| 2025-04 | 14.6%  | 85.4%  | 0.0%   | 0.0%   | 37,322    | $379,834     | $10.18  |
| 2025-05 | 12.6%  | 87.4%  | 0.0%   | 0.0%   | 48,154    | $489,657     | $10.17  |
| 2025-06 | 15.1%  | 84.9%  | 0.0%   | 0.0%   | 37,955    | $386,463     | $10.18  |
| 2025-07 | 11.5%  | 72.5%  | 2.1%   | 13.9%  | 36,242    | $380,778     | $10.51  |
| 2025-08 | 2.7%   | 44.9%  | 16.1%  | 36.4%  | 33,696    | $361,530     | $10.73  |
| 2025-09 | 0.0%   | 12.4%  | 37.1%  | 50.5%  | 30,399    | $336,160     | $11.06  |
| 2025-10 | 0.0%   | 14.3%  | 38.8%  | 46.9%  | 35,375    | $405,723     | $11.47  |
| 2025-11 | 0.0%   | 16.4%  | 33.9%  | 49.7%  | 58,007    | $655,907     | $11.31  |
| 2025-12 | 0.0%   | 5.1%   | 45.6%  | 49.3%  | 121,227   | $1,221,592   | $10.08  |

**Key observations:**
- Jan-Jun 2025: DHL (~15%) + FedEx (~85%) only
- Jul 2025: USPS and OnTrac start ramping up
- Sep 2025 onwards: OnTrac becomes dominant (~50%), USPS grows to ~37%, FedEx drops to ~12-16%
- Dec 2025: Peak volume (121K) with lowest avg cost ($10.08) - shift to cheaper carriers
- USPS consistently cheapest at $7-8 avg; OnTrac most expensive at $11-14 avg

### Comparison: 100% Single Carrier Scenarios

| Carrier       | Serviceable   | Coverage   | Total Cost        | Avg Cost   |
|---------------|---------------|------------|-------------------|------------|
| **Current**   | **558,013**   | **100.0%** | **$5,833,893.77** | **$10.45** |
| FedEx         | 558,013       | 100.0%     | $5,889,065.68     | $10.55     |
| Maersk        | 558,013       | 100.0%     | $6,041,478.28     | $10.83     |
| USPS          | 558,013       | 100.0%     | $14,835,549.16    | $26.59     |
| OnTrac        | 360,151       | 64.5%      | $3,998,470.55     | $11.10     |
| P2P           | 289,272       | 51.8%      | $3,098,915.03     | $10.71     |

**Note:** OnTrac and P2P have partial geographic coverage. Costs shown are only for shipments they can service.

## Key Findings

1. **Current mix baseline**: $5.83M for 558K shipments ($10.45 avg)

2. **2026 rates are 14.4% lower** than 2025 actuals for matched shipments ($5.60M vs $6.54M), primarily driven by the SmartPost rate correction

3. **FedEx dominates volume** at 49.1% of shipments, accounting for 51.8% of total cost

4. **SmartPost is significantly cheaper than Home Delivery**: FXESPPS shipments average $9.46 vs FXEHD at $12.05 - the corrected SmartPost pricing reduced the FedEx carrier total by ~$604K

5. **Full-coverage carrier ranking** (can service all shipments):
   - Current Mix: $10.45 avg (cheapest)
   - FedEx: $10.55 avg
   - Maersk: $10.83 avg
   - USPS: $26.59 avg (penalized by heavy/oversize packages)

6. **Partial-coverage carriers** (cannot service all shipments):
   - OnTrac: 64.5% coverage, $11.10 avg (West region only)
   - P2P: 51.8% coverage, $10.71 avg (limited ZIP coverage)

7. **Weight-based pricing impact**: Shipments 5-10 lbs cost 2.1x more than 0-1 lb shipments

8. **Phoenix is the largest cost center** at 48.2% of shipments and 53.6% of costs

## Cost Imputations

| Item                              | Count    | Method                              |
|-----------------------------------|----------|-------------------------------------|
| DHL eCommerce America             | 40,157   | $6.00/shipment flat estimate        |
| OnTrac OML/LPS excluded          | 197      | Removed from all calculations       |

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
