"""
Investigate why there's no variation in base rates within groups.
This will help us understand FedEx pricing structure.
"""

import polars as pl
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Load data
df = pl.read_parquet("C:/Users/niklavs.felsbergs/Desktop/SHIPPING-COSTS/carriers/fedex/dashboard/data/comparison.parquet")
df = df.filter(pl.col('actual_base').is_not_null())

# Create weight brackets
df = df.with_columns([
    pl.when(pl.col('billable_weight_lbs') <= 5).then(pl.lit('0-5 lbs'))
    .when(pl.col('billable_weight_lbs') <= 10).then(pl.lit('5-10 lbs'))
    .when(pl.col('billable_weight_lbs') <= 20).then(pl.lit('10-20 lbs'))
    .when(pl.col('billable_weight_lbs') <= 50).then(pl.lit('20-50 lbs'))
    .otherwise(pl.lit('50+ lbs'))
    .alias('weight_bracket')
])

print("="*80)
print("INVESTIGATING FEDEX BASE RATE STRUCTURE")
print("="*80)

# Look at a single group in detail
print("\nExample: Home Delivery, Zone 02, 10-20 lbs")
example_group = df.filter(
    (pl.col('rate_service') == 'Home Delivery') &
    (pl.col('actual_zone') == '02') &
    (pl.col('weight_bracket') == '10-20 lbs')
).select([
    'ship_date', 'billable_weight_lbs', 'actual_base',
    'pcs_ordernumber', 'actual_rated_weight_lbs'
]).sort('ship_date')

print(f"Total shipments: {len(example_group)}")
print(f"Date range: {example_group['ship_date'].min()} to {example_group['ship_date'].max()}")
print(f"Unique actual_base values: {example_group['actual_base'].n_unique()}")
print("\nFirst 30 shipments:")
print(example_group.head(30))

# Check if base rate varies by exact weight
print("\n" + "="*80)
print("DO BASE RATES VARY BY EXACT WEIGHT WITHIN A WEIGHT BRACKET?")
print("="*80)

weight_detail = example_group.group_by('billable_weight_lbs').agg([
    pl.len().alias('shipments'),
    pl.col('actual_base').mean().alias('avg_base'),
    pl.col('actual_base').n_unique().alias('unique_bases'),
    pl.col('actual_base').min().alias('min_base'),
    pl.col('actual_base').max().alias('max_base')
]).sort('billable_weight_lbs')

print(weight_detail)

# Check if base rate varies by actual_rated_weight
print("\n" + "="*80)
print("DO BASE RATES VARY BY ACTUAL_RATED_WEIGHT?")
print("="*80)

rated_weight_detail = example_group.group_by('actual_rated_weight_lbs').agg([
    pl.len().alias('shipments'),
    pl.col('billable_weight_lbs').mean().alias('avg_billable_weight'),
    pl.col('actual_base').mean().alias('avg_base'),
    pl.col('actual_base').n_unique().alias('unique_bases')
]).sort('actual_rated_weight_lbs')

print(rated_weight_detail)

# Look at shipments over time
print("\n" + "="*80)
print("DO BASE RATES CHANGE OVER TIME?")
print("="*80)

# Group by month
monthly_rates = example_group.with_columns([
    pl.col('ship_date').dt.strftime('%Y-%m').alias('month')
]).group_by('month').agg([
    pl.len().alias('shipments'),
    pl.col('actual_base').mean().alias('avg_base'),
    pl.col('actual_base').n_unique().alias('unique_bases'),
    pl.col('billable_weight_lbs').mean().alias('avg_weight')
]).sort('month')

print(monthly_rates)

# Show examples from Dec vs Jan
print("\n" + "="*80)
print("DECEMBER 2025 vs JANUARY 2026 EXAMPLES")
print("="*80)

dec_examples = example_group.filter(pl.col('ship_date') < pl.date(2026, 1, 1)).head(10)
jan_examples = example_group.filter(pl.col('ship_date') >= pl.date(2026, 1, 1)).head(10)

print("\nDecember 2025:")
print(dec_examples)

print("\nJanuary 2026:")
print(jan_examples)

# Let's check if it's a zone + rated_weight lookup
print("\n" + "="*80)
print("FEDEX PRICING STRUCTURE HYPOTHESIS")
print("="*80)

# For each combination of service + zone + rated_weight, is there exactly one base rate?
rate_structure = df.filter(pl.col('ship_date') < pl.date(2026, 1, 1)).group_by([
    'rate_service', 'actual_zone', 'actual_rated_weight_lbs'
]).agg([
    pl.len().alias('shipments'),
    pl.col('actual_base').n_unique().alias('unique_bases'),
    pl.col('actual_base').mean().alias('base_rate')
]).filter(pl.col('shipments') >= 3)

groups_with_multiple_rates = rate_structure.filter(pl.col('unique_bases') > 1)

print(f"Total service+zone+rated_weight combinations (≥3 shipments): {len(rate_structure)}")
print(f"Combinations with multiple base rates: {len(groups_with_multiple_rates)}")
print(f"Combinations with exactly one base rate: {len(rate_structure) - len(groups_with_multiple_rates)}")

if len(groups_with_multiple_rates) > 0:
    print("\nExamples of groups with multiple base rates (anomalies):")
    print(groups_with_multiple_rates.head(10))

    # Investigate one anomaly
    if len(groups_with_multiple_rates) > 0:
        anomaly = groups_with_multiple_rates.row(0, named=True)
        service = anomaly['rate_service']
        zone = anomaly['actual_zone']
        weight = anomaly['actual_rated_weight_lbs']

        print(f"\nInvestigating: {service}, Zone {zone}, Rated Weight {weight} lbs")
        anomaly_detail = df.filter(
            (pl.col('rate_service') == service) &
            (pl.col('actual_zone') == zone) &
            (pl.col('actual_rated_weight_lbs') == weight) &
            (pl.col('ship_date') < pl.date(2026, 1, 1))
        ).select([
            'ship_date', 'billable_weight_lbs', 'actual_rated_weight_lbs',
            'actual_base', 'invoice_number'
        ]).sort('actual_base')

        print(anomaly_detail)

print("\n" + "="*80)
print("CONCLUSION ON PRICING STRUCTURE")
print("="*80)

if len(groups_with_multiple_rates) == 0:
    print("✓ CONFIRMED: FedEx uses a fixed rate card")
    print("  Base rate = f(service, zone, rated_weight)")
    print("  No variation within these dimensions in December 2025")
    print("")
    print("IMPLICATION FOR RATE INCREASE ANALYSIS:")
    print("  Since base rates don't vary naturally, ANY systematic change")
    print("  in base rates between Dec 2025 and Jan 2026 indicates a")
    print("  rate increase, not random variation.")
else:
    pct_with_variation = len(groups_with_multiple_rates) / len(rate_structure) * 100
    print(f"⚠ MIXED: {pct_with_variation:.1f}% of groups show variation")
    print("  Base rates are mostly deterministic but have some exceptions")

print("\n" + "="*80)
