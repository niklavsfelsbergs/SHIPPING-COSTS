"""
Compare Calculated Base Rates to Invoice Data (using parquet)

Usage:
    python -m carriers.fedex.development.compare_base_rates_v2
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
import polars as pl
from shared.database import pull_data
from carriers.fedex.calculate_costs import calculate_costs

INVOICE_PARQUET = Path(__file__).parent / "invoice_data.parquet"


def load_pcs_shipments(limit: int = 1000) -> pl.DataFrame:
    """Load PCS shipments for FXEHD only."""
    query = f"""
    WITH trackingnumbers AS (
        SELECT orderid, trackingnumber,
            ROW_NUMBER() OVER (PARTITION BY orderid ORDER BY id DESC) AS row_nr
        FROM bi_stage_dev_dbo.pcsu_sentparcels
    )
    SELECT
        tn.trackingnumber AS latest_trackingnumber,
        (po.createddate + INTERVAL '2 days')::date AS ship_date,
        pp."name" AS production_site,
        po.shippingzipcode AS shipping_zip_code,
        po.shippingregion AS shipping_region,
        ps.extkey AS pcs_shipping_provider,
        (GREATEST(po.packagelength, po.packagewidth) / 10.0 * 0.39370079)::float8 AS length_in,
        (LEAST(po.packagelength, po.packagewidth) / 10.0 * 0.39370079)::float8 AS width_in,
        (po.packageheight / 10.0 * 0.39370079)::float8 AS height_in,
        (po.packageweight * 2.20462262)::float8 AS weight_lbs
    FROM bi_stage_dev_dbo.pcsu_orders po
    JOIN bi_stage_dev_dbo.pcsu_productionsites pp ON pp.id = po.productionsiteid
    JOIN bi_stage_dev_dbo.pcsu_shippingproviders ps ON ps.id = po.shippingproviderid
    LEFT JOIN trackingnumbers tn ON tn.orderid = po.id AND tn.row_nr = 1
    WHERE ps.extkey = 'FXEHD'
      AND pp."name" IN ('Columbus', 'Phoenix')
      AND po.createddate >= '2025-01-01'
      AND tn.trackingnumber IS NOT NULL
    LIMIT {limit}
    """
    return pull_data(query)


def main():
    print("Loading invoice data from parquet...")
    invoice_df = pl.read_parquet(INVOICE_PARQUET)
    print(f"  Loaded {len(invoice_df):,} invoice rows")

    # Filter for Performance Pricing rows and Home Delivery
    pp_df = invoice_df.filter(
        (pl.col("charge_description") == "Performance Pricing") &
        (pl.col("service_type") == "Home Delivery")
    )
    print(f"  Performance Pricing rows (Home Delivery): {len(pp_df):,}")

    # Calculate invoice base rate: transportation_charge_usd + charge_description_amount
    # (charge_description_amount is negative for Performance Pricing, so this gives net rate)
    pp_df = pp_df.with_columns(
        (pl.col("transportation_charge_usd").cast(pl.Float64) + pl.col("charge_description_amount").cast(pl.Float64))
        .alias("invoice_base_rate")
    )

    # Select relevant columns for joining
    invoice_for_join = pp_df.select([
        "trackingnumber",
        "shipping_zone",
        "rated_weight",
        "transportation_charge_usd",
        "charge_description_amount",
        "invoice_base_rate",
    ]).rename({
        "shipping_zone": "invoice_zone",
        "rated_weight": "invoice_rated_weight",
        "charge_description_amount": "performance_pricing",
    })

    print("\nLoading PCS shipments...")
    pcs_df = load_pcs_shipments(limit=1000)
    print(f"  Loaded {len(pcs_df)} PCS shipments")

    print("\nCalculating expected costs...")
    calculated_df = calculate_costs(pcs_df)

    print("\nJoining...")
    comparison_df = calculated_df.join(
        invoice_for_join,
        left_on="latest_trackingnumber",
        right_on="trackingnumber",
        how="inner"
    )
    print(f"  Matched {len(comparison_df)} shipments")

    # Calculate variance
    comparison_df = comparison_df.with_columns(
        (pl.col("cost_base_list") - pl.col("invoice_base_rate")).alias("base_variance")
    )

    # Summary
    print("\n" + "=" * 70)
    print("COMPARISON SUMMARY")
    print("=" * 70)

    print(f"\nTotal matched: {len(comparison_df)}")
    print(f"\nOur cost_base_list total:       ${comparison_df['cost_base_list'].sum():,.2f}")
    print(f"Invoice transportation total:   ${comparison_df['transportation_charge_usd'].cast(pl.Float64).sum():,.2f}")
    print(f"Performance Pricing total:      ${comparison_df['performance_pricing'].cast(pl.Float64).sum():,.2f}")
    print(f"Invoice base rate total:        ${comparison_df['invoice_base_rate'].sum():,.2f}")

    variance = comparison_df['cost_base_list'].sum() - comparison_df['invoice_base_rate'].sum()
    variance_pct = variance / comparison_df['invoice_base_rate'].sum() * 100
    print(f"\nVariance: ${variance:,.2f} ({variance_pct:+.2f}%)")

    print("\nSample rows:")
    print(comparison_df.select([
        "shipping_zone",
        "invoice_zone",
        "billable_weight_lbs",
        "invoice_rated_weight",
        "cost_base_list",
        "transportation_charge_usd",
        "performance_pricing",
        "invoice_base_rate",
        "base_variance",
    ]).head(20))


if __name__ == "__main__":
    main()
