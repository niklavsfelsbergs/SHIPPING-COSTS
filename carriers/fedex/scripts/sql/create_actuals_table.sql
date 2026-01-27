-- Create actual_shipping_costs_fedex table
-- FedEx invoice actual costs, charges mapped from charge_description
--
-- Run this DDL in Redshift before using upload_actuals.py

CREATE TABLE IF NOT EXISTS shipping_costs.actual_shipping_costs_fedex (
    -- Identification
    pcs_orderid             BIGINT,
    trackingnumber          VARCHAR(50),
    invoice_number          VARCHAR(50),
    invoice_date            DATE,

    -- Shipment info from invoice
    shipment_date           DATE,
    service_type            VARCHAR(100),
    actual_zone             VARCHAR(10),
    actual_weight_lbs       DECIMAL(10,4),
    rated_weight_lbs        DECIMAL(10,4),

    -- Expected charges (mapped from charge_description)
    actual_base             DECIMAL(10,2),
    actual_ahs              DECIMAL(10,2),
    actual_ahs_weight       DECIMAL(10,2),
    actual_das              DECIMAL(10,2),
    actual_residential      DECIMAL(10,2),
    actual_oversize         DECIMAL(10,2),
    actual_dem_base         DECIMAL(10,2),
    actual_dem_ahs          DECIMAL(10,2),
    actual_dem_oversize     DECIMAL(10,2),
    actual_dem_residential  DECIMAL(10,2),
    actual_fuel             DECIMAL(10,2),

    -- Discounts (negative values)
    actual_performance_pricing DECIMAL(10,2),
    actual_earned_discount  DECIMAL(10,2),
    actual_grace_discount   DECIMAL(10,2),
    actual_discount         DECIMAL(10,2),

    -- Unpredictable charges (catch-all for unmapped charges)
    actual_unpredictable    DECIMAL(10,2),

    -- Totals from invoice
    actual_net_charge       DECIMAL(10,2),
    actual_transportation   DECIMAL(10,2),

    -- Metadata
    dw_timestamp            TIMESTAMP DEFAULT GETDATE()
)
DISTSTYLE AUTO
SORTKEY (invoice_date, shipment_date);

-- Grant permissions
GRANT ALL ON shipping_costs.actual_shipping_costs_fedex TO tcg_nfe;
