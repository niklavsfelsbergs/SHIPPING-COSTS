"""
Analyze SmartPost rates:
1. Verify undiscounted rates match invoice Base Charge
2. Analyze Performance Pricing consistency
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
from datetime import date
import polars as pl
from shared.database import pull_data

RATE_TABLES = Path(__file__).parent / "final_rate_tables"


def main():
    print("=" * 80)
    print("SMARTPOST RATE ANALYSIS")
    print("=" * 80)

    # Load SmartPost invoice data for Nov-Dec
    print("\n1. Loading SmartPost invoice data (Nov-Dec 2025)...")
    invoice_query = """
    WITH charge_positions AS (
        SELECT 0 AS n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
        UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
    )
    SELECT
        CASE
            WHEN f.express_or_ground_tracking_id LIKE '%.%'
            THEN f.express_or_ground_tracking_id::numeric::text
            ELSE f.express_or_ground_tracking_id::text
        END AS trackingnumber,
        f.crossreftrackingid_prefix || f.crossreftrackingid AS pcs_trackingnumber,
        f.invoice_date::date AS invoice_date,
        f.zone_code AS shipping_zone,
        REPLACE(f.rated_weight_amount, ',', '')::float8 AS rated_weight,
        REPLACE(f.transportation_charge_amount, ',', '')::float8 AS base_charge,
        CASE p.n
            WHEN 0 THEN f.tracking_id_charge_description
            WHEN 1 THEN f.tracking_id_charge_description_1
            WHEN 2 THEN f.tracking_id_charge_description_2
            WHEN 3 THEN f.tracking_id_charge_description_3
            WHEN 4 THEN f.tracking_id_charge_description_4
            WHEN 5 THEN f.tracking_id_charge_description_5
            WHEN 6 THEN f.tracking_id_charge_description_6
            WHEN 7 THEN f.tracking_id_charge_description_7
            WHEN 8 THEN f.tracking_id_charge_description_8
            WHEN 9 THEN f.tracking_id_charge_description_9
        END AS charge_description,
        REPLACE(CASE p.n
            WHEN 0 THEN f.tracking_id_charge_amount
            WHEN 1 THEN f.tracking_id_charge_amount_1
            WHEN 2 THEN f.tracking_id_charge_amount_2
            WHEN 3 THEN f.tracking_id_charge_amount_3
            WHEN 4 THEN f.tracking_id_charge_amount_4
            WHEN 5 THEN f.tracking_id_charge_amount_5
            WHEN 6 THEN f.tracking_id_charge_amount_6
            WHEN 7 THEN f.tracking_id_charge_amount_7
            WHEN 8 THEN f.tracking_id_charge_amount_8
            WHEN 9 THEN f.tracking_id_charge_amount_9
        END, ',', '')::float8 AS charge_amount
    FROM bi_stage_dev_dbo.fedex_invoicedata_historical f
    CROSS JOIN charge_positions p
    WHERE f.invoice_date::date >= '2025-11-01'
      AND f.invoice_date::date <= '2025-12-31'
      AND f.service_type = 'SmartPost'
      AND f.zone_code IN ('2', '3', '4', '5', '6', '7', '8', '02', '03', '04', '05', '06', '07', '08')
    """
    invoice_df = pull_data(invoice_query)
    print(f"   Loaded {len(invoice_df):,} rows")

    # Filter to Performance Pricing rows
    pp_df = invoice_df.filter(pl.col("charge_description") == "Performance Pricing")
    print(f"   Performance Pricing rows: {len(pp_df):,}")

    # Check Grace and Earned Discount presence
    grace_df = invoice_df.filter(pl.col("charge_description") == "Grace Discount")
    earned_df = invoice_df.filter(pl.col("charge_description") == "Earned Discount")
    print(f"   Grace Discount rows: {len(grace_df):,}")
    print(f"   Earned Discount rows: {len(earned_df):,}")

    # =========================================================================
    # VERIFY UNDISCOUNTED RATES
    # =========================================================================
    print("\n" + "=" * 80)
    print("2. VERIFYING UNDISCOUNTED RATES (Base Charge)")
    print("=" * 80)

    # Load our undiscounted rates
    undiscounted = pl.read_csv(RATE_TABLES / "undiscounted_rates.csv")
    undiscounted_long = undiscounted.unpivot(
        index="weight_lbs",
        variable_name="zone_col",
        value_name="our_undiscounted"
    ).with_columns(
        pl.col("zone_col").str.replace("zone_", "").cast(pl.Int64).alias("zone")
    ).select(["weight_lbs", "zone", "our_undiscounted"])

    # Get unique base_charge by weight/zone from invoice
    invoice_base = pp_df.with_columns([
        pl.col("rated_weight").cast(pl.Int64).alias("weight"),
        pl.col("shipping_zone").str.replace("^0", "").cast(pl.Int64).alias("zone")
    ]).group_by(["weight", "zone"]).agg([
        pl.col("base_charge").mode().first().alias("invoice_base"),
        pl.len().alias("count")
    ])

    # Join and compare
    base_comparison = invoice_base.join(
        undiscounted_long,
        left_on=["weight", "zone"],
        right_on=["weight_lbs", "zone"],
        how="left"
    ).with_columns(
        (pl.col("invoice_base") - pl.col("our_undiscounted")).round(2).alias("diff")
    )

    matches = base_comparison.filter(pl.col("diff").abs() < 0.02)
    mismatches = base_comparison.filter(pl.col("diff").abs() >= 0.02)

    print(f"\n   Weight/zone combinations: {len(base_comparison)}")
    print(f"   Matches (<$0.02 diff): {len(matches)} ({len(matches)/len(base_comparison)*100:.1f}%)")
    print(f"   Mismatches: {len(mismatches)}")

    if len(mismatches) > 0:
        print("\n   Sample mismatches:")
        print(mismatches.sort(["zone", "weight"]).head(20))

    # =========================================================================
    # ANALYZE PERFORMANCE PRICING CONSISTENCY
    # =========================================================================
    print("\n" + "=" * 80)
    print("3. ANALYZING PERFORMANCE PRICING CONSISTENCY")
    print("=" * 80)

    # Get PP values by weight/zone
    pp_by_wz = pp_df.with_columns([
        pl.col("rated_weight").cast(pl.Int64).alias("weight"),
        pl.col("shipping_zone").str.replace("^0", "").cast(pl.Int64).alias("zone")
    ]).group_by(["weight", "zone"]).agg([
        pl.col("charge_amount").mean().round(2).alias("avg_pp"),
        pl.col("charge_amount").std().round(4).alias("std_pp"),
        pl.col("charge_amount").min().alias("min_pp"),
        pl.col("charge_amount").max().alias("max_pp"),
        pl.col("charge_amount").mode().first().alias("mode_pp"),
        pl.len().alias("count")
    ])

    # Check consistency (std should be ~0 or very small)
    consistent = pp_by_wz.filter(pl.col("std_pp").is_null() | (pl.col("std_pp") < 0.02))
    inconsistent = pp_by_wz.filter(pl.col("std_pp") >= 0.02)

    print(f"\n   Weight/zone combinations with PP data: {len(pp_by_wz)}")
    print(f"   Consistent (std < $0.02): {len(consistent)} ({len(consistent)/len(pp_by_wz)*100:.1f}%)")
    print(f"   Inconsistent: {len(inconsistent)}")

    if len(inconsistent) > 0:
        print("\n   Inconsistent combinations:")
        print(inconsistent.sort(["zone", "weight"]))

    # =========================================================================
    # CREATE PERFORMANCE PRICING TABLE
    # =========================================================================
    print("\n" + "=" * 80)
    print("4. CREATING SMARTPOST PERFORMANCE PRICING TABLE")
    print("=" * 80)

    # Use mode PP values
    pp_table_data = pp_by_wz.select(["weight", "zone", "mode_pp"])

    # Pivot to wide format
    pp_wide = pp_table_data.pivot(
        index="weight",
        on="zone",
        values="mode_pp"
    ).sort("weight").rename({"weight": "weight_lbs"})

    # Rename columns
    for col in pp_wide.columns:
        if col != "weight_lbs" and col.isdigit():
            pp_wide = pp_wide.rename({col: f"zone_{col}"})

    print(f"\n   PP table shape: {pp_wide.shape}")
    print("\n   First 30 rows:")
    print(pp_wide.head(30))

    # Save PP table
    pp_output = RATE_TABLES / "smartpost_performance_pricing.csv"
    pp_wide.write_csv(pp_output)
    print(f"\n   Saved to: {pp_output}")

    # =========================================================================
    # CREATE ZERO TABLES FOR GRACE AND EARNED
    # =========================================================================
    print("\n" + "=" * 80)
    print("5. CREATING ZERO TABLES FOR GRACE AND EARNED DISCOUNT")
    print("=" * 80)

    # Get the weights present in PP data
    weights = sorted(pp_wide["weight_lbs"].to_list())
    zones = ["zone_2", "zone_3", "zone_4", "zone_5", "zone_6", "zone_7", "zone_8"]

    zero_data = [{"weight_lbs": w, **{z: 0 for z in zones}} for w in weights]
    zero_df = pl.DataFrame(zero_data)

    # Save
    zero_df.write_csv(RATE_TABLES / "smartpost_earned_discount.csv")
    zero_df.write_csv(RATE_TABLES / "smartpost_grace_discount.csv")
    print(f"   Created smartpost_earned_discount.csv ({len(zero_df)} rows)")
    print(f"   Created smartpost_grace_discount.csv ({len(zero_df)} rows)")


if __name__ == "__main__":
    main()
