"""
Compare Nov/Dec calculated vs invoice totals for Home Delivery and SmartPost.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import polars as pl
from pathlib import Path
from shared.database import pull_data

RATE_TABLES = Path(__file__).parent / "final_rate_tables"


def to_long(df, value_name):
    return df.unpivot(
        index='weight_lbs',
        variable_name='zone_col',
        value_name=value_name
    ).with_columns(
        pl.col('zone_col').str.replace('zone_', '').cast(pl.Int64).alias('zone')
    ).select(['weight_lbs', 'zone', value_name])


def main():
    # Load rate tables
    hd_undiscounted = pl.read_csv(RATE_TABLES / 'home_delivery_undiscounted_rates.csv')
    sp_undiscounted = pl.read_csv(RATE_TABLES / 'smartpost_undiscounted_rates.csv')
    hd_pp = pl.read_csv(RATE_TABLES / 'home_delivery_performance_pricing.csv')
    hd_earned = pl.read_csv(RATE_TABLES / 'home_delivery_earned_discount.csv')
    hd_grace = pl.read_csv(RATE_TABLES / 'home_delivery_grace_discount.csv')
    sp_pp = pl.read_csv(RATE_TABLES / 'smartpost_performance_pricing.csv')
    sp_earned = pl.read_csv(RATE_TABLES / 'smartpost_earned_discount.csv')
    sp_grace = pl.read_csv(RATE_TABLES / 'smartpost_grace_discount.csv')

    # Convert to long format
    hd_und_long = to_long(hd_undiscounted, 'undiscounted')
    sp_und_long = to_long(sp_undiscounted, 'undiscounted')
    hd_pp_long = to_long(hd_pp, 'pp')
    hd_earned_long = to_long(hd_earned, 'earned')
    hd_grace_long = to_long(hd_grace, 'grace')
    sp_pp_long = to_long(sp_pp, 'pp')
    sp_earned_long = to_long(sp_earned, 'earned')
    sp_grace_long = to_long(sp_grace, 'grace')

    # Pull invoice data
    query = """
    WITH charge_positions AS (
        SELECT 0 AS n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
        UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
    )
    SELECT
        CASE
            WHEN f.express_or_ground_tracking_id LIKE '%.%'
            THEN f.express_or_ground_tracking_id::numeric::text
            ELSE f.express_or_ground_tracking_id::text
        END AS trackingnumber,
        f.service_type,
        f.zone_code AS shipping_zone,
        REPLACE(f.rated_weight_amount, ',', '')::float8 AS rated_weight,
        REPLACE(f.transportation_charge_amount, ',', '')::float8 AS base_charge,
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
        END AS charge_description,
        REPLACE(CASE p.n
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
        END, ',', '')::float8 AS charge_amount
    FROM bi_stage_dev_dbo.fedex_invoicedata_historical f
    CROSS JOIN charge_positions p
    WHERE f.invoice_date::date >= '2025-11-01'
      AND f.invoice_date::date <= '2025-12-31'
      AND f.service_type IN ('Home Delivery', 'SmartPost')
      AND f.zone_code IN ('2', '3', '4', '5', '6', '7', '8', '9', '17', '02', '03', '04', '05', '06', '07', '08', '09')
    """
    df = pull_data(query)
    print(f"Loaded {len(df):,} charge rows")

    df = df.with_columns([
        pl.col('rated_weight').cast(pl.Int64).alias('weight'),
        pl.col('shipping_zone').str.replace('^0', '').cast(pl.Int64).alias('zone')
    ])

    # Get invoice totals per shipment
    invoice_pp = df.filter(pl.col('charge_description') == 'Performance Pricing').group_by(
        ['trackingnumber', 'service_type', 'weight', 'zone', 'base_charge']
    ).agg(pl.col('charge_amount').sum().alias('invoice_pp'))

    invoice_earned = df.filter(pl.col('charge_description') == 'Earned Discount').group_by(
        ['trackingnumber']
    ).agg(pl.col('charge_amount').sum().alias('invoice_earned'))

    invoice_grace = df.filter(pl.col('charge_description') == 'Grace Discount').group_by(
        ['trackingnumber']
    ).agg(pl.col('charge_amount').sum().alias('invoice_grace'))

    # Build shipment-level data
    shipments = invoice_pp.join(invoice_earned, on='trackingnumber', how='left')
    shipments = shipments.join(invoice_grace, on='trackingnumber', how='left')
    shipments = shipments.with_columns([
        pl.col('invoice_earned').fill_null(0),
        pl.col('invoice_grace').fill_null(0)
    ])

    print(f"Unique shipments: {len(shipments):,}")

    # Split by service type
    hd_shipments = shipments.filter(pl.col('service_type') == 'Home Delivery')
    sp_shipments = shipments.filter(pl.col('service_type') == 'SmartPost')

    print(f"Home Delivery: {len(hd_shipments):,}")
    print(f"SmartPost: {len(sp_shipments):,}")

    # Join with rate tables - HOME DELIVERY
    hd_calc = hd_shipments.join(hd_und_long, left_on=['weight', 'zone'], right_on=['weight_lbs', 'zone'], how='left')
    hd_calc = hd_calc.join(hd_pp_long, left_on=['weight', 'zone'], right_on=['weight_lbs', 'zone'], how='left')
    hd_calc = hd_calc.join(hd_earned_long, left_on=['weight', 'zone'], right_on=['weight_lbs', 'zone'], how='left')
    hd_calc = hd_calc.join(hd_grace_long, left_on=['weight', 'zone'], right_on=['weight_lbs', 'zone'], how='left')

    hd_calc = hd_calc.with_columns([
        (pl.col('undiscounted') + pl.col('pp').fill_null(0) + pl.col('earned').fill_null(0) + pl.col('grace').fill_null(0)).alias('calc_total'),
        (pl.col('base_charge') + pl.col('invoice_pp') + pl.col('invoice_earned') + pl.col('invoice_grace')).alias('invoice_total')
    ])

    # Join with rate tables - SMARTPOST
    sp_calc = sp_shipments.join(sp_und_long, left_on=['weight', 'zone'], right_on=['weight_lbs', 'zone'], how='left')
    sp_calc = sp_calc.join(sp_pp_long, left_on=['weight', 'zone'], right_on=['weight_lbs', 'zone'], how='left')
    sp_calc = sp_calc.join(sp_earned_long, left_on=['weight', 'zone'], right_on=['weight_lbs', 'zone'], how='left')
    sp_calc = sp_calc.join(sp_grace_long, left_on=['weight', 'zone'], right_on=['weight_lbs', 'zone'], how='left')

    sp_calc = sp_calc.with_columns([
        (pl.col('undiscounted') + pl.col('pp').fill_null(0) + pl.col('earned').fill_null(0) + pl.col('grace').fill_null(0)).alias('calc_total'),
        (pl.col('base_charge') + pl.col('invoice_pp') + pl.col('invoice_earned') + pl.col('invoice_grace')).alias('invoice_total')
    ])

    # Report - HOME DELIVERY
    print('\n' + '=' * 80)
    print('HOME DELIVERY - NOV/DEC 2025')
    print('=' * 80)
    hd_invoice_sum = hd_calc['invoice_total'].sum()
    hd_calc_sum = hd_calc['calc_total'].sum()
    hd_diff = hd_calc_sum - hd_invoice_sum
    hd_pct = (hd_diff / hd_invoice_sum) * 100
    print(f"Shipments: {len(hd_calc):,}")
    print(f"Invoice total (base+pp+earned+grace): ${hd_invoice_sum:,.2f}")
    print(f"Calculated total (und+pp+earned+grace): ${hd_calc_sum:,.2f}")
    print(f"Difference: ${hd_diff:,.2f} ({hd_pct:+.2f}%)")

    hd_calc = hd_calc.with_columns((pl.col('calc_total') - pl.col('invoice_total')).abs().alias('diff'))
    hd_exact = hd_calc.filter(pl.col('diff') < 0.02)
    print(f"Exact matches (<$0.02): {len(hd_exact):,} / {len(hd_calc):,} ({len(hd_exact)/len(hd_calc)*100:.1f}%)")

    # Report - SMARTPOST
    print('\n' + '=' * 80)
    print('SMARTPOST - NOV/DEC 2025')
    print('=' * 80)
    sp_invoice_sum = sp_calc['invoice_total'].sum()
    sp_calc_sum = sp_calc['calc_total'].sum()
    sp_diff = sp_calc_sum - sp_invoice_sum
    sp_pct = (sp_diff / sp_invoice_sum) * 100
    print(f"Shipments: {len(sp_calc):,}")
    print(f"Invoice total (base+pp+earned+grace): ${sp_invoice_sum:,.2f}")
    print(f"Calculated total (und+pp+earned+grace): ${sp_calc_sum:,.2f}")
    print(f"Difference: ${sp_diff:,.2f} ({sp_pct:+.2f}%)")

    sp_calc = sp_calc.with_columns((pl.col('calc_total') - pl.col('invoice_total')).abs().alias('diff'))
    sp_exact = sp_calc.filter(pl.col('diff') < 0.02)
    print(f"Exact matches (<$0.02): {len(sp_exact):,} / {len(sp_calc):,} ({len(sp_exact)/len(sp_calc)*100:.1f}%)")

    # Show SmartPost mismatches breakdown
    sp_mismatch = sp_calc.filter(pl.col('diff') >= 0.02)
    if len(sp_mismatch) > 0:
        print(f"\nSmartPost mismatches by weight:")
        print(sp_mismatch.group_by('weight').agg(pl.len().alias('count')).sort('weight'))


if __name__ == "__main__":
    main()
