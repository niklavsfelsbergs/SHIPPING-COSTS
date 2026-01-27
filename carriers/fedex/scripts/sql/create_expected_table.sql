-- Create expected_shipping_costs_fedex table
-- FedEx Ground/Home Delivery expected costs from calculator
--
-- Run this DDL in Redshift before using upload_expected.py

CREATE TABLE IF NOT EXISTS shipping_costs.expected_shipping_costs_fedex (
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

    -- Location (6)
    production_site         VARCHAR(50),
    shipping_zip_code       VARCHAR(20),
    shipping_region         VARCHAR(50),
    shipping_country        VARCHAR(50),
    shipping_zone           INTEGER,
    das_zone                VARCHAR(20),

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

    -- Service and weight (4)
    rate_service            VARCHAR(30),
    dim_weight_lbs          DECIMAL(10,4),
    uses_dim_weight         BOOLEAN,
    billable_weight_lbs     DECIMAL(10,4),

    -- Surcharge flags (8)
    surcharge_ahs           BOOLEAN,
    surcharge_ahs_weight    BOOLEAN,
    surcharge_oversize      BOOLEAN,
    surcharge_das           BOOLEAN,
    surcharge_residential   BOOLEAN,
    surcharge_dem_base      BOOLEAN,
    surcharge_dem_ahs       BOOLEAN,
    surcharge_dem_oversize  BOOLEAN,

    -- Costs - Rate components (4)
    cost_base_rate          DECIMAL(10,2),
    cost_performance_pricing DECIMAL(10,2),
    cost_earned_discount    DECIMAL(10,2),
    cost_grace_discount     DECIMAL(10,2),

    -- Costs - Surcharges (8)
    cost_ahs                DECIMAL(10,2),
    cost_ahs_weight         DECIMAL(10,2),
    cost_oversize           DECIMAL(10,2),
    cost_das                DECIMAL(10,2),
    cost_residential        DECIMAL(10,2),
    cost_dem_base           DECIMAL(10,2),
    cost_dem_ahs            DECIMAL(10,2),
    cost_dem_oversize       DECIMAL(10,2),

    -- Costs - Totals (4)
    cost_subtotal           DECIMAL(10,2),
    cost_fuel               DECIMAL(10,2),
    cost_total              DECIMAL(10,2),
    cost_total_multishipment DECIMAL(10,2),

    -- Metadata (2)
    calculator_version      VARCHAR(20),
    dw_timestamp            TIMESTAMP DEFAULT GETDATE()
)
DISTSTYLE AUTO
SORTKEY (pcs_created, ship_date);

-- Grant permissions
GRANT ALL ON shipping_costs.expected_shipping_costs_fedex TO tcg_nfe;
