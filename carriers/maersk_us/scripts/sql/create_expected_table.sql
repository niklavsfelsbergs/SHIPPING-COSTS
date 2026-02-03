-- Create expected_shipping_costs_maersk_us tables
-- Maersk US domestic last mile expected costs from calculator
--
-- Two tables:
--   _all_us: All US domestic shipments (filtered by country = 'United States of America')
--   _p2p:    P2P shipments only (TBD - different filtering logic)
--
-- Run this DDL in Redshift before using upload_expected_all_us.py

-- =============================================================================
-- ALL US SHIPMENTS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS shipping_costs.expected_shipping_costs_maersk_us_all_us (
    -- Identification (7)
    pcs_orderid             BIGINT,
    pcs_ordernumber         VARCHAR(50),
    latest_trackingnumber   VARCHAR(50),
    trackingnumber_count    INTEGER,
    shop_ordernumber        VARCHAR(100),
    packagetype             VARCHAR(100),
    pcs_shipping_provider   VARCHAR(50),

    -- Dates (2)
    pcs_created             TIMESTAMP,
    ship_date               DATE,

    -- Location (5)
    production_site         VARCHAR(50),
    shipping_zip_code       VARCHAR(20),
    shipping_region         VARCHAR(50),
    shipping_country        VARCHAR(50),
    shipping_zone           INTEGER,            -- Zone 1-9

    -- Dimensions imperial (4)
    length_in               DECIMAL(10,2),
    width_in                DECIMAL(10,2),
    height_in               DECIMAL(10,2),
    weight_lbs              DECIMAL(10,4),

    -- Calculated dimensions (3)
    cubic_in                DECIMAL(12,2),
    longest_side_in         DECIMAL(10,2),
    second_longest_in       DECIMAL(10,2),

    -- Weight calculations (3)
    dim_weight_lbs          DECIMAL(10,4),
    uses_dim_weight         BOOLEAN,
    billable_weight_lbs     DECIMAL(10,4),

    -- Surcharge flags (4)
    surcharge_nsl1          BOOLEAN,            -- Nonstandard Length >21"
    surcharge_nsl2          BOOLEAN,            -- Nonstandard Length >30"
    surcharge_nsd           BOOLEAN,            -- Nonstandard Dimensions >3456 cu in
    surcharge_pickup        BOOLEAN,            -- Pickup Fee (always true)

    -- Costs (8)
    cost_base               DECIMAL(10,2),
    cost_nsl1               DECIMAL(10,2),
    cost_nsl2               DECIMAL(10,2),
    cost_nsd                DECIMAL(10,2),
    cost_pickup             DECIMAL(10,2),      -- $0.04/lb (rounded up)
    cost_subtotal           DECIMAL(10,2),
    cost_total              DECIMAL(10,2),      -- Same as subtotal (no fuel)
    cost_total_multishipment DECIMAL(10,2),     -- cost_total * trackingnumber_count

    -- Metadata (2)
    calculator_version      VARCHAR(30),
    dw_timestamp            TIMESTAMP DEFAULT GETDATE()
)
DISTSTYLE AUTO
SORTKEY (pcs_created, ship_date);

GRANT ALL ON shipping_costs.expected_shipping_costs_maersk_us_all_us TO tcg_nfe;


-- =============================================================================
-- P2P SHIPMENTS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS shipping_costs.expected_shipping_costs_maersk_us_p2p (
    -- Identification (7)
    pcs_orderid             BIGINT,
    pcs_ordernumber         VARCHAR(50),
    latest_trackingnumber   VARCHAR(50),
    trackingnumber_count    INTEGER,
    shop_ordernumber        VARCHAR(100),
    packagetype             VARCHAR(100),
    pcs_shipping_provider   VARCHAR(50),

    -- Dates (2)
    pcs_created             TIMESTAMP,
    ship_date               DATE,

    -- Location (5)
    production_site         VARCHAR(50),
    shipping_zip_code       VARCHAR(20),
    shipping_region         VARCHAR(50),
    shipping_country        VARCHAR(50),
    shipping_zone           INTEGER,            -- Zone 1-9

    -- Dimensions imperial (4)
    length_in               DECIMAL(10,2),
    width_in                DECIMAL(10,2),
    height_in               DECIMAL(10,2),
    weight_lbs              DECIMAL(10,4),

    -- Calculated dimensions (3)
    cubic_in                DECIMAL(12,2),
    longest_side_in         DECIMAL(10,2),
    second_longest_in       DECIMAL(10,2),

    -- Weight calculations (3)
    dim_weight_lbs          DECIMAL(10,4),
    uses_dim_weight         BOOLEAN,
    billable_weight_lbs     DECIMAL(10,4),

    -- Surcharge flags (4)
    surcharge_nsl1          BOOLEAN,            -- Nonstandard Length >21"
    surcharge_nsl2          BOOLEAN,            -- Nonstandard Length >30"
    surcharge_nsd           BOOLEAN,            -- Nonstandard Dimensions >3456 cu in
    surcharge_pickup        BOOLEAN,            -- Pickup Fee (always true)

    -- Costs (8)
    cost_base               DECIMAL(10,2),
    cost_nsl1               DECIMAL(10,2),
    cost_nsl2               DECIMAL(10,2),
    cost_nsd                DECIMAL(10,2),
    cost_pickup             DECIMAL(10,2),      -- $0.04/lb (rounded up)
    cost_subtotal           DECIMAL(10,2),
    cost_total              DECIMAL(10,2),      -- Same as subtotal (no fuel)
    cost_total_multishipment DECIMAL(10,2),     -- cost_total * trackingnumber_count

    -- Metadata (2)
    calculator_version      VARCHAR(30),
    dw_timestamp            TIMESTAMP DEFAULT GETDATE()
)
DISTSTYLE AUTO
SORTKEY (pcs_created, ship_date);

GRANT ALL ON shipping_costs.expected_shipping_costs_maersk_us_p2p TO tcg_nfe;
