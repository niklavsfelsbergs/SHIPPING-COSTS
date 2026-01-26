WITH fedex_invoice AS (
    SELECT * 
    FROM bi_stage_dev_dbo.fedex_invoicedata_historical f 
    WHERE invoice_date::date >= '2025-01-01' and invoice_date::date < '2026-01-01'
--        AND CASE
--                WHEN f.express_or_ground_tracking_id LIKE '%.%' 
--                THEN f.express_or_ground_tracking_id::numeric::text
--                ELSE f.express_or_ground_tracking_id::text
--            END = '884598556596'
)
, charge_positions AS (
    SELECT 0 AS n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 
    UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
    UNION ALL SELECT 10 UNION ALL SELECT 11 UNION ALL SELECT 12 UNION ALL SELECT 13 UNION ALL SELECT 14
    UNION ALL SELECT 15 UNION ALL SELECT 16 UNION ALL SELECT 17 UNION ALL SELECT 18 UNION ALL SELECT 19
    UNION ALL SELECT 20 UNION ALL SELECT 21 UNION ALL SELECT 22 UNION ALL SELECT 23 UNION ALL SELECT 24
)
, unpivoted_charges AS (
    SELECT
        f.invoice_date::date AS invoice_date,
        f.invoice_number AS invoice_number,
        CASE
            WHEN f.express_or_ground_tracking_id LIKE '%.%'
            THEN f.express_or_ground_tracking_id::numeric::text
            ELSE f.express_or_ground_tracking_id::text
        END AS trackingnumber,
        f.crossreftrackingid_prefix || f.crossreftrackingid AS pcs_trackingnumber,
        REPLACE(f.transportation_charge_amount, ',', '')::numeric(38,4) AS transportation_charge_usd,
        REPLACE(f.net_charge_amount, ',', '')::numeric(38,4) AS net_charge_usd,
        f.service_type,
        f.ground_service,
        COALESCE(f.shipment_date::date, f.invoice_date::date) AS shipment_date,
        f.pod_delivery_date::date AS pod_delivery_date,
        f.actual_weight_amount AS actual_weight,
        f.actual_weight_units,
        f.rated_weight_amount AS rated_weight,
        f.rated_weight_units,
        f.number_of_pieces,
        f.recipient_city,
        f.recipient_state,
        f.recipient_zip_code,
        f.recipient_country_territory,
        f.original_customer_reference,
        f.zone_code AS shipping_zone,
        CASE p.n
            WHEN 0 THEN f.tracking_id_charge_description
            WHEN 1 THEN f.tracking_id_charge_description_1
            WHEN 2 THEN f.tracking_id_charge_description_2
            WHEN 3 THEN f.tracking_id_charge_description_3
            WHEN 4 THEN f.tracking_id_charge_description_4
            WHEN 5 THEN f.tracking_id_charge_description_5
            WHEN 6 THEN f.tracking_id_charge_description_6
            WHEN 7 THEN f.tracking_id_charge_description_7
            WHEN 8 THEN f.tracking_id_charge_description_8
            WHEN 9 THEN f.tracking_id_charge_description_9
            WHEN 10 THEN f.tracking_id_charge_description_10
            WHEN 11 THEN f.tracking_id_charge_description_11
            WHEN 12 THEN f.tracking_id_charge_description_12
            WHEN 13 THEN f.tracking_id_charge_description_13
            WHEN 14 THEN f.tracking_id_charge_description_14
            WHEN 15 THEN f.tracking_id_charge_description_15
            WHEN 16 THEN f.tracking_id_charge_description_16
            WHEN 17 THEN f.tracking_id_charge_description_17
            WHEN 18 THEN f.tracking_id_charge_description_18
            WHEN 19 THEN f.tracking_id_charge_description_19
            WHEN 20 THEN f.tracking_id_charge_description_20
            WHEN 21 THEN f.tracking_id_charge_description_21
            WHEN 22 THEN f.tracking_id_charge_description_22
            WHEN 23 THEN f.tracking_id_charge_description_23
            WHEN 24 THEN f.tracking_id_charge_description_24
        END AS charge_description,
        REPLACE(
            CASE p.n
                WHEN 0 THEN f.tracking_id_charge_amount
                WHEN 1 THEN f.tracking_id_charge_amount_1
                WHEN 2 THEN f.tracking_id_charge_amount_2
                WHEN 3 THEN f.tracking_id_charge_amount_3
                WHEN 4 THEN f.tracking_id_charge_amount_4
                WHEN 5 THEN f.tracking_id_charge_amount_5
                WHEN 6 THEN f.tracking_id_charge_amount_6
                WHEN 7 THEN f.tracking_id_charge_amount_7
                WHEN 8 THEN f.tracking_id_charge_amount_8
                WHEN 9 THEN f.tracking_id_charge_amount_9
                WHEN 10 THEN f.tracking_id_charge_amount_10
                WHEN 11 THEN f.tracking_id_charge_amount_11
                WHEN 12 THEN f.tracking_id_charge_amount_12
                WHEN 13 THEN f.tracking_id_charge_amount_13
                WHEN 14 THEN f.tracking_id_charge_amount_14
                WHEN 15 THEN f.tracking_id_charge_amount_15
                WHEN 16 THEN f.tracking_id_charge_amount_16
                WHEN 17 THEN f.tracking_id_charge_amount_17
                WHEN 18 THEN f.tracking_id_charge_amount_18
                WHEN 19 THEN f.tracking_id_charge_amount_19
                WHEN 20 THEN f.tracking_id_charge_amount_20
                WHEN 21 THEN f.tracking_id_charge_amount_21
                WHEN 22 THEN f.tracking_id_charge_amount_22
                WHEN 23 THEN f.tracking_id_charge_amount_23
                WHEN 24 THEN f.tracking_id_charge_amount_24
            END, ',', '')::numeric(38,4) AS charge_amount
    FROM fedex_invoice f
    CROSS JOIN charge_positions p
    WHERE CASE p.n
            WHEN 0 THEN f.tracking_id_charge_amount
            WHEN 1 THEN f.tracking_id_charge_amount_1
            WHEN 2 THEN f.tracking_id_charge_amount_2
            WHEN 3 THEN f.tracking_id_charge_amount_3
            WHEN 4 THEN f.tracking_id_charge_amount_4
            WHEN 5 THEN f.tracking_id_charge_amount_5
            WHEN 6 THEN f.tracking_id_charge_amount_6
            WHEN 7 THEN f.tracking_id_charge_amount_7
            WHEN 8 THEN f.tracking_id_charge_amount_8
            WHEN 9 THEN f.tracking_id_charge_amount_9
            WHEN 10 THEN f.tracking_id_charge_amount_10
            WHEN 11 THEN f.tracking_id_charge_amount_11
            WHEN 12 THEN f.tracking_id_charge_amount_12
            WHEN 13 THEN f.tracking_id_charge_amount_13
            WHEN 14 THEN f.tracking_id_charge_amount_14
            WHEN 15 THEN f.tracking_id_charge_amount_15
            WHEN 16 THEN f.tracking_id_charge_amount_16
            WHEN 17 THEN f.tracking_id_charge_amount_17
            WHEN 18 THEN f.tracking_id_charge_amount_18
            WHEN 19 THEN f.tracking_id_charge_amount_19
            WHEN 20 THEN f.tracking_id_charge_amount_20
            WHEN 21 THEN f.tracking_id_charge_amount_21
            WHEN 22 THEN f.tracking_id_charge_amount_22
            WHEN 23 THEN f.tracking_id_charge_amount_23
            WHEN 24 THEN f.tracking_id_charge_amount_24
        END IS NOT NULL
)
SELECT
    invoice_date,
    invoice_number,
    trackingnumber,
    pcs_trackingnumber,
    transportation_charge_usd,
    net_charge_usd,
    service_type,
    ground_service,
    shipment_date,
    pod_delivery_date,
    actual_weight,
    actual_weight_units,
    rated_weight,
    rated_weight_units,
    number_of_pieces,
    recipient_city,
    recipient_state,
    recipient_zip_code,
    recipient_country_territory,
    original_customer_reference,
    shipping_zone,
    charge_description,
    charge_amount AS charge_description_amount
FROM unpivoted_charges

UNION ALL

-- Base charge calculation
SELECT
    invoice_date,
    invoice_number,
    trackingnumber,
    pcs_trackingnumber,
    transportation_charge_usd,
    net_charge_usd,
    service_type,
    ground_service,
    shipment_date,
    pod_delivery_date,
    actual_weight,
    actual_weight_units,
    rated_weight,
    rated_weight_units,
    number_of_pieces,
    recipient_city,
    recipient_state,
    recipient_zip_code,
    recipient_country_territory,
    original_customer_reference,
    shipping_zone,
    'Base Charge' AS charge_description,
    (net_charge_usd - SUM(charge_amount))::numeric(38,4) AS charge_description_amount
FROM unpivoted_charges
GROUP BY
    invoice_date, invoice_number, trackingnumber, pcs_trackingnumber, transportation_charge_usd,
    net_charge_usd, service_type, ground_service, shipment_date, pod_delivery_date,
    actual_weight, actual_weight_units, rated_weight, rated_weight_units,
    number_of_pieces, recipient_city, recipient_state, recipient_zip_code,
    recipient_country_territory, original_customer_reference, shipping_zone