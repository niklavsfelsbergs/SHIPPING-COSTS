"""
Verify rate tables against November and December invoice data.

Expected: Undiscounted + PP + Earned (0) + Grace (0) = Invoice Base + PP + Earned + Grace
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
from datetime import date
import polars as pl

INVOICE_PARQUET = Path(__file__).parent / "invoice_data.parquet"
RATE_TABLES = Path(__file__).parent / "final_rate_tables"


def main():
    print("Loading rate tables...")
    undiscounted = pl.read_csv(RATE_TABLES / "undiscounted_rates.csv")
    pp_table = pl.read_csv(RATE_TABLES / "performance_pricing.csv")

    # Convert to long format for lookup
    undiscounted_long = undiscounted.unpivot(
        index="weight_lbs",
        variable_name="zone_col",
        value_name="undiscounted_rate"
    ).with_columns(
        pl.col("zone_col").str.replace("zone_", "").cast(pl.Int64).alias("zone")
    ).select(["weight_lbs", "zone", "undiscounted_rate"])

    pp_long = pp_table.unpivot(
        index="weight_lbs",
        variable_name="zone_col",
        value_name="pp_rate"
    ).with_columns(
        pl.col("zone_col").str.replace("zone_", "").cast(pl.Int64).alias("zone")
    ).select(["weight_lbs", "zone", "pp_rate"])

    # Our expected rate = undiscounted + pp (earned=0, grace=0)
    our_rates = undiscounted_long.join(pp_long, on=["weight_lbs", "zone"], how="left")
    our_rates = our_rates.with_columns(
        (pl.col("undiscounted_rate") + pl.col("pp_rate").fill_null(0)).alias("our_total")
    )

    print("Loading invoice data...")
    invoice_df = pl.read_parquet(INVOICE_PARQUET)

    # Filter November and December 2025, Home Delivery, zones 2-8
    print("Filtering November and December 2025...")
    df = invoice_df.filter(
        (pl.col("invoice_date") >= date(2025, 11, 1)) &
        (pl.col("invoice_date") <= date(2025, 12, 31)) &
        (pl.col("service_type") == "Home Delivery") &
        (pl.col("shipping_zone").is_in(["2", "3", "4", "5", "6", "7", "8", "02", "03", "04", "05", "06", "07", "08"]))
    )

    # Get base charge from PP rows
    pp_data = df.filter(
        pl.col("charge_description") == "Performance Pricing"
    ).select([
        "trackingnumber",
        "invoice_date",
        pl.col("shipping_zone").str.replace("^0", "").cast(pl.Int64).alias("zone"),
        pl.col("rated_weight").cast(pl.Int64).alias("weight_lbs"),
        pl.col("transportation_charge_usd").cast(pl.Float64).alias("invoice_base"),
        pl.col("charge_description_amount").cast(pl.Float64).alias("invoice_pp")
    ])

    # Get Grace and Earned
    grace_data = df.filter(
        pl.col("charge_description") == "Grace Discount"
    ).select([
        "trackingnumber",
        pl.col("charge_description_amount").cast(pl.Float64).alias("invoice_grace")
    ])

    earned_data = df.filter(
        pl.col("charge_description") == "Earned Discount"
    ).select([
        "trackingnumber",
        pl.col("charge_description_amount").cast(pl.Float64).alias("invoice_earned")
    ])

    # Join all invoice data
    invoice_combined = pp_data.join(grace_data, on="trackingnumber", how="left")
    invoice_combined = invoice_combined.join(earned_data, on="trackingnumber", how="left")
    invoice_combined = invoice_combined.with_columns([
        pl.col("invoice_grace").fill_null(0),
        pl.col("invoice_earned").fill_null(0)
    ])

    # Calculate invoice total
    invoice_combined = invoice_combined.with_columns(
        (pl.col("invoice_base") + pl.col("invoice_pp") + pl.col("invoice_grace") + pl.col("invoice_earned"))
        .round(2).alias("invoice_total")
    )

    print(f"\nNov-Dec shipments: {len(invoice_combined):,}")

    # Check how many have Grace or Earned discounts
    with_grace = invoice_combined.filter(pl.col("invoice_grace") != 0)
    with_earned = invoice_combined.filter(pl.col("invoice_earned") != 0)
    print(f"  With Grace Discount: {len(with_grace):,} ({len(with_grace)/len(invoice_combined)*100:.1f}%)")
    print(f"  With Earned Discount: {len(with_earned):,} ({len(with_earned)/len(invoice_combined)*100:.1f}%)")

    # Join with our rates
    comparison = invoice_combined.join(
        our_rates,
        on=["weight_lbs", "zone"],
        how="left"
    )

    # Calculate difference
    comparison = comparison.with_columns(
        (pl.col("our_total") - pl.col("invoice_total")).round(2).alias("diff")
    )

    # Filter to those where we have PP rate
    valid = comparison.filter(pl.col("pp_rate").is_not_null())
    print(f"\nShipments with matching weight/zone in our tables: {len(valid):,}")

    # Check match rate
    matches = valid.filter(pl.col("diff").abs() < 0.02)
    print(f"\n" + "=" * 80)
    print("VERIFICATION RESULTS")
    print("=" * 80)
    print(f"\nOur rate (undiscounted + PP) vs Invoice (base + PP + grace + earned):")
    print(f"  Matches: {len(matches):,} / {len(valid):,} ({len(matches)/len(valid)*100:.1f}%)")

    # Also check against just base + PP (ignoring grace/earned)
    comparison = comparison.with_columns(
        (pl.col("invoice_base") + pl.col("invoice_pp")).round(2).alias("invoice_base_pp_only")
    )
    comparison = comparison.with_columns(
        (pl.col("our_total") - pl.col("invoice_base_pp_only")).round(2).alias("diff_base_pp")
    )

    matches_base_pp = valid.filter(
        (pl.col("our_total") - (pl.col("invoice_base") + pl.col("invoice_pp"))).abs() < 0.02
    )
    print(f"\nOur rate vs Invoice (base + PP only, ignoring grace/earned):")
    print(f"  Matches: {len(matches_base_pp):,} / {len(valid):,} ({len(matches_base_pp)/len(valid)*100:.1f}%)")

    # Show sample mismatches
    mismatches = valid.filter(pl.col("diff").abs() >= 0.02)
    if len(mismatches) > 0:
        print(f"\nSample mismatches:")
        print(mismatches.select([
            "zone", "weight_lbs", "invoice_base", "invoice_pp", "invoice_grace", "invoice_earned",
            "invoice_total", "our_total", "diff"
        ]).head(20))


if __name__ == "__main__":
    main()
