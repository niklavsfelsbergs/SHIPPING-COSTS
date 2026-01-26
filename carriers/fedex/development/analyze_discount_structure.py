"""
Analyze the FedEx discount structure from invoice data.

Goal: Determine what discount percentage applies to each weight bracket.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
from datetime import date
import polars as pl

INVOICE_PARQUET = Path(__file__).parent / "invoice_data.parquet"
UNDISCOUNTED_RATES = Path(__file__).parent.parent / "temp_files" / "fedex_ground_rates_2025_undiscounted.csv"


def main():
    # Load invoice data
    print("Loading invoice data...")
    invoice_df = pl.read_parquet(INVOICE_PARQUET)

    # Filter for Q3+Q4 2025, Home Delivery, Performance Pricing rows
    print("Filtering for Q3+Q4 2025 Home Delivery with Performance Pricing...")
    df = invoice_df.filter(
        (pl.col("invoice_date") >= date(2025, 7, 1)) &
        (pl.col("invoice_date") <= date(2025, 12, 31)) &
        (pl.col("service_type") == "Home Delivery") &
        (pl.col("charge_description") == "Performance Pricing")
    )
    print(f"  Filtered to {len(df):,} rows")

    # Get PP values by weight/zone
    pp_data = df.with_columns([
        pl.col("rated_weight").cast(pl.Int64),
        pl.col("shipping_zone").cast(pl.Int64),
        pl.col("charge_description_amount").cast(pl.Float64).alias("pp_amount")
    ])

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

    # Join to get undiscounted rate for each shipment
    df_joined = pp_data.join(
        undiscounted_long,
        left_on=["rated_weight", "shipping_zone"],
        right_on=["weight", "zone"],
        how="inner"
    )

    # Calculate discount percentage for each shipment
    df_joined = df_joined.with_columns(
        ((pl.col("pp_amount").abs() / pl.col("undiscounted_rate")) * 100).round(2).alias("discount_pct")
    )

    print(f"\nTotal shipments with discount data: {len(df_joined):,}")

    # Analyze discount by exact weight
    print("\n" + "=" * 80)
    print("DISCOUNT PERCENTAGE BY WEIGHT")
    print("=" * 80)

    weight_discounts = df_joined.group_by("rated_weight").agg([
        pl.col("discount_pct").mean().round(2).alias("avg_discount"),
        pl.col("discount_pct").std().round(2).alias("std_discount"),
        pl.len().alias("count")
    ]).sort("rated_weight")

    print("\nWeights 1-50:")
    print(weight_discounts.filter(pl.col("rated_weight") <= 50))

    print("\nWeights 51-100:")
    print(weight_discounts.filter(
        (pl.col("rated_weight") > 50) & (pl.col("rated_weight") <= 100)
    ))

    # Find natural breakpoints where discount changes
    print("\n" + "=" * 80)
    print("DISCOUNT BREAKPOINTS")
    print("=" * 80)

    # Calculate the mode discount for each weight
    weight_mode_discount = df_joined.group_by("rated_weight").agg([
        pl.col("discount_pct").mode().first().alias("mode_discount"),
        pl.len().alias("count")
    ]).sort("rated_weight")

    # Look at transitions
    weight_mode_discount = weight_mode_discount.with_columns(
        pl.col("mode_discount").shift(1).alias("prev_discount")
    ).with_columns(
        (pl.col("mode_discount") - pl.col("prev_discount")).alias("discount_change")
    )

    # Show where discount changes significantly (>1%)
    transitions = weight_mode_discount.filter(
        pl.col("discount_change").abs() > 1.0
    )
    print("\nWeights where discount changes by >1%:")
    print(transitions)

    # Define weight tiers based on observed breakpoints
    print("\n" + "=" * 80)
    print("PROPOSED WEIGHT TIER DISCOUNTS")
    print("=" * 80)

    # Common FedEx weight tiers
    tiers = [
        (1, 10, "1-10 lbs"),
        (11, 25, "11-25 lbs"),
        (26, 50, "26-50 lbs"),
        (51, 150, "51-150 lbs"),
    ]

    for min_wt, max_wt, label in tiers:
        tier_data = df_joined.filter(
            (pl.col("rated_weight") >= min_wt) &
            (pl.col("rated_weight") <= max_wt)
        )
        if len(tier_data) > 0:
            avg = tier_data["discount_pct"].mean()
            std = tier_data["discount_pct"].std()
            mode_val = tier_data["discount_pct"].mode().to_list()
            mode_str = f"{mode_val[0]:.2f}%" if mode_val else "N/A"
            print(f"{label}: avg={avg:.2f}%, std={std:.2f}%, mode={mode_str}, n={len(tier_data):,}")

    # Try to find exact discount tiers by looking at most common values
    print("\n" + "=" * 80)
    print("MOST COMMON DISCOUNT VALUES (ROUNDED TO 0.5%)")
    print("=" * 80)

    df_joined = df_joined.with_columns(
        (pl.col("discount_pct") / 0.5).round() * 0.5
    ).alias("discount_rounded")

    discount_counts = df_joined.group_by("discount_pct").agg([
        pl.len().alias("count")
    ]).sort("count", descending=True)

    print(discount_counts.head(20))

    # Cross-tab: discount by weight ranges
    print("\n" + "=" * 80)
    print("CROSS-TAB: DISCOUNT BY WEIGHT RANGE AND ZONE")
    print("=" * 80)

    df_joined = df_joined.with_columns(
        pl.when(pl.col("rated_weight") <= 10).then(pl.lit("01-10"))
        .when(pl.col("rated_weight") <= 25).then(pl.lit("11-25"))
        .when(pl.col("rated_weight") <= 50).then(pl.lit("26-50"))
        .when(pl.col("rated_weight") <= 70).then(pl.lit("51-70"))
        .otherwise(pl.lit("71+"))
        .alias("weight_tier")
    )

    crosstab = df_joined.group_by(["weight_tier", "shipping_zone"]).agg([
        pl.col("discount_pct").mean().round(2).alias("avg_discount"),
        pl.len().alias("count")
    ]).sort(["weight_tier", "shipping_zone"])

    pivot_table = crosstab.pivot(
        index="weight_tier",
        on="shipping_zone",
        values="avg_discount"
    )
    print(pivot_table)


if __name__ == "__main__":
    main()
