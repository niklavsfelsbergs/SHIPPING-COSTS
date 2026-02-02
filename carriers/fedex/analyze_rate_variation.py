"""
Analyze natural variation in FedEx base rates within December 2025 to compare against Jan 2026 increases.
This helps determine if observed rate changes are due to a rate increase or natural variation.
"""

import polars as pl
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("="*80)
print("ANALYZING NATURAL VARIATION IN FEDEX BASE RATES")
print("="*80)

# Load data
df = pl.read_parquet("C:/Users/niklavs.felsbergs/Desktop/SHIPPING-COSTS/carriers/fedex/dashboard/data/comparison.parquet")

# Filter to only rows with actual_base values
df = df.filter(pl.col('actual_base').is_not_null())
print(f"Total shipments with actual_base data: {len(df):,}")

# Create weight brackets
df = df.with_columns([
    pl.when(pl.col('billable_weight_lbs') <= 5).then(pl.lit('0-5 lbs'))
    .when(pl.col('billable_weight_lbs') <= 10).then(pl.lit('5-10 lbs'))
    .when(pl.col('billable_weight_lbs') <= 20).then(pl.lit('10-20 lbs'))
    .when(pl.col('billable_weight_lbs') <= 50).then(pl.lit('20-50 lbs'))
    .otherwise(pl.lit('50+ lbs'))
    .alias('weight_bracket')
])

# Focus on December 2025 only
dec_df = df.filter(pl.col('ship_date') < pl.date(2026, 1, 1))
print(f"December 2025 shipments: {len(dec_df):,}")

print("\n" + "="*80)
print("WITHIN-GROUP VARIATION IN DECEMBER 2025")
print("="*80)
print("Analyzing how much base rates vary for 'comparable' shipments in Dec 2025")
print("This establishes baseline natural variation in pricing")

# Calculate variation within each comparable group in December
dec_variation = dec_df.group_by(['rate_service', 'actual_zone', 'weight_bracket']).agg([
    pl.len().alias('shipments'),
    pl.col('actual_base').mean().alias('avg_base'),
    pl.col('actual_base').std().alias('std_base'),
    pl.col('actual_base').min().alias('min_base'),
    pl.col('actual_base').max().alias('max_base'),
    ((pl.col('actual_base').max() - pl.col('actual_base').min()) / pl.col('actual_base').mean() * 100).alias('range_pct'),
    pl.col('billable_weight_lbs').mean().alias('avg_weight'),
    pl.col('billable_weight_lbs').std().alias('std_weight')
]).filter(
    pl.col('shipments') >= 10  # Groups with at least 10 shipments for meaningful stats
).sort('std_base', descending=True, nulls_last=True)

print(f"\nGroups with >= 10 shipments in Dec 2025: {len(dec_variation)}")

# Filter to groups with valid std_base
valid_variation = dec_variation.filter(pl.col('std_base').is_not_null())
print(f"Groups with calculable variation (>1 unique value): {len(valid_variation)}")

if len(valid_variation) > 0:
    print("\nTop groups by base rate variation (standard deviation):")
    print(valid_variation.head(20))

    print("\n" + "="*80)
    print("VARIATION STATISTICS - DECEMBER 2025")
    print("="*80)

    print(f"Average std dev within groups: ${valid_variation['std_base'].mean():.2f}")
    print(f"Median std dev within groups: ${valid_variation['std_base'].median():.2f}")
    print(f"Average range (max-min) within groups: {valid_variation['range_pct'].mean():.1f}%")
    print(f"Median range (max-min) within groups: {valid_variation['range_pct'].median():.1f}%")

    # Look at specific groups with high variation
    print("\n" + "="*80)
    print("EXAMPLES OF HIGH VARIATION GROUPS IN DECEMBER 2025")
    print("="*80)

    for i in range(min(3, len(valid_variation))):
        row = valid_variation.row(i, named=True)
        service = row['rate_service']
        zone = row['actual_zone']
        weight = row['weight_bracket']

        print(f"\n{i+1}. {service}, Zone {zone}, {weight}")
        print(f"   Shipments: {row['shipments']}")
        print(f"   Avg base: ${row['avg_base']:.2f} ± ${row['std_base']:.2f}")
        print(f"   Range: ${row['min_base']:.2f} - ${row['max_base']:.2f} ({row['range_pct']:.1f}%)")
        print(f"   Avg weight: {row['avg_weight']:.2f} lbs")

        # Show actual shipments
        examples = dec_df.filter(
            (pl.col('rate_service') == service) &
            (pl.col('actual_zone') == zone) &
            (pl.col('weight_bracket') == weight)
        ).select([
            'ship_date', 'billable_weight_lbs', 'actual_base', 'pcs_ordernumber'
        ]).sort('actual_base', descending=True).head(10)

        print("   Sample shipments (highest base rates):")
        print(examples)

# Now compare natural variation to Dec->Jan rate changes
print("\n" + "="*80)
print("COMPARING NATURAL VARIATION TO DEC→JAN RATE CHANGES")
print("="*80)

# Get Jan 2026 data
jan_df = df.filter(pl.col('ship_date') >= pl.date(2026, 1, 1))
print(f"January 2026 shipments: {len(jan_df):,}")

# Calculate average base rates for comparable groups in both periods
dec_avg = dec_df.group_by(['rate_service', 'actual_zone', 'weight_bracket']).agg([
    pl.len().alias('dec_shipments'),
    pl.col('actual_base').mean().alias('dec_avg_base'),
    pl.col('actual_base').std().alias('dec_std_base')
]).filter(pl.col('dec_shipments') >= 5)

jan_avg = jan_df.group_by(['rate_service', 'actual_zone', 'weight_bracket']).agg([
    pl.len().alias('jan_shipments'),
    pl.col('actual_base').mean().alias('jan_avg_base'),
    pl.col('actual_base').std().alias('jan_std_base')
]).filter(pl.col('jan_shipments') >= 5)

# Join to compare
comparison = dec_avg.join(
    jan_avg,
    on=['rate_service', 'actual_zone', 'weight_bracket'],
    how='inner'
).with_columns([
    (pl.col('jan_avg_base') - pl.col('dec_avg_base')).alias('dollar_change'),
    ((pl.col('jan_avg_base') - pl.col('dec_avg_base')) / pl.col('dec_avg_base') * 100).alias('pct_change'),
    # How many standard deviations is the change?
    pl.when(pl.col('dec_std_base').is_not_null() & (pl.col('dec_std_base') > 0))
    .then((pl.col('jan_avg_base') - pl.col('dec_avg_base')) / pl.col('dec_std_base'))
    .otherwise(pl.lit(None))
    .alias('std_devs_change')
]).sort('pct_change', descending=True)

print(f"\nGroups in both periods: {len(comparison)}")
print("\nRate changes with context of natural variation:")
print(comparison.select([
    'rate_service', 'actual_zone', 'weight_bracket',
    'dec_shipments', 'jan_shipments',
    'dec_avg_base', 'dec_std_base',
    'jan_avg_base',
    'pct_change', 'std_devs_change'
]))

print("\n" + "="*80)
print("STATISTICAL SIGNIFICANCE OF RATE CHANGES")
print("="*80)

# Filter to groups where we can calculate std devs
measurable = comparison.filter(pl.col('std_devs_change').is_not_null())
print(f"\nGroups with measurable variation: {len(measurable)} of {len(comparison)}")

if len(measurable) > 0:
    # Changes > 2 standard deviations are likely real rate changes, not natural variation
    significant = measurable.filter(pl.col('std_devs_change').abs() > 2)
    print(f"Groups with changes >2 std devs (likely real rate changes): {len(significant)}")
    print(f"Percentage: {len(significant)/len(measurable)*100:.1f}%")

    if len(significant) > 0:
        print("\nThese groups show statistically significant increases:")
        print(significant.select([
            'rate_service', 'actual_zone', 'weight_bracket',
            'dec_avg_base', 'jan_avg_base', 'pct_change', 'std_devs_change'
        ]).sort('std_devs_change', descending=True))

    # Natural variation cases
    natural_var = measurable.filter(pl.col('std_devs_change').abs() <= 2)
    print(f"\nGroups with changes ≤2 std devs (could be natural variation): {len(natural_var)}")
    if len(natural_var) > 0:
        print(natural_var.select([
            'rate_service', 'actual_zone', 'weight_bracket',
            'dec_avg_base', 'jan_avg_base', 'pct_change', 'std_devs_change'
        ]).sort('std_devs_change', descending=True))

print("\n" + "="*80)
print("WEIGHT VARIATION ANALYSIS")
print("="*80)
print("Checking if weight differences could explain rate differences")

# Get weight distributions
dec_weight_dist = dec_df.group_by(['rate_service', 'actual_zone', 'weight_bracket']).agg([
    pl.col('billable_weight_lbs').mean().alias('dec_avg_weight'),
    pl.col('billable_weight_lbs').median().alias('dec_median_weight'),
    pl.col('billable_weight_lbs').std().alias('dec_std_weight')
])

jan_weight_dist = jan_df.group_by(['rate_service', 'actual_zone', 'weight_bracket']).agg([
    pl.col('billable_weight_lbs').mean().alias('jan_avg_weight'),
    pl.col('billable_weight_lbs').median().alias('jan_median_weight'),
    pl.col('billable_weight_lbs').std().alias('jan_std_weight')
])

weight_comparison = dec_weight_dist.join(
    jan_weight_dist,
    on=['rate_service', 'actual_zone', 'weight_bracket'],
    how='inner'
).join(
    comparison.select(['rate_service', 'actual_zone', 'weight_bracket', 'pct_change', 'std_devs_change']),
    on=['rate_service', 'actual_zone', 'weight_bracket'],
    how='inner'
).with_columns([
    ((pl.col('jan_avg_weight') - pl.col('dec_avg_weight')) / pl.col('dec_avg_weight') * 100).alias('weight_pct_change')
]).sort('pct_change', descending=True)

print("\nDid heavier packages in Jan 2026 explain higher base rates?")
print(weight_comparison.select([
    'rate_service', 'actual_zone', 'weight_bracket',
    'dec_avg_weight', 'jan_avg_weight', 'weight_pct_change',
    'pct_change', 'std_devs_change'
]))

# Correlation
corr_result = weight_comparison.select([
    pl.corr('weight_pct_change', 'pct_change').alias('correlation')
])
if corr_result['correlation'][0] is not None:
    print(f"\nCorrelation between weight change and base rate change: {corr_result['correlation'][0]:.3f}")

print("\n" + "="*80)
print("SUMMARY CONCLUSION")
print("="*80)

total_groups = len(comparison)
if len(measurable) > 0:
    rate_increase_groups = len(significant)
    natural_var_groups = len(natural_var)

    print(f"Total comparable groups: {total_groups}")
    print(f"Measurable groups (with variation data): {len(measurable)}")
    print(f"Groups with likely rate increases (>2σ): {rate_increase_groups} ({rate_increase_groups/len(measurable)*100:.1f}%)")
    print(f"Groups within natural variation (≤2σ): {natural_var_groups} ({natural_var_groups/len(measurable)*100:.1f}%)")

    if len(significant) > 0:
        avg_increase = significant['pct_change'].mean()
        print(f"\nAverage rate increase for significant groups: {avg_increase:.2f}%")

        print("\nEVIDENCE FOR RATE INCREASE:")
        if rate_increase_groups / len(measurable) > 0.5:
            print("✓ STRONG EVIDENCE: Majority of measurable groups show changes beyond natural variation")
        else:
            print("✗ WEAK EVIDENCE: Most measurable groups within natural variation")

        if avg_increase > 5:
            print(f"✓ STRONG EVIDENCE: Average increase of {avg_increase:.2f}% is substantial")
        else:
            print("✗ WEAK EVIDENCE: Changes are small")
else:
    print("Unable to perform statistical significance testing - insufficient variation data")
    print(f"However, {total_groups} groups show rate changes averaging {comparison['pct_change'].mean():.2f}%")

print("\n" + "="*80)
