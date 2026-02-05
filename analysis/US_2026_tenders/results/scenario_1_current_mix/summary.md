# Scenario 1: Current Carrier Mix

## Executive Summary

This scenario establishes the baseline shipping cost using the current carrier routing strategy. Using calculated/expected costs from 2026 rate tables (not invoice actuals), the current carrier mix achieves a total cost of **$6,389,595.72** for 558,210 shipments.

## Methodology

**Data Source:** `shipments_unified.parquet` - shipment-level data with costs calculated for each carrier

**Cost Calculation:**
- Each shipment uses the cost from its actual carrier (recorded in `pcs_shipping_provider`)
- FedEx shipments use FedEx calculated costs
- OnTrac shipments use OnTrac calculated costs
- USPS shipments use USPS calculated costs
- DHL shipments use **$6.00 estimated cost** (no DHL calculator available)
- 144 OnTrac shipments to "non-serviceable" ZIPs imputed with packagetype average

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
| **Total Expected Cost**     | **$6,389,595.72**    |
| Total Shipments             | 558,210              |
| Non-DHL Shipments           | 518,053 (92.8%)      |
| DHL Shipments               | 40,157 (7.2%)        |
| DHL Estimated Cost          | $240,942.00          |
| Average Cost per Shipment   | $11.45               |

### Breakdown by Carrier

| Carrier         | Shipments   | Share    | Total Cost        | Avg Cost   |
|-----------------|-------------|----------|-------------------|------------|
| FedEx           | 273,941     | 49.1%    | $3,531,655.39     | $12.89     |
| OnTrac          | 137,961     | 24.7%    | $1,821,035.29     | $13.20     |
| USPS            | 106,151     | 19.0%    | $795,963.04       | $7.50      |
| DHL             | 40,157      | 7.2%     | $240,942.00       | $6.00      |

### Breakdown by Provider (Detailed)

| Provider                  | Shipments   | Share    | Total Cost        | Avg Cost   |
|---------------------------|-------------|----------|-------------------|------------|
| FXEHD (Home Delivery)     | 165,565     | 29.7%    | $2,485,410.93     | $15.01     |
| ONTRAC                    | 137,961     | 24.7%    | $1,821,035.29     | $13.20     |
| FXESPPS (SmartPost)       | 107,197     | 19.2%    | $1,029,712.98     | $9.61      |
| USPS                      | 106,151     | 19.0%    | $795,963.04       | $7.50      |
| DHL ECOMMERCE AMERICA     | 40,157      | 7.2%     | $240,942.00       | $6.00      |
| FXEGRD (Ground)           | 850         | 0.2%     | $10,849.20        | $12.76     |
| FXE2D (2Day)              | 326         | 0.1%     | $5,616.81         | $17.23     |
| Other FedEx               | 3           | 0.0%     | $65.47            | $21.82     |

### Breakdown by Weight

| Weight Bracket   | Shipments   | Share    | Total Cost        | Avg Cost   |
|------------------|-------------|----------|-------------------|------------|
| 0-1 lbs          | 106,094     | 19.0%    | $753,284.27       | $7.10      |
| 1-5 lbs          | 294,429     | 52.7%    | $3,007,944.63     | $10.22     |
| 5-10 lbs         | 87,915      | 15.7%    | $1,626,825.18     | $18.50     |
| 10-20 lbs        | 24,028      | 4.3%     | $595,388.33       | $24.78     |
| 20-30 lbs        | 3,677       | 0.7%     | $100,023.68       | $27.20     |
| 30+ lbs          | 1,910       | 0.3%     | $65,187.63        | $34.13     |

### Breakdown by Production Site

| Site       | Shipments   | Share    | Total Cost        | Avg Cost   |
|------------|-------------|----------|-------------------|------------|
| Phoenix    | 269,095     | 48.2%    | $3,406,964.06     | $12.66     |
| Miami      | 129,396     | 23.2%    | $1,509,974.47     | $11.67     |
| Columbus   | 119,561     | 21.4%    | $1,231,706.16     | $10.30     |

### Monthly Breakdown (by order created date)

|         | Carrier Share (%)                 | Carrier Avg Cost ($)                  |           |              |        |
| Month   | DHL    | FedEx  | USPS   | OnTrac | DHL   | FedEx  | USPS   | OnTrac | Total   | Total Cost   | Avg    |
|---------|--------|--------|--------|--------|-------|--------|--------|--------|---------|--------------|--------|
| 2025-01 | 16.1%  | 83.9%  | 0.0%   | 0.0%   | $6.00 | $13.02 | -      | -      | 45,019  | $535,072     | $11.89 |
| 2025-02 | 12.8%  | 87.2%  | 0.0%   | 0.0%   | $6.00 | $12.39 | -      | -      | 41,368  | $478,909     | $11.58 |
| 2025-03 | 16.0%  | 84.0%  | 0.0%   | 0.0%   | $6.00 | $12.66 | -      | -      | 33,249  | $385,462     | $11.59 |
| 2025-04 | 14.6%  | 85.4%  | 0.0%   | 0.0%   | $6.00 | $12.32 | -      | -      | 37,322  | $425,369     | $11.40 |
| 2025-05 | 12.6%  | 87.4%  | 0.0%   | 0.0%   | $6.00 | $12.07 | -      | -      | 48,154  | $544,291     | $11.30 |
| 2025-06 | 15.1%  | 84.9%  | 0.0%   | 0.0%   | $6.00 | $12.33 | -      | -      | 37,955  | $431,804     | $11.38 |
| 2025-07 | 11.5%  | 72.5%  | 2.1%   | 13.9%  | $6.00 | $12.13 | $8.08  | $13.08 | 36,245  | $415,715     | $11.47 |
| 2025-08 | 2.7%   | 44.9%  | 16.1%  | 36.4%  | $6.00 | $12.82 | $8.92  | $11.25 | 33,706  | $385,692     | $11.44 |
| 2025-09 | 0.0%   | 12.4%  | 37.0%  | 50.6%  | -     | $16.55 | $7.76  | $12.99 | 30,425  | $349,774     | $11.50 |
| 2025-10 | 0.0%   | 14.3%  | 38.7%  | 47.0%  | -     | $16.19 | $7.49  | $15.30 | 35,439  | $439,554     | $12.40 |
| 2025-11 | 0.0%   | 16.3%  | 33.9%  | 49.7%  | -     | $15.25 | $7.67  | $14.19 | 58,061  | $705,624     | $12.15 |
| 2025-12 | 0.0%   | 5.1%   | 45.6%  | 49.3%  | -     | $22.37 | $7.24  | $12.60 | 121,267 | $1,292,331   | $10.66 |

**Key observations:**
- Jan-Jun 2025: DHL (~15%) + FedEx (~85%) only
- Jul 2025: USPS and OnTrac start ramping up
- Sep 2025 onwards: OnTrac becomes dominant (~50%), USPS grows to ~37%, FedEx drops to ~12-16%
- Dec 2025: Peak volume (121K) with lowest avg cost ($10.66) - FedEx avg spikes to $22 (heavier packages remaining)
- USPS consistently cheapest at $7-8 avg; FedEx avg increases as lighter packages shift to other carriers

### Comparison: 100% Single Carrier Scenarios

| Carrier       | Serviceable   | Coverage   | Total Cost        | Avg Cost   |
|---------------|---------------|------------|-------------------|------------|
| **Current**   | **558,210**   | **100.0%** | **$6,389,595.72** | **$11.45** |
| OnTrac        | 360,348       | 64.6%      | $4,058,854.37     | $11.26     |
| USPS          | 558,210       | 100.0%     | $8,195,287.24     | $14.68     |
| FedEx         | 558,210       | 100.0%     | $6,920,940.31     | $12.40     |
| P2P           | 289,429       | 51.8%      | $3,103,799.20     | $10.72     |
| Maersk        | 558,210       | 100.0%     | $6,444,524.54     | $11.54     |

**Note:** OnTrac and P2P have partial geographic coverage. Costs shown are only for shipments they can service. Non-serviceable shipments have null costs.

## Key Findings

1. **Current mix baseline**: $6.39M for 558K shipments ($11.45 avg)

2. **FedEx dominates volume** at 49.1% of shipments, accounting for 55.3% of total cost

3. **USPS is cost-efficient** at $7.50 avg (but $14.68 if used for all shipments due to weight/size mix)

4. **Full-coverage carrier ranking** (can service all shipments):
   - Maersk: $11.54 avg (cheapest)
   - FedEx: $12.40 avg
   - USPS: $14.68 avg

5. **Partial-coverage carriers** (cannot service all shipments):
   - OnTrac: 64.6% coverage, $11.26 avg (West region only)
   - P2P: 51.8% coverage, $10.72 avg (limited ZIP coverage)

6. **Weight-based pricing impact**: Shipments 5-10 lbs cost 2.6x more than 0-1 lb shipments

7. **Phoenix is the largest cost center** at 48.2% of shipments and 53.3% of costs

## Cost Imputations

| Item                              | Count    | Method                              |
|-----------------------------------|----------|-------------------------------------|
| DHL eCommerce America             | 40,157   | $6.00/shipment flat estimate        |
| OnTrac to non-serviceable ZIPs    | 144      | Average OnTrac cost by packagetype  |

## Files Generated

- `breakdown_by_carrier.csv` - Carrier-level summary
- `breakdown_by_provider.csv` - Provider-level detail (includes FedEx service types)
- `breakdown_by_packagetype.csv` - Full package type breakdown
- `breakdown_by_weight.csv` - Weight bracket analysis
- `breakdown_by_site.csv` - Production site summary
- `breakdown_by_month.csv` - Monthly carrier split with costs
- `comparison_single_carrier.csv` - Single carrier scenario costs

---
*Generated: February 2026*
*Data Period: 2025 shipment volumes with 2026 calculated rates*
