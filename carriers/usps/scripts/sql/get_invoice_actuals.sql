-- Get actual costs from USPS invoices
-- Parameter: {tracking_numbers} - comma-separated list of tracking numbers (quoted)
-- Note: Uses 'pic' column for tracking number (impb is often NULL)

SELECT
    pic as trackingnumber,
    mailing_date as billing_date,
    zone as actual_zone,
    manifest_weight as actual_weight_lbs,
    manifest_length as actual_length_in,
    manifest_width as actual_width_in,
    manifest_height as actual_height_in,
    base_postage as actual_base,
    COALESCE(op_nonstandard_fee_len_threshold_1, 0) as actual_nsl1,
    COALESCE(op_nonstandard_fee_len_threshold_2, 0) as actual_nsl2,
    COALESCE(ca_noncompliance_fee, 0) as actual_noncompliance,
    final_postage_usd as actual_total,
    ca_has_adjustment as has_adjustment,
    ca_reason as adjustment_reason
FROM poc_staging.usps
WHERE pic IN ({tracking_numbers})
