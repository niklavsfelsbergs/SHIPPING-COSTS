-- Extended comparison query for USPS dashboard
-- Pulls columns from both expected and actual tables
-- No filters in SQL - filtering done in Python via sidebar

SELECT
    e.pcs_orderid,
    e.pcs_ordernumber,
    e.latest_trackingnumber,
    e.shop_ordernumber,
    e.pcs_created,
    e.ship_date,
    e.production_site,
    e.shipping_zip_code,
    e.shipping_region,
    e.shipping_country,
    e.packagetype,

    -- Expected zone/weight (cast to VARCHAR to ensure consistent types)
    CAST(e.shipping_zone AS VARCHAR(10)) AS shipping_zone,
    CAST(e.rate_zone AS VARCHAR(10)) AS rate_zone,
    e.billable_weight_lbs,

    -- Raw dimensions
    e.length_in,
    e.width_in,
    e.height_in,
    e.weight_lbs,

    -- Calculated dimensions
    e.cubic_in,
    e.longest_side_in,
    e.second_longest_in,
    e.length_plus_girth,

    -- DIM weight
    e.dim_weight_lbs,
    e.uses_dim_weight,

    -- Expected surcharge flags
    e.surcharge_nsl1,
    e.surcharge_nsl2,
    e.surcharge_nsv,
    e.surcharge_peak,

    -- Expected costs
    e.cost_base,
    e.cost_nsl1,
    e.cost_nsl2,
    e.cost_nsv,
    e.cost_peak,
    e.cost_subtotal,
    e.cost_total,

    -- Actual invoice info
    a.trackingnumber AS actual_trackingnumber,
    a.billing_date,

    -- Actual zone/weight (cast to VARCHAR to ensure consistent types)
    CAST(a.actual_zone AS VARCHAR(10)) AS actual_zone,
    a.actual_weight_lbs AS actual_billed_weight_lbs,

    -- Actual costs
    a.actual_base,
    a.actual_nsl1,
    a.actual_nsl2,
    a.actual_noncompliance,
    a.actual_total,

    -- Adjustment info
    a.has_adjustment,
    a.adjustment_reason

FROM shipping_costs.expected_shipping_costs_usps e
INNER JOIN shipping_costs.actual_shipping_costs_usps a
    ON e.pcs_orderid = a.pcs_orderid
