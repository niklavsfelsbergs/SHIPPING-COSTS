"""
Generate sample shipments CSV - 10 from each zone/weight combination.
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

    # Filter Q3+Q4 2025, Home Delivery, zones 2-8
    print("Filtering Q3+Q4 2025 Home Delivery...")
    df = invoice_df.filter(
        (pl.col("invoice_date") >= date(2025, 7, 1)) &
        (pl.col("invoice_date") <= date(2025, 12, 31)) &
        (pl.col("service_type") == "Home Delivery") &
        (pl.col("shipping_zone").is_in(["2", "3", "4", "5", "6", "7", "8", "02", "03", "04", "05", "06", "07", "08"]))
    )

    # Get PP rows - they have both transportation_charge and PP amount
    pp_df = df.filter(
        pl.col("charge_description") == "Performance Pricing"
    ).select([
        "trackingnumber",
        "invoice_date",
        pl.col("shipping_zone").str.replace("^0", "").cast(pl.Int64).alias("zone"),
        pl.col("rated_weight").cast(pl.Int64).alias("weight_lbs"),
        pl.col("transportation_charge_usd").cast(pl.Float64).alias("base_charge"),
        pl.col("charge_description_amount").cast(pl.Float64).alias("performance_pricing")
    ])

    # Calculate final base charge
    pp_df = pp_df.with_columns(
        (pl.col("base_charge") + pl.col("performance_pricing")).round(2).alias("final_base_charge")
    )

    joined = pp_df

    print(f"Total shipments with base + PP: {len(joined):,}")

    # Sample 10 from each zone/weight combination
    print("Sampling 10 per zone/weight combination...")

    sampled = joined.group_by(["zone", "weight_lbs"]).agg([
        pl.col("trackingnumber").head(10),
        pl.col("invoice_date").head(10),
        pl.col("base_charge").head(10),
        pl.col("performance_pricing").head(10),
        pl.col("final_base_charge").head(10),
    ]).explode([
        "trackingnumber", "invoice_date", "base_charge",
        "performance_pricing", "final_base_charge"
    ]).sort(["zone", "weight_lbs", "trackingnumber"])

    print(f"Total samples: {len(sampled):,}")

    # Reorder columns
    sampled = sampled.select([
        "trackingnumber",
        "invoice_date",
        "zone",
        "weight_lbs",
        "base_charge",
        "performance_pricing",
        "final_base_charge"
    ])

    # Save to CSV
    output_path = Path(__file__).parent / "sample_shipments.csv"
    sampled.write_csv(output_path)
    print(f"\nSaved to: {output_path}")

    # Show summary
    print(f"\nZone/weight combinations: {sampled.select(['zone', 'weight_lbs']).unique().height}")
    print("\nSample rows:")
    print(sampled.head(20))


if __name__ == "__main__":
    main()
