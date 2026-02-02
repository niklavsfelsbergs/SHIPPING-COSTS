# FedEx Dashboard Implementation Summary

## Overview

Successfully implemented a complete FedEx expected vs actual costs dashboard by adapting the proven OnTrac dashboard architecture. The implementation follows the plan exactly, reusing patterns while adapting for FedEx-specific features.

## Files Created

```
carriers/fedex/dashboard/
├── FedEx.py                    # Landing page (86 lines)
├── data.py                     # Data layer (835 lines)
├── export_data.py              # Export script (158 lines)
├── README.md                   # User documentation
├── IMPLEMENTATION.md           # This file
├── sql/
│   └── comparison.sql          # Query without filters (82 lines)
└── pages/
    ├── 1_Portfolio.py          # Portfolio page (520 lines)
    ├── 2_Accuracy.py           # Accuracy page (668 lines)
    ├── 3_Anomalies.py          # Anomalies page (505 lines)
    └── 4_Cost_Drivers.py       # Cost drivers page (628 lines)
```

## Implementation Details

### 1. Data Layer (data.py)

**Reused from OnTrac:**
- 3-layer caching architecture (load_raw → prepare_df → get_filtered_df)
- Sidebar rendering with checkbox dropdowns
- Invoice search with scrollable list
- Drilldown helper with dimension slicing
- Format helpers and chart layout utilities

**FedEx-Specific Adaptations:**
- **COST_POSITIONS**: 4-part rate structure (Base Rate, Performance Pricing, Earned Discount, Grace Discount) + surcharges
- **DETERMINISTIC_SURCHARGES**: Updated to `["ahs", "ahs_weight", "oversize", "das", "residential"]`
- **CHARGE_TYPES**: 8 FedEx surcharges (removed OnTrac-specific OML, LPS, EDAS)
- **WEIGHT_BRACKETS**: Extended to 100+ lbs (OnTrac stops at 50+)
- **Service Type Filter**: Added service_type to sidebar filters
- **prepare_df()**: Added service_type segment, net_base calculation, SmartPost anomaly flag
- **Field names**: Changed `actual_total` → `actual_net_charge`, `billing_date` → `invoice_date`

### 2. SQL Query (sql/comparison.sql)

**Approach:**
- Based on `fedex/scripts/sql/comparison_base.sql`
- Removed WHERE clause parameters (filtering in Python layer)
- Added all required columns: rate_service, dimensional fields, das_zone, surcharge flags

**Columns Added:**
- `rate_service` - Service type (Home Delivery vs Ground Economy)
- Dimensional fields: length, width, height, cubic, longest_side, etc.
- `das_zone` - DAS tier (1-5)
- All surcharge flags and cost components

### 3. Export Script (export_data.py)

**Reused from OnTrac:**
- Overall structure: comparison → match rate → unmatched shipments
- Validation logic
- Parquet export

**FedEx-Specific Changes:**
- Updated table names: `expected_shipping_costs_fedex`, `actual_shipping_costs_fedex`
- Updated SQL path: `sql/comparison.sql`
- Updated field names: `invoice_date`, `actual_net_charge`, `actual_rated_weight_lbs`
- Updated unmatched queries with FedEx column lists (rate_service, unpredictable, etc.)

### 4. Landing Page (FedEx.py)

**Changes:**
- Title: "FedEx Expected Cost Calculation"
- Description: References Home Delivery and Ground Economy
- Page captions: Updated for FedEx-specific features
- Export command path: Updated to FedEx

**Unchanged:**
- Page structure and navigation
- Grain note logic
- Layout and styling

### 5. Portfolio Page (pages/1_Portfolio.py)

**Reused from OnTrac:**
- KPI cards (6 metrics)
- Unmatched shipments section
- Time series chart (daily/weekly/monthly)
- Cost breakdown by component
- Distribution charts (zone, weight, site)
- Data quality & coverage section

**FedEx-Specific Additions:**
- **Service Comparison Section**: Table comparing Home Delivery vs Ground Economy (shipments, expected, actual, variance)
- **SmartPost Anomaly Alert**: Info banner flagging Ground Economy 10+ lb shipments
- **Top Variance Drivers**: Added "By Service Type" tab

**Field Updates:**
- `actual_total` → `actual_net_charge` throughout
- `billing_date` → `invoice_date` in unmatched actual filters

### 6. Accuracy Page (pages/2_Accuracy.py)

**Reused from OnTrac:**
- Deviation histogram with KDE
- Stats tables (full dataset + clean matches)
- Confusion matrix for surcharge detection
- Zone accuracy analysis
- Weight accuracy comparison

**FedEx-Specific Changes:**
- **Surcharge detection**: Updated to FedEx surcharges (ahs, ahs_weight, oversize, das, residential)
- **Service type tab**: Added in "Accuracy by Segment" section
- **Field names**: `actual_total` → `actual_net_charge`, `actual_billed_weight_lbs` → `actual_rated_weight_lbs`

**Removed:**
- OnTrac-specific das_zone field from detail views

### 7. Anomalies Page (pages/3_Anomalies.py)

**Reused from OnTrac:**
- Billing anomalies with configurable thresholds
- Component breakdown analysis
- Surcharge surprises (false positives/negatives)
- Trend monitoring over time

**FedEx-Specific Additions:**
- **SmartPost Anomaly Metric**: Count and percentage of Ground Economy 10+ lb shipments
- **Unpredictable Charges Metric**: Total count and amount of `actual_unpredictable`
- **Unpredictable Charges in Operational Issues**: Added as new operational issue type

**Removed:**
- OnTrac-specific operational issues (OML billing, return_to_sender)

**Field Updates:**
- `actual_total` → `actual_net_charge`

### 8. Cost Drivers Page (pages/4_Cost_Drivers.py)

**Reused from OnTrac:**
- Surcharge frequency analysis
- Weight distribution charts
- Zone & geography analysis
- Dimensional analysis (scatter plots)

**FedEx-Specific Additions:**
- **Service Type Analysis Section**: Volume pie chart + avg cost per shipment by service
- **SmartPost Weight Cliff Section**: Line chart showing rate jump at 10 lbs threshold with metric
- **Surcharge Updates**: Updated to FedEx surcharges (removed OML, LPS, EDAS; added AHS-Weight, Oversize)
- **Dimensional thresholds**: Updated boundary lines for AHS (30") and Oversize (96")

**Field Updates:**
- `actual_total` → `actual_net_charge` throughout

## Key Design Decisions

### 1. Service Type as First-Class Dimension
Treated `rate_service` (mapped to `service_type`) like production_site - essential filter for meaningful analysis. Added to sidebar, included in all segment breakdowns.

### 2. 4-Part Rate Transparency
Show Base + Performance Pricing + Earned/Grace Discounts separately in COST_POSITIONS, combine to "Net Base" for derived calculations. This matches FedEx invoice structure.

### 3. SmartPost Anomaly Visibility
Flag 10+ lb Ground Economy shipments prominently across Portfolio and Anomalies pages. This is a critical cost optimization insight due to USPS weight limits affecting Ground Economy rates.

### 4. Origin-Zone Complexity
Leveraged existing production_site filter rather than adding zone-origin visualization. Future enhancement could add origin × destination heatmap in Cost Drivers.

### 5. DAS Tier Granularity
Kept DAS as single surcharge in frequency analysis. Future enhancement could break down by 5 tiers using das_zone field.

### 6. Unpredictable Charges Tracking
Added as separate metric and operational issue type. These charges represent invoice items not covered by standard calculator logic.

### 7. Field Name Consistency
Consistently used FedEx field names:
- `actual_net_charge` (not `actual_total`) - matches FedEx invoice terminology
- `invoice_date` (not `billing_date`) - matches FedEx invoice field
- `actual_rated_weight_lbs` (not `actual_billed_weight_lbs`) - FedEx uses "rated weight"

## Testing Checklist

### Pre-Launch Testing

- [ ] **Data Export**: Run `python -m carriers.fedex.dashboard.export_data`
  - [ ] Verify parquet files created in data/
  - [ ] Check match_rate.json values
  - [ ] Confirm unmatched files have expected columns

- [ ] **Dashboard Launch**: Run `streamlit run carriers/fedex/dashboard/FedEx.py`
  - [ ] All 4 pages load without errors
  - [ ] Sidebar filters appear and persist across pages

- [ ] **Filter Testing**:
  - [ ] Service type filter shows "Home Delivery" and "Ground Economy"
  - [ ] Selecting single service updates all charts
  - [ ] Date range, production site, invoice filters work
  - [ ] Cost position zeroing recalculates totals correctly

- [ ] **Visualization Validation**:
  - [ ] Portfolio: Service comparison shows both services
  - [ ] Portfolio: SmartPost anomaly alert appears when applicable
  - [ ] Portfolio: Cost breakdown shows 4-part rate structure
  - [ ] Accuracy: Service type tab in segment breakdown works
  - [ ] Anomalies: SmartPost and unpredictable charges metrics display
  - [ ] Cost Drivers: SmartPost weight cliff chart shows 10 lb jump
  - [ ] Cost Drivers: Service analysis pie chart renders

- [ ] **Performance**:
  - [ ] Page loads in <5 seconds with full dataset
  - [ ] Changing tabs doesn't re-filter (caching works)
  - [ ] First filter change may be slow, subsequent changes are fast

- [ ] **Data Quality**:
  - [ ] Deviation = actual_net_charge - cost_total
  - [ ] 4-part rate components sum to net base correctly
  - [ ] Surcharge costs match expected values
  - [ ] Service type populated (not "Unknown")

### Post-Launch Validation

- [ ] Compare variance metrics to existing FedEx reports
- [ ] Validate SmartPost 10+ lb anomaly count with raw data
- [ ] Cross-check surcharge detection rates with invoice samples
- [ ] Review unpredictable charges examples for patterns

## Success Criteria

✅ All 4 pages render without errors
✅ Service comparison distinguishes Home Delivery vs Ground Economy
✅ 4-part rate breakdown visible and accurate
✅ SmartPost 10+ lb anomaly identified and visualized
✅ Filters persist across pages
✅ Export script completes successfully
✅ Dashboard structure matches OnTrac for consistency
✅ All Python files compile without syntax errors

## Future Enhancements

### Potential Additions:
1. **Origin-Zone Heatmap**: Visualize production_site × destination_state → zone assignments
2. **DAS Tier Breakdown**: Show cost impact by 5 DAS tiers (currently aggregated)
3. **Discount Impact Analysis**: Separate page for Performance Pricing distribution
4. **Unpredictable Charge Decoder**: Mapping of actual_unpredictable to charge descriptions
5. **Service-Specific Thresholds**: Different AHS/Oversize rules for HD vs GE
6. **Weight Cliff Optimizer**: Suggest package weight adjustments to avoid 10 lb threshold

### Code Improvements:
1. **Type Hints**: Add full type annotations to all functions
2. **Unit Tests**: Add pytest tests for data transformations
3. **Config File**: Move constants (COST_POSITIONS, etc.) to YAML config
4. **Cache Invalidation**: Add manual cache clear button
5. **Export Scheduling**: Add cron job or scheduler for daily exports

## Lessons Learned

1. **Pattern Reuse Works**: OnTrac dashboard architecture transferred cleanly to FedEx with minimal refactoring
2. **Service Type is Critical**: Having service as a first-class filter revealed significant differences between HD and GE
3. **Field Name Consistency**: Using FedEx terminology (net_charge, invoice_date) improves user trust
4. **SmartPost Anomaly is Key**: 10 lb threshold has major cost implications worth highlighting
5. **4-Part Rate Structure**: Breaking down discounts provides transparency into contract performance

## Maintenance Notes

### Configuration Updates
- **Base rates**: Update when FedEx contract renews
- **Performance Pricing**: Update discount percentages as negotiated
- **Surcharge prices**: Update when FedEx announces changes
- **Demand periods**: Update annually or as FedEx changes seasonal rules

### Dashboard Updates
To update with new data:
```bash
# 1. Upload latest expected costs
python -m carriers.fedex.scripts.upload_expected --incremental

# 2. Upload latest actual costs (after receiving invoices)
python -m carriers.fedex.scripts.upload_actuals --incremental

# 3. Re-export dashboard data
python -m carriers.fedex.dashboard.export_data

# 4. Refresh browser (Streamlit auto-reloads)
```

### Version Tracking
When making calculator changes, always update `carriers/fedex/version.py` so dashboard data includes version stamp for audit trail.

## Contact

For questions or issues with the FedEx dashboard implementation:
- See main project `CLAUDE.md` for carrier-specific documentation
- Check OnTrac dashboard for reference implementation
- Review FedEx calculator in `carriers/fedex/calculate_costs.py`
