"""
Plot discounts over time for the most popular weight+zone combination.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
from datetime import date
import polars as pl
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

INVOICE_PARQUET = Path(__file__).parent / "invoice_data.parquet"


def main():
    print("Loading invoice data...")
    invoice_df = pl.read_parquet(INVOICE_PARQUET)

    # Filter Q3+Q4 2025, Home Delivery, zones 2-8
    df = invoice_df.filter(
        (pl.col("invoice_date") >= date(2025, 7, 1)) &
        (pl.col("invoice_date") <= date(2025, 12, 31)) &
        (pl.col("service_type") == "Home Delivery") &
        (pl.col("shipping_zone").is_in(["2", "3", "4", "5", "6", "7", "8", "02", "03", "04", "05", "06", "07", "08"]))
    )

    # Find most popular weight+zone combination (from PP rows)
    pp_df = df.filter(pl.col("charge_description") == "Performance Pricing")

    popularity = pp_df.group_by([
        pl.col("shipping_zone").str.replace("^0", "").alias("zone"),
        pl.col("rated_weight").alias("weight")
    ]).agg(pl.len().alias("count")).sort("count", descending=True)

    print("\nTop 10 weight+zone combinations:")
    print(popularity.head(10))

    top_zone = popularity["zone"][0]
    top_weight = popularity["weight"][0]
    print(f"\nMost popular: Zone {top_zone}, Weight {top_weight}")

    # Filter to this combination
    target_df = df.filter(
        (pl.col("shipping_zone").str.replace("^0", "") == top_zone) &
        (pl.col("rated_weight") == top_weight)
    )

    # Get base charge (from PP rows - they have transportation_charge)
    base_data = target_df.filter(
        pl.col("charge_description") == "Performance Pricing"
    ).select([
        "trackingnumber",
        "invoice_date",
        pl.col("transportation_charge_usd").cast(pl.Float64).alias("base_charge")
    ])

    # Get PP
    pp_data = target_df.filter(
        pl.col("charge_description") == "Performance Pricing"
    ).select([
        "trackingnumber",
        pl.col("charge_description_amount").cast(pl.Float64).alias("pp_amount")
    ])

    # Get Grace
    grace_data = target_df.filter(
        pl.col("charge_description") == "Grace Discount"
    ).select([
        "trackingnumber",
        pl.col("charge_description_amount").cast(pl.Float64).alias("grace_amount")
    ])

    # Get Earned
    earned_data = target_df.filter(
        pl.col("charge_description") == "Earned Discount"
    ).select([
        "trackingnumber",
        pl.col("charge_description_amount").cast(pl.Float64).alias("earned_amount")
    ])

    # Join all
    combined = base_data.join(pp_data, on="trackingnumber", how="left")
    combined = combined.join(grace_data, on="trackingnumber", how="left")
    combined = combined.join(earned_data, on="trackingnumber", how="left")
    combined = combined.with_columns([
        pl.col("grace_amount").fill_null(0),
        pl.col("earned_amount").fill_null(0)
    ])

    # Calculate sum
    combined = combined.with_columns(
        (pl.col("base_charge") + pl.col("pp_amount") + pl.col("grace_amount") + pl.col("earned_amount"))
        .alias("total")
    )

    # Aggregate by date
    daily = combined.group_by("invoice_date").agg([
        pl.col("base_charge").mean().alias("base_charge"),
        pl.col("pp_amount").mean().alias("performance_pricing"),
        pl.col("grace_amount").mean().alias("grace_discount"),
        pl.col("earned_amount").mean().alias("earned_discount"),
        pl.col("total").mean().alias("total"),
        pl.len().alias("count")
    ]).sort("invoice_date")

    print(f"\nDaily data points: {len(daily)}")
    print(daily.head(10))

    # Convert to pandas for plotting
    daily_pd = daily.to_pandas()
    daily_pd['invoice_date'] = pd.to_datetime(daily_pd['invoice_date'])

    # Create plot
    fig, ax = plt.subplots(figsize=(14, 8))

    ax.plot(daily_pd['invoice_date'], daily_pd['base_charge'], label='Base Charge', linewidth=2, color='blue')
    ax.plot(daily_pd['invoice_date'], daily_pd['performance_pricing'], label='Performance Pricing', linewidth=2, color='orange')
    ax.plot(daily_pd['invoice_date'], daily_pd['grace_discount'], label='Grace Discount', linewidth=2, color='green')
    ax.plot(daily_pd['invoice_date'], daily_pd['earned_discount'], label='Earned Discount', linewidth=2, color='red')
    ax.plot(daily_pd['invoice_date'], daily_pd['total'], label='Total (Sum)', linewidth=2, color='purple', linestyle='--')

    ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.5)

    ax.set_xlabel('Invoice Date', fontsize=12)
    ax.set_ylabel('Amount ($)', fontsize=12)
    ax.set_title(f'FedEx Home Delivery Charges Over Time\nZone {top_zone}, Weight {top_weight} lbs', fontsize=14)
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    plt.xticks(rotation=45)

    plt.tight_layout()

    # Save plot
    output_path = Path(__file__).parent / "discounts_over_time.png"
    plt.savefig(output_path, dpi=150)
    print(f"\nSaved plot to: {output_path}")

    plt.show()


if __name__ == "__main__":
    import pandas as pd
    main()
