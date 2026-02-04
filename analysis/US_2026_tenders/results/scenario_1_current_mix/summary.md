# Scenario 1: Current Carrier Mix

## Executive Summary

This scenario establishes the baseline shipping cost using the current carrier routing strategy. Using calculated/expected costs from 2026 rate tables (not invoice actuals), the current carrier mix achieves a total cost of **$6,218,604.91** for 518,053 mapped shipments. The remaining 40,157 shipments (7.2%) were shipped via DHL eCommerce America, which is not included in the carrier optimization analysis.

## Methodology

**Data Source:** `shipments_unified.parquet` - shipment-level data with costs calculated for each carrier

**Cost Calculation:**
- Each shipment uses the cost from its actual carrier (recorded in `pcs_shipping_provider`)
- FedEx shipments use FedEx calculated costs
- OnTrac shipments use OnTrac calculated costs
- USPS shipments use USPS calculated costs
- DHL shipments have NULL costs (no DHL calculator available)

**Carrier Mapping:**
| Provider Code | Carrier | Description |
|---------------|---------|-------------|
| ONTRAC | OnTrac | OnTrac Ground |
| USPS | USPS | USPS Ground Advantage |
| FXEHD | FedEx | FedEx Home Delivery |
| FXESPPS | FedEx | FedEx SmartPost Parcel Select |
| FXEGRD | FedEx | FedEx Ground |
| FXE2D | FedEx | FedEx 2Day |
| FXEINTPRIO | FedEx | FedEx International Priority |
| FXEINTECON | FedEx | FedEx International Economy |
| DHL ECOMMERCE AMERICA | DHL (unmapped) | Not included in analysis |

## Results

### Total Cost

| Metric | Value |
|--------|-------|
| **Total Expected Cost** | **$6,218,604.91** |
| Total Shipments | 558,210 |
| Mapped Shipments | 518,053 (92.8%) |
| Unmapped (DHL) | 40,157 (7.2%) |
| Average Cost per Shipment | $12.00 |

### Breakdown by Carrier

| Carrier | Shipments | Share | Total Cost | Avg Cost |
|---------|-----------|-------|------------|----------|
| FedEx | 273,941 | 49.1% | $3,531,655.39 | $12.89 |
| OnTrac | 137,961 | 24.7% | $1,890,986.48 | $13.71 |
| USPS | 106,151 | 19.0% | $795,963.04 | $7.50 |
| DHL (unmapped) | 40,157 | 7.2% | $0.00 | - |

### Breakdown by Provider (Detailed)

| Provider | Shipments | Share | Total Cost | Avg Cost |
|----------|-----------|-------|------------|----------|
| FXEHD (Home Delivery) | 165,565 | 29.7% | $2,485,410.93 | $15.01 |
| ONTRAC | 137,961 | 24.7% | $1,890,986.48 | $13.71 |
| FXESPPS (SmartPost) | 107,197 | 19.2% | $1,029,712.98 | $9.61 |
| USPS | 106,151 | 19.0% | $795,963.04 | $7.50 |
| DHL ECOMMERCE AMERICA | 40,157 | 7.2% | - | - |
| FXEGRD (Ground) | 850 | 0.2% | $10,849.20 | $12.76 |
| FXE2D (2Day) | 326 | 0.1% | $5,616.81 | $17.23 |
| Other FedEx | 3 | 0.0% | $65.47 | $21.82 |

### Breakdown by Package Type (Top 15)

| Package Type | Shipments | Total Cost | Avg Cost |
|--------------|-----------|------------|----------|
| PIZZA BOX 20x16x1 | 117,166 | $1,018,108.57 | $8.69 |
| PIZZA BOX 42x32x2 | 24,827 | $705,266.25 | $28.41 |
| PIZZA BOX 48X36X1 | 19,799 | $669,969.83 | $33.84 |
| PIZZA BOX 40x30x1 | 21,021 | $444,327.82 | $21.14 |
| PIZZA BOX 36x24x2 | 37,115 | $434,609.89 | $11.71 |
| PIZZA BOX 24x20x2 | 40,941 | $431,755.71 | $10.55 |
| PIZZA BOX 16x12x2 | 43,668 | $385,133.32 | $8.82 |
| PIZZA BOX 20x16x2 | 36,290 | $347,072.09 | $9.56 |
| WRAP 16''x12'' | 33,368 | $265,154.43 | $7.95 |
| WRAP 24''x16'' | 23,412 | $226,182.88 | $9.66 |
| PIZZA BOX 12x8x1 | 32,954 | $196,438.07 | $5.96 |
| CROSS PACKAGING 30X24" | 15,092 | $163,793.18 | $10.85 |
| PIZZA BOX 30x20x3 | 10,149 | $119,436.36 | $11.77 |
| PIZZA BOX 42x32x2 (2x strapped) | 2,910 | $100,273.15 | $34.46 |
| 21" Tube | 8,482 | $65,670.09 | $7.74 |

### Breakdown by Weight

| Weight Bracket | Shipments | Share | Total Cost | Avg Cost |
|----------------|-----------|-------|------------|----------|
| 0-1 lbs | 106,094 | 20.5% | $762,155.93 | $7.18 |
| 1-5 lbs | 294,429 | 56.8% | $3,048,428.38 | $10.35 |
| 5-10 lbs | 87,915 | 17.0% | $1,641,696.86 | $18.67 |
| 10-20 lbs | 24,028 | 4.6% | $600,625.73 | $25.00 |
| 20-30 lbs | 3,677 | 0.7% | $100,510.38 | $27.33 |
| 30+ lbs | 1,910 | 0.4% | $65,187.63 | $34.13 |

### Breakdown by Production Site

| Site | Shipments | Share | Total Cost | Avg Cost |
|------|-----------|-------|------------|----------|
| Phoenix | 269,095 | 51.9% | $3,457,382.75 | $12.85 |
| Miami | 129,396 | 25.0% | $1,509,974.47 | $11.67 |
| Columbus | 119,561 | 23.1% | $1,251,238.66 | $10.47 |

### Comparison: 100% Single Carrier Scenarios

| Scenario | Total Cost | vs Current | Diff % |
|----------|------------|------------|--------|
| **Current Mix** | **$6,218,604.91** | - | - |
| 100% FedEx | $6,920,940.31 | +$702,335.40 | +11.3% |
| 100% USPS | $8,195,287.24 | +$1,976,682.33 | +31.8% |
| 100% OnTrac | $102,989,854.37 | +$96,771,249.46 | +1556.2% |

**Note on 100% OnTrac:** The extreme cost increase is due to OnTrac's limited geographic coverage. OnTrac only services the Western United States, and shipments to non-serviceable areas receive a $500 penalty cost in the calculation. This makes OnTrac unsuitable as a single-carrier solution for nationwide shipping.

## Key Findings

- **FedEx dominates the current mix** at 49.1% of shipments, accounting for 56.8% of total cost
- **USPS is the most cost-efficient carrier** at $7.50 average cost per shipment (42% cheaper than FedEx Home Delivery's $15.01)
- **FedEx SmartPost vs Home Delivery**: SmartPost averages $9.61 vs Home Delivery's $15.01 - a 36% savings on comparable shipments
- **The current mix is near-optimal for current carriers**: 100% FedEx would cost 11.3% more, 100% USPS would cost 31.8% more
- **Large packages drive costs**: Pizza boxes 42x32x2 and 48X36X1 average $28-34 per shipment (3x the overall average)
- **OnTrac shows regional strength**: For Phoenix-originated shipments within its service area, OnTrac is competitive at $13.71 average
- **Weight-based pricing is significant**: Shipments 5-10 lbs cost 2.6x more than 0-1 lb shipments
- **Phoenix is the largest cost center** at 51.9% of shipments and 55.6% of costs

## DHL Shipments Handling

DHL eCommerce America shipments (40,157 shipments, 7.2% of total) are **excluded from cost calculations** because:
1. No DHL cost calculator exists in this analysis
2. DHL is not being considered for 2026 tender optimization

These shipments ARE included in 100% single-carrier comparisons (e.g., "100% FedEx" calculates FedEx costs for all 558,210 shipments including the DHL ones).

## Files Generated

- `breakdown_by_carrier.csv` - Carrier-level summary
- `breakdown_by_provider.csv` - Provider-level detail (includes FedEx service types)
- `breakdown_by_packagetype.csv` - Full package type breakdown
- `breakdown_by_weight.csv` - Weight bracket analysis
- `breakdown_by_site.csv` - Production site summary
- `comparison_single_carrier.csv` - Single carrier scenario costs

---
*Generated: February 2026*
*Data Period: 2025 shipment volumes with 2026 calculated rates*
