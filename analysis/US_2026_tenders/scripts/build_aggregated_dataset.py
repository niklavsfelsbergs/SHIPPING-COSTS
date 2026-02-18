"""
Build aggregated dataset grouped by (packagetype, shipping_zip_code, weight_bracket).

Creates totals and averages for optimization calculations.
"""

import polars as pl
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
COMBINED_DATASETS = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "combined_datasets"


def main():
    # Load unified dataset
    input_path = COMBINED_DATASETS / "shipments_unified.parquet"
    print(f"Loading: {input_path}")
    df = pl.read_parquet(input_path)
    print(f"  {df.shape[0]:,} rows loaded")

    # Add weight bracket (1 lb increments, ceiling)
    print("\nAdding weight bracket...")
    df = df.with_columns(
        pl.col("weight_lbs").ceil().cast(pl.Int32).alias("weight_bracket")
    )

    # Group by dimensions
    group_cols = ["packagetype", "shipping_zip_code", "weight_bracket"]

    print(f"Aggregating by: {group_cols}")

    # Define aggregations
    agg_exprs = [
        pl.len().alias("shipment_count"),

        # Current carrier costs
        pl.col("cost_current_carrier").sum().alias("cost_current_carrier_total"),
        pl.col("cost_current_carrier").mean().alias("cost_current_carrier_avg"),

        # OnTrac
        pl.col("ontrac_cost_total").sum().alias("ontrac_cost_total"),
        pl.col("ontrac_cost_total").mean().alias("ontrac_cost_avg"),

        # USPS
        pl.col("usps_cost_total").sum().alias("usps_cost_total"),
        pl.col("usps_cost_total").mean().alias("usps_cost_avg"),

        # FedEx (best of HD vs SP)
        pl.col("fedex_cost_total").sum().alias("fedex_cost_total"),
        pl.col("fedex_cost_total").mean().alias("fedex_cost_avg"),

        # FedEx HD vs SP breakdown
        pl.col("fedex_hd_cost_total").sum().alias("fedex_hd_cost_total"),
        pl.col("fedex_hd_cost_total").mean().alias("fedex_hd_cost_avg"),
        pl.col("fedex_sp_cost_total").sum().alias("fedex_sp_cost_total"),
        pl.col("fedex_sp_cost_total").mean().alias("fedex_sp_cost_avg"),
        (pl.col("fedex_service_selected") == "FXSP").sum().alias("fedex_sp_shipment_count"),
        (pl.col("fedex_service_selected") == "FXEHD").sum().alias("fedex_hd_shipment_count"),

        # P2P
        pl.col("p2p_cost_total").sum().alias("p2p_cost_total"),
        pl.col("p2p_cost_total").mean().alias("p2p_cost_avg"),

        # P2P US2 (best of PFA/PFS per group)
        pl.col("p2p_us2_cost_total").sum().alias("p2p_us2_cost_total"),
        pl.col("p2p_us2_cost_total").mean().alias("p2p_us2_cost_avg"),
        pl.col("p2p_us2_pfa_cost_total").sum().alias("p2p_us2_pfa_cost_total"),
        pl.col("p2p_us2_pfa_cost_total").mean().alias("p2p_us2_pfa_cost_avg"),
        pl.col("p2p_us2_pfs_cost_total").sum().alias("p2p_us2_pfs_cost_total"),
        pl.col("p2p_us2_pfs_cost_total").mean().alias("p2p_us2_pfs_cost_avg"),
        (pl.col("p2p_us2_service_selected") == "PFA").sum().alias("p2p_us2_pfa_shipment_count"),
        (pl.col("p2p_us2_service_selected") == "PFS").sum().alias("p2p_us2_pfs_shipment_count"),

        # Maersk
        pl.col("maersk_cost_total").sum().alias("maersk_cost_total"),
        pl.col("maersk_cost_total").mean().alias("maersk_cost_avg"),
    ]

    # Perform aggregation
    df_agg = df.group_by(group_cols).agg(agg_exprs).sort(group_cols)

    # Add cheapest carrier column (among current carriers: OnTrac, USPS, FedEx)
    df_agg = df_agg.with_columns(
        pl.min_horizontal("ontrac_cost_avg", "usps_cost_avg", "fedex_cost_avg").alias("cheapest_current_cost_avg"),
    )

    # Determine which carrier is cheapest
    df_agg = df_agg.with_columns(
        pl.when(pl.col("ontrac_cost_avg") == pl.col("cheapest_current_cost_avg"))
        .then(pl.lit("ONTRAC"))
        .when(pl.col("usps_cost_avg") == pl.col("cheapest_current_cost_avg"))
        .then(pl.lit("USPS"))
        .when(pl.col("fedex_cost_avg") == pl.col("cheapest_current_cost_avg"))
        .then(pl.lit("FEDEX"))
        .otherwise(pl.lit("UNKNOWN"))
        .alias("cheapest_current_carrier")
    )

    # Summary stats
    print(f"\nAggregated dataset:")
    print(f"  Groups: {df_agg.shape[0]:,}")
    print(f"  Columns: {df_agg.shape[1]}")

    print(f"\n  Unique values:")
    print(f"    packagetype: {df_agg['packagetype'].n_unique():,}")
    print(f"    shipping_zip_code: {df_agg['shipping_zip_code'].n_unique():,}")
    print(f"    weight_bracket: {df_agg['weight_bracket'].n_unique():,}")

    total_shipments = df_agg["shipment_count"].sum()
    print(f"\n  Total shipments: {total_shipments:,}")

    # Cheapest carrier distribution
    print("\n  Cheapest carrier distribution (by shipment count):")
    cheapest_dist = (
        df_agg
        .group_by("cheapest_current_carrier")
        .agg(pl.col("shipment_count").sum().alias("total_shipments"))
        .sort("total_shipments", descending=True)
    )
    for row in cheapest_dist.iter_rows():
        carrier, count = row
        pct = count / total_shipments * 100
        print(f"    {carrier}: {count:,} ({pct:.1f}%)")

    # Cost comparison
    print("\n  Total cost by scenario:")
    current_total = df_agg["cost_current_carrier_total"].sum()
    print(f"    Current mix:     ${current_total:,.2f}")

    for carrier in ["ontrac", "usps", "fedex", "p2p", "p2p_us2", "maersk"]:
        col = f"{carrier}_cost_total"
        total = df_agg[col].sum()
        diff_pct = (total - current_total) / current_total * 100
        print(f"    100% {carrier.upper():8}: ${total:,.2f} ({diff_pct:+.1f}%)")

    # FedEx HD vs SP breakdown
    fedex_hd_count = df_agg["fedex_hd_shipment_count"].sum()
    fedex_sp_count = df_agg["fedex_sp_shipment_count"].sum()
    print(f"\n  FedEx service breakdown:")
    print(f"    Home Delivery: {fedex_hd_count:,} ({fedex_hd_count/total_shipments*100:.1f}%)")
    print(f"    SmartPost:     {fedex_sp_count:,} ({fedex_sp_count/total_shipments*100:.1f}%)")

    # Optimal (cheapest current carrier per group)
    optimal_cost = (
        df_agg
        .with_columns(
            (pl.col("cheapest_current_cost_avg") * pl.col("shipment_count")).alias("optimal_group_cost")
        )
        ["optimal_group_cost"].sum()
    )
    diff_pct = (optimal_cost - current_total) / current_total * 100
    print(f"    Optimal (no constraints): ${optimal_cost:,.2f} ({diff_pct:+.1f}%)")

    # Save
    output_path = COMBINED_DATASETS / "shipments_aggregated.parquet"
    df_agg.write_parquet(output_path)
    print(f"\nSaved to: {output_path}")
    print("Done.")


if __name__ == "__main__":
    main()
