"""
Build unified shipment dataset by joining all carrier parquet files.

Joins on pcs_orderid and creates a single dataset with costs from all carriers.
Also pulls actual invoice costs from Redshift for comparison.
"""

import polars as pl
from pathlib import Path

from shared.database import pull_data

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


def load_p2p_us2() -> pl.DataFrame:
    """Load P2P US2 data with renamed columns.

    Includes both PFA and PFS costs, the selected service, and the final cost_total.
    """
    path = list(CARRIER_DATASETS.glob("p2p_us2_all_us_*.parquet"))[0]
    df = pl.read_parquet(path)

    return df.select([
        "pcs_orderid",
        pl.col("shipping_zone").alias("p2p_us2_shipping_zone"),
        pl.col("is_remote").alias("p2p_us2_is_remote"),
        pl.col("service").alias("p2p_us2_service_selected"),
        pl.col("pfa_cost_total").alias("p2p_us2_pfa_cost_total"),
        pl.col("pfs_cost_total").alias("p2p_us2_pfs_cost_total"),
        pl.col("cost_total").alias("p2p_us2_cost_total"),
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


def load_actuals() -> pl.DataFrame:
    """Load actual invoice costs from Redshift.

    Only loads single-shipment orders (pcs_orderid with exactly 1 row)
    to ensure clean 1:1 join with expected costs.

    Returns DataFrame with columns: pcs_orderid, cost_actual, actual_carrier
    """
    print("  Loading actuals from Redshift...")

    # OnTrac actuals - only single-shipment orders, exclude OML/LPS outliers
    ontrac_sql = """
        SELECT pcs_orderid, actual_total as cost_actual, 'ONTRAC' as actual_carrier
        FROM shipping_costs.actual_shipping_costs_ontrac
        WHERE pcs_orderid IN (
            SELECT pcs_orderid
            FROM shipping_costs.actual_shipping_costs_ontrac
            GROUP BY pcs_orderid
            HAVING COUNT(*) = 1
        )
        AND COALESCE(actual_oml, 0) = 0
        AND COALESCE(actual_lps, 0) = 0
        AND COALESCE(actual_dem_oml, 0) = 0
        AND COALESCE(actual_dem_lps, 0) = 0
    """

    # USPS actuals - only single-shipment orders
    usps_sql = """
        SELECT pcs_orderid, "actual_Total" as cost_actual, 'USPS' as actual_carrier
        FROM shipping_costs.actual_shipping_costs_usps
        WHERE pcs_orderid IN (
            SELECT pcs_orderid
            FROM shipping_costs.actual_shipping_costs_usps
            GROUP BY pcs_orderid
            HAVING COUNT(*) = 1
        )
    """

    # FedEx actuals - only single-shipment orders
    fedex_sql = """
        SELECT pcs_orderid, actual_net_charge as cost_actual, 'FEDEX' as actual_carrier
        FROM shipping_costs.actual_shipping_costs_fedex
        WHERE pcs_orderid IN (
            SELECT pcs_orderid
            FROM shipping_costs.actual_shipping_costs_fedex
            GROUP BY pcs_orderid
            HAVING COUNT(*) = 1
        )
    """

    # Pull from Redshift
    print("    Pulling OnTrac actuals...")
    df_ontrac = pull_data(ontrac_sql)
    print(f"      {df_ontrac.shape[0]:,} single-shipment orders")

    print("    Pulling USPS actuals...")
    df_usps = pull_data(usps_sql)
    print(f"      {df_usps.shape[0]:,} single-shipment orders")

    print("    Pulling FedEx actuals...")
    df_fedex = pull_data(fedex_sql)
    print(f"      {df_fedex.shape[0]:,} single-shipment orders")

    # Combine all actuals
    df_actuals = pl.concat([df_ontrac, df_usps, df_fedex])
    # Cast cost_actual to Float64 (Redshift returns Decimal)
    df_actuals = df_actuals.with_columns(pl.col("cost_actual").cast(pl.Float64))
    print(f"    Total actuals: {df_actuals.shape[0]:,}")

    return df_actuals


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

    print("  Loading and joining P2P US2...")
    df = df.join(load_p2p_us2(), on="pcs_orderid", how="left")

    # Add current carrier cost
    print("  Calculating cost_current_carrier...")
    df = determine_current_carrier_cost(df)

    # Load and join actuals
    DHL_ESTIMATED_COST = 6.00
    df_actuals = load_actuals()
    df = df.join(df_actuals, on="pcs_orderid", how="left")

    # For DHL shipments, set cost_actual to estimated cost
    df = df.with_columns(
        pl.when(pl.col("pcs_shipping_provider") == "DHL ECOMMERCE AMERICA")
        .then(pl.lit(DHL_ESTIMATED_COST))
        .otherwise(pl.col("cost_actual"))
        .alias("cost_actual")
    )

    # Keep only shipments with matched actuals (invoice-matched or DHL estimate)
    before_filter = df.shape[0]
    df = df.filter(pl.col("cost_actual").is_not_null())
    dropped = before_filter - df.shape[0]
    print(f"\n  Filtering to matched-actuals only: dropped {dropped:,} unmatched shipments")
    print(f"    Remaining: {df.shape[0]:,}")

    # Exclude OnTrac OML/LPS shipments from entire dataset
    # These are outlier shipments with over-max-limits or large package surcharges
    # that we cannot predict (expected cost is always 0 for these)
    print("\n  Excluding OnTrac OML/LPS shipments...")
    oml_lps_orderids = pull_data("""
        SELECT DISTINCT pcs_orderid
        FROM shipping_costs.actual_shipping_costs_ontrac
        WHERE COALESCE(actual_oml, 0) > 0
           OR COALESCE(actual_lps, 0) > 0
           OR COALESCE(actual_dem_oml, 0) > 0
           OR COALESCE(actual_dem_lps, 0) > 0
    """)
    if len(oml_lps_orderids) > 0:
        exclude_ids = oml_lps_orderids["pcs_orderid"].to_list()
        before = df.shape[0]
        df = df.filter(~pl.col("pcs_orderid").is_in(exclude_ids))
        excluded = before - df.shape[0]
        print(f"    Excluded {excluded:,} shipments with OML/LPS surcharges")
    else:
        print("    No OML/LPS shipments found")

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
    for carrier in ["ontrac", "usps", "fedex", "p2p", "p2p_us2", "maersk"]:
        col = f"{carrier}_cost_total"
        total = df[col].sum()
        diff_pct = (total - current_total) / current_total * 100
        print(f"    {carrier.upper():8}: ${total:,.2f} ({diff_pct:+.1f}%)")

    # Actuals matching stats
    print("\n  Actuals matching:")
    total_shipments = df.shape[0]
    has_actual = df.filter(pl.col("cost_actual").is_not_null()).shape[0]
    no_actual = total_shipments - has_actual
    print(f"    With actuals:    {has_actual:,} ({has_actual/total_shipments*100:.1f}%)")
    print(f"    Without actuals: {no_actual:,} ({no_actual/total_shipments*100:.1f}%)")

    # Actuals by carrier
    print("\n  Actuals by carrier:")
    for carrier in ["ONTRAC", "USPS", "FEDEX", "DHL ECOMMERCE AMERICA"]:
        carrier_df = df.filter(pl.col("pcs_shipping_provider") == carrier)
        carrier_total = carrier_df.shape[0]
        carrier_has_actual = carrier_df.filter(pl.col("cost_actual").is_not_null()).shape[0]
        if carrier_total > 0:
            match_pct = carrier_has_actual / carrier_total * 100
            print(f"    {carrier:25}: {carrier_has_actual:,} / {carrier_total:,} ({match_pct:.1f}%)")

    # Cost comparison (actuals vs calculated)
    df_matched = df.filter(pl.col("cost_actual").is_not_null())
    if df_matched.shape[0] > 0:
        actual_total = df_matched["cost_actual"].sum()
        calculated_total = df_matched["cost_current_carrier"].sum()
        diff = calculated_total - actual_total
        diff_pct = diff / actual_total * 100
        print("\n  Actuals vs Calculated (matched shipments only):")
        print(f"    2025 Actual total:     ${actual_total:,.2f}")
        print(f"    2026 Calculated total: ${calculated_total:,.2f}")
        print(f"    Difference:            ${diff:+,.2f} ({diff_pct:+.1f}%)")

    # Save
    output_path = OUTPUT_DIR / "shipments_unified.parquet"
    df.write_parquet(output_path)
    print(f"\nSaved to: {output_path}")
    print("Done.")


if __name__ == "__main__":
    main()
