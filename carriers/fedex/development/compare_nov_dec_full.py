"""
Full comparison of November and December Home Delivery shipments.
Compare invoice data to PCS data with calculated costs.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
from datetime import date
import polars as pl

INVOICE_PARQUET = Path(__file__).parent / "invoice_data.parquet"
RATE_TABLES = Path(__file__).parent / "final_rate_tables"


def load_rate_tables():
    """Load rate tables and create lookup."""
    undiscounted = pl.read_csv(RATE_TABLES / "undiscounted_rates.csv")
    pp = pl.read_csv(RATE_TABLES / "performance_pricing.csv")

    # Convert to long format and join
    zones = ["zone_2", "zone_3", "zone_4", "zone_5", "zone_6", "zone_7", "zone_8"]

    undiscounted_long = undiscounted.unpivot(
        index="weight_lbs",
        variable_name="zone_col",
        value_name="undiscounted_rate"
    ).with_columns(
        pl.col("zone_col").str.replace("zone_", "").cast(pl.Int64).alias("zone")
    ).select(["weight_lbs", "zone", "undiscounted_rate"])

    pp_long = pp.unpivot(
        index="weight_lbs",
        variable_name="zone_col",
        value_name="pp_amount"
    ).with_columns(
        pl.col("zone_col").str.replace("zone_", "").cast(pl.Int64).alias("zone")
    ).select(["weight_lbs", "zone", "pp_amount"])

    rates = undiscounted_long.join(pp_long, on=["weight_lbs", "zone"], how="left")
    rates = rates.with_columns(
        (pl.col("undiscounted_rate") + pl.col("pp_amount")).round(2).alias("calculated_base")
    )

    return rates


def load_pcs_data():
    """Load PCS shipments for FedEx Home Delivery."""
    from shared.database import pull_data

    query = """
    WITH trackingnumbers AS (
        SELECT orderid, trackingnumber,
            ROW_NUMBER() OVER (PARTITION BY orderid ORDER BY id DESC) AS row_nr
        FROM bi_stage_dev_dbo.pcsu_sentparcels
    )
    SELECT
        tn.trackingnumber,
        (po.createddate + INTERVAL '2 days')::date AS ship_date,
        pp."name" AS production_site,
        po.shippingzipcode AS shipping_zip_code,
        ps.extkey AS pcs_shipping_provider,
        (po.packageweight * 2.20462262)::float8 AS weight_lbs
    FROM bi_stage_dev_dbo.pcsu_orders po
    JOIN bi_stage_dev_dbo.pcsu_productionsites pp ON pp.id = po.productionsiteid
    JOIN bi_stage_dev_dbo.pcsu_shippingproviders ps ON ps.id = po.shippingproviderid
    LEFT JOIN trackingnumbers tn ON tn.orderid = po.id AND tn.row_nr = 1
    WHERE ps.extkey = 'FXEHD'
      AND pp."name" IN ('Columbus', 'Phoenix')
      AND po.createddate >= '2025-10-01'
      AND po.createddate <= '2025-12-31'
      AND tn.trackingnumber IS NOT NULL
    """
    return pull_data(query)


def main():
    print("=" * 80)
    print("NOVEMBER & DECEMBER HOME DELIVERY COMPARISON")
    print("=" * 80)

    # Load invoice data
    print("\n1. Loading invoice data...")
    invoice_df = pl.read_parquet(INVOICE_PARQUET)

    # Filter Nov-Dec 2025, Home Delivery, zones 2-8, PP rows
    invoice_nov_dec = invoice_df.filter(
        (pl.col("invoice_date") >= date(2025, 11, 1)) &
        (pl.col("invoice_date") <= date(2025, 12, 31)) &
        (pl.col("service_type") == "Home Delivery") &
        (pl.col("shipping_zone").is_in(["2", "3", "4", "5", "6", "7", "8", "02", "03", "04", "05", "06", "07", "08"])) &
        (pl.col("charge_description") == "Performance Pricing")
    ).select([
        "trackingnumber",
        "invoice_date",
        pl.col("shipping_zone").str.replace("^0", "").cast(pl.Int64).alias("invoice_zone"),
        pl.col("rated_weight").cast(pl.Int64).alias("invoice_weight"),
        pl.col("transportation_charge_usd").cast(pl.Float64).alias("invoice_base_charge"),
        pl.col("charge_description_amount").cast(pl.Float64).alias("invoice_pp")
    ])

    # Calculate invoice total base (after discounts)
    invoice_nov_dec = invoice_nov_dec.with_columns(
        (pl.col("invoice_base_charge") + pl.col("invoice_pp")).round(2).alias("invoice_base_after_discount")
    )

    print(f"   Invoice shipments (Nov-Dec, Home Delivery): {len(invoice_nov_dec):,}")

    # Load PCS data
    print("\n2. Loading PCS data...")
    pcs_df = load_pcs_data()
    print(f"   PCS shipments (FXEHD, Oct-Dec): {len(pcs_df):,}")

    # Join invoice to PCS
    print("\n3. Joining invoice to PCS data...")
    joined = invoice_nov_dec.join(
        pcs_df,
        on="trackingnumber",
        how="left"
    )

    # Count join results
    matched = joined.filter(pl.col("ship_date").is_not_null())
    unmatched = joined.filter(pl.col("ship_date").is_null())

    print(f"\n" + "=" * 80)
    print("JOIN RESULTS")
    print("=" * 80)
    print(f"   Total invoice shipments: {len(invoice_nov_dec):,}")
    print(f"   Matched to PCS: {len(matched):,} ({len(matched)/len(invoice_nov_dec)*100:.1f}%)")
    print(f"   NOT matched to PCS: {len(unmatched):,} ({len(unmatched)/len(invoice_nov_dec)*100:.1f}%)")

    # Load rate tables
    print("\n4. Loading rate tables...")
    rates = load_rate_tables()

    # For matched shipments, calculate expected base using invoice weight/zone
    print("\n5. Calculating expected costs...")
    comparison = matched.join(
        rates,
        left_on=["invoice_weight", "invoice_zone"],
        right_on=["weight_lbs", "zone"],
        how="left"
    )

    # Check for missing rates
    missing_rates = comparison.filter(pl.col("calculated_base").is_null())
    valid = comparison.filter(pl.col("calculated_base").is_not_null())

    print(f"   Shipments with rate lookup: {len(valid):,}")
    print(f"   Shipments missing rate: {len(missing_rates):,}")

    # Compare totals
    print(f"\n" + "=" * 80)
    print("COMPARISON RESULTS (Matched Shipments)")
    print("=" * 80)

    invoice_total = valid["invoice_base_after_discount"].sum()
    calculated_total = valid["calculated_base"].sum()
    difference = calculated_total - invoice_total
    diff_pct = (difference / invoice_total) * 100

    print(f"\n   Shipments compared: {len(valid):,}")
    print(f"\n   Invoice base after discount:    ${invoice_total:,.2f}")
    print(f"   Calculated base (our tables):   ${calculated_total:,.2f}")
    print(f"   Difference:                     ${difference:,.2f} ({diff_pct:+.2f}%)")

    # Show per-shipment accuracy
    valid = valid.with_columns(
        (pl.col("calculated_base") - pl.col("invoice_base_after_discount")).alias("diff")
    )

    exact_matches = valid.filter(pl.col("diff").abs() < 0.02)
    print(f"\n   Exact matches (<$0.02 diff): {len(exact_matches):,} / {len(valid):,} ({len(exact_matches)/len(valid)*100:.1f}%)")

    # Show sample of mismatches if any
    mismatches = valid.filter(pl.col("diff").abs() >= 0.02)
    if len(mismatches) > 0:
        print(f"\n   Sample mismatches:")
        print(mismatches.select([
            "trackingnumber", "invoice_zone", "invoice_weight",
            "invoice_base_after_discount", "calculated_base", "diff"
        ]).head(10))


if __name__ == "__main__":
    main()
