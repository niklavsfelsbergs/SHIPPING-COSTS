"""Check raw invoice data for weight 1."""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
from datetime import date
import polars as pl

INVOICE_PARQUET = Path(__file__).parent / "invoice_data.parquet"


def main():
    print("Loading invoice data...")
    invoice_df = pl.read_parquet(INVOICE_PARQUET)

    # Get weight 1 shipments
    df = invoice_df.filter(
        (pl.col("invoice_date") >= date(2025, 7, 1)) &
        (pl.col("invoice_date") <= date(2025, 12, 31)) &
        (pl.col("service_type") == "Home Delivery") &
        (pl.col("rated_weight") == "1")
    )

    print(f"\nWeight 1 rows: {len(df):,}")
    print(f"\nColumns: {df.columns}")

    # Show sample rows
    print("\nSample rows:")
    print(df.select([
        "trackingnumber",
        "shipping_zone",
        "rated_weight",
        "transportation_charge_usd",
        "charge_description",
        "charge_description_amount"
    ]).head(20))

    # Summary by charge_description
    print("\n" + "=" * 80)
    print("CHARGE DESCRIPTIONS FOR WEIGHT 1")
    print("=" * 80)
    print(df.group_by("charge_description").agg([
        pl.len().alias("count"),
        pl.col("charge_description_amount").cast(pl.Float64).mean().round(2).alias("avg_amount")
    ]).sort("count", descending=True))

    # Get PP rows by zone
    pp_df = df.filter(pl.col("charge_description") == "Performance Pricing")
    print("\n" + "=" * 80)
    print("PERFORMANCE PRICING BY ZONE FOR WEIGHT 1")
    print("=" * 80)

    print(pp_df.group_by("shipping_zone").agg([
        pl.col("transportation_charge_usd").cast(pl.Float64).mode().first().alias("mode_transport"),
        pl.col("charge_description_amount").cast(pl.Float64).mode().first().alias("mode_pp"),
        pl.len().alias("count")
    ]).sort("shipping_zone"))

    # Calculate net rate from PP rows (they have transportation_charge too)
    print("\n" + "=" * 80)
    print("NET RATES (TRANSPORT + PP) BY ZONE FOR WEIGHT 1")
    print("=" * 80)

    pp_df = pp_df.with_columns([
        pl.col("transportation_charge_usd").cast(pl.Float64),
        pl.col("charge_description_amount").cast(pl.Float64).alias("pp_amount")
    ]).with_columns(
        (pl.col("transportation_charge_usd") + pl.col("pp_amount")).round(2).alias("net_rate")
    )

    print(pp_df.group_by("shipping_zone").agg([
        pl.col("net_rate").mode().first().alias("mode_net_rate"),
        pl.col("transportation_charge_usd").mode().first().alias("mode_transport"),
        pl.col("pp_amount").mode().first().alias("mode_pp"),
        pl.len().alias("count")
    ]).sort("shipping_zone"))

    # Compare with undiscounted rates
    print("\n" + "=" * 80)
    print("UNDISCOUNTED RATES FOR WEIGHT 1")
    print("=" * 80)
    undiscounted = pl.read_csv(Path(__file__).parent.parent / "temp_files" / "fedex_ground_rates_2025_undiscounted.csv")
    print(undiscounted.filter(pl.col("Weight_lbs") == 1))


if __name__ == "__main__":
    main()
