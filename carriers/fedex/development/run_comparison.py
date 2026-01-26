"""Quick comparison script for FXESPPS and FXEHD only."""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import polars as pl
from shared.database import pull_data
from carriers.fedex.calculate_costs import calculate_costs

# Load PCS shipments with specific extkeys only
query = """
WITH trackingnumbers AS (
    SELECT
        orderid,
        trackingnumber,
        COUNT(*) OVER (PARTITION BY orderid) AS trackingnumber_count,
        ROW_NUMBER() OVER (PARTITION BY orderid ORDER BY id DESC) AS row_nr
    FROM bi_stage_dev_dbo.pcsu_sentparcels
)
SELECT
    po.id AS pcs_orderid,
    po.ordernumber AS pcs_ordernumber,
    tn.trackingnumber AS latest_trackingnumber,
    tn.trackingnumber_count,
    po.createddate AS pcs_created,
    (po.createddate + INTERVAL '2 days')::date AS ship_date,
    pp."name" AS production_site,
    po.shippingzipcode AS shipping_zip_code,
    po.shippingregion AS shipping_region,
    ps.extkey AS pcs_shipping_provider,
    (GREATEST(po.packagelength, po.packagewidth) / 10.0 * 0.39370079)::float8 AS length_in,
    (LEAST(po.packagelength, po.packagewidth) / 10.0 * 0.39370079)::float8 AS width_in,
    (po.packageheight / 10.0 * 0.39370079)::float8 AS height_in,
    (po.packageweight * 2.20462262)::float8 AS weight_lbs
FROM bi_stage_dev_dbo.pcsu_orders po
JOIN bi_stage_dev_dbo.pcsu_productionsites pp ON pp.id = po.productionsiteid
JOIN bi_stage_dev_dbo.pcsu_shippingproviders ps ON ps.id = po.shippingproviderid
LEFT JOIN trackingnumbers tn ON tn.orderid = po.id AND tn.row_nr = 1
WHERE ps.extkey IN ('FXESPPS', 'FXEHD')
  AND pp."name" IN ('Columbus', 'Phoenix')
  AND po.createddate >= '2025-01-01'
  AND tn.trackingnumber IS NOT NULL
LIMIT 1000
"""

print('Loading PCS shipments (FXESPPS, FXEHD only)...')
pcs_df = pull_data(query)
print(f'  Loaded {len(pcs_df)} PCS shipments')
print(f'  By extkey:')
print(pcs_df.group_by("pcs_shipping_provider").len().sort("pcs_shipping_provider"))

# Load invoice data
print('\nLoading invoice data...')
invoice_query = """
WITH charge_positions AS (
    SELECT 0 AS n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
    UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
    UNION ALL SELECT 10 UNION ALL SELECT 11 UNION ALL SELECT 12 UNION ALL SELECT 13 UNION ALL SELECT 14
    UNION ALL SELECT 15 UNION ALL SELECT 16 UNION ALL SELECT 17 UNION ALL SELECT 18 UNION ALL SELECT 19
    UNION ALL SELECT 20 UNION ALL SELECT 21 UNION ALL SELECT 22 UNION ALL SELECT 23 UNION ALL SELECT 24
),
performance_pricing AS (
    SELECT
        CASE
            WHEN f.express_or_ground_tracking_id LIKE '%.%'
            THEN f.express_or_ground_tracking_id::numeric::text
            ELSE f.express_or_ground_tracking_id::text
        END AS trackingnumber,
        SUM(
            CASE WHEN
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
                END = 'Performance Pricing'
            THEN REPLACE(
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
                END, ',', '')::float8
            ELSE 0 END
        ) AS performance_pricing_amount
    FROM bi_stage_dev_dbo.fedex_invoicedata_historical f
    CROSS JOIN charge_positions p
    WHERE f.invoice_date::date >= '2025-01-01'
      AND f.service_type IN ('Home Delivery', 'SmartPost')
    GROUP BY 1
)
SELECT
    CASE
        WHEN f.express_or_ground_tracking_id LIKE '%.%'
        THEN f.express_or_ground_tracking_id::numeric::text
        ELSE f.express_or_ground_tracking_id::text
    END AS trackingnumber,
    f.invoice_date::date AS invoice_date,
    f.service_type AS invoice_service_type,
    f.zone_code AS invoice_zone,
    REPLACE(f.rated_weight_amount, ',', '')::float8 AS invoice_rated_weight,
    REPLACE(f.transportation_charge_amount, ',', '')::float8 AS invoice_transportation_charge,
    COALESCE(pp.performance_pricing_amount, 0) AS invoice_performance_pricing,
    REPLACE(f.net_charge_amount, ',', '')::float8 AS invoice_net_charge
FROM bi_stage_dev_dbo.fedex_invoicedata_historical f
LEFT JOIN performance_pricing pp ON pp.trackingnumber = CASE
        WHEN f.express_or_ground_tracking_id LIKE '%.%'
        THEN f.express_or_ground_tracking_id::numeric::text
        ELSE f.express_or_ground_tracking_id::text
    END
WHERE f.invoice_date::date >= '2025-01-01'
  AND f.service_type IN ('Home Delivery', 'SmartPost')
"""
invoice_df = pull_data(invoice_query)
print(f'  Loaded {len(invoice_df)} invoice records')

# Calculate costs
print('\nCalculating expected costs...')
calculated_df = calculate_costs(pcs_df)
print(f'  Calculated costs for {len(calculated_df)} shipments')

# Join
print('\nJoining...')
comparison_df = calculated_df.join(
    invoice_df,
    left_on='latest_trackingnumber',
    right_on='trackingnumber',
    how='inner'
)
print(f'  Matched {len(comparison_df)} shipments')

# Calculate invoice base after discount
comparison_df = comparison_df.with_columns(
    (pl.col('invoice_transportation_charge') + pl.col('invoice_performance_pricing'))
    .alias('invoice_base_after_discount')
)

# Calculate variance
comparison_df = comparison_df.with_columns([
    (pl.col('cost_base_list') - pl.col('invoice_base_after_discount')).alias('base_variance'),
    ((pl.col('cost_base_list') - pl.col('invoice_base_after_discount')) / pl.col('invoice_base_after_discount') * 100).alias('base_variance_pct'),
])

# Summary
print()
print('=' * 70)
print('COMPARISON SUMMARY')
print('=' * 70)

print(f'\nTotal matched shipments: {len(comparison_df)}')

print('\nBy Service Type:')
service_summary = comparison_df.group_by('rate_service').agg([
    pl.len().alias('count'),
    pl.col('cost_base_list').mean().alias('avg_expected'),
    pl.col('invoice_base_after_discount').mean().alias('avg_invoice_base'),
    pl.col('base_variance').mean().alias('avg_variance'),
    pl.col('base_variance_pct').mean().alias('avg_variance_pct'),
])
print(service_summary)

print('\nOverall:')
print(f'  Expected (cost_base_list) total:        ${comparison_df["cost_base_list"].sum():,.2f}')
print(f'  Invoice base after discount total:      ${comparison_df["invoice_base_after_discount"].sum():,.2f}')
variance = comparison_df['cost_base_list'].sum() - comparison_df['invoice_base_after_discount'].sum()
variance_pct = variance / comparison_df['invoice_base_after_discount'].sum() * 100
print(f'  Variance: ${variance:,.2f} ({variance_pct:+.2f}%)')

print('\nSample rows:')
print(comparison_df.select([
    'rate_service',
    'pcs_shipping_provider',
    'shipping_zone',
    'invoice_zone',
    'billable_weight_lbs',
    'invoice_rated_weight',
    'cost_base_list',
    'invoice_transportation_charge',
    'invoice_performance_pricing',
    'invoice_base_after_discount',
    'base_variance',
]).head(15))
