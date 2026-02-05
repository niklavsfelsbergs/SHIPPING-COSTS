"""
Build unified shipment dataset by joining all carrier parquet files.

Joins on pcs_orderid and creates a single dataset with costs from all carriers.
"""

import polars as pl
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
CARRIER_DATASETS = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "carrier_datasets"
OUTPUT_DIR = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "combined_datasets"


def load_ontrac() -> pl.DataFrame:
    """Load OnTrac data with renamed columns."""
    path = list(CARRIER_DATASETS.glob("ontrac_all_us_*.parquet"))[0]
    df = pl.read_parquet(path)

    # Select and rename columns
    return df.select([
        "pcs_orderid",
        pl.col("shipping_zone").alias("ontrac_shipping_zone"),
        pl.col("billable_weight_lbs").alias("ontrac_billable_weight"),
        pl.col("ontrac_cost_base").alias("ontrac_cost_base"),
        pl.col("ontrac_cost_oml").alias("ontrac_cost_oml"),
        pl.col("ontrac_cost_lps").alias("ontrac_cost_lps"),
        pl.col("ontrac_cost_ahs").alias("ontrac_cost_ahs"),
        pl.col("ontrac_cost_das").alias("ontrac_cost_das"),
        pl.col("ontrac_cost_edas").alias("ontrac_cost_edas"),
        pl.col("ontrac_cost_res").alias("ontrac_cost_res"),
        pl.col("ontrac_cost_dem_oml").alias("ontrac_cost_dem_oml"),
        pl.col("ontrac_cost_dem_lps").alias("ontrac_cost_dem_lps"),
        pl.col("ontrac_cost_dem_ahs").alias("ontrac_cost_dem_ahs"),
        pl.col("ontrac_cost_dem_res").alias("ontrac_cost_dem_res"),
        pl.col("ontrac_cost_fuel").alias("ontrac_cost_fuel"),
        pl.col("ontrac_cost_total").alias("ontrac_cost_total"),
    ])


def load_usps() -> pl.DataFrame:
    """Load USPS data with renamed columns."""
    path = list(CARRIER_DATASETS.glob("usps_all_us_*.parquet"))[0]
    df = pl.read_parquet(path)

    return df.select([
        "pcs_orderid",
        pl.col("shipping_zone").alias("usps_shipping_zone"),
        pl.col("billable_weight_lbs").alias("usps_billable_weight"),
        pl.col("usps_cost_base").alias("usps_cost_base"),
        pl.col("usps_cost_nsl1").alias("usps_cost_nsl1"),
        pl.col("usps_cost_nsl2").alias("usps_cost_nsl2"),
        pl.col("usps_cost_nsv").alias("usps_cost_nsv"),
        pl.col("usps_cost_peak").alias("usps_cost_peak"),
        pl.col("usps_cost_total").alias("usps_cost_total"),
    ])


def load_fedex() -> pl.DataFrame:
    """Load FedEx data with renamed columns."""
    path = list(CARRIER_DATASETS.glob("fedex_all_us_*.parquet"))[0]
    df = pl.read_parquet(path)

    return df.select([
        "pcs_orderid",
        pl.col("shipping_zone").alias("fedex_shipping_zone"),
        pl.col("billable_weight_lbs").alias("fedex_billable_weight"),
        pl.col("fedex_service_selected").alias("fedex_service_selected"),
        pl.col("fedex_cost_base_rate").alias("fedex_cost_base_rate"),
        pl.col("fedex_cost_performance_pricing").alias("fedex_cost_performance_pricing"),
        pl.col("fedex_cost_earned_discount").alias("fedex_cost_earned_discount"),
        pl.col("fedex_cost_grace_discount").alias("fedex_cost_grace_discount"),
        pl.col("fedex_cost_ahs").alias("fedex_cost_ahs"),
        pl.col("fedex_cost_ahs_weight").alias("fedex_cost_ahs_weight"),
        pl.col("fedex_cost_oversize").alias("fedex_cost_oversize"),
        pl.col("fedex_cost_das").alias("fedex_cost_das"),
        pl.col("fedex_cost_residential").alias("fedex_cost_residential"),
        pl.col("fedex_cost_dem_base").alias("fedex_cost_dem_base"),
        pl.col("fedex_cost_dem_ahs").alias("fedex_cost_dem_ahs"),
        pl.col("fedex_cost_dem_oversize").alias("fedex_cost_dem_oversize"),
        pl.col("fedex_cost_fuel").alias("fedex_cost_fuel"),
        pl.col("fedex_cost_total").alias("fedex_cost_total"),
        pl.col("fedex_hd_cost_total").alias("fedex_hd_cost_total"),
        pl.col("fedex_sp_cost_total").alias("fedex_sp_cost_total"),
    ])


def load_p2p() -> pl.DataFrame:
    """Load P2P data with renamed columns."""
    path = list(CARRIER_DATASETS.glob("p2p_us_all_us_*.parquet"))[0]
    df = pl.read_parquet(path)

    return df.select([
        "pcs_orderid",
        pl.col("shipping_zone").alias("p2p_shipping_zone"),
        pl.col("billable_weight_lbs").alias("p2p_billable_weight"),
        pl.col("cost_base").alias("p2p_cost_base"),
        pl.col("cost_ahs").alias("p2p_cost_ahs"),
        pl.col("cost_oversize").alias("p2p_cost_oversize"),
        pl.col("cost_total").alias("p2p_cost_total"),
    ])


def load_maersk() -> pl.DataFrame:
    """Load Maersk data with base columns and renamed cost columns."""
    path = list(CARRIER_DATASETS.glob("maersk_us_all_us_*.parquet"))[0]
    df = pl.read_parquet(path)

    # Maersk has the most complete base columns, so we use it as the base
    base_cols = [
        "pcs_orderid",
        "pcs_ordernumber",
        "packagetype",
        "pcs_shipping_provider",
        "pcs_created",
        "ship_date",
        "production_site",
        "shipping_zip_code",
        "shipping_region",
        "length_in",
        "width_in",
        "height_in",
        "weight_lbs",
    ]

    maersk_cols = [
        pl.col("shipping_zone").alias("maersk_shipping_zone"),
        pl.col("billable_weight_lbs").alias("maersk_billable_weight"),
        pl.col("cost_base").alias("maersk_cost_base"),
        pl.col("cost_nsl1").alias("maersk_cost_nsl1"),
        pl.col("cost_nsl2").alias("maersk_cost_nsl2"),
        pl.col("cost_nsd").alias("maersk_cost_nsd"),
        pl.col("cost_pickup").alias("maersk_cost_pickup"),
        pl.col("cost_total").alias("maersk_cost_total"),
    ]

    return df.select(base_cols + maersk_cols)


def determine_current_carrier_cost(df: pl.DataFrame) -> pl.DataFrame:
    """Add cost_current_carrier based on pcs_shipping_provider mapping.

    Imputation:
    - DHL: $6.00/shipment (estimated based on typical DHL eCommerce rates)
    - OnTrac nulls (non-serviceable ZIPs that were actually shipped): packagetype average
    """
    DHL_ESTIMATED_COST = 6.00

    # Initial assignment
    df = df.with_columns(
        pl.when(pl.col("pcs_shipping_provider") == "ONTRAC")
        .then(pl.col("ontrac_cost_total"))
        .when(pl.col("pcs_shipping_provider") == "USPS")
        .then(pl.col("usps_cost_total"))
        .when(pl.col("pcs_shipping_provider").str.contains("FX"))
        .then(pl.col("fedex_cost_total"))
        .when(pl.col("pcs_shipping_provider") == "DHL ECOMMERCE AMERICA")
        .then(pl.lit(DHL_ESTIMATED_COST))
        .otherwise(None)
        .alias("cost_current_carrier")
    )

    # Impute OnTrac null costs (shipments to non-serviceable ZIPs that were actually shipped)
    # Use average OnTrac cost by packagetype
    ontrac_null_count = df.filter(
        (pl.col("pcs_shipping_provider") == "ONTRAC") &
        (pl.col("cost_current_carrier").is_null())
    ).height

    if ontrac_null_count > 0:
        print(f"    Imputing {ontrac_null_count:,} OnTrac null costs with packagetype average...")
        # Calculate average OnTrac cost by packagetype (excluding nulls)
        ontrac_avg_by_pkg = df.filter(
            (pl.col("pcs_shipping_provider") == "ONTRAC") &
            (pl.col("cost_current_carrier").is_not_null())
        ).group_by("packagetype").agg(
            pl.col("cost_current_carrier").mean().alias("_ontrac_avg_cost")
        )

        # Join and fill nulls
        df = df.join(ontrac_avg_by_pkg, on="packagetype", how="left")
        df = df.with_columns(
            pl.when(
                (pl.col("pcs_shipping_provider") == "ONTRAC") &
                (pl.col("cost_current_carrier").is_null())
            )
            .then(pl.col("_ontrac_avg_cost"))
            .otherwise(pl.col("cost_current_carrier"))
            .alias("cost_current_carrier")
        ).drop("_ontrac_avg_cost")

    return df


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading carrier datasets...")

    # Load Maersk first (has base columns)
    print("  Loading Maersk (base)...")
    df = load_maersk()
    print(f"    {df.shape[0]:,} rows")

    # Join other carriers
    print("  Loading and joining OnTrac...")
    df = df.join(load_ontrac(), on="pcs_orderid", how="left")

    print("  Loading and joining USPS...")
    df = df.join(load_usps(), on="pcs_orderid", how="left")

    print("  Loading and joining FedEx...")
    df = df.join(load_fedex(), on="pcs_orderid", how="left")

    print("  Loading and joining P2P...")
    df = df.join(load_p2p(), on="pcs_orderid", how="left")

    # Add current carrier cost
    print("  Calculating cost_current_carrier...")
    df = determine_current_carrier_cost(df)

    # Summary stats
    print("\nDataset summary:")
    print(f"  Total rows: {df.shape[0]:,}")
    print(f"  Total columns: {df.shape[1]}")

    # Current carrier distribution
    print("\n  Current carrier distribution:")
    carrier_counts = df.group_by("pcs_shipping_provider").agg(pl.len().alias("count")).sort("count", descending=True)
    for row in carrier_counts.iter_rows():
        provider, count = row
        pct = count / df.shape[0] * 100
        print(f"    {provider}: {count:,} ({pct:.1f}%)")

    # Cost totals
    print("\n  Cost totals (current carrier mix):")
    current_total = df["cost_current_carrier"].sum()
    print(f"    Current carrier total: ${current_total:,.2f}")

    print("\n  Cost totals (100% single carrier):")
    for carrier in ["ontrac", "usps", "fedex", "p2p", "maersk"]:
        col = f"{carrier}_cost_total"
        total = df[col].sum()
        diff_pct = (total - current_total) / current_total * 100
        print(f"    {carrier.upper():8}: ${total:,.2f} ({diff_pct:+.1f}%)")

    # Save
    output_path = OUTPUT_DIR / "shipments_unified.parquet"
    df.write_parquet(output_path)
    print(f"\nSaved to: {output_path}")
    print("Done.")


if __name__ == "__main__":
    main()
