"""
Upload Expected Costs for ALL US Shipments (P2P US2)
=====================================================

Calculates hypothetical P2P US2 shipping costs for ALL US shipments
with group-level PFA vs PFS service selection.

Service selection logic:
    1. Calculate both PFA and PFS costs per shipment
    2. Group by (packagetype, weight_bracket)
    3. For each group, sum PFA and PFS costs
    4. Pick the service with lower aggregate cost
    5. Assign cost_total from the chosen service

Modes:
    --full          Full calculation since 2025-01-01, delete existing and reupload
    --incremental   Find max date, delete that day's data, recalculate from there
    --days N        Delete and recalculate last N days (by pcs_created)
    --parquet       Save to parquet file instead of database

Usage:
    python -m carriers.p2p_us2.scripts.upload_expected_all_us --parquet --start-date 2025-01-01 --end-date 2025-12-31
    python -m carriers.p2p_us2.scripts.upload_expected_all_us --parquet --parquet-data shared/data/pcs_shipments_all_us_2025-01-01_2025-12-31.parquet --start-date 2025-01-01 --end-date 2025-12-31
"""

import argparse
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl

from shared.database import pull_data, execute_query, push_data
from carriers.p2p_us2.data import load_pcs_shipments_all_us, DEFAULT_START_DATE
from carriers.p2p_us2.calculate_costs import calculate_costs


# =============================================================================
# CONFIGURATION
# =============================================================================

TABLE_NAME = "shipping_costs.expected_shipping_costs_p2p_us2_all_us"

PARQUET_OUTPUT_DIR = Path(__file__).parent / "output" / "all_us"

# PFS weight limit (PFA is 30, PFS is 70 — use the higher for filtering)
MAX_WEIGHT_LBS = 70

# Penalty cost for overweight/uncovered shipments
OVERWEIGHT_PENALTY_COST = 200.0
OUT_OF_COVERAGE_PENALTY_COST = 200.0

# Weight bracket size for group-level service selection (in lbs)
WEIGHT_BRACKET_SIZE = 5

# Columns to upload (matches output structure)
UPLOAD_COLUMNS = [
    # Identification (7)
    "pcs_orderid", "pcs_ordernumber", "latest_trackingnumber",
    "trackingnumber_count", "shop_ordernumber", "packagetype",
    "pcs_shipping_provider",
    # Dates (2)
    "pcs_created", "ship_date",
    # Location (7)
    "production_site", "shipping_zip_code", "shipping_region",
    "shipping_country", "shipping_zone", "is_remote", "zone_covered",
    # Dimensions imperial (4)
    "length_in", "width_in", "height_in", "weight_lbs",
    # Calculated dimensions (4)
    "cubic_in", "longest_side_in", "second_longest_in", "shortest_side_in",
    # PFA weight (3)
    "pfa_dim_weight_lbs", "pfa_uses_dim_weight", "pfa_billable_weight_lbs",
    # PFS weight (3)
    "pfs_dim_weight_lbs", "pfs_uses_dim_weight", "pfs_billable_weight_lbs",
    # PFA surcharge flags (2)
    "surcharge_pfa_oversize", "surcharge_pfa_oversize_volume",
    # PFS surcharge flags (2)
    "surcharge_pfs_nsl", "surcharge_pfs_nsv",
    # PFA costs (3)
    "pfa_cost_base", "pfa_cost_subtotal", "pfa_cost_total",
    # PFS costs (3)
    "pfs_cost_base", "pfs_cost_subtotal", "pfs_cost_total",
    # PFA surcharge costs (2)
    "cost_pfa_oversize", "cost_pfa_oversize_volume",
    # PFS surcharge costs (2)
    "cost_pfs_nsl", "cost_pfs_nsv",
    # Service selection (3)
    "weight_bracket", "service", "cost_total",
    # Multi-shipment (1)
    "cost_total_multishipment",
    # Metadata (2)
    "calculator_version", "dw_timestamp",
]


# =============================================================================
# DATABASE HELPERS
# =============================================================================

def get_max_pcs_created() -> datetime | None:
    query = f"SELECT MAX(pcs_created) as max_date FROM {TABLE_NAME}"
    try:
        result = pull_data(query)
        if len(result) == 0 or result["max_date"][0] is None:
            return None
        return result["max_date"][0]
    except Exception:
        return None


def get_row_count() -> int:
    query = f"SELECT COUNT(*) as cnt FROM {TABLE_NAME}"
    try:
        result = pull_data(query)
        return int(result["cnt"][0])
    except Exception:
        return 0


def get_row_count_from_date(start_date: str) -> int:
    query = f"""
        SELECT COUNT(*) as cnt
        FROM {TABLE_NAME}
        WHERE pcs_created::date >= '{start_date}'::date
    """
    try:
        result = pull_data(query)
        return int(result["cnt"][0])
    except Exception:
        return 0


def delete_all(dry_run: bool = False) -> int:
    count = get_row_count()
    if count == 0:
        return 0
    if dry_run:
        print(f"  [DRY RUN] Would delete {count:,} rows")
        return count
    execute_query(f"DELETE FROM {TABLE_NAME}", commit=True)
    print(f"  Deleted {count:,} rows")
    return count


def delete_from_date(start_date: str, dry_run: bool = False) -> int:
    count = get_row_count_from_date(start_date)
    if count == 0:
        return 0
    if dry_run:
        print(f"  [DRY RUN] Would delete {count:,} rows from {start_date} onwards")
        return count
    delete_query = f"""
        DELETE FROM {TABLE_NAME}
        WHERE pcs_created::date >= '{start_date}'::date
    """
    execute_query(delete_query, commit=True)
    print(f"  Deleted {count:,} rows from {start_date} onwards")
    return count


# =============================================================================
# GROUP-LEVEL SERVICE SELECTION
# =============================================================================

def _add_weight_bracket(df: pl.DataFrame) -> pl.DataFrame:
    """Add weight bracket column for group-level service selection."""
    return df.with_columns(
        (pl.col("weight_lbs") / WEIGHT_BRACKET_SIZE).ceil().cast(pl.Int64)
        .mul(WEIGHT_BRACKET_SIZE)
        .alias("weight_bracket")
    )


def _select_service(df: pl.DataFrame) -> pl.DataFrame:
    """
    Group-level PFA vs PFS service selection.

    For each (packagetype, weight_bracket) group:
    1. Sum PFA and PFS costs (treating null PFA as infinite)
    2. Pick the service with lower aggregate cost
    3. Assign 'service' and 'cost_total' per shipment
    """
    # For aggregation, replace null PFA costs with a large value
    # so PFA-ineligible shipments push the group toward PFS
    INFINITY = 999999.0

    group_costs = (
        df
        .group_by(["packagetype", "weight_bracket"])
        .agg([
            pl.col("pfa_cost_total").fill_null(INFINITY).sum().alias("group_pfa_total"),
            pl.col("pfs_cost_total").fill_null(INFINITY).sum().alias("group_pfs_total"),
        ])
        .with_columns(
            pl.when(pl.col("group_pfa_total") <= pl.col("group_pfs_total"))
            .then(pl.lit("PFA"))
            .otherwise(pl.lit("PFS"))
            .alias("service")
        )
        .select(["packagetype", "weight_bracket", "service"])
    )

    # Join service selection back to shipments
    df = df.join(group_costs, on=["packagetype", "weight_bracket"], how="left")

    # Assign cost_total based on selected service
    # If selected PFA but this specific shipment is PFA-ineligible, use PFS
    df = df.with_columns(
        pl.when(
            (pl.col("service") == "PFA") & pl.col("pfa_cost_total").is_not_null()
        )
        .then(pl.col("pfa_cost_total"))
        .otherwise(pl.col("pfs_cost_total"))
        .alias("cost_total")
    )

    # Update service for shipments that couldn't use the group's choice
    df = df.with_columns(
        pl.when(
            (pl.col("service") == "PFA") & pl.col("pfa_cost_total").is_null()
        )
        .then(pl.lit("PFS"))
        .otherwise(pl.col("service"))
        .alias("service")
    )

    return df


# =============================================================================
# PIPELINE
# =============================================================================

def run_pipeline(
    start_date: str,
    end_date: str | None = None,
    parquet_data: str | None = None,
) -> pl.DataFrame:
    """Run the full calculation pipeline for a date range."""
    # Load ALL US shipments
    if parquet_data:
        print(f"  Loading ALL US shipments from parquet: {parquet_data}...")
        df = pl.read_parquet(parquet_data)
        if start_date:
            df = df.filter(pl.col("pcs_created").cast(pl.Date) >= pl.lit(start_date).str.to_date("%Y-%m-%d"))
        if end_date:
            df = df.filter(pl.col("pcs_created").cast(pl.Date) <= pl.lit(end_date).str.to_date("%Y-%m-%d"))
    else:
        print(f"  Loading ALL US shipments from {start_date} to {end_date or 'today'}...")
        df = load_pcs_shipments_all_us(
            start_date=start_date,
            end_date=end_date,
        )
    print(f"  Loaded {len(df):,} shipments")

    if len(df) == 0:
        return pl.DataFrame()

    # Filter out shipments with missing dimensions/weight
    initial_count = len(df)
    df = df.filter(
        pl.col("weight_lbs").is_not_null() &
        pl.col("length_in").is_not_null() &
        pl.col("width_in").is_not_null() &
        pl.col("height_in").is_not_null()
    )
    filtered_count = initial_count - len(df)
    if filtered_count > 0:
        print(f"  Filtered {filtered_count:,} shipments with missing dimensions/weight")

    # Mark overweight shipments (PFS max 70 lbs)
    overweight_count = df.filter(pl.col("weight_lbs") > MAX_WEIGHT_LBS).height
    if overweight_count > 0:
        print(f"  Marked {overweight_count:,} shipments over {MAX_WEIGHT_LBS} lbs (will set cost to null)")

    df = df.with_columns(
        (pl.col("weight_lbs") > MAX_WEIGHT_LBS).alias("_is_overweight")
    )

    print(f"  {len(df):,} shipments to process")

    if len(df) == 0:
        return pl.DataFrame()

    # Cap weight at max for calculation to avoid rate lookup errors
    df = df.with_columns(
        pl.when(pl.col("_is_overweight"))
        .then(pl.lit(MAX_WEIGHT_LBS))
        .otherwise(pl.col("weight_lbs"))
        .alias("weight_lbs_calc")
    )
    original_weight = df["weight_lbs"]
    df = df.with_columns(pl.col("weight_lbs_calc").alias("weight_lbs"))

    # Calculate costs (both PFA and PFS)
    print("  Calculating costs...")
    df = calculate_costs(df)

    # Restore original weight
    df = df.with_columns(original_weight.alias("weight_lbs"))

    # Set overweight shipments to null
    overweight_null_cols = [
        "pfa_cost_base", "pfa_cost_subtotal", "pfa_cost_total",
        "cost_pfa_oversize", "cost_pfa_oversize_volume",
        "pfs_cost_base", "pfs_cost_subtotal", "pfs_cost_total",
        "cost_pfs_nsl", "cost_pfs_nsv",
    ]
    df = df.with_columns([
        pl.when(pl.col("_is_overweight"))
        .then(pl.lit(None))
        .otherwise(pl.col(c))
        .alias(c)
        for c in overweight_null_cols
    ])

    # Set out-of-coverage shipments to null
    out_of_coverage_count = df.filter(~pl.col("zone_covered")).height
    if out_of_coverage_count > 0:
        print(f"  Marked {out_of_coverage_count:,} shipments with uncovered ZIPs (will set cost to null)")

    df = df.with_columns([
        pl.when(~pl.col("zone_covered"))
        .then(pl.lit(None))
        .otherwise(pl.col(c))
        .alias(c)
        for c in overweight_null_cols
    ])

    # Add weight bracket and do group-level service selection
    print("  Performing group-level service selection...")
    df = _add_weight_bracket(df)
    df = _select_service(df)

    # Report service selection
    service_counts = df.group_by("service").len().sort("service")
    for row in service_counts.iter_rows():
        print(f"    {row[0]}: {row[1]:,} shipments")

    # Calculate multishipment cost
    df = df.with_columns(
        pl.when(pl.col("trackingnumber_count") > 0)
        .then(pl.col("cost_total") * pl.col("trackingnumber_count"))
        .otherwise(pl.col("cost_total"))
        .alias("cost_total_multishipment")
    )

    # Add timestamp
    df = df.with_columns(
        pl.lit(datetime.now()).alias("dw_timestamp")
    )

    # Drop intermediate columns
    df = df.drop(["_is_overweight", "weight_lbs_calc"], strict=False)

    # Select upload columns
    df = df.select(UPLOAD_COLUMNS)

    return df


# =============================================================================
# MODE HANDLERS
# =============================================================================

def _run_calculation_and_upload(
    start_date: str,
    rows_deleted: int,
    batch_size: int,
    dry_run: bool,
    end_date: str | None = None,
    date_range_suffix: str = "",
    show_net_change: bool = False,
    calc_step_num: int = 2,
    upload_step_num: int = 3,
    parquet_data: str | None = None,
) -> int:
    print(f"\nStep {calc_step_num}: Calculating expected costs from {start_date} to {end_date or 'today'}...")
    df = run_pipeline(
        start_date=start_date,
        end_date=end_date,
        parquet_data=parquet_data,
    )

    if len(df) == 0:
        print("\nNo shipments found.")
        return 0

    print("\n" + "=" * 60)
    print("UPLOAD SUMMARY")
    print("=" * 60)
    print(f"Rows deleted: {rows_deleted:,}")
    print(f"New rows to upload: {len(df):,}")
    if show_net_change:
        print(f"Net change: {len(df) - rows_deleted:+,}")
    print(f"Date range: {start_date} to {end_date or 'today'}{date_range_suffix}")
    cost_total_sum = df["cost_total"].sum()
    cost_total_mean = df["cost_total"].mean()
    if cost_total_sum is not None:
        print(f"Total expected cost: ${cost_total_sum:,.2f}")
    if cost_total_mean is not None:
        print(f"Avg per shipment: ${cost_total_mean:,.2f}")

    if dry_run:
        print(f"\n[DRY RUN] Would upload to: {TABLE_NAME}")
        return len(df)

    print(f"\nStep {upload_step_num}: Uploading to {TABLE_NAME}...")
    push_data(df, TABLE_NAME, batch_size=batch_size)

    return len(df)


def run_full_mode(
    batch_size: int,
    dry_run: bool,
    start_date: str | None = None,
    end_date: str | None = None,
    parquet_data: str | None = None,
) -> int:
    start = start_date or DEFAULT_START_DATE

    print("=" * 60)
    print("FULL MODE - P2P US2 EXPECTED COSTS (ALL US)")
    print("=" * 60)

    if end_date:
        print(f"Date range: {start} to {end_date}")
    if parquet_data:
        print(f"Data source: {parquet_data}")

    print("\nStep 1: Deleting all existing rows...")
    deleted = delete_all(dry_run=dry_run)

    return _run_calculation_and_upload(
        start_date=start,
        end_date=end_date,
        rows_deleted=deleted,
        batch_size=batch_size,
        dry_run=dry_run,
        parquet_data=parquet_data,
    )


def run_incremental_mode(batch_size: int, dry_run: bool) -> int:
    print("=" * 60)
    print("INCREMENTAL MODE - P2P US2 EXPECTED COSTS (ALL US)")
    print("=" * 60)

    print("\nStep 1: Finding latest data in table...")
    max_pcs_created = get_max_pcs_created()

    if max_pcs_created is None:
        print(f"  Table is empty or doesn't exist. Using default start date: {DEFAULT_START_DATE}")
        start_date = DEFAULT_START_DATE
        rows_deleted = 0
    else:
        start_date = max_pcs_created.strftime("%Y-%m-%d")
        print(f"  Max pcs_created: {max_pcs_created}")
        print(f"  Will process from: {start_date}")

        print(f"\nStep 2: Deleting data from {start_date} onwards...")
        rows_deleted = delete_from_date(start_date, dry_run=dry_run)

    return _run_calculation_and_upload(
        start_date=start_date,
        rows_deleted=rows_deleted,
        batch_size=batch_size,
        dry_run=dry_run,
        show_net_change=True,
        calc_step_num=3,
        upload_step_num=4,
    )


def run_days_mode(days: int, batch_size: int, dry_run: bool) -> int:
    print("=" * 60)
    print(f"DAYS MODE ({days} days) - P2P US2 EXPECTED COSTS (ALL US)")
    print("=" * 60)

    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    print(f"\nStep 1: Deleting rows from {start_date} onwards...")
    rows_deleted = delete_from_date(start_date, dry_run=dry_run)

    return _run_calculation_and_upload(
        start_date=start_date,
        rows_deleted=rows_deleted,
        batch_size=batch_size,
        dry_run=dry_run,
        date_range_suffix=f" ({days} days)",
        show_net_change=True,
    )


def run_parquet_mode(
    start_date: str | None = None,
    end_date: str | None = None,
    parquet_data: str | None = None,
) -> int:
    start = start_date or DEFAULT_START_DATE

    print("=" * 60)
    print("PARQUET MODE - P2P US2 EXPECTED COSTS (ALL US)")
    print("=" * 60)
    print(f"Date range: {start} to {end_date or 'today'}")
    if parquet_data:
        print(f"Data source: {parquet_data}")

    print("\nStep 1: Calculating expected costs...")
    df = run_pipeline(
        start_date=start,
        end_date=end_date,
        parquet_data=parquet_data,
    )

    if len(df) == 0:
        print("\nNo shipments found.")
        return 0

    print("\n" + "=" * 60)
    print("CALCULATION SUMMARY")
    print("=" * 60)
    print(f"Rows calculated: {len(df):,}")
    print(f"Date range: {start} to {end_date or 'today'}")
    cost_total_sum = df["cost_total"].sum()
    cost_total_mean = df["cost_total"].mean()
    if cost_total_sum is not None:
        print(f"Total expected cost: ${cost_total_sum:,.2f}")
    if cost_total_mean is not None:
        print(f"Avg per shipment: ${cost_total_mean:,.2f}")

    # Service breakdown
    print("\nService breakdown:")
    service_costs = (
        df.group_by("service")
        .agg([
            pl.len().alias("count"),
            pl.col("cost_total").sum().alias("total_cost"),
            pl.col("cost_total").mean().alias("avg_cost"),
        ])
        .sort("service")
    )
    for row in service_costs.iter_rows():
        svc, cnt, total, avg = row
        if total is not None and avg is not None:
            print(f"  {svc}: {cnt:,} shipments, ${total:,.2f} total, ${avg:,.2f} avg")

    PARQUET_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    end_str = end_date or datetime.now().strftime("%Y-%m-%d")
    filename = f"p2p_us2_all_us_{start}_{end_str}.parquet"
    output_path = PARQUET_OUTPUT_DIR / filename

    print(f"\nStep 2: Saving to {output_path}...")
    df.write_parquet(output_path)
    print(f"Saved {len(df):,} rows to {output_path}")

    return len(df)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Upload expected P2P US2 shipping costs to database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  --full          Full calculation since 2025-01-01, delete existing and reupload
  --incremental   Find max date, delete that day's data, recalculate from there
  --days N        Delete and recalculate last N days (by pcs_created)
  --parquet       Save to parquet file instead of database

Examples:
  python -m carriers.p2p_us2.scripts.upload_expected_all_us --parquet --start-date 2025-01-01 --end-date 2025-12-31
  python -m carriers.p2p_us2.scripts.upload_expected_all_us --full
  python -m carriers.p2p_us2.scripts.upload_expected_all_us --incremental
        """
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--full", action="store_true",
        help="Full calculation since 2025-01-01")
    mode_group.add_argument("--incremental", action="store_true",
        help="Find max date, delete that day's data, recalculate from there")
    mode_group.add_argument("--days", type=int, metavar="N",
        help="Delete and recalculate last N days")

    parser.add_argument("--batch-size", type=int, default=5000,
        help="Number of rows per INSERT batch (default: 5000)")
    parser.add_argument("--dry-run", action="store_true",
        help="Don't modify database, just show what would happen")
    parser.add_argument("--start-date", type=str,
        help="Override start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str,
        help="End date (YYYY-MM-DD)")
    parser.add_argument("--parquet", action="store_true",
        help="Save to parquet file instead of uploading to database")
    parser.add_argument("--parquet-data", type=str, metavar="PATH",
        help="Load PCS shipments from parquet file instead of database")

    args = parser.parse_args()

    try:
        if args.parquet:
            rows = run_parquet_mode(
                start_date=args.start_date,
                end_date=args.end_date,
                parquet_data=args.parquet_data,
            )
            print("\n" + "=" * 60)
            print(f"Successfully saved {rows:,} rows to parquet")
            print("=" * 60)
        elif args.full:
            rows = run_full_mode(
                batch_size=args.batch_size,
                dry_run=args.dry_run,
                start_date=args.start_date,
                end_date=args.end_date,
                parquet_data=args.parquet_data,
            )
            print("\n" + "=" * 60)
            if args.dry_run:
                print(f"[DRY RUN] Would have uploaded {rows:,} rows to {TABLE_NAME}")
            else:
                print(f"Successfully uploaded {rows:,} rows to {TABLE_NAME}")
            print("=" * 60)
        elif args.incremental:
            rows = run_incremental_mode(
                batch_size=args.batch_size,
                dry_run=args.dry_run,
            )
            print("\n" + "=" * 60)
            if args.dry_run:
                print(f"[DRY RUN] Would have uploaded {rows:,} rows to {TABLE_NAME}")
            else:
                print(f"Successfully uploaded {rows:,} rows to {TABLE_NAME}")
            print("=" * 60)
        else:
            rows = run_days_mode(
                days=args.days,
                batch_size=args.batch_size,
                dry_run=args.dry_run,
            )
            print("\n" + "=" * 60)
            if args.dry_run:
                print(f"[DRY RUN] Would have uploaded {rows:,} rows to {TABLE_NAME}")
            else:
                print(f"Successfully uploaded {rows:,} rows to {TABLE_NAME}")
            print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        raise


if __name__ == "__main__":
    main()
