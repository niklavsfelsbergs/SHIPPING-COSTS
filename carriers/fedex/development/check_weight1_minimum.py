"""Check if weight 1 has a minimum rate."""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
from datetime import date
import polars as pl

INVOICE_PARQUET = Path(__file__).parent / "invoice_data.parquet"
UNDISCOUNTED_RATES = Path(__file__).parent.parent / "temp_files" / "fedex_ground_rates_2025_undiscounted.csv"


def main():
    # Load data
    print("Loading invoice data...")
    invoice_df = pl.read_parquet(INVOICE_PARQUET)

    # Get transportation charges for weight 1 shipments
    df = invoice_df.filter(
        (pl.col("invoice_date") >= date(2025, 7, 1)) &
        (pl.col("invoice_date") <= date(2025, 12, 31)) &
        (pl.col("service_type") == "Home Delivery") &
        (pl.col("rated_weight") == "1")
    )

    # Get base charge rows (not PP rows)
    base_df = df.filter(pl.col("charge_description").is_null())

    # Get PP rows
    pp_df = df.filter(pl.col("charge_description") == "Performance Pricing")

    print(f"\nWeight 1 shipments: {len(df):,}")
    print(f"Base charge rows: {len(base_df):,}")
    print(f"PP rows: {len(pp_df):,}")

    # Calculate net rate (transportation - PP) for weight 1 by zone
    # Join base and PP on tracking number
    net_rates = base_df.select([
        "trackingnumber",
        "shipping_zone",
        pl.col("transportation_charge_usd").cast(pl.Float64).alias("transportation")
    ]).join(
        pp_df.select([
            "trackingnumber",
            pl.col("charge_description_amount").cast(pl.Float64).alias("pp")
        ]),
        on="trackingnumber",
        how="inner"
    ).with_columns(
        (pl.col("transportation") + pl.col("pp")).alias("net_rate")  # PP is negative
    )

    print("\n" + "=" * 80)
    print("WEIGHT 1 NET RATES BY ZONE (Q3+Q4 2025)")
    print("=" * 80)

    by_zone = net_rates.group_by("shipping_zone").agg([
        pl.col("net_rate").mean().round(2).alias("avg_net"),
        pl.col("net_rate").mode().first().alias("mode_net"),
        pl.col("transportation").mode().first().alias("mode_transport"),
        pl.col("pp").mode().first().alias("mode_pp"),
        pl.len().alias("count")
    ]).sort("shipping_zone")

    print(by_zone)

    # Load undiscounted rates for comparison
    undiscounted = pl.read_csv(UNDISCOUNTED_RATES)
    weight1_undiscounted = undiscounted.filter(pl.col("Weight_lbs") == 1)
    print("\nUndiscounted weight 1 rates:")
    print(weight1_undiscounted)

    # Check if net rate matches $8.07 minimum
    print("\n" + "=" * 80)
    print("CHECKING MINIMUM RATE PATTERN")
    print("=" * 80)

    for zone in [2, 3, 4, 5, 6, 7, 8]:
        zone_data = net_rates.filter(pl.col("shipping_zone") == str(zone))
        if len(zone_data) > 0:
            avg_net = zone_data["net_rate"].mean()
            mode_net = zone_data["net_rate"].mode()[0]
            undiscounted_col = f"Zone{zone}"
            undiscounted_val = undiscounted.filter(pl.col("Weight_lbs") == 1)[undiscounted_col][0]
            discount_pct = ((undiscounted_val - mode_net) / undiscounted_val * 100)
            print(f"Zone {zone}: undiscounted=${undiscounted_val:.2f}, net=${mode_net:.2f}, discount={discount_pct:.1f}%")


if __name__ == "__main__":
    main()
