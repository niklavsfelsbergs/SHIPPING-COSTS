"""Test using actual weight only (no DIM weight)."""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import polars as pl
from shared.database import pull_data
from carriers.fedex.calculate_costs import calculate_costs
from carriers.fedex.data import load_base_rates_home_delivery

# Load PCS shipments
query = """
WITH trackingnumbers AS (
    SELECT orderid, trackingnumber,
        ROW_NUMBER() OVER (PARTITION BY orderid ORDER BY id DESC) AS row_nr
    FROM bi_stage_dev_dbo.pcsu_sentparcels
)
SELECT
    tn.trackingnumber AS latest_trackingnumber,
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
WHERE ps.extkey = 'FXEHD'
  AND pp."name" IN ('Columbus', 'Phoenix')
  AND po.createddate >= '2025-01-01'
  AND tn.trackingnumber IS NOT NULL
LIMIT 500
"""
print("Loading PCS shipments...")
pcs_df = pull_data(query)
print(f"  Loaded {len(pcs_df)} shipments")

# Load invoice data with performance pricing
invoice_query = """
WITH charge_positions AS (
    SELECT 0 AS n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
    UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
),
performance_pricing AS (
    SELECT
        CASE WHEN f.express_or_ground_tracking_id LIKE '%.%'
            THEN f.express_or_ground_tracking_id::numeric::text
            ELSE f.express_or_ground_tracking_id::text END AS trackingnumber,
        SUM(CASE WHEN CASE p.n
            WHEN 0 THEN f.tracking_id_charge_description WHEN 1 THEN f.tracking_id_charge_description_1
            WHEN 2 THEN f.tracking_id_charge_description_2 WHEN 3 THEN f.tracking_id_charge_description_3
            WHEN 4 THEN f.tracking_id_charge_description_4 WHEN 5 THEN f.tracking_id_charge_description_5
            WHEN 6 THEN f.tracking_id_charge_description_6 WHEN 7 THEN f.tracking_id_charge_description_7
            WHEN 8 THEN f.tracking_id_charge_description_8 WHEN 9 THEN f.tracking_id_charge_description_9
        END = 'Performance Pricing'
        THEN REPLACE(CASE p.n
            WHEN 0 THEN f.tracking_id_charge_amount WHEN 1 THEN f.tracking_id_charge_amount_1
            WHEN 2 THEN f.tracking_id_charge_amount_2 WHEN 3 THEN f.tracking_id_charge_amount_3
            WHEN 4 THEN f.tracking_id_charge_amount_4 WHEN 5 THEN f.tracking_id_charge_amount_5
            WHEN 6 THEN f.tracking_id_charge_amount_6 WHEN 7 THEN f.tracking_id_charge_amount_7
            WHEN 8 THEN f.tracking_id_charge_amount_8 WHEN 9 THEN f.tracking_id_charge_amount_9
        END, ',', '')::float8 ELSE 0 END) AS pp_amount
    FROM bi_stage_dev_dbo.fedex_invoicedata_historical f
    CROSS JOIN charge_positions p
    WHERE f.invoice_date::date >= '2025-01-01' AND f.service_type = 'Home Delivery'
    GROUP BY 1
)
SELECT
    CASE WHEN f.express_or_ground_tracking_id LIKE '%.%'
        THEN f.express_or_ground_tracking_id::numeric::text
        ELSE f.express_or_ground_tracking_id::text END AS trackingnumber,
    REPLACE(f.rated_weight_amount, ',', '')::float8 AS invoice_rated_weight,
    REPLACE(f.transportation_charge_amount, ',', '')::float8 AS invoice_transportation_charge,
    COALESCE(pp.pp_amount, 0) AS invoice_performance_pricing
FROM bi_stage_dev_dbo.fedex_invoicedata_historical f
LEFT JOIN performance_pricing pp ON pp.trackingnumber = CASE WHEN f.express_or_ground_tracking_id LIKE '%.%'
    THEN f.express_or_ground_tracking_id::numeric::text ELSE f.express_or_ground_tracking_id::text END
WHERE f.invoice_date::date >= '2025-01-01' AND f.service_type = 'Home Delivery'
"""
print("Loading invoice data...")
invoice_df = pull_data(invoice_query)
print(f"  Loaded {len(invoice_df)} invoice records")

# Calculate with current logic (uses DIM weight)
print("\nCalculating with current logic...")
calculated_df = calculate_costs(pcs_df)

# Join with invoice
comparison_df = calculated_df.join(
    invoice_df,
    left_on='latest_trackingnumber',
    right_on='trackingnumber',
    how='inner'
)
print(f"  Matched {len(comparison_df)} shipments")

# Filter out data quality issues
df = comparison_df.filter(
    (pl.col('cubic_in') > 0) &
    (pl.col('invoice_rated_weight') >= (pl.col('weight_lbs') * 0.5))
)
print(f"  Clean records: {len(df)}")

# Calculate invoice base
df = df.with_columns(
    (pl.col('invoice_transportation_charge') + pl.col('invoice_performance_pricing'))
    .alias('invoice_base')
)

# Calculate variance with current DIM logic
df = df.with_columns(
    (pl.col('cost_base_list') - pl.col('invoice_base')).alias('variance_with_dim')
)

print("\n" + "="*70)
print("COMPARISON: DIM WEIGHT vs ACTUAL WEIGHT")
print("="*70)

print("\nWith current DIM weight logic:")
print(f"  Total expected (DIM): ${df['cost_base_list'].sum():,.2f}")
print(f"  Total invoice base:   ${df['invoice_base'].sum():,.2f}")
variance_pct = (df['cost_base_list'].sum() - df['invoice_base'].sum()) / df['invoice_base'].sum() * 100
print(f"  Variance: {variance_pct:+.2f}%")

# Now recalculate using ACTUAL weight only
print("\nRecalculating with ACTUAL weight only (no DIM)...")

df = df.with_columns(
    pl.col('weight_lbs').ceil().clip(1, 150).cast(pl.Int64).alias('actual_weight_bracket')
)

# Prepare rate lookup
hd_rates = load_base_rates_home_delivery()
hd_long = hd_rates.unpivot(index='weight_lbs', variable_name='zone', value_name='rate')
hd_long = hd_long.with_columns(
    pl.col('zone').str.replace('zone_', '').cast(pl.Int64).alias('zone')
)

df = df.with_columns(
    pl.when(pl.col('shipping_zone').is_in([2,3,4,5,6,7,8,9,17]))
    .then(pl.col('shipping_zone'))
    .otherwise(pl.lit(17))
    .cast(pl.Int64)
    .alias('rate_zone')
)

df = df.join(
    hd_long,
    left_on=['actual_weight_bracket', 'rate_zone'],
    right_on=['weight_lbs', 'zone'],
    how='left'
).rename({'rate': 'rate_actual_weight'})

df = df.with_columns(
    (pl.col('rate_actual_weight') - pl.col('invoice_base')).alias('variance_actual')
)

df_valid = df.filter(pl.col('rate_actual_weight').is_not_null())

print(f"\nWith ACTUAL weight only:")
print(f"  Total expected (actual): ${df_valid['rate_actual_weight'].sum():,.2f}")
print(f"  Total invoice base:      ${df_valid['invoice_base'].sum():,.2f}")
variance_pct = (df_valid['rate_actual_weight'].sum() - df_valid['invoice_base'].sum()) / df_valid['invoice_base'].sum() * 100
print(f"  Variance: {variance_pct:+.2f}%")

# Show sample
print("\nSample comparison:")
print(df_valid.select([
    'shipping_zone',
    'weight_lbs',
    'dim_weight_lbs',
    'billable_weight_lbs',
    'actual_weight_bracket',
    'invoice_rated_weight',
    'cost_base_list',
    'rate_actual_weight',
    'invoice_base',
    'variance_with_dim',
    'variance_actual',
]).head(15))
