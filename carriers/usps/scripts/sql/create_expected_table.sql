-- Create expected_shipping_costs_usps table
-- USPS Ground Advantage expected costs from calculator

CREATE TABLE IF NOT EXISTS shipping_costs.expected_shipping_costs_usps (
    -- Identification (5)
    pcs_orderid             BIGINT,
    pcs_ordernumber         VARCHAR(50),
    latest_trackingnumber   VARCHAR(50),
    trackingnumber_count    INTEGER,
    shop_ordernumber        VARCHAR(100),

    -- Dates (2)
    pcs_created             TIMESTAMP,
    ship_date               DATE,

    -- Location (5)
    production_site         VARCHAR(50),
    shipping_zip_code       VARCHAR(20),
    shipping_region         VARCHAR(50),
    shipping_country        VARCHAR(50),
    shipping_zone           VARCHAR(5),         -- Zone with asterisk (e.g., "1*", "4")

    -- Dimensions imperial (4)
    length_in               DECIMAL(10,2),
    width_in                DECIMAL(10,2),
    height_in               DECIMAL(10,2),
    weight_lbs              DECIMAL(10,4),

    -- Calculated dimensions (4)
    cubic_in                DECIMAL(12,2),
    longest_side_in         DECIMAL(10,2),
    second_longest_in       DECIMAL(10,2),
    length_plus_girth       DECIMAL(10,2),

    -- Weight calculations (4)
    dim_weight_lbs          DECIMAL(10,4),
    uses_dim_weight         BOOLEAN,
    billable_weight_lbs     DECIMAL(10,4),
    rate_zone               INTEGER,            -- Zone stripped of asterisk (1-8)

    -- Surcharge flags (4)
    surcharge_nsl1          BOOLEAN,            -- Nonstandard Length 22-30"
    surcharge_nsl2          BOOLEAN,            -- Nonstandard Length >30"
    surcharge_nsv           BOOLEAN,            -- Nonstandard Volume >2 cu ft
    surcharge_peak          BOOLEAN,            -- Peak Season (Oct-Jan)

    -- Costs (7)
    cost_base               DECIMAL(10,2),
    cost_nsl1               DECIMAL(10,2),
    cost_nsl2               DECIMAL(10,2),
    cost_nsv                DECIMAL(10,2),
    cost_peak               DECIMAL(10,2),
    cost_subtotal           DECIMAL(10,2),
    cost_total              DECIMAL(10,2),      -- Same as subtotal (no fuel)

    -- Metadata (2)
    calculator_version      VARCHAR(20),
    dw_timestamp            TIMESTAMP DEFAULT GETDATE()
)
DISTSTYLE AUTO
SORTKEY (pcs_created, ship_date);

-- Grant permissions
GRANT ALL ON shipping_costs.expected_shipping_costs_usps TO tcg_nfe;
