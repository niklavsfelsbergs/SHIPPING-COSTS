-- Get actual costs from OnTrac invoices
-- Parameter: {tracking_numbers} - comma-separated list of tracking numbers (quoted)

SELECT
    tracking_number as trackingnumber,
    invoice_number,
    billing_date,
    zone as actual_zone,
    billed_weight_lbs as actual_billed_weight_lbs,
    return_to_sender,
    SUM(service_charge) as actual_base,
    SUM(over_maximum_limits_surcharge) as actual_oml,
    SUM(large_package_surcharge) as actual_lps,
    SUM(additional_handling_surcharge) as actual_ahs,
    SUM(delivery_area_surcharge) as actual_das,
    SUM(extended_area_surcharge) as actual_edas,
    SUM(residential_surcharge) as actual_res,
    SUM(demand_surcharge) as actual_dem_res,
    SUM(demand_additional_handling_surcharge) as actual_dem_ahs,
    SUM(demand_large_package_surcharge) as actual_dem_lps,
    SUM(demand_over_maximum_limits_surcharge) as actual_dem_oml,
    SUM(fuel_surcharge) as actual_fuel,
    SUM(total) as actual_total,
    SUM(unresolved_address_surcharge) as actual_unresolved_address,
    SUM(address_correction_surcharge) as actual_address_correction
FROM poc_landing.ontrac
WHERE tracking_number IN ({tracking_numbers})
GROUP BY tracking_number, invoice_number, billing_date, zone, billed_weight_lbs, return_to_sender
