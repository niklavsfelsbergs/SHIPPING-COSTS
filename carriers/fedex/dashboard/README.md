# FedEx Dashboard

Interactive Streamlit dashboard for analyzing expected vs actual FedEx shipping costs.

## Features

- **Portfolio Overview**: KPIs, time series, service type comparison, cost breakdown
- **Estimation Accuracy**: Deviation analysis, surcharge detection, zone & weight accuracy
- **Anomaly Detection**: Billing anomalies, unpredictable charges, SmartPost 10+ lb issues
- **Cost Drivers**: Service analysis, discount impact, DAS tiers, SmartPost weight cliff

## Prerequisites

1. Expected and actual costs uploaded to Redshift:
   - `shipping_costs.expected_shipping_costs_fedex`
   - `shipping_costs.actual_shipping_costs_fedex`

2. Python packages installed (from repository root):
   ```bash
   pip install -e .
   ```

## Usage

### 1. Export Data from Redshift

```bash
python -m carriers.fedex.dashboard.export_data
```

This creates:
- `data/comparison.parquet` - Matched expected vs actual records
- `data/match_rate.json` - Match rate statistics
- `data/unmatched_expected.parquet` - Expected shipments without actuals
- `data/unmatched_actual.parquet` - Actual shipments without expecteds

### 2. Launch Dashboard

```bash
streamlit run carriers/fedex/dashboard/FedEx.py
```

The dashboard will open in your browser at http://localhost:8501

## Dashboard Pages

### 1. Portfolio Overview
- **KPIs**: Expected, Actual, Variance, Match Rate
- **Service Comparison**: Home Delivery vs Ground Economy performance
- **SmartPost Anomaly Alert**: Flags 10+ lb Ground Economy shipments
- **Time Series**: Daily/Weekly/Monthly cost trends
- **Cost Breakdown**: 4-part rate structure (Base + Performance Pricing + Discounts)
- **Distribution**: Shipment counts by zone, weight, site
- **Unmatched Shipments**: Expected-only and Actual-only records

### 2. Estimation Accuracy
- **Deviation Analysis**: Histogram, stats by segment
- **Surcharge Detection**: Confusion matrix for AHS, AHS-Weight, Oversize, DAS, Residential
- **Zone Accuracy**: Match rates by zone
- **Weight Accuracy**: Comparison of expected vs actual rated weight
- **Accuracy by Segment**: Breakdowns by production site, service type, error source

### 3. Anomaly Detection
- **Billing Anomalies**: Large deviations (>$10 or >20%)
- **SmartPost Anomalies**: Ground Economy 10+ lb shipments
- **Unpredictable Charges**: Shipments with unexpected charge types
- **Surcharge Surprises**: False positives and negatives
- **Trend Monitoring**: Anomaly rates over time

### 4. Cost Drivers
- **Service Type Analysis**: Volume and cost by Home Delivery vs Ground Economy
- **SmartPost Weight Cliff**: Rate jump at 10 lbs threshold (~26% increase)
- **Surcharge Frequency**: AHS, AHS-Weight, Oversize, DAS, Residential occurrence rates
- **Dimensional Analysis**: Package dimensions vs surcharge thresholds
- **Weight Distribution**: Shipment counts by weight bracket
- **DAS Tier Distribution**: Shipments by 5-tier DAS structure
- **Zone & Geography**: Cost by zone, destination state heatmap

## Sidebar Filters

All filters persist across pages:

- **Time Axis**: Invoice Date vs Ship Date
- **Time Grain**: Daily / Weekly / Monthly
- **Date Range**: Configurable start and end dates
- **Metric Mode**: Total vs Average per shipment
- **Production Site**: Multi-select facility filter
- **Service Type**: Home Delivery / Ground Economy filter
- **Invoice Number**: Searchable multi-select invoice filter
- **Charges**: Include/exclude shipments with specific surcharges
- **Positions**: Zero out specific cost components for analysis

## FedEx-Specific Features

### Service Types
- **Home Delivery**: Residential delivery service
- **Ground Economy**: SmartPost service (formerly FedEx SmartPost)

### 4-Part Rate Structure
1. **Base Rate**: Undiscounted list price by zone/weight
2. **Performance Pricing**: Contractual discount (negative)
3. **Earned Discount**: Volume-based discount (negative, currently $0)
4. **Grace Discount**: Additional discount (negative, currently $0)
5. **Net Base** = Base + PP + Earned + Grace

### Surcharges
- **AHS**: Additional Handling Surcharge (oversized packages)
- **AHS-Weight**: Weight-based additional handling
- **Oversize**: Packages exceeding dimensional limits
- **DAS**: Delivery Area Surcharge (5 tiers)
- **Residential**: Residential delivery fee
- **DEM-Base**: Demand period base surcharge
- **DEM-AHS**: Demand period AHS surcharge
- **DEM-Oversize**: Demand period oversize surcharge

### SmartPost 10+ lb Anomaly
Ground Economy (SmartPost) has unpredictable rate increases for packages ≥10 lbs due to USPS weight limits. The dashboard flags these shipments for review.

### Unpredictable Charges
FedEx invoices may include unexpected charges not covered by standard rate logic. These are tracked separately as `actual_unpredictable`.

## Data Refresh

To update the dashboard with new data:

1. Ensure latest expected costs are uploaded:
   ```bash
   python -m carriers.fedex.scripts.upload_expected --incremental
   ```

2. Ensure latest actual costs are uploaded:
   ```bash
   python -m carriers.fedex.scripts.upload_actuals --incremental
   ```

3. Re-export dashboard data:
   ```bash
   python -m carriers.fedex.dashboard.export_data
   ```

4. Refresh browser (dashboard will reload automatically)

## Performance

- **Data Size**: Handles 100K+ matched shipments efficiently
- **Load Time**: <5 seconds with proper caching
- **Caching**: 3-layer architecture (load_raw → prepare_df → get_filtered_df)

## Troubleshooting

### "Data file not found" error
Run `python -m carriers.fedex.dashboard.export_data` to create the required parquet files.

### Slow filter updates
This is expected on first filter change. Subsequent changes are cached and fast.

### Missing columns in drilldown
Check that the export_data script is using the latest comparison.sql query with all required columns.

### Service type shows "Unknown"
Ensure `rate_service` column is populated in the expected costs table. Check that `calculate_costs()` is assigning service type correctly.

## Architecture

```
FedEx.py (landing page)
  ↓
data.py (data layer)
  ├─ load_raw() → reads comparison.parquet
  ├─ prepare_df() → adds derived columns (service_type, net_base, deviation, etc.)
  └─ get_filtered_df() → applies sidebar filters

pages/
  ├─ 1_Portfolio.py → KPIs, service comparison, time series
  ├─ 2_Accuracy.py → deviation, surcharge detection, zone/weight accuracy
  ├─ 3_Anomalies.py → billing anomalies, SmartPost issues, unpredictable charges
  └─ 4_Cost_Drivers.py → service analysis, weight cliff, DAS tiers
```

## Comparison to OnTrac Dashboard

Key differences:
- **Service Type Filter**: FedEx has Home Delivery vs Ground Economy; OnTrac is single-service
- **Rate Structure**: FedEx uses 4-part (Base + PP + Discounts); OnTrac uses Base + Fuel
- **Surcharges**: FedEx has 8 surcharges; OnTrac has 10 (different types)
- **DAS Structure**: FedEx has 5 tiers; OnTrac has 2 (Standard/Extended)
- **SmartPost Anomaly**: FedEx-specific 10 lb weight threshold issue
- **Unpredictable Charges**: FedEx invoices have additional charge types not in calculator

## Support

For issues or questions, see the main project README or contact the data team.
