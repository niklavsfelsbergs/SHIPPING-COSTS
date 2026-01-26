"""
Generate Performance Pricing (discount) table from invoice data.

Extracts the PP amount for each weight/zone combination from Q3+Q4 2025 invoices.
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

    # Filter for Q3+Q4 2025, Home Delivery, Performance Pricing rows
    print("Filtering for Q3+Q4 2025 Home Delivery with Performance Pricing...")
    df = invoice_df.filter(
        (pl.col("invoice_date") >= date(2025, 7, 1)) &
        (pl.col("invoice_date") <= date(2025, 12, 31)) &
        (pl.col("service_type") == "Home Delivery") &
        (pl.col("charge_description") == "Performance Pricing")
    )
    print(f"  Filtered to {len(df):,} rows")

    # Get mode PP by weight/zone (since PP is consistent, mode = the value)
    pp_by_weight_zone = df.group_by(["rated_weight", "shipping_zone"]).agg([
        pl.col("charge_description_amount").cast(pl.Float64).mode().first().alias("pp_amount"),
        pl.len().alias("count")
    ]).with_columns([
        pl.col("rated_weight").cast(pl.Int64),
        pl.col("shipping_zone").cast(pl.Int64)
    ])

    print(f"  Unique weight/zone combinations: {len(pp_by_weight_zone)}")

    # Filter to standard zones 2-8 only
    pp_standard = pp_by_weight_zone.filter(
        pl.col("shipping_zone").is_in([2, 3, 4, 5, 6, 7, 8])
    )

    # Pivot to create table
    pp_table = pp_standard.select(["rated_weight", "shipping_zone", "pp_amount"]).pivot(
        index="rated_weight",
        on="shipping_zone",
        values="pp_amount"
    ).sort("rated_weight")

    # Rename columns
    pp_table = pp_table.rename({"rated_weight": "weight_lbs"})
    for col in pp_table.columns:
        if col != "weight_lbs" and col.isdigit():
            pp_table = pp_table.rename({col: f"zone_{col}"})

    # Reorder columns
    ordered_cols = ["weight_lbs"] + [f"zone_{z}" for z in [2, 3, 4, 5, 6, 7, 8] if f"zone_{z}" in pp_table.columns]
    pp_table = pp_table.select(ordered_cols)

    print("\n" + "=" * 100)
    print("PERFORMANCE PRICING TABLE (USD) - Q3+Q4 2025 - ZONES 2-8")
    print("=" * 100)
    print("\nNote: Values are negative (discounts)")
    print(pp_table)

    # Save to CSV
    output_path = Path(__file__).parent / "performance_pricing_table.csv"
    pp_table.write_csv(output_path)
    print(f"\nSaved to: {output_path}")

    # Also show count table to see data coverage
    count_table = pp_by_weight_zone.select(["rated_weight", "shipping_zone", "count"]).pivot(
        index="rated_weight",
        on="shipping_zone",
        values="count"
    ).sort("rated_weight")

    count_table = count_table.rename({"rated_weight": "weight_lbs"})
    for col in count_table.columns:
        if col != "weight_lbs" and col.isdigit():
            count_table = count_table.rename({col: f"zone_{col}"})

    print("\n" + "=" * 100)
    print("SHIPMENT COUNTS BY WEIGHT/ZONE")
    print("=" * 100)
    print(count_table.head(50))


if __name__ == "__main__":
    main()
