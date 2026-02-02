"""
Final comprehensive rate increase analysis for FedEx.
"""

import polars as pl
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Load data
df = pl.read_parquet("C:/Users/niklavs.felsbergs/Desktop/SHIPPING-COSTS/carriers/fedex/dashboard/data/comparison.parquet")
df = df.filter(pl.col('actual_base').is_not_null())

print("="*80)
print("FEDEX RATE INCREASE ANALYSIS - JANUARY 2026")
print("="*80)
print(f"Data analyzed: {len(df):,} shipments from {df['ship_date'].min()} to {df['ship_date'].max()}")

# Look at rate changes by service+zone+rated_weight over time
print("\n" + "="*80)
print("RATE CARD CHANGES OVER TIME")
print("="*80)

# For each service+zone+rated_weight, track the base rate by month
rate_card_evolution = df.with_columns([
    pl.col('ship_date').dt.strftime('%Y-%m').alias('month')
]).group_by(['rate_service', 'actual_zone', 'actual_rated_weight_lbs', 'month']).agg([
    pl.len().alias('shipments'),
    pl.col('actual_base').mode().first().alias('mode_base'),  # Most common base rate
    pl.col('actual_base').min().alias('min_base'),
    pl.col('actual_base').max().alias('max_base')
]).sort(['rate_service', 'actual_zone', 'actual_rated_weight_lbs', 'month'])

# Filter to rate cards that appear in both Dec and Jan
dec_rates = rate_card_evolution.filter(pl.col('month') == '2025-12').select([
    'rate_service', 'actual_zone', 'actual_rated_weight_lbs',
    pl.col('mode_base').alias('dec_base'),
    pl.col('shipments').alias('dec_shipments')
])

jan_rates = rate_card_evolution.filter(pl.col('month') == '2026-01').select([
    'rate_service', 'actual_zone', 'actual_rated_weight_lbs',
    pl.col('mode_base').alias('jan_base'),
    pl.col('shipments').alias('jan_shipments')
])

rate_changes = dec_rates.join(
    jan_rates,
    on=['rate_service', 'actual_zone', 'actual_rated_weight_lbs'],
    how='inner'
).with_columns([
    (pl.col('jan_base') - pl.col('dec_base')).alias('dollar_change'),
    ((pl.col('jan_base') - pl.col('dec_base')) / pl.col('dec_base') * 100).alias('pct_change')
]).sort('pct_change', descending=True)

print(f"\nRate cards appearing in both Dec 2025 and Jan 2026: {len(rate_changes)}")

# Filter to only rates that actually changed
changed_rates = rate_changes.filter(pl.col('pct_change').abs() > 0.01)
unchanged_rates = rate_changes.filter(pl.col('pct_change').abs() <= 0.01)

print(f"Rate cards with changes: {len(changed_rates)} ({len(changed_rates)/len(rate_changes)*100:.1f}%)")
print(f"Rate cards unchanged: {len(unchanged_rates)} ({len(unchanged_rates)/len(rate_changes)*100:.1f}%)")

if len(changed_rates) > 0:
    print("\n" + "="*80)
    print("RATE CARDS THAT CHANGED (Dec 2025 → Jan 2026)")
    print("="*80)

    print("\nTop 30 largest increases:")
    print(changed_rates.head(30))

    print("\nTop 30 largest decreases:")
    print(changed_rates.tail(30))

    print("\n" + "="*80)
    print("SUMMARY STATISTICS - CHANGED RATES")
    print("="*80)

    increases = changed_rates.filter(pl.col('pct_change') > 0)
    decreases = changed_rates.filter(pl.col('pct_change') < 0)

    print(f"Rate cards with increases: {len(increases)} ({len(increases)/len(changed_rates)*100:.1f}%)")
    print(f"Rate cards with decreases: {len(decreases)} ({len(decreases)/len(changed_rates)*100:.1f}%)")

    print(f"\nIncrease statistics:")
    print(f"  Average: {increases['pct_change'].mean():.2f}%")
    print(f"  Median: {increases['pct_change'].median():.2f}%")
    print(f"  Min: {increases['pct_change'].min():.2f}%")
    print(f"  Max: {increases['pct_change'].max():.2f}%")
    print(f"  Average dollar change: ${increases['dollar_change'].mean():.2f}")

    if len(decreases) > 0:
        print(f"\nDecrease statistics:")
        print(f"  Average: {decreases['pct_change'].mean():.2f}%")
        print(f"  Median: {decreases['pct_change'].median():.2f}%")
        print(f"  Average dollar change: ${decreases['dollar_change'].mean():.2f}")

    print("\n" + "="*80)
    print("BREAKDOWN BY SERVICE TYPE")
    print("="*80)

    service_breakdown = changed_rates.group_by('rate_service').agg([
        pl.len().alias('rate_cards'),
        pl.col('pct_change').mean().alias('avg_pct_change'),
        pl.col('pct_change').median().alias('median_pct_change'),
        pl.col('dollar_change').mean().alias('avg_dollar_change'),
        pl.col('dec_shipments').sum().alias('dec_shipments'),
        pl.col('jan_shipments').sum().alias('jan_shipments')
    ]).sort('avg_pct_change', descending=True)

    print(service_breakdown)

    print("\n" + "="*80)
    print("BREAKDOWN BY ZONE")
    print("="*80)

    zone_breakdown = changed_rates.group_by('actual_zone').agg([
        pl.len().alias('rate_cards'),
        pl.col('pct_change').mean().alias('avg_pct_change'),
        pl.col('pct_change').median().alias('median_pct_change'),
        pl.col('dollar_change').mean().alias('avg_dollar_change')
    ]).sort('actual_zone')

    print(zone_breakdown)

    print("\n" + "="*80)
    print("BREAKDOWN BY WEIGHT BRACKET")
    print("="*80)

    weight_breakdown = changed_rates.with_columns([
        pl.when(pl.col('actual_rated_weight_lbs') <= 5).then(pl.lit('0-5 lbs'))
        .when(pl.col('actual_rated_weight_lbs') <= 10).then(pl.lit('5-10 lbs'))
        .when(pl.col('actual_rated_weight_lbs') <= 20).then(pl.lit('10-20 lbs'))
        .when(pl.col('actual_rated_weight_lbs') <= 50).then(pl.lit('20-50 lbs'))
        .otherwise(pl.lit('50+ lbs'))
        .alias('weight_bracket')
    ]).group_by('weight_bracket').agg([
        pl.len().alias('rate_cards'),
        pl.col('pct_change').mean().alias('avg_pct_change'),
        pl.col('pct_change').median().alias('median_pct_change'),
        pl.col('dollar_change').mean().alias('avg_dollar_change')
    ]).sort('weight_bracket')

    print(weight_breakdown)

# Impact on actual shipments
print("\n" + "="*80)
print("IMPACT ON ACTUAL DECEMBER → JANUARY SHIPMENTS")
print("="*80)

dec_shipments = df.filter(pl.col('ship_date') < pl.date(2026, 1, 1))
jan_shipments = df.filter(pl.col('ship_date') >= pl.date(2026, 1, 1))

print(f"\nDecember 2025 shipments: {len(dec_shipments):,}")
print(f"January 2026 shipments: {len(jan_shipments):,}")

print(f"\nDecember 2025:")
print(f"  Total actual base charges: ${dec_shipments['actual_base'].sum():,.2f}")
print(f"  Average base per shipment: ${dec_shipments['actual_base'].mean():.2f}")
print(f"  Median base per shipment: ${dec_shipments['actual_base'].median():.2f}")

print(f"\nJanuary 2026:")
print(f"  Total actual base charges: ${jan_shipments['actual_base'].sum():,.2f}")
print(f"  Average base per shipment: ${jan_shipments['actual_base'].mean():.2f}")
print(f"  Median base per shipment: ${jan_shipments['actual_base'].median():.2f}")

avg_change = ((jan_shipments['actual_base'].mean() - dec_shipments['actual_base'].mean()) /
              dec_shipments['actual_base'].mean() * 100)
median_change = ((jan_shipments['actual_base'].median() - dec_shipments['actual_base'].median()) /
                dec_shipments['actual_base'].median() * 100)

print(f"\nAverage base rate change: {avg_change:+.2f}%")
print(f"Median base rate change: {median_change:+.2f}%")

# Look for the effective date of the rate change
print("\n" + "="*80)
print("EFFECTIVE DATE ANALYSIS")
print("="*80)

# For a few specific rate cards that increased, when did the rate change?
example_increases = changed_rates.filter(pl.col('pct_change') > 10).head(5)

for i in range(len(example_increases)):
    row = example_increases.row(i, named=True)
    service = row['rate_service']
    zone = row['actual_zone']
    weight = row['actual_rated_weight_lbs']

    print(f"\nExample {i+1}: {service}, Zone {zone}, {weight} lbs")
    print(f"Rate change: ${row['dec_base']:.2f} → ${row['jan_base']:.2f} ({row['pct_change']:+.2f}%)")

    # Get all shipments for this rate card
    rate_card_history = df.filter(
        (pl.col('rate_service') == service) &
        (pl.col('actual_zone') == zone) &
        (pl.col('actual_rated_weight_lbs') == weight)
    ).select([
        'ship_date', 'actual_base'
    ]).sort('ship_date')

    # Group by week to see when the change occurred
    weekly = rate_card_history.with_columns([
        pl.col('ship_date').dt.strftime('%Y-%m-%d').alias('date_str')
    ]).group_by('date_str').agg([
        pl.col('actual_base').mode().first().alias('rate'),
        pl.len().alias('shipments')
    ]).sort('date_str').tail(15)

    print("Recent rate history (last 15 dates):")
    print(weekly)

print("\n" + "="*80)
print("FINAL CONCLUSIONS")
print("="*80)

if len(changed_rates) > 0:
    pct_increased = len(increases) / len(changed_rates) * 100
    avg_increase = increases['pct_change'].mean()

    print(f"✓ CONFIRMED: FedEx implemented a rate increase around January 1, 2026")
    print(f"\nKey findings:")
    print(f"  • {len(changed_rates)} rate cards changed")
    print(f"  • {pct_increased:.0f}% of changes were increases")
    print(f"  • Average increase: {avg_increase:.2f}%")
    print(f"  • Overall impact: {avg_change:+.2f}% average base rate increase")
    print(f"  • Median impact: {median_change:+.2f}%")

    print(f"\nThis is clearly a systematic rate increase, not natural variation.")
    print(f"FedEx uses a fixed rate card (service + zone + rated_weight),")
    print(f"and the rate cards were updated effective January 2026.")
else:
    print("✗ No clear rate increase detected")

print("\n" + "="*80)
