"""
Show SmartPost Base Charge examples that don't match undiscounted_rates.csv
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
import polars as pl
from shared.database import pull_data

RATE_TABLES = Path(__file__).parent / "final_rate_tables"


def main():
    # Load undiscounted rates
    undiscounted = pl.read_csv(RATE_TABLES / "undiscounted_rates.csv")
    undiscounted_long = undiscounted.unpivot(
        index="weight_lbs",
        variable_name="zone_col",
        value_name="undiscounted_rate"
    ).with_columns(
        pl.col("zone_col").str.replace("zone_", "").cast(pl.Int64).alias("zone")
    ).select(["weight_lbs", "zone", "undiscounted_rate"])

    # Pull SmartPost Nov-Dec data
    query = """
    SELECT DISTINCT
        CASE
            WHEN f.express_or_ground_tracking_id LIKE '%.%'
            THEN f.express_or_ground_tracking_id::numeric::text
            ELSE f.express_or_ground_tracking_id::text
        END AS trackingnumber,
        f.zone_code AS shipping_zone,
        REPLACE(f.rated_weight_amount, ',', '')::float8 AS rated_weight,
        REPLACE(f.transportation_charge_amount, ',', '')::float8 AS base_charge
    FROM bi_stage_dev_dbo.fedex_invoicedata_historical f
    WHERE f.invoice_date::date >= '2025-11-01'
      AND f.invoice_date::date <= '2025-12-31'
      AND f.service_type = 'SmartPost'
      AND f.zone_code IN ('2', '3', '4', '5', '6', '7', '8', '02', '03', '04', '05', '06', '07', '08')
    """
    df = pull_data(query)

    # Prepare for join
    df = df.with_columns([
        pl.col("rated_weight").cast(pl.Int64).alias("weight"),
        pl.col("shipping_zone").str.replace("^0", "").cast(pl.Int64).alias("zone")
    ])

    # Join with undiscounted rates
    comparison = df.join(
        undiscounted_long,
        left_on=["weight", "zone"],
        right_on=["weight_lbs", "zone"],
        how="left"
    ).with_columns(
        (pl.col("base_charge") - pl.col("undiscounted_rate")).round(2).alias("diff")
    )

    # Show mismatches
    mismatches = comparison.filter(pl.col("diff").abs() >= 0.02)

    print("=" * 80)
    print("SMARTPOST BASE CHARGE vs UNDISCOUNTED RATES - MISMATCHES")
    print("=" * 80)
    print(f"\nTotal shipments: {len(df):,}")
    print(f"Mismatches: {len(mismatches):,}")

    print("\n" + "=" * 80)
    print("SAMPLE MISMATCHES (20 examples)")
    print("=" * 80)
    print(mismatches.select([
        "trackingnumber", "zone", "weight", "base_charge", "undiscounted_rate", "diff"
    ]).sort(["zone", "weight"]).head(20))


if __name__ == "__main__":
    main()
