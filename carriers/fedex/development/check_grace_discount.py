"""
Check if Grace Discount and Earned Discount affect our base rate calculations.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
from datetime import date
import polars as pl

INVOICE_PARQUET = Path(__file__).parent / "invoice_data.parquet"


def main():
    print("Loading invoice data...")
    invoice_df = pl.read_parquet(INVOICE_PARQUET)

    # Filter Q3+Q4 2025, Home Delivery
    print("Filtering Q3+Q4 2025 Home Delivery...")
    df = invoice_df.filter(
        (pl.col("invoice_date") >= date(2025, 7, 1)) &
        (pl.col("invoice_date") <= date(2025, 12, 31)) &
        (pl.col("service_type") == "Home Delivery") &
        (pl.col("shipping_zone").is_in(["2", "3", "4", "5", "6", "7", "8", "02", "03", "04", "05", "06", "07", "08"]))
    )

    # Check Grace Discount and Earned Discount prevalence
    print("\n" + "=" * 80)
    print("DISCOUNT ANALYSIS")
    print("=" * 80)

    # Total unique shipments (from PP rows)
    pp_df = df.filter(pl.col("charge_description") == "Performance Pricing")
    total_shipments = pp_df.select("trackingnumber").unique().height
    print(f"Total unique shipments: {total_shipments:,}")

    # Grace Discount
    grace_df = df.filter(pl.col("charge_description") == "Grace Discount")
    grace_trackings = grace_df.select("trackingnumber").unique()
    print(f"\nGrace Discount:")
    print(f"  Shipments with Grace Discount: {len(grace_trackings):,} ({len(grace_trackings)/total_shipments*100:.1f}%)")
    print(f"  Average amount: ${grace_df['charge_description_amount'].cast(pl.Float64).mean():.2f}")

    # Earned Discount
    earned_df = df.filter(pl.col("charge_description") == "Earned Discount")
    earned_trackings = earned_df.select("trackingnumber").unique()
    print(f"\nEarned Discount:")
    print(f"  Shipments with Earned Discount: {len(earned_trackings):,} ({len(earned_trackings)/total_shipments*100:.1f}%)")
    print(f"  Average amount: ${earned_df['charge_description_amount'].cast(pl.Float64).mean():.2f}")

    # Build dataset with all discounts
    print("\n" + "=" * 80)
    print("COMPARING DISCOUNT COMBINATIONS")
    print("=" * 80)

    # Build dataset: for each tracking, get base_charge, PP, Grace, and Earned
    pp_data = df.filter(
        pl.col("charge_description") == "Performance Pricing"
    ).select([
        "trackingnumber",
        pl.col("shipping_zone").str.replace("^0", "").cast(pl.Int64).alias("zone"),
        pl.col("rated_weight").cast(pl.Int64).alias("weight_lbs"),
        pl.col("transportation_charge_usd").cast(pl.Float64).alias("base_charge"),
        pl.col("charge_description_amount").cast(pl.Float64).alias("pp_amount")
    ])

    grace_data = df.filter(
        pl.col("charge_description") == "Grace Discount"
    ).select([
        "trackingnumber",
        pl.col("charge_description_amount").cast(pl.Float64).alias("grace_amount")
    ])

    earned_data = df.filter(
        pl.col("charge_description") == "Earned Discount"
    ).select([
        "trackingnumber",
        pl.col("charge_description_amount").cast(pl.Float64).alias("earned_amount")
    ])

    # Join all
    combined = pp_data.join(grace_data, on="trackingnumber", how="left")
    combined = combined.join(earned_data, on="trackingnumber", how="left")
    combined = combined.with_columns([
        pl.col("grace_amount").fill_null(0),
        pl.col("earned_amount").fill_null(0)
    ])

    # Calculate final rates with different combinations
    combined = combined.with_columns([
        (pl.col("base_charge") + pl.col("pp_amount")).round(2).alias("base_plus_pp"),
        (pl.col("base_charge") + pl.col("pp_amount") + pl.col("grace_amount")).round(2).alias("base_pp_grace"),
        (pl.col("base_charge") + pl.col("pp_amount") + pl.col("earned_amount")).round(2).alias("base_pp_earned"),
        (pl.col("base_charge") + pl.col("pp_amount") + pl.col("grace_amount") + pl.col("earned_amount")).round(2).alias("base_pp_grace_earned")
    ])

    # Compare to original rate card
    print("\nLoading original rate card...")
    rate_card = pl.read_csv(Path(__file__).parent.parent / "data" / "reference" / "base_rates_home_delivery.csv")
    rate_long = rate_card.unpivot(
        index="weight_lbs",
        variable_name="zone_col",
        value_name="our_rate"
    ).with_columns(
        pl.col("zone_col").str.replace("zone_", "").cast(pl.Int64).alias("zone")
    ).select(["weight_lbs", "zone", "our_rate"])

    # Join with our rates
    comparison = combined.join(
        rate_long,
        on=["weight_lbs", "zone"],
        how="left"
    )

    # Calculate differences for each combination
    comparison = comparison.with_columns([
        (pl.col("our_rate") - pl.col("base_plus_pp")).round(2).alias("diff_base_pp"),
        (pl.col("our_rate") - pl.col("base_pp_grace")).round(2).alias("diff_base_pp_grace"),
        (pl.col("our_rate") - pl.col("base_pp_earned")).round(2).alias("diff_base_pp_earned"),
        (pl.col("our_rate") - pl.col("base_pp_grace_earned")).round(2).alias("diff_all")
    ])

    print(f"\nTotal shipments: {len(comparison):,}")

    # Check match rates for each combination
    print("\n" + "=" * 80)
    print("MATCH RATES FOR EACH FORMULA")
    print("=" * 80)

    formulas = [
        ("base + PP", "diff_base_pp"),
        ("base + PP + Grace", "diff_base_pp_grace"),
        ("base + PP + Earned", "diff_base_pp_earned"),
        ("base + PP + Grace + Earned", "diff_all"),
    ]

    for name, col in formulas:
        matches = comparison.filter(pl.col(col).abs() < 0.02)
        pct = len(matches) / len(comparison) * 100
        print(f"{name}: {len(matches):,} / {len(comparison):,} ({pct:.1f}%)")

    # Show sample rows
    print("\n" + "=" * 80)
    print("SAMPLE ROWS")
    print("=" * 80)
    print(comparison.select([
        "zone", "weight_lbs", "base_charge", "pp_amount", "grace_amount", "earned_amount",
        "base_plus_pp", "base_pp_grace_earned", "our_rate", "diff_base_pp", "diff_all"
    ]).head(30))


if __name__ == "__main__":
    main()
