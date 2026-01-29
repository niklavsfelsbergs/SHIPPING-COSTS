-- Extended comparison query for dashboard
-- Pulls ALL columns from both expected and actual tables
-- No filters in SQL — filtering done in Python via sidebar

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

    -- Expected zone/weight
    e.shipping_zone,
    e.das_zone,
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

    -- Expected surcharge flags (deterministic only)
    e.surcharge_oml,
    e.surcharge_lps,
    e.surcharge_ahs,
    e.surcharge_das,
    e.surcharge_edas,
    e.surcharge_res,
    e.surcharge_dem_oml,
    e.surcharge_dem_lps,
    e.surcharge_dem_ahs,
    e.surcharge_dem_res,

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
    e.cost_subtotal,
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
    a.actual_total,

    -- Anomaly signals
    a.actual_unresolved_address,
    a.actual_address_correction,
    a.return_to_sender

FROM shipping_costs.expected_shipping_costs_ontrac e
INNER JOIN shipping_costs.actual_shipping_costs_ontrac a
    ON e.pcs_orderid = a.pcs_orderid
