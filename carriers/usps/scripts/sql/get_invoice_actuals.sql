-- Get actual costs from USPS invoices
-- Parameter: {tracking_numbers} - comma-separated list of tracking numbers (quoted)
-- Note: Uses 'pic' column for tracking number (impb is often NULL)

SELECT
    REPLACE(pic, '''', '')::TEXT as trackingnumber,
    mailing_date as billing_date,
    zone::TEXT as actual_zone,
    manifest_weight::FLOAT as actual_weight_lbs,
    manifest_length::FLOAT as actual_length_in,
    manifest_width::FLOAT as actual_width_in,
    manifest_height::FLOAT as actual_height_in,
    -- actual_base absorbs the variance so components sum to actual_total
    -- Formula: actual_base + actual_nsl1 + actual_nsl2 = actual_total
    (COALESCE(base_postage, 0) - COALESCE(ca_postage_variance, 0))::FLOAT as actual_base,
    COALESCE(op_nonstandard_fee_len_threshold_1, 0)::FLOAT as actual_nsl1,
    COALESCE(op_nonstandard_fee_len_threshold_2, 0)::FLOAT as actual_nsl2,
    COALESCE(ca_noncompliance_fee, 0)::FLOAT as actual_noncompliance,
    final_postage_usd::FLOAT as actual_total,
    ca_has_adjustment as has_adjustment,
    ca_reason::TEXT as adjustment_reason,
    COALESCE(ca_postage_variance, 0)::FLOAT as adjustment_amount
FROM poc_staging.usps
WHERE REPLACE(pic, '''', '') IN ({tracking_numbers})
  AND transaction_type = 'PURCHASE'
  AND base_postage IS NOT NULL  -- Exclude records without manifest data
