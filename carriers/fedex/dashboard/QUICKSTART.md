# FedEx Dashboard Quick Start

Get the FedEx dashboard running in 3 steps.

## Step 1: Export Data (5 minutes)

```bash
cd carriers
python -m fedex.dashboard.export_data
```

This pulls data from Redshift and creates local parquet files. You should see:
```
Loading comparison data from Redshift...
  Loaded 50,000 rows, 75 columns
  Saved to C:\...\carriers\fedex\dashboard\data\comparison.parquet
Loading match rate counts...
  actual_orderids: 52,000
  matched_orderids: 50,000
  Saved to C:\...\carriers\fedex\dashboard\data\match_rate.json
Loading unmatched shipments...
  Expected-only: 2,500
  Actual-only:   2,000
  Saved to C:\...\carriers\fedex\dashboard\data\unmatched_expected.parquet and ...

Done. Run the dashboard with:
  streamlit run carriers/fedex/dashboard/FedEx.py
```

## Step 2: Launch Dashboard (30 seconds)

```bash
streamlit run fedex/dashboard/FedEx.py
```

Your browser will open automatically to http://localhost:8501

## Step 3: Explore

### Landing Page
- Review the 4 available pages
- Note the grain warning if present

### Use Sidebar Filters
1. **Date Range**: Set to desired period (default: Jul 2025 - Dec 2026)
2. **Service Type**: Select Home Delivery and/or Ground Economy
3. **Production Site**: Choose facility or keep all selected
4. **Invoice Number**: Search for specific invoice

### Navigate to Pages

#### Portfolio (Page 1)
- Check KPIs: Expected, Actual, Variance
- Review Service Comparison table
- Look for SmartPost anomaly alert
- View time series chart

#### Accuracy (Page 2)
- Review deviation histogram
- Check surcharge detection matrix
- Compare zone accuracy
- Review service type breakdown

#### Anomalies (Page 3)
- Check SmartPost anomaly count
- Review unpredictable charges
- Set deviation threshold ($10 or 20%)
- View false positives/negatives

#### Cost Drivers (Page 4)
- Review service type volume split
- Check SmartPost weight cliff chart
- View surcharge frequency
- Analyze dimensional thresholds

## Common Tasks

### Compare Home Delivery vs Ground Economy
1. Go to Portfolio page
2. Scroll to "Service Type Comparison" section
3. Review shipments and variance by service

### Find SmartPost 10+ lb Issues
1. Go to Anomalies page
2. Check "SmartPost 10+ lb anomaly" metric
3. Or go to Cost Drivers → "SmartPost Weight Cliff Analysis"

### Analyze Specific Invoice
1. In sidebar, click "Invoice number" expander
2. Use search box or scroll to find invoice
3. Uncheck "None" button
4. Check only desired invoice
5. All pages now show only that invoice

### Export Data for Analysis
1. Navigate to any page
2. Scroll to a chart/section of interest
3. Open "Drilldown" expander
4. Select dimension (e.g., production_site)
5. Click "Download CSV"

### Zero Out Cost Components
1. In sidebar, scroll to "Positions" expander
2. Uncheck components to exclude (e.g., "Fuel")
3. Dashboard recalculates totals without those components

### View Unmatched Shipments
1. Go to Portfolio page
2. Expand "View unmatched shipments"
3. Tab 1: Expected without Actual (calculated but not invoiced)
4. Tab 2: Actual without Expected (invoiced but not calculated)

## Troubleshooting

### Error: "Data file not found"
**Solution**: Run `python -m carriers.fedex.dashboard.export_data` from the carriers directory

### Service type shows "Unknown"
**Problem**: rate_service column not populated in expected costs
**Solution**: Check that calculate_costs() is assigning service type, re-upload expected costs

### Dashboard is slow
**Expected**: First filter change may take 5-10 seconds (building cache)
**Subsequent**: Filter changes should be <1 second (using cache)

### Charts not updating
**Solution**: Click outside the filter, or press Enter to trigger update

### Can't find specific invoice
**Solution**: Use search box in "Invoice number" expander (type part of invoice number)

## Next Steps

### Daily Workflow
1. Upload new expected costs (if shipments changed)
2. Upload new actual costs (when invoices arrive)
3. Re-export dashboard data
4. Refresh browser

### Weekly Review
1. Portfolio → Check variance trend
2. Accuracy → Review surcharge detection rates
3. Anomalies → Investigate high-deviation shipments
4. Cost Drivers → Analyze service mix changes

### Monthly Analysis
1. Export full dataset via drilldown
2. Compare to previous month
3. Identify cost optimization opportunities
4. Review SmartPost usage and 10+ lb frequency

## Tips

- **Use Average per Shipment**: Switch metric mode to "Average per shipment" for normalized comparisons
- **Change Time Grain**: Use Daily for recent data, Weekly for trends, Monthly for long-term analysis
- **Filter by Service**: Analyze Home Delivery and Ground Economy separately to understand differences
- **Set Cost Thresholds**: In Anomalies, adjust threshold to focus on significant deviations only
- **Bookmark Specific Views**: URL includes page, so you can bookmark frequently used views
- **Export for Deeper Analysis**: Use drilldown CSV exports for pivot tables and custom analysis

## Support

- **Documentation**: See `README.md` for full feature list
- **Implementation**: See `IMPLEMENTATION.md` for technical details
- **Carrier Details**: See `carriers/fedex/README.md` for FedEx-specific surcharge info
- **Issues**: Report problems with calculator or dashboard to data team

---

**Happy analyzing! 📊**
