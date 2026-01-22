"""
USPS November 2025 Cost Comparison Analysis

Compares calculated costs vs actual invoice costs for November 2025.
Specifically analyzes the impact of peak surcharge on accuracy.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import polars as pl
from shared.database import pull_data
from carriers.usps.calculate_costs import calculate_costs


def main():
    # Load November 2025 data
    query = """
    SELECT
        impb,
        mailing_date,
        entry_zip_code,
        destination_zip_code,
        manifest_length,
        manifest_width,
        manifest_height,
        manifest_weight,
        zone as invoice_zone,
        base_postage as actual_base_cost,
        final_postage_usd as actual_total_cost
    FROM poc_staging.usps
    WHERE mailing_date >= '2025-11-01' AND mailing_date < '2025-12-01'
        AND entry_zip_code IS NOT NULL
        AND destination_zip_code IS NOT NULL
        AND manifest_weight IS NOT NULL
        AND manifest_weight > 0
        AND manifest_weight <= 20
        AND manifest_length IS NOT NULL
        AND manifest_width IS NOT NULL
        AND manifest_height IS NOT NULL
    """

    print('Loading November 2025 data from database...')
    raw_df = pull_data(query)
    print(f'Loaded {len(raw_df):,} shipments')

    # Transform to calculator input
    print('Transforming data...')
    input_df = raw_df.with_columns([
        pl.col('mailing_date').cast(pl.Date).alias('ship_date'),
        pl.when(pl.col('entry_zip_code') == '85027')
        .then(pl.lit('Phoenix'))
        .when(pl.col('entry_zip_code') == '43194')
        .then(pl.lit('Columbus'))
        .otherwise(pl.lit('Unknown'))
        .alias('production_site'),
        pl.col('destination_zip_code').alias('shipping_zip_code'),
        pl.col('manifest_length').cast(pl.Float64).alias('length_in'),
        pl.col('manifest_width').cast(pl.Float64).alias('width_in'),
        pl.col('manifest_height').cast(pl.Float64).alias('height_in'),
        pl.col('manifest_weight').cast(pl.Float64).alias('weight_lbs'),
        pl.lit('').alias('shipping_region'),
    ])

    # Filter out unknown production sites
    input_df = input_df.filter(pl.col('production_site') != 'Unknown')
    print(f'After filtering known production sites: {len(input_df):,} shipments')

    # Run calculator
    print('Running cost calculator...')
    result_df = calculate_costs(input_df)

    # Cast actual costs to float to avoid decimal type issues
    result_df = result_df.with_columns([
        pl.col('actual_total_cost').cast(pl.Float64),
        pl.col('actual_base_cost').cast(pl.Float64),
    ])

    # Calculate totals
    total_shipments = len(result_df)
    actual_total = result_df['actual_total_cost'].sum()
    calc_total = result_df['cost_total'].sum()
    calc_subtotal_no_peak = (result_df['cost_total'] - result_df['cost_peak']).sum()
    total_peak = result_df['cost_peak'].sum()

    diff_with_peak = calc_total - actual_total
    diff_without_peak = calc_subtotal_no_peak - actual_total
    avg_diff = diff_with_peak / total_shipments

    print()
    print('=' * 80)
    print('USPS NOVEMBER 2025 COST COMPARISON')
    print('=' * 80)
    print()
    print(f'Total shipments: {total_shipments:,}')
    print()
    print('-' * 80)
    print('TOTALS')
    print('-' * 80)
    print(f'1. Total actual invoice costs (final_postage_usd):   ${actual_total:>14,.2f}')
    print(f'2. Total calculated costs (cost_total):             ${calc_total:>14,.2f}')
    print(f'3. Dollar difference (calculated - actual):         ${diff_with_peak:>14,.2f}')
    print(f'4. Average difference per shipment:                 ${avg_diff:>14,.4f}')
    pct_diff = 100 * diff_with_peak / actual_total if actual_total != 0 else 0
    print(f'   Percentage difference:                           {pct_diff:>14.2f}%')
    print()
    print('-' * 80)
    print('PEAK SURCHARGE IMPACT')
    print('-' * 80)
    print(f'Total peak surcharge calculated:                    ${total_peak:>14,.2f}')
    print()
    print('WITHOUT peak surcharge (base + other surcharges):')
    print(f'   Calculated total (no peak):                      ${calc_subtotal_no_peak:>14,.2f}')
    print(f'   Difference (calc no peak - actual):              ${diff_without_peak:>14,.2f}')
    pct_no_peak = 100 * diff_without_peak / actual_total if actual_total != 0 else 0
    print(f'   Percentage difference:                           {pct_no_peak:>14.2f}%')
    print()
    print('WITH peak surcharge (current calculator):')
    print(f'   Calculated total (with peak):                    ${calc_total:>14,.2f}')
    print(f'   Difference (calc with peak - actual):            ${diff_with_peak:>14,.2f}')
    print(f'   Percentage difference:                           {pct_diff:>14.2f}%')
    print()
    print('-' * 80)
    print('INTERPRETATION')
    print('-' * 80)
    improvement = diff_without_peak - diff_with_peak
    print(f'Peak surcharge improves accuracy by:                ${improvement:>14,.2f}')
    print('  (closer to zero = better match)')
    print()

    # Additional breakdown
    print('-' * 80)
    print('COMPONENT BREAKDOWN')
    print('-' * 80)
    cost_base = result_df['cost_base'].sum()
    cost_nsl1 = result_df['cost_nsl1'].sum()
    cost_nsl2 = result_df['cost_nsl2'].sum()
    cost_nsv = result_df['cost_nsv'].sum()
    cost_peak = result_df['cost_peak'].sum()

    print(f'Base shipping cost:                                 ${cost_base:>14,.2f}')
    print(f'NSL1 surcharge (22+ in):                            ${cost_nsl1:>14,.2f}')
    print(f'NSL2 surcharge (30+ in):                            ${cost_nsl2:>14,.2f}')
    print(f'NSV surcharge (non-standard volume):                ${cost_nsv:>14,.2f}')
    print(f'Peak season surcharge:                              ${cost_peak:>14,.2f}')
    print(f'                                                    --------------')
    print(f'Total calculated:                                   ${calc_total:>14,.2f}')
    print()
    print('=' * 80)


if __name__ == "__main__":
    main()
