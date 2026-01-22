-- Create actual_shipping_costs_usps table
-- USPS actual costs from invoice data (poc_staging.usps)

CREATE TABLE IF NOT EXISTS shipping_costs.actual_shipping_costs_usps (
    -- Identification (2)
    pcs_orderid             BIGINT,
    trackingnumber          VARCHAR(50),

    -- Invoice info (2)
    billing_date            TIMESTAMP,
    actual_zone             VARCHAR(10),

    -- Actual dimensions (4)
    actual_weight_lbs       DECIMAL(10,4),
    actual_length_in        DECIMAL(10,2),
    actual_width_in         DECIMAL(10,2),
    actual_height_in        DECIMAL(10,2),

    -- Actual costs (5)
    actual_base             DECIMAL(10,2),
    actual_nsl1             DECIMAL(10,2),
    actual_nsl2             DECIMAL(10,2),
    actual_noncompliance    DECIMAL(10,2),
    actual_total            DECIMAL(10,2),

    -- Adjustment info (2)
    has_adjustment          BOOLEAN,
    adjustment_reason       VARCHAR(500),

    -- Metadata (1)
    dw_timestamp            TIMESTAMP DEFAULT GETDATE()
)
DISTSTYLE AUTO
SORTKEY (billing_date);

-- Grant permissions
GRANT ALL ON shipping_costs.actual_shipping_costs_usps TO tcg_nfe;
