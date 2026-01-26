"""
Monthly analysis of 2025 FedEx invoice data vs calculator.
Uses pre-saved parquet file instead of pulling from database.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import polars as pl
from pathlib import Path
from shared.database import pull_data

RATE_TABLES = Path(__file__).parent / "final_rate_tables"
INVOICE_PARQUET = Path(__file__).parent / "invoice_data.parquet"


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
    sp_pp = pl.read_csv(RATE_TABLES / 'smartpost_performance_pricing.csv')
    hd_earned = pl.read_csv(RATE_TABLES / 'home_delivery_earned_discount.csv')
    sp_earned = pl.read_csv(RATE_TABLES / 'smartpost_earned_discount.csv')
    hd_grace = pl.read_csv(RATE_TABLES / 'home_delivery_grace_discount.csv')
    sp_grace = pl.read_csv(RATE_TABLES / 'smartpost_grace_discount.csv')

    # Convert to long format
    hd_und_long = to_long(hd_undiscounted, 'undiscounted')
    sp_und_long = to_long(sp_undiscounted, 'undiscounted')
    hd_pp_long = to_long(hd_pp, 'pp')
    sp_pp_long = to_long(sp_pp, 'pp')
    hd_earned_long = to_long(hd_earned, 'earned')
    sp_earned_long = to_long(sp_earned, 'earned')
    hd_grace_long = to_long(hd_grace, 'grace')
    sp_grace_long = to_long(sp_grace, 'grace')

    # Load invoice data from parquet
    print('Loading invoice data from parquet...')
    df = pl.read_parquet(INVOICE_PARQUET)

    # Filter to Sep-Dec only
    df = df.filter(pl.col('invoice_date') >= pl.date(2025, 9, 1))
    print(f'Loaded {len(df):,} charge rows (Sep-Dec 2025)')

    # Load PCS tracking numbers for match checking
    print('Loading PCS tracking numbers...')
    pcs_query = """
    WITH trackingnumbers AS (
        SELECT orderid, trackingnumber,
            ROW_NUMBER() OVER (PARTITION BY orderid ORDER BY id DESC) AS row_nr
        FROM bi_stage_dev_dbo.pcsu_sentparcels
    )
    SELECT DISTINCT tn.trackingnumber
    FROM bi_stage_dev_dbo.pcsu_orders po
    JOIN bi_stage_dev_dbo.pcsu_productionsites pp ON pp.id = po.productionsiteid
    JOIN bi_stage_dev_dbo.pcsu_shippingproviders ps ON ps.id = po.shippingproviderid
    LEFT JOIN trackingnumbers tn ON tn.orderid = po.id AND tn.row_nr = 1
    WHERE ps.extkey LIKE 'FXE%'
      AND pp."name" IN ('Columbus', 'Phoenix')
      AND po.createddate >= '2025-09-01'
      AND po.createddate < '2026-01-01'
      AND tn.trackingnumber IS NOT NULL
    """
    pcs_df = pull_data(pcs_query)
    pcs_trackings = set(pcs_df['trackingnumber'].to_list())
    print(f'Loaded {len(pcs_trackings):,} PCS tracking numbers')

    # Add month column and normalize zones
    df = df.with_columns([
        pl.col('invoice_date').dt.strftime('%Y-%m').alias('month'),
        pl.col('rated_weight').cast(pl.Float64).ceil().cast(pl.Int64).alias('weight'),
        pl.when(pl.col('shipping_zone').is_null())
          .then(pl.lit(5))
          .when(pl.col('shipping_zone').cast(pl.Utf8).is_in(['A', 'H', 'M', 'P']))
          .then(pl.lit(9))
          .otherwise(pl.col('shipping_zone').cast(pl.Utf8).str.replace('^0', '').cast(pl.Int64, strict=False).fill_null(5))
          .alias('zone')
    ])

    # Get invoice totals per shipment
    invoice_base = df.group_by(['trackingnumber', 'month', 'service_type', 'weight', 'zone', 'pcs_trackingnumber']).agg(
        pl.col('transportation_charge_usd').first().cast(pl.Float64).alias('base_charge')
    )

    invoice_pp = df.filter(pl.col('charge_description') == 'Performance Pricing').group_by(
        ['trackingnumber']
    ).agg(pl.col('charge_description_amount').cast(pl.Float64).sum().alias('invoice_pp'))

    invoice_earned = df.filter(pl.col('charge_description') == 'Earned Discount').group_by(
        ['trackingnumber']
    ).agg(pl.col('charge_description_amount').cast(pl.Float64).sum().alias('invoice_earned'))

    invoice_grace = df.filter(pl.col('charge_description') == 'Grace Discount').group_by(
        ['trackingnumber']
    ).agg(pl.col('charge_description_amount').cast(pl.Float64).sum().alias('invoice_grace'))

    # Build shipment-level data
    shipments = invoice_base.join(invoice_pp, on='trackingnumber', how='left')
    shipments = shipments.join(invoice_earned, on='trackingnumber', how='left')
    shipments = shipments.join(invoice_grace, on='trackingnumber', how='left')
    shipments = shipments.with_columns([
        pl.col('invoice_pp').fill_null(0),
        pl.col('invoice_earned').fill_null(0),
        pl.col('invoice_grace').fill_null(0),
    ])

    # Determine PCS match based on service type:
    # - Home Delivery: match on trackingnumber (invoice tracking = PCS tracking)
    # - SmartPost: match on pcs_trackingnumber (crossref tracking = PCS tracking)
    shipments = shipments.with_columns(
        pl.when(pl.col('service_type') == 'Home Delivery')
        .then(pl.col('trackingnumber').is_in(list(pcs_trackings)))
        .otherwise(pl.col('pcs_trackingnumber').is_in(list(pcs_trackings)))
        .alias('has_pcs_match')
    )

    print(f'Unique shipments: {len(shipments):,}')

    # Join with rate tables based on service type
    def join_rates(service_shipments, und_long, pp_long, earned_long, grace_long):
        calc = service_shipments.join(und_long, left_on=['weight', 'zone'], right_on=['weight_lbs', 'zone'], how='left')
        calc = calc.join(pp_long, left_on=['weight', 'zone'], right_on=['weight_lbs', 'zone'], how='left')
        calc = calc.join(earned_long, left_on=['weight', 'zone'], right_on=['weight_lbs', 'zone'], how='left')
        calc = calc.join(grace_long, left_on=['weight', 'zone'], right_on=['weight_lbs', 'zone'], how='left')
        calc = calc.with_columns([
            (pl.col('undiscounted').fill_null(0) + pl.col('pp').fill_null(0) + pl.col('earned').fill_null(0) + pl.col('grace').fill_null(0)).alias('calc_total'),
            (pl.col('base_charge') + pl.col('invoice_pp') + pl.col('invoice_earned') + pl.col('invoice_grace')).alias('invoice_total'),
            pl.col('undiscounted').is_null().alias('no_rate_match')
        ])
        calc = calc.with_columns((pl.col('calc_total') - pl.col('invoice_total')).abs().alias('diff'))
        return calc

    hd_calc = join_rates(shipments.filter(pl.col('service_type') == 'Home Delivery'), hd_und_long, hd_pp_long, hd_earned_long, hd_grace_long)
    sp_calc = join_rates(shipments.filter(pl.col('service_type') == 'SmartPost'), sp_und_long, sp_pp_long, sp_earned_long, sp_grace_long)

    # Print monthly stats - HOME DELIVERY
    print()
    print('=' * 120)
    print('MONTHLY STATISTICS - HOME DELIVERY (Sep-Dec 2025)')
    print('=' * 120)
    print(f'{"Month":<8} {"Count":>8} {"Invoice $":>14} {"Calc $":>14} {"Diff $":>12} {"Diff %":>8} {"Exact":>8} {"No PCS":>8} {"No Rate":>8}')
    print('-' * 120)

    for month in sorted(hd_calc['month'].unique().to_list()):
        m = hd_calc.filter(pl.col('month') == month)
        count = len(m)
        invoice_sum = m['invoice_total'].sum()
        calc_sum = m['calc_total'].sum()
        diff = calc_sum - invoice_sum
        pct = (diff / invoice_sum * 100) if invoice_sum != 0 else 0
        exact = len(m.filter(pl.col('diff') < 0.02))
        no_pcs = len(m.filter(~pl.col('has_pcs_match')))
        no_rate = len(m.filter(pl.col('no_rate_match')))
        print(f'{month:<8} {count:>8,} {invoice_sum:>14,.2f} {calc_sum:>14,.2f} {diff:>+12,.2f} {pct:>+7.2f}% {exact:>7,} {no_pcs:>8,} {no_rate:>8,}')

    # Totals
    total_count = len(hd_calc)
    total_invoice = hd_calc['invoice_total'].sum()
    total_calc = hd_calc['calc_total'].sum()
    total_diff = total_calc - total_invoice
    total_pct = (total_diff / total_invoice * 100) if total_invoice != 0 else 0
    total_exact = len(hd_calc.filter(pl.col('diff') < 0.02))
    total_no_pcs = len(hd_calc.filter(~pl.col('has_pcs_match')))
    total_no_rate = len(hd_calc.filter(pl.col('no_rate_match')))
    print('-' * 120)
    print(f'{"TOTAL":<8} {total_count:>8,} {total_invoice:>14,.2f} {total_calc:>14,.2f} {total_diff:>+12,.2f} {total_pct:>+7.2f}% {total_exact:>7,} {total_no_pcs:>8,} {total_no_rate:>8,}')

    # Print monthly stats - SMARTPOST
    print()
    print('=' * 120)
    print('MONTHLY STATISTICS - SMARTPOST (Sep-Dec 2025)')
    print('=' * 120)
    print(f'{"Month":<8} {"Count":>8} {"Invoice $":>14} {"Calc $":>14} {"Diff $":>12} {"Diff %":>8} {"Exact":>8} {"No PCS":>8} {"No Rate":>8}')
    print('-' * 120)

    for month in sorted(sp_calc['month'].unique().to_list()):
        m = sp_calc.filter(pl.col('month') == month)
        count = len(m)
        invoice_sum = m['invoice_total'].sum()
        calc_sum = m['calc_total'].sum()
        diff = calc_sum - invoice_sum
        pct = (diff / invoice_sum * 100) if invoice_sum != 0 else 0
        exact = len(m.filter(pl.col('diff') < 0.02))
        no_pcs = len(m.filter(~pl.col('has_pcs_match')))
        no_rate = len(m.filter(pl.col('no_rate_match')))
        print(f'{month:<8} {count:>8,} {invoice_sum:>14,.2f} {calc_sum:>14,.2f} {diff:>+12,.2f} {pct:>+7.2f}% {exact:>7,} {no_pcs:>8,} {no_rate:>8,}')

    # Totals
    total_count = len(sp_calc)
    total_invoice = sp_calc['invoice_total'].sum()
    total_calc = sp_calc['calc_total'].sum()
    total_diff = total_calc - total_invoice
    total_pct = (total_diff / total_invoice * 100) if total_invoice != 0 else 0
    total_exact = len(sp_calc.filter(pl.col('diff') < 0.02))
    total_no_pcs = len(sp_calc.filter(~pl.col('has_pcs_match')))
    total_no_rate = len(sp_calc.filter(pl.col('no_rate_match')))
    print('-' * 120)
    print(f'{"TOTAL":<8} {total_count:>8,} {total_invoice:>14,.2f} {total_calc:>14,.2f} {total_diff:>+12,.2f} {total_pct:>+7.2f}% {total_exact:>7,} {total_no_pcs:>8,} {total_no_rate:>8,}')

    print()
    print('Legend:')
    print('  Exact    = Calculated matches invoice within $0.02')
    print('  No PCS   = Invoice shipment has no matching PCS tracking number')
    print('  No Rate  = Weight/zone combination not found in rate tables')


if __name__ == "__main__":
    main()
