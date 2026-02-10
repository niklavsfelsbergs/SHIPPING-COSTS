# Scenario 1: Current Carrier Mix

## Executive Summary

This scenario establishes the baseline shipping cost using the current carrier routing strategy. Using calculated/expected costs from 2026 rate tables (not invoice actuals), the current carrier mix achieves a total cost of **$6,435,014.81** for 558,210 shipments.

## Methodology

**Data Source:** `shipments_unified.parquet` - shipment-level data with costs calculated for each carrier

**Cost Calculation:**
- Each shipment uses the cost from its actual carrier (recorded in `pcs_shipping_provider`)
- FedEx shipments use FedEx calculated costs (optimal of Home Delivery vs SmartPost)
- OnTrac shipments use OnTrac calculated costs
- USPS shipments use USPS calculated costs
- DHL shipments use **$6.00 estimated cost** (no DHL calculator available)

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
| **Total Expected Cost**     | **$6,435,014.81**    |
| Total Shipments             | 558,210              |
| Non-DHL Shipments           | 518,053 (92.8%)      |
| DHL Shipments               | 40,157 (7.2%)        |
| DHL Estimated Cost          | $240,942.00          |
| Average Cost per Shipment   | $11.53               |

### Breakdown by Carrier

| Carrier         | Shipments   | Share    | Total Cost        | Avg Cost   |
|-----------------|-------------|----------|-------------------|------------|
| FedEx           | 273,941     | 49.1%    | $3,619,641.60     | $13.21     |
| OnTrac          | 137,961     | 24.7%    | $1,741,243.00     | $12.62     |
| USPS            | 106,151     | 19.0%    | $833,188.21       | $7.85      |
| DHL             | 40,157      | 7.2%     | $240,942.00       | $6.00      |

### Breakdown by Provider (Detailed)

| Provider                  | Shipments   | Share    | Total Cost        | Avg Cost   |
|---------------------------|-------------|----------|-------------------|------------|
| FXEHD (Home Delivery)     | 165,565     | 29.7%    | $2,485,410.93     | $15.01     |
| ONTRAC                    | 137,961     | 24.7%    | $1,741,243.00     | $12.62     |
| FXESPPS (SmartPost)       | 107,197     | 19.2%    | $1,118,797.54     | $10.44     |
| USPS                      | 106,151     | 19.0%    | $833,188.21       | $7.85      |
| DHL ECOMMERCE AMERICA     | 40,157      | 7.2%     | $240,942.00       | $6.00      |
| FXEGRD (Ground)           | 850         | 0.2%     | $9,750.85         | $11.47     |
| FXE2D (2Day)              | 326         | 0.1%     | $5,616.81         | $17.23     |
| Other FedEx               | 3           | 0.0%     | $65.47            | $21.82     |

### Breakdown by Weight

| Weight Bracket   | Shipments   | Share    | Total Cost        | Avg Cost   |
|------------------|-------------|----------|-------------------|------------|
| 0-1 lbs          | 106,094     | 19.0%    | $791,392.27       | $7.46      |
| 1-5 lbs          | 294,429     | 52.7%    | $3,067,110.89     | $10.42     |
| 5-10 lbs         | 87,915      | 15.7%    | $1,594,156.67     | $18.13     |
| 10-20 lbs        | 24,028      | 4.3%     | $580,802.63       | $24.17     |
| 20-30 lbs        | 3,677       | 0.7%     | $97,306.60        | $26.46     |
| 30+ lbs          | 1,910       | 0.3%     | $63,303.76        | $33.14     |

### Breakdown by Production Site

| Site       | Shipments   | Share    | Total Cost        | Avg Cost   |
|------------|-------------|----------|-------------------|------------|
| Phoenix    | 269,095     | 48.2%    | $3,421,867.02     | $12.72     |
| Miami      | 129,396     | 23.2%    | $1,563,517.76     | $12.08     |
| Columbus   | 119,561     | 21.4%    | $1,208,679.00     | $10.11     |

### Monthly Breakdown

| Month   | DHL    | FedEx  | USPS   | OnTrac | Total     | Total Cost   | Avg     |
|---------|--------|--------|--------|--------|-----------|--------------|---------|
| 2025-01 | 16.1%  | 83.9%  | 0.0%   | 0.0%   | 45,019    | $554,821     | $12.32  |
| 2025-02 | 12.8%  | 87.2%  | 0.0%   | 0.0%   | 41,368    | $485,163     | $11.73  |
| 2025-03 | 16.0%  | 84.0%  | 0.0%   | 0.0%   | 33,249    | $392,153     | $11.79  |
| 2025-04 | 14.6%  | 85.4%  | 0.0%   | 0.0%   | 37,322    | $436,665     | $11.70  |
| 2025-05 | 12.6%  | 87.4%  | 0.0%   | 0.0%   | 48,154    | $560,347     | $11.64  |
| 2025-06 | 15.1%  | 84.9%  | 0.0%   | 0.0%   | 37,955    | $444,198     | $11.70  |
| 2025-07 | 11.5%  | 72.5%  | 2.1%   | 13.9%  | 36,245    | $425,710     | $11.75  |
| 2025-08 | 2.7%   | 44.9%  | 16.1%  | 36.4%  | 33,706    | $392,661     | $11.65  |
| 2025-09 | 0.0%   | 12.4%  | 37.0%  | 50.6%  | 30,425    | $350,570     | $11.52  |
| 2025-10 | 0.0%   | 14.3%  | 38.7%  | 47.0%  | 35,439    | $427,536     | $12.06  |
| 2025-11 | 0.0%   | 16.3%  | 33.9%  | 49.7%  | 58,061    | $692,591     | $11.93  |
| 2025-12 | 0.0%   | 5.1%   | 45.6%  | 49.3%  | 121,267   | $1,272,599   | $10.49  |

**Key observations:**
- Jan-Jun 2025: DHL (~15%) + FedEx (~85%) only
- Jul 2025: USPS and OnTrac start ramping up
- Sep 2025 onwards: OnTrac becomes dominant (~50%), USPS grows to ~37%, FedEx drops to ~12-16%
- Dec 2025: Peak volume (121K) with lowest avg cost ($10.49) - shift to cheaper carriers
- USPS consistently cheapest at $7-8 avg; FedEx Home Delivery most expensive at $15+ avg

### Comparison: 100% Single Carrier Scenarios

| Carrier       | Serviceable   | Coverage   | Total Cost        | Avg Cost   |
|---------------|---------------|------------|-------------------|------------|
| **Current**   | **558,210**   | **100.0%** | **$6,435,014.81** | **$11.53** |
| OnTrac        | 360,348       | 64.6%      | $4,003,075.63     | $11.11     |
| USPS          | 558,210       | 100.0%     | $14,855,381.21    | $26.61     |
| FedEx         | 558,210       | 100.0%     | $7,008,926.52     | $12.56     |
| P2P           | 289,429       | 51.8%      | $3,103,799.20     | $10.72     |
| Maersk        | 558,210       | 100.0%     | $6,047,014.02     | $10.83     |

**Note:** OnTrac and P2P have partial geographic coverage. Costs shown are only for shipments they can service.

### 2025 Actuals vs 2026 Calculated Rates

This comparison shows what we paid in 2025 vs what we would pay using 2026 rate tables for matched shipments.

**Matching Summary by Carrier:**

| Carrier    | Total       | Matched     | Match %   |
|------------|-------------|-------------|-----------|
| OnTrac     | 137,961     | 129,158     | 93.6%     |
| USPS       | 106,151     | 103,164     | 97.2%     |
| FedEx      | 273,941     | 97,601      | 35.6%     |
| DHL        | 40,157      | 40,157      | 100.0%    |
| **TOTAL**  | **558,210** | **370,080** | **66.3%** |

**Note:** DHL uses $6.00 flat estimate for both actual and calculated (no invoice data available).

**Cost Comparison (matched shipments only):**

| Metric                    | Value              |
|---------------------------|--------------------|
| **2025 Actual Total**     | **$4,606,141.50**  |
| **2026 Calculated Total** | **$4,189,118.90**  |
| **Difference**            | **-$417,022.60 (-9.1%)** |

**By Carrier:**

| Carrier    | Matched     | 2025 Actual       | 2026 Calculated   | Diff %    |
|------------|-------------|-------------------|-------------------|-----------|
| OnTrac     | 129,158     | $1,667,784.95     | $1,622,674.50     | -2.7%     |
| USPS       | 103,164     | $812,301.21       | $806,305.23       | -0.7%     |
| FedEx      | 97,601      | $1,885,113.34     | $1,519,197.17     | -19.4%    |
| DHL        | 40,157      | $240,942.00       | $240,942.00       | 0.0%      |

**Key observations:**
- Overall 2026 rates are **9.1% lower** than 2025 actuals for matched shipments
- **FedEx shows the largest decrease (-19.4%)** - this is the expected cost decrease from new 2026 rates
- OnTrac and USPS show smaller decreases (-2.7% and -0.7% respectively)
- DHL uses the same $6.00 flat estimate for both periods (no change)

**Note:** FedEx has lowest match rate (35.6%) due to incomplete actuals upload for early 2025 period. OnTrac and USPS have high match rates (93%+).

## Key Findings

1. **Current mix baseline**: $6.44M for 558K shipments ($11.53 avg)

2. **2026 rates are 9.1% lower** than 2025 actuals for matched shipments ($4.2M vs $4.6M)

3. **FedEx dominates volume** at 49.1% of shipments, accounting for 56.3% of total cost

4. **USPS is cost-efficient** at $7.85 avg for current mix, but $26.61 if used for all shipments (due to weight/size penalties)

5. **Full-coverage carrier ranking** (can service all shipments):
   - Maersk: $10.83 avg (cheapest)
   - FedEx: $12.56 avg
   - USPS: $26.61 avg (penalized by heavy/oversize packages)

6. **Partial-coverage carriers** (cannot service all shipments):
   - OnTrac: 64.6% coverage, $11.11 avg (West region only)
   - P2P: 51.8% coverage, $10.72 avg (limited ZIP coverage)

7. **Weight-based pricing impact**: Shipments 5-10 lbs cost 2.4x more than 0-1 lb shipments

8. **Phoenix is the largest cost center** at 48.2% of shipments and 53.2% of costs

## Cost Imputations

| Item                              | Count    | Method                              |
|-----------------------------------|----------|-------------------------------------|
| DHL eCommerce America             | 40,157   | $6.00/shipment flat estimate        |

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
