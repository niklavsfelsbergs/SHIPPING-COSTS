"""
Derive the correct discounted rate card from invoice data.

Formula: correct_rate = undiscounted_rate + invoice_pp
(PP is negative, so this gives the net rate after discount)
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
import polars as pl

INVOICE_PARQUET = Path(__file__).parent / "invoice_data.parquet"
UNDISCOUNTED_RATES = Path(__file__).parent.parent / "temp_files" / "fedex_ground_rates_2025_undiscounted.csv"
CURRENT_RATES = Path(__file__).parent.parent / "data" / "reference" / "base_rates_home_delivery.csv"


def main():
    # Load invoice data
    print("Loading invoice data...")
    invoice_df = pl.read_parquet(INVOICE_PARQUET)

    # Filter for Q3+Q4 2025, Home Delivery, Performance Pricing rows
    print("Filtering for Q3+Q4 2025 Home Delivery with Performance Pricing...")
    from datetime import date
    df = invoice_df.filter(
        (pl.col("invoice_date") >= date(2025, 7, 1)) &
        (pl.col("invoice_date") <= date(2025, 12, 31)) &
        (pl.col("service_type") == "Home Delivery") &
        (pl.col("charge_description") == "Performance Pricing")
    )
    print(f"  Filtered to {len(df):,} rows")

    # Get unique weight/zone/PP combinations
    # Since PP is consistent (verified earlier), we can take the mode
    pp_by_weight_zone = df.group_by(["rated_weight", "shipping_zone"]).agg([
        pl.col("charge_description_amount").cast(pl.Float64).mode().first().alias("invoice_pp"),
        pl.len().alias("count")
    ])

    # Cast to proper types for joining
    pp_by_weight_zone = pp_by_weight_zone.with_columns([
        pl.col("rated_weight").cast(pl.Int64),
        pl.col("shipping_zone").cast(pl.Int64)
    ])
    print(f"  Unique weight/zone combinations: {len(pp_by_weight_zone)}")

    # Load undiscounted rates
    print("\nLoading undiscounted rates...")
    undiscounted = pl.read_csv(UNDISCOUNTED_RATES)

    # Unpivot to long format
    undiscounted_long = undiscounted.unpivot(
        index="Weight_lbs",
        variable_name="zone_col",
        value_name="undiscounted_rate"
    ).with_columns([
        pl.col("zone_col").str.replace("Zone", "").cast(pl.Int64).alias("zone"),
        pl.col("Weight_lbs").cast(pl.Int64).alias("weight")
    ]).select(["weight", "zone", "undiscounted_rate"])

    # Join with invoice PP data
    print("\nJoining to derive correct rates...")
    derived = pp_by_weight_zone.join(
        undiscounted_long,
        left_on=["rated_weight", "shipping_zone"],
        right_on=["weight", "zone"],
        how="inner"
    )

    # Calculate correct discounted rate
    derived = derived.with_columns(
        (pl.col("undiscounted_rate") + pl.col("invoice_pp")).round(2).alias("correct_rate")
    )

    print(f"  Derived rates for {len(derived)} weight/zone combinations")

    # Load current rates for comparison
    print("\nLoading current rates...")
    current = pl.read_csv(CURRENT_RATES)
    current_long = current.unpivot(
        index="weight_lbs",
        variable_name="zone_col",
        value_name="current_rate"
    ).with_columns([
        pl.col("zone_col").str.replace("zone_", "").cast(pl.Int64).alias("zone"),
        pl.col("weight_lbs").cast(pl.Int64).alias("weight")
    ]).select(["weight", "zone", "current_rate"])

    # Join with current rates
    comparison = derived.join(
        current_long,
        left_on=["rated_weight", "shipping_zone"],
        right_on=["weight", "zone"],
        how="left"
    )

    # Calculate difference
    comparison = comparison.with_columns(
        (pl.col("correct_rate") - pl.col("current_rate")).round(2).alias("rate_diff")
    )

    # Show summary
    print("\n" + "=" * 80)
    print("RATE COMPARISON: CURRENT vs DERIVED FROM INVOICE")
    print("=" * 80)

    matches = comparison.filter(pl.col("rate_diff").abs() < 0.01)
    mismatches = comparison.filter(pl.col("rate_diff").abs() >= 0.01)

    print(f"\nTotal comparisons: {len(comparison)}")
    print(f"Matches (diff < $0.01): {len(matches)} ({len(matches)/len(comparison)*100:.1f}%)")
    print(f"Mismatches: {len(mismatches)} ({len(mismatches)/len(comparison)*100:.1f}%)")

    # Show sample of mismatches
    if len(mismatches) > 0:
        print("\nSample mismatches:")
        print(mismatches.select([
            "rated_weight", "shipping_zone", "undiscounted_rate", "invoice_pp",
            "correct_rate", "current_rate", "rate_diff"
        ]).sort(["shipping_zone", "rated_weight"]).head(30))

    # Show discount percentages
    print("\n" + "=" * 80)
    print("DISCOUNT ANALYSIS")
    print("=" * 80)

    derived = derived.with_columns(
        ((pl.col("invoice_pp").abs() / pl.col("undiscounted_rate")) * 100).round(2).alias("discount_pct")
    )

    # Group by zone
    zone_discounts = derived.group_by("shipping_zone").agg([
        pl.col("discount_pct").mean().alias("avg_discount_pct"),
        pl.col("discount_pct").min().alias("min_discount_pct"),
        pl.col("discount_pct").max().alias("max_discount_pct"),
        pl.len().alias("count")
    ]).sort("shipping_zone")

    print("\nDiscount % by Zone:")
    print(zone_discounts)

    # Group by weight ranges
    derived = derived.with_columns(
        pl.when(pl.col("rated_weight") <= 10).then(pl.lit("1-10"))
        .when(pl.col("rated_weight") <= 30).then(pl.lit("11-30"))
        .when(pl.col("rated_weight") <= 50).then(pl.lit("31-50"))
        .when(pl.col("rated_weight") <= 70).then(pl.lit("51-70"))
        .otherwise(pl.lit("71+"))
        .alias("weight_range")
    )

    weight_discounts = derived.group_by("weight_range").agg([
        pl.col("discount_pct").mean().alias("avg_discount_pct"),
        pl.col("discount_pct").min().alias("min_discount_pct"),
        pl.col("discount_pct").max().alias("max_discount_pct"),
        pl.len().alias("count")
    ]).sort("weight_range")

    print("\nDiscount % by Weight Range:")
    print(weight_discounts)

    # Pivot to create new rate card
    print("\n" + "=" * 80)
    print("DERIVED RATE CARD")
    print("=" * 80)

    rate_card = derived.pivot(
        index="rated_weight",
        on="shipping_zone",
        values="correct_rate"
    ).sort("rated_weight")

    # Rename columns to match expected format
    rate_card = rate_card.rename({"rated_weight": "weight_lbs"})
    for col in rate_card.columns:
        if col != "weight_lbs" and col.isdigit():
            rate_card = rate_card.rename({col: f"zone_{col}"})

    print("\nFirst 30 rows of derived rate card:")
    print(rate_card.head(30))

    # Save to CSV
    output_path = Path(__file__).parent / "derived_rates_home_delivery.csv"
    rate_card.write_csv(output_path)
    print(f"\nSaved derived rate card to: {output_path}")


if __name__ == "__main__":
    main()
