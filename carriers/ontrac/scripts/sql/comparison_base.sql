-- Get matched expected vs actual data for comparison
-- Parameters:
--   {invoice_filter} - e.g., "AND a.invoice_number = 'INV-123'" or ""
--   {date_from_filter} - e.g., "AND a.billing_date >= '2025-01-01'" or ""
--   {date_to_filter} - e.g., "AND a.billing_date <= '2025-01-31'" or ""

SELECT
    e.pcs_orderid,
    e.pcs_ordernumber,
    e.latest_trackingnumber,
    e.pcs_created,
    e.ship_date,
    e.production_site,
    e.shipping_region,
    e.packagetype,

    -- Expected zone/weight
    e.shipping_zone,
    e.billable_weight_lbs,

    -- Expected surcharge flags (deterministic only)
    e.surcharge_oml,
    e.surcharge_lps,
    e.surcharge_ahs,
    e.surcharge_das,
    e.surcharge_edas,

    -- Expected costs
    e.cost_base,
    e.cost_oml,
    e.cost_lps,
    e.cost_ahs,
    e.cost_das,
    e.cost_edas,
    e.cost_res,
    e.cost_dem_oml,
    e.cost_dem_lps,
    e.cost_dem_ahs,
    e.cost_dem_res,
    e.cost_fuel,
    e.cost_total,

    -- Actual invoice info
    a.trackingnumber AS actual_trackingnumber,
    a.invoice_number,
    a.billing_date,

    -- Actual zone/weight
    a.actual_zone,
    a.actual_billed_weight_lbs,

    -- Actual costs
    a.actual_base,
    a.actual_oml,
    a.actual_lps,
    a.actual_ahs,
    a.actual_das,
    a.actual_edas,
    a.actual_res,
    a.actual_dem_oml,
    a.actual_dem_lps,
    a.actual_dem_ahs,
    a.actual_dem_res,
    a.actual_fuel,
    a.actual_total

FROM shipping_costs.expected_shipping_costs_ontrac e
INNER JOIN shipping_costs.actual_shipping_costs_ontrac a
    ON e.pcs_orderid = a.pcs_orderid
WHERE 1=1
    {invoice_filter}
    {date_from_filter}
    {date_to_filter}
