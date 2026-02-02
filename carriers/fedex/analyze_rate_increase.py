"""
Analyze FedEx actual shipping costs for potential rate increase around January 2026.
"""

import polars as pl
import sys
from pathlib import Path

# Set UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

# Load the comparison data
print("Loading FedEx comparison data...")
df = pl.read_parquet("C:/Users/niklavs.felsbergs/Desktop/SHIPPING-COSTS/carriers/fedex/dashboard/data/comparison.parquet")

print(f"\nDataset shape: {df.shape}")
print(f"Total shipments: {len(df):,}")

# Check date range
print("\n" + "="*80)
print("DATE RANGE ANALYSIS")
print("="*80)
print(f"Date range: {df['ship_date'].min()} to {df['ship_date'].max()}")

# Shipments by month
monthly = df.group_by(pl.col('ship_date').dt.strftime('%Y-%m').alias('month')).agg([
    pl.count().alias('shipments'),
    pl.col('actual_base').mean().alias('avg_base'),
    pl.col('actual_base').median().alias('median_base'),
    pl.col('billable_weight_lbs').mean().alias('avg_weight')
]).sort('month')

print("\nShipments by month:")
print(monthly)

# Create weight brackets
df = df.with_columns([
    pl.when(pl.col('billable_weight_lbs') <= 5).then(pl.lit('0-5 lbs'))
    .when(pl.col('billable_weight_lbs') <= 10).then(pl.lit('5-10 lbs'))
    .when(pl.col('billable_weight_lbs') <= 20).then(pl.lit('10-20 lbs'))
    .when(pl.col('billable_weight_lbs') <= 50).then(pl.lit('20-50 lbs'))
    .otherwise(pl.lit('50+ lbs'))
    .alias('weight_bracket'),

    # Create period column (December 2025 vs January 2026)
    pl.when(pl.col('ship_date') < pl.date(2026, 1, 1)).then(pl.lit('Dec 2025'))
    .otherwise(pl.lit('Jan 2026+'))
    .alias('period')
])

print("\n" + "="*80)
print("WEIGHT BRACKET DISTRIBUTION")
print("="*80)
weight_dist = df.group_by('weight_bracket').agg([
    pl.count().alias('shipments')
]).sort('weight_bracket')
print(weight_dist)

print("\n" + "="*80)
print("SERVICE TYPE DISTRIBUTION")
print("="*80)
service_dist = df.group_by('rate_service').agg([
    pl.count().alias('shipments'),
    pl.col('actual_base').mean().alias('avg_base')
]).sort('shipments', descending=True)
print(service_dist)

print("\n" + "="*80)
print("PERIOD COMPARISON - OVERALL")
print("="*80)
period_comparison = df.group_by('period').agg([
    pl.count().alias('shipments'),
    pl.col('actual_base').mean().alias('avg_base'),
    pl.col('actual_base').median().alias('median_base'),
    pl.col('billable_weight_lbs').mean().alias('avg_weight'),
    pl.col('actual_zone').mean().alias('avg_zone')
]).sort('period')
print(period_comparison)

# Calculate percentage change
if len(period_comparison) >= 2:
    dec_base = period_comparison.filter(pl.col('period') == 'Dec 2025')['avg_base'][0]
    jan_base = period_comparison.filter(pl.col('period') == 'Jan 2026+')['avg_base'][0]
    pct_change = ((jan_base - dec_base) / dec_base) * 100
    print(f"\nOverall average base rate change: {pct_change:+.2f}%")

print("\n" + "="*80)
print("DETAILED ANALYSIS BY SERVICE, ZONE, AND WEIGHT")
print("="*80)

# Group by comparable characteristics
comparable_groups = df.group_by(['period', 'rate_service', 'actual_zone', 'weight_bracket']).agg([
    pl.count().alias('shipments'),
    pl.col('actual_base').mean().alias('avg_base'),
    pl.col('actual_base').median().alias('median_base'),
    pl.col('actual_base').std().alias('std_base'),
    pl.col('actual_base').min().alias('min_base'),
    pl.col('actual_base').max().alias('max_base'),
    pl.col('billable_weight_lbs').mean().alias('avg_weight')
]).filter(
    pl.col('shipments') >= 5  # Only groups with at least 5 shipments
).sort(['rate_service', 'actual_zone', 'weight_bracket', 'period'])

print(f"\nFound {len(comparable_groups)} comparable groups with >= 5 shipments")
print("\nSample of comparable groups:")
print(comparable_groups.head(20))

# Find groups that exist in both periods
groups_pivot = comparable_groups.pivot(
    index=['rate_service', 'actual_zone', 'weight_bracket'],
    columns='period',
    values='avg_base'
).filter(
    pl.col('Dec 2025').is_not_null() & pl.col('Jan 2026+').is_not_null()
).with_columns([
    ((pl.col('Jan 2026+') - pl.col('Dec 2025')) / pl.col('Dec 2025') * 100).alias('pct_change'),
    (pl.col('Jan 2026+') - pl.col('Dec 2025')).alias('dollar_change')
])

print("\n" + "="*80)
print("RATE CHANGES FOR COMPARABLE GROUPS (Both periods)")
print("="*80)
print(f"Groups appearing in both periods: {len(groups_pivot)}")
print("\nRate changes:")
print(groups_pivot.sort('pct_change', descending=True))

# Summary statistics of rate changes
if len(groups_pivot) > 0:
    print("\n" + "="*80)
    print("RATE CHANGE STATISTICS")
    print("="*80)
    print(f"Mean rate change: {groups_pivot['pct_change'].mean():.2f}%")
    print(f"Median rate change: {groups_pivot['pct_change'].median():.2f}%")
    print(f"Std dev: {groups_pivot['pct_change'].std():.2f}%")
    print(f"Min change: {groups_pivot['pct_change'].min():.2f}%")
    print(f"Max change: {groups_pivot['pct_change'].max():.2f}%")

    # Count increases vs decreases
    increases = groups_pivot.filter(pl.col('pct_change') > 1)
    decreases = groups_pivot.filter(pl.col('pct_change') < -1)
    stable = groups_pivot.filter((pl.col('pct_change') >= -1) & (pl.col('pct_change') <= 1))

    print(f"\nGroups with >1% increase: {len(increases)} ({len(increases)/len(groups_pivot)*100:.1f}%)")
    print(f"Groups with >1% decrease: {len(decreases)} ({len(decreases)/len(groups_pivot)*100:.1f}%)")
    print(f"Groups stable (±1%): {len(stable)} ({len(stable)/len(groups_pivot)*100:.1f}%)")

print("\n" + "="*80)
print("RATE CHANGES BY SERVICE TYPE")
print("="*80)
service_changes = groups_pivot.group_by('rate_service').agg([
    pl.count().alias('groups'),
    pl.col('pct_change').mean().alias('avg_pct_change'),
    pl.col('pct_change').median().alias('median_pct_change'),
    pl.col('dollar_change').mean().alias('avg_dollar_change')
]).sort('avg_pct_change', descending=True)
print(service_changes)

print("\n" + "="*80)
print("RATE CHANGES BY WEIGHT BRACKET")
print("="*80)
weight_changes = groups_pivot.group_by('weight_bracket').agg([
    pl.count().alias('groups'),
    pl.col('pct_change').mean().alias('avg_pct_change'),
    pl.col('pct_change').median().alias('median_pct_change'),
    pl.col('dollar_change').mean().alias('avg_dollar_change')
]).sort('weight_bracket')
print(weight_changes)

print("\n" + "="*80)
print("RATE CHANGES BY ZONE")
print("="*80)
zone_changes = groups_pivot.group_by('actual_zone').agg([
    pl.count().alias('groups'),
    pl.col('pct_change').mean().alias('avg_pct_change'),
    pl.col('pct_change').median().alias('median_pct_change'),
    pl.col('dollar_change').mean().alias('avg_dollar_change')
]).sort('actual_zone')
print(zone_changes)

# Find specific examples of rate changes
print("\n" + "="*80)
print("EXAMPLES OF LARGEST RATE INCREASES")
print("="*80)
top_increases = groups_pivot.sort('pct_change', descending=True).head(10)
print(top_increases)

print("\n" + "="*80)
print("EXAMPLES OF LARGEST RATE DECREASES")
print("="*80)
top_decreases = groups_pivot.sort('pct_change').head(10)
print(top_decreases)

# Show specific shipment examples for a few groups
print("\n" + "="*80)
print("SPECIFIC SHIPMENT EXAMPLES (Top 3 rate increase groups)")
print("="*80)

for i in range(min(3, len(top_increases))):
    row = top_increases.row(i, named=True)
    service = row['rate_service']
    zone = row['actual_zone']
    weight = row['weight_bracket']

    print(f"\nGroup: {service}, Zone {zone}, {weight}")
    print(f"Rate change: {row['pct_change']:.2f}% (${row['Dec 2025']:.2f} → ${row['Jan 2026+']:.2f})")

    examples = df.filter(
        (pl.col('rate_service') == service) &
        (pl.col('actual_zone') == zone) &
        (pl.col('weight_bracket') == weight)
    ).select([
        'ship_date', 'period', 'billable_weight_lbs', 'actual_base',
        'pcs_ordernumber', 'invoice_number'
    ]).sort('ship_date').head(10)

    print(examples)

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
