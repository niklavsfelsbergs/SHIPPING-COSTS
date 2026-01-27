"""
FedEx Cost Comparison Script

Compares calculator output against invoice actuals for Sep-Dec 2025.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import polars as pl
from carriers.fedex.data.loaders import load_pcs_shipments
from carriers.fedex.calculate_costs import calculate_costs

# =============================================================================
# STEP 1: Load Invoice Data
# =============================================================================
print('Loading invoice data...')
invoice = pl.read_parquet('carriers/fedex/development/invoice_data.parquet')

# Filter to Sep-Dec 2025
invoice = invoice.filter(
    (pl.col('shipment_date') >= pl.date(2025, 9, 1)) &
    (pl.col('shipment_date') < pl.date(2026, 1, 1))
)
print(f'Invoice records: {len(invoice):,}')

# =============================================================================
# STEP 2: Pivot Invoice to One Row Per Shipment
# =============================================================================
print('Pivoting invoice data...')

# Base charge
base = invoice.filter(pl.col('charge_description') == 'Base Charge') \
    .group_by('trackingnumber').agg(pl.col('charge_description_amount').sum().alias('actual_base'))

# Performance Pricing (negative)
pp = invoice.filter(pl.col('charge_description') == 'Performance Pricing') \
    .group_by('trackingnumber').agg(pl.col('charge_description_amount').sum().alias('actual_pp'))

# Earned Discount (negative)
earned = invoice.filter(pl.col('charge_description') == 'Earned Discount') \
    .group_by('trackingnumber').agg(pl.col('charge_description_amount').sum().alias('actual_earned'))

# Grace Discount (negative)
grace = invoice.filter(pl.col('charge_description') == 'Grace Discount') \
    .group_by('trackingnumber').agg(pl.col('charge_description_amount').sum().alias('actual_grace'))

# DAS (all variants)
das = invoice.filter(
    pl.col('charge_description').str.contains('DAS') |
    pl.col('charge_description').str.contains('Delivery Area Surcharge')
).group_by('trackingnumber').agg(pl.col('charge_description_amount').sum().alias('actual_das'))

# Residential
res = invoice.filter(pl.col('charge_description') == 'Residential') \
    .group_by('trackingnumber').agg(pl.col('charge_description_amount').sum().alias('actual_residential'))

# AHS - Dimensions
ahs = invoice.filter(pl.col('charge_description') == 'AHS - Dimensions') \
    .group_by('trackingnumber').agg(pl.col('charge_description_amount').sum().alias('actual_ahs'))

# AHS - Weight
ahs_weight = invoice.filter(pl.col('charge_description') == 'AHS - Weight') \
    .group_by('trackingnumber').agg(pl.col('charge_description_amount').sum().alias('actual_ahs_weight'))

# Oversize
oversize = invoice.filter(pl.col('charge_description') == 'Oversize Charge') \
    .group_by('trackingnumber').agg(pl.col('charge_description_amount').sum().alias('actual_oversize'))

# Demand-Add'l Handling
dem_ahs = invoice.filter(pl.col('charge_description') == "Demand-Add'l Handling") \
    .group_by('trackingnumber').agg(pl.col('charge_description_amount').sum().alias('actual_dem_ahs'))

# Demand-Oversize
dem_oversize = invoice.filter(pl.col('charge_description') == 'Demand-Oversize') \
    .group_by('trackingnumber').agg(pl.col('charge_description_amount').sum().alias('actual_dem_oversize'))

# Demand Surcharge (base)
dem_base = invoice.filter(pl.col('charge_description') == 'Demand Surcharge') \
    .group_by('trackingnumber').agg(pl.col('charge_description_amount').sum().alias('actual_dem_base'))

# Fuel Surcharge
fuel = invoice.filter(pl.col('charge_description') == 'Fuel Surcharge') \
    .group_by('trackingnumber').agg(pl.col('charge_description_amount').sum().alias('actual_fuel'))

# =============================================================================
# Uncovered charge descriptions (not included in comparison)
# =============================================================================
COVERED_DESCRIPTIONS = [
    'Base Charge',
    'Performance Pricing',
    'Earned Discount',
    'Grace Discount',
    'Residential',
    'AHS - Dimensions',
    'AHS - Weight',
    'Oversize Charge',
    "Demand-Add'l Handling",
    'Demand-Oversize',
    'Demand Surcharge',
    'Fuel Surcharge',
]
# DAS variants handled separately with contains

uncovered = invoice.filter(
    ~pl.col('charge_description').is_in(COVERED_DESCRIPTIONS) &
    ~pl.col('charge_description').str.contains('DAS') &
    ~pl.col('charge_description').str.contains('Delivery Area Surcharge')
)

# Summary by charge description (for header list)
uncovered_by_desc = uncovered.group_by('charge_description').agg(
    pl.col('charge_description_amount').sum().alias('total_amount')
).sort('total_amount')

# Monthly uncovered totals per shipment
uncovered_monthly = uncovered.group_by('trackingnumber').agg(
    pl.col('charge_description_amount').sum().alias('actual_uncovered')
)

# Get unique shipments with metadata
shipments = invoice.group_by('trackingnumber').agg([
    pl.col('shipment_date').first(),
    pl.col('invoice_date').first(),
    pl.col('service_type').first(),
    pl.col('pcs_trackingnumber').first(),
    pl.col('rated_weight').first(),
    pl.col('shipping_zone').first(),
])

# Join all
invoice_pivoted = shipments.join(base, on='trackingnumber', how='left') \
    .join(pp, on='trackingnumber', how='left') \
    .join(earned, on='trackingnumber', how='left') \
    .join(grace, on='trackingnumber', how='left') \
    .join(das, on='trackingnumber', how='left') \
    .join(res, on='trackingnumber', how='left') \
    .join(ahs, on='trackingnumber', how='left') \
    .join(ahs_weight, on='trackingnumber', how='left') \
    .join(oversize, on='trackingnumber', how='left') \
    .join(dem_ahs, on='trackingnumber', how='left') \
    .join(dem_oversize, on='trackingnumber', how='left') \
    .join(dem_base, on='trackingnumber', how='left') \
    .join(fuel, on='trackingnumber', how='left') \
    .join(uncovered_monthly, on='trackingnumber', how='left') \
    .fill_null(0)

# Cast decimal columns to float
invoice_pivoted = invoice_pivoted.with_columns([
    pl.col('actual_base').cast(pl.Float64),
    pl.col('actual_pp').cast(pl.Float64),
    pl.col('actual_earned').cast(pl.Float64),
    pl.col('actual_grace').cast(pl.Float64),
    pl.col('actual_das').cast(pl.Float64),
    pl.col('actual_residential').cast(pl.Float64),
    pl.col('actual_ahs').cast(pl.Float64),
    pl.col('actual_ahs_weight').cast(pl.Float64),
    pl.col('actual_oversize').cast(pl.Float64),
    pl.col('actual_dem_ahs').cast(pl.Float64),
    pl.col('actual_dem_oversize').cast(pl.Float64),
    pl.col('actual_dem_base').cast(pl.Float64),
    pl.col('actual_fuel').cast(pl.Float64),
    pl.col('actual_uncovered').cast(pl.Float64),
])

print(f'Unique shipments in invoice: {len(invoice_pivoted):,}')

# =============================================================================
# STEP 3: Load PCS Data and Calculate
# =============================================================================
print('Loading PCS data (extended date range)...')
pcs = load_pcs_shipments(start_date='2025-08-01', end_date='2026-02-01')
print(f'PCS records: {len(pcs):,}')

print('Running calculator...')
calculated = calculate_costs(pcs)

# =============================================================================
# STEP 4: Join - Handle HD and SP separately
# =============================================================================
print('Joining data...')

# Split by service type
invoice_hd = invoice_pivoted.filter(pl.col('service_type') == 'Home Delivery')
invoice_sp = invoice_pivoted.filter(pl.col('service_type') != 'Home Delivery')

# Join HD on trackingnumber
comparison_hd = calculated.join(
    invoice_hd,
    left_on='latest_trackingnumber',
    right_on='trackingnumber',
    how='inner'
)

# Join SP on pcs_trackingnumber
comparison_sp = calculated.join(
    invoice_sp,
    left_on='latest_trackingnumber',
    right_on='pcs_trackingnumber',
    how='inner'
)

# Combine
comparison = pl.concat([comparison_hd, comparison_sp], how='diagonal')
print(f'Matched shipments: {len(comparison):,}')

# Calculate expected and actual base totals
comparison = comparison.with_columns([
    (pl.col('cost_base_rate') + pl.col('cost_performance_pricing') +
     pl.col('cost_earned_discount') + pl.col('cost_grace_discount')).alias('expected_base'),
    (pl.col('actual_base') + pl.col('actual_pp') +
     pl.col('actual_earned') + pl.col('actual_grace')).alias('actual_base_total')
])

# =============================================================================
# STEP 5: Generate Monthly Summary
# =============================================================================
comparison = comparison.with_columns(
    pl.col('invoice_date').dt.strftime('%Y-%m').alias('month')
)

monthly = comparison.group_by('month').agg([
    pl.len().alias('shipments'),
    pl.col('expected_base').sum().alias('expected_base'),
    pl.col('actual_base_total').sum().alias('actual_base'),
    pl.col('cost_das').sum().alias('expected_das'),
    pl.col('actual_das').sum().alias('actual_das'),
    pl.col('cost_residential').sum().alias('expected_res'),
    pl.col('actual_residential').sum().alias('actual_res'),
    pl.col('cost_ahs').sum().alias('expected_ahs'),
    pl.col('actual_ahs').sum().alias('actual_ahs'),
    pl.col('cost_ahs_weight').sum().alias('expected_ahs_weight'),
    pl.col('actual_ahs_weight').sum().alias('actual_ahs_weight'),
    pl.col('cost_oversize').sum().alias('expected_oversize'),
    pl.col('actual_oversize').sum().alias('actual_oversize'),
    pl.col('cost_dem_ahs').sum().alias('expected_dem_ahs'),
    pl.col('actual_dem_ahs').sum().alias('actual_dem_ahs'),
    pl.col('cost_dem_oversize').sum().alias('expected_dem_oversize'),
    pl.col('actual_dem_oversize').sum().alias('actual_dem_oversize'),
    pl.col('cost_dem_base').sum().alias('expected_dem_base'),
    pl.col('actual_dem_base').sum().alias('actual_dem_base'),
    pl.col('cost_fuel').sum().alias('expected_fuel'),
    pl.col('actual_fuel').sum().alias('actual_fuel'),
    pl.col('actual_uncovered').sum().alias('actual_uncovered'),
]).sort('month')

# Add total columns (sum of all tracked positions)
monthly = monthly.with_columns([
    (pl.col('expected_base') + pl.col('expected_das') + pl.col('expected_res') +
     pl.col('expected_ahs') + pl.col('expected_ahs_weight') + pl.col('expected_oversize') +
     pl.col('expected_dem_ahs') + pl.col('expected_dem_oversize') +
     pl.col('expected_dem_base') + pl.col('expected_fuel')).alias('expected_total'),
    (pl.col('actual_base') + pl.col('actual_das') + pl.col('actual_res') +
     pl.col('actual_ahs') + pl.col('actual_ahs_weight') + pl.col('actual_oversize') +
     pl.col('actual_dem_ahs') + pl.col('actual_dem_oversize') +
     pl.col('actual_dem_base') + pl.col('actual_fuel') + pl.col('actual_uncovered')).alias('actual_total'),
])

# =============================================================================
# STEP 6: Print Output
# =============================================================================
print()
print('FedEx Cost Comparison (Sep 2025 - Dec 2025)')
print('=' * 42)

def print_monthly_table(title, exp_col, act_col):
    """Print a monthly comparison table for a cost position."""
    print()
    print(f'{title}:')
    print(f"{'Month':<10} | {'Expected':>10} | {'Actual':>10} | {'Variance $':>10} | {'Variance %':>10}")
    print('-' * 10 + '|' + '-' * 11 + '|' + '-' * 11 + '|' + '-' * 12 + '|' + '-' * 12)

    total_exp = 0
    total_act = 0

    for row in monthly.iter_rows(named=True):
        exp = row[exp_col]
        act = row[act_col]
        total_exp += exp
        total_act += act
        var_amt = exp - act
        var_pct = (var_amt / act * 100) if act != 0 else 0
        sign = '+' if var_amt >= 0 else ''
        print(f"{row['month']:<10} | ${exp:>9,.0f} | ${act:>9,.0f} | {sign}${var_amt:>9,.0f} | {sign}{var_pct:>9.2f}%")

    # Total row
    print('-' * 10 + '|' + '-' * 11 + '|' + '-' * 11 + '|' + '-' * 12 + '|' + '-' * 12)
    var_total = total_exp - total_act
    var_pct_total = (var_total / total_act * 100) if total_act != 0 else 0
    sign = '+' if var_total >= 0 else ''
    print(f"{'TOTAL':<10} | ${total_exp:>9,.0f} | ${total_act:>9,.0f} | {sign}${var_total:>9,.0f} | {sign}{var_pct_total:>9.2f}%")

# Total (all tracked positions)
print_monthly_table('TOTAL (all tracked positions)', 'expected_total', 'actual_total')

# Base (after discounts)
print_monthly_table('Base (after discounts)', 'expected_base', 'actual_base')

# DAS
print_monthly_table('DAS', 'expected_das', 'actual_das')

# Residential
print_monthly_table('Residential', 'expected_res', 'actual_res')

# AHS - Dimensions
print_monthly_table('AHS - Dimensions', 'expected_ahs', 'actual_ahs')

# AHS - Weight
print_monthly_table('AHS - Weight', 'expected_ahs_weight', 'actual_ahs_weight')

# Oversize
print_monthly_table('Oversize', 'expected_oversize', 'actual_oversize')

# Demand-Add'l Handling
print_monthly_table("Demand-Add'l Handling", 'expected_dem_ahs', 'actual_dem_ahs')

# Demand-Oversize
print_monthly_table('Demand-Oversize', 'expected_dem_oversize', 'actual_dem_oversize')

# Demand Surcharge (base)
print_monthly_table('Demand Surcharge', 'expected_dem_base', 'actual_dem_base')

# Fuel Surcharge
print_monthly_table('Fuel Surcharge', 'expected_fuel', 'actual_fuel')

# =============================================================================
# Uncovered Charges Section
# =============================================================================
print()
print('=' * 60)
print('NOT COVERED BY CALCULATOR (included in TOTAL actual):')
print('=' * 60)

# Print individual charge descriptions with totals
print()
print('Charge Description Totals (all months):')
print('-' * 50)
for row in uncovered_by_desc.iter_rows(named=True):
    amt = row['total_amount']
    print(f"  {row['charge_description']:<35} ${amt:>12,.2f}")

uncovered_grand_total = uncovered_by_desc.select(pl.col('total_amount').sum()).item()
print('-' * 50)
print(f"  {'TOTAL UNCOVERED':<35} ${uncovered_grand_total:>12,.2f}")

# Print monthly breakdown
print()
print('Monthly Uncovered Totals:')
print(f"{'Month':<10} | {'Amount':>12}")
print('-' * 10 + '|' + '-' * 14)
for row in monthly.iter_rows(named=True):
    amt = row['actual_uncovered']
    print(f"{row['month']:<10} | ${amt:>11,.0f}")
print('-' * 10 + '|' + '-' * 14)
monthly_uncovered_total = monthly.select(pl.col('actual_uncovered').sum()).item()
print(f"{'TOTAL':<10} | ${monthly_uncovered_total:>11,.0f}")

print()
print('=' * 60)

print()
print('(Base = cost_base_rate + cost_performance_pricing + cost_earned_discount + cost_grace_discount)')
print('(Fuel = 10% of base_rate + surcharges)')
print('(TOTAL actual includes uncovered charges)')
