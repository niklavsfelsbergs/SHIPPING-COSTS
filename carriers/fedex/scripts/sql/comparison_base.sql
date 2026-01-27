-- Get matched expected vs actual data for comparison
-- Parameters:
--   {invoice_filter} - e.g., "AND a.invoice_number = 'INV-123'" or ""
--   {date_from_filter} - e.g., "AND a.invoice_date >= '2025-01-01'" or ""
--   {date_to_filter} - e.g., "AND a.invoice_date <= '2025-01-31'" or ""

SELECT
    e.pcs_orderid,
    e.pcs_ordernumber,
    e.latest_trackingnumber,
    e.pcs_created,
    e.ship_date,
    e.production_site,
    e.shipping_region,

    -- Expected zone/weight
    e.shipping_zone,
    e.billable_weight_lbs,

    -- Expected surcharge flags (deterministic only)
    e.surcharge_ahs,
    e.surcharge_ahs_weight,
    e.surcharge_oversize,
    e.surcharge_das,
    e.surcharge_residential,

    -- Expected costs - Rate components
    e.cost_base_rate,
    e.cost_performance_pricing,
    e.cost_earned_discount,
    e.cost_grace_discount,

    -- Expected costs - Surcharges
    e.cost_ahs,
    e.cost_ahs_weight,
    e.cost_oversize,
    e.cost_das,
    e.cost_residential,
    e.cost_dem_base,
    e.cost_dem_ahs,
    e.cost_dem_oversize,

    -- Expected costs - Totals
    e.cost_fuel,
    e.cost_total,

    -- Actual invoice info
    a.trackingnumber AS actual_trackingnumber,
    a.invoice_number,
    a.invoice_date,

    -- Actual zone/weight
    a.actual_zone,
    a.rated_weight_lbs AS actual_rated_weight_lbs,

    -- Actual costs - Rate components
    a.actual_base,
    a.actual_performance_pricing,
    a.actual_earned_discount,
    a.actual_grace_discount,

    -- Actual costs - Surcharges
    a.actual_ahs,
    a.actual_ahs_weight,
    a.actual_oversize,
    a.actual_das,
    a.actual_residential,
    a.actual_dem_base,
    a.actual_dem_ahs,
    a.actual_dem_oversize,
    a.actual_dem_residential,

    -- Actual costs - Totals
    a.actual_fuel,
    a.actual_net_charge,

    -- Unpredictable charges (FedEx-specific)
    a.actual_unpredictable

FROM shipping_costs.expected_shipping_costs_fedex e
INNER JOIN shipping_costs.actual_shipping_costs_fedex a
    ON e.pcs_orderid = a.pcs_orderid
WHERE 1=1
    {invoice_filter}
    {date_from_filter}
    {date_to_filter}
