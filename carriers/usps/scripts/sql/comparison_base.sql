-- Get matched expected vs actual data for comparison
-- Parameters:
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

    -- Expected zone/weight
    e.shipping_zone,
    e.billable_weight_lbs,

    -- Expected surcharge flags (deterministic only)
    e.surcharge_nsl1,
    e.surcharge_nsl2,

    -- Expected costs
    e.cost_base,
    e.cost_nsl1,
    e.cost_nsl2,
    e.cost_nsv,
    e.cost_peak,
    e.cost_total,

    -- Actual invoice info
    a.trackingnumber AS actual_trackingnumber,
    a.billing_date,

    -- Actual zone/weight
    a.actual_zone,
    a.actual_weight_lbs AS actual_billed_weight_lbs,

    -- Actual costs
    a.actual_base,
    a.actual_nsl1,
    a.actual_nsl2,
    a.actual_noncompliance,
    a.actual_total

FROM shipping_costs.expected_shipping_costs_usps e
INNER JOIN shipping_costs.actual_shipping_costs_usps a
    ON e.pcs_orderid = a.pcs_orderid
WHERE 1=1
    {date_from_filter}
    {date_to_filter}
