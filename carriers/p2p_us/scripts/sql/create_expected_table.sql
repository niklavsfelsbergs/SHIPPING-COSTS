-- Create expected_shipping_costs_p2p_us table
-- P2P Parcel Flex Advantage Plus (PFAP2) expected costs from calculator
--
-- Run this DDL in Redshift before using upload_expected.py

CREATE TABLE IF NOT EXISTS shipping_costs.expected_shipping_costs_p2p_us (
    -- Identification (7)
    pcs_orderid             BIGINT,
    pcs_ordernumber         VARCHAR(50),
    latest_trackingnumber   VARCHAR(50),
    trackingnumber_count    INTEGER,
    shop_ordernumber        VARCHAR(100),
    packagetype             VARCHAR(100),
    pcs_shipping_provider   VARCHAR(20),

    -- Dates (2)
    pcs_created             TIMESTAMP,
    ship_date               DATE,

    -- Location (5)
    production_site         VARCHAR(50),
    shipping_zip_code       VARCHAR(20),
    shipping_region         VARCHAR(50),
    shipping_country        VARCHAR(50),
    shipping_zone           INTEGER,            -- Zone 1-8

    -- Dimensions imperial (4)
    length_in               DECIMAL(10,2),
    width_in                DECIMAL(10,2),
    height_in               DECIMAL(10,2),
    weight_lbs              DECIMAL(10,4),

    -- Calculated dimensions (4)
    cubic_in                DECIMAL(12,2),
    longest_side_in         DECIMAL(10,2),
    second_longest_in       DECIMAL(10,2),
    length_plus_girth       DECIMAL(10,2),      -- L + 2*(W+H), used for AHS

    -- Weight calculations (3)
    dim_weight_lbs          DECIMAL(10,4),
    uses_dim_weight         BOOLEAN,
    billable_weight_lbs     DECIMAL(10,4),

    -- Surcharge flags (2)
    surcharge_ahs           BOOLEAN,            -- Additional Handling
    surcharge_oversize      BOOLEAN,            -- Oversize >70 lbs

    -- Costs (6)
    cost_base               DECIMAL(10,2),
    cost_ahs                DECIMAL(10,2),      -- $29.00 if triggered
    cost_oversize           DECIMAL(10,2),      -- $125.00 if triggered
    cost_subtotal           DECIMAL(10,2),
    cost_total              DECIMAL(10,2),      -- Same as subtotal (no fuel)
    cost_total_multishipment DECIMAL(10,2),     -- cost_total * trackingnumber_count

    -- Metadata (2)
    calculator_version      VARCHAR(30),
    dw_timestamp            TIMESTAMP DEFAULT GETDATE()
)
DISTSTYLE AUTO
SORTKEY (pcs_created, ship_date);

-- Grant permissions
GRANT ALL ON shipping_costs.expected_shipping_costs_p2p_us TO tcg_nfe;
