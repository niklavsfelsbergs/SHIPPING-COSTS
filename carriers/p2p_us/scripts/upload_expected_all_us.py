"""
Upload Expected Costs for ALL US Shipments
===========================================

Calculates hypothetical P2P US shipping costs for ALL US shipments
and uploads them to the database.

This enables carrier cost optimization analysis by comparing what shipments
would cost with P2P US vs what they actually cost with their real carrier.

Modes:
    --full          Full calculation since 2025-01-01, delete existing and reupload
    --incremental   Find max date, delete that day's data, recalculate from there
    --days N        Delete and recalculate last N days (by pcs_created)

Usage:
    python -m carriers.p2p_us.scripts.upload_expected_all_us --full
    python -m carriers.p2p_us.scripts.upload_expected_all_us --incremental
    python -m carriers.p2p_us.scripts.upload_expected_all_us --days 7
    python -m carriers.p2p_us.scripts.upload_expected_all_us --full --dry-run
    python -m carriers.p2p_us.scripts.upload_expected_all_us --full --parquet --start-date 2025-01-01 --end-date 2025-12-31

    # Load from pre-exported parquet instead of database (faster iteration):
    python -m shared.scripts.export_pcs_shipments --start-date 2025-01-01 --end-date 2025-12-31
    python -m carriers.p2p_us.scripts.upload_expected_all_us --full --parquet-data shared/data/pcs_shipments_all_us_2025-01-01_2025-12-31.parquet --start-date 2025-01-01 --end-date 2025-12-31
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl

from shared.database import pull_data, execute_query, push_data
from carriers.p2p_us.data import load_pcs_shipments_all_us, DEFAULT_START_DATE
from carriers.p2p_us.calculate_costs import calculate_costs


# =============================================================================
# CONFIGURATION
# =============================================================================

TABLE_NAME = "shipping_costs.expected_shipping_costs_p2p_us_all_us"

# Output directory for parquet files
PARQUET_OUTPUT_DIR = Path(__file__).parent / "output" / "all_us"

# P2P US weight limit
MAX_WEIGHT_LBS = 50

# Penalty cost for overweight shipments (ensures they're never optimal)
OVERWEIGHT_PENALTY_COST = 200.0

# Penalty cost for shipments to ZIPs not covered by P2P US zone file
# These ZIPs are outside P2P US service area and would require a different carrier
OUT_OF_COVERAGE_PENALTY_COST = 200.0

# Columns to upload (matches DDL order)
UPLOAD_COLUMNS = [
    # Identification (7)
    "pcs_orderid", "pcs_ordernumber", "latest_trackingnumber",
    "trackingnumber_count", "shop_ordernumber", "packagetype",
    "pcs_shipping_provider",
    # Dates (2)
    "pcs_created", "ship_date",
    # Location (6)
    "production_site", "shipping_zip_code", "shipping_region",
    "shipping_country", "shipping_zone", "zone_covered",
    # Dimensions imperial (4)
    "length_in", "width_in", "height_in", "weight_lbs",
    # Calculated dimensions (4)
    "cubic_in", "longest_side_in", "second_longest_in", "length_plus_girth",
    # Weight calculations (3)
    "dim_weight_lbs", "uses_dim_weight", "billable_weight_lbs",
    # Surcharge flags (2)
    "surcharge_ahs", "surcharge_oversize",
    # Costs (6)
    "cost_base", "cost_ahs", "cost_oversize",
    "cost_subtotal", "cost_total", "cost_total_multishipment",
    # Metadata (2)
    "calculator_version", "dw_timestamp",
]


# =============================================================================
# DATABASE HELPERS
# =============================================================================

def get_max_pcs_created() -> datetime | None:
    """Get the maximum pcs_created timestamp in the table."""
    query = f"SELECT MAX(pcs_created) as max_date FROM {TABLE_NAME}"
    try:
        result = pull_data(query)
        if len(result) == 0 or result["max_date"][0] is None:
            return None
        return result["max_date"][0]
    except Exception:
        return None


def get_row_count() -> int:
    """Get total row count in the table."""
    query = f"SELECT COUNT(*) as cnt FROM {TABLE_NAME}"
    try:
        result = pull_data(query)
        return int(result["cnt"][0])
    except Exception:
        return 0


def get_row_count_from_date(start_date: str) -> int:
    """Get count of rows from a start date onwards."""
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
    """Delete all rows from the table."""
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
    """Delete all rows from a start date onwards."""
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
# PIPELINE
# =============================================================================

def run_pipeline(
    start_date: str,
    end_date: str | None = None,
    parquet_data: str | None = None,
) -> pl.DataFrame:
    """
    Run the full calculation pipeline for a date range.

    Returns DataFrame ready for upload with UPLOAD_COLUMNS.
    """
    # Load ALL US shipments (from parquet or database)
    if parquet_data:
        print(f"  Loading ALL US shipments from parquet: {parquet_data}...")
        df = pl.read_parquet(parquet_data)
        # Filter by date range
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

    # Mark overweight shipments (P2P US max 50 lbs)
    overweight_count = df.filter(pl.col("weight_lbs") > MAX_WEIGHT_LBS).height
    if overweight_count > 0:
        print(f"  Marked {overweight_count:,} shipments over {MAX_WEIGHT_LBS} lbs (will set cost to null)")

    df = df.with_columns(
        (pl.col("weight_lbs") > MAX_WEIGHT_LBS).alias("_is_overweight")
    )

    print(f"  {len(df):,} shipments to process")

    if len(df) == 0:
        return pl.DataFrame()

    # For overweight shipments, cap weight at max for calculation to avoid errors
    df = df.with_columns(
        pl.when(pl.col("_is_overweight"))
        .then(pl.lit(MAX_WEIGHT_LBS))
        .otherwise(pl.col("weight_lbs"))
        .alias("weight_lbs_calc")
    )
    original_weight = df["weight_lbs"]
    df = df.with_columns(pl.col("weight_lbs_calc").alias("weight_lbs"))

    # Calculate costs
    print("  Calculating costs...")
    df = calculate_costs(df)

    # Restore original weight
    df = df.with_columns(original_weight.alias("weight_lbs"))

    # Set overweight shipments to null (P2P cannot service them)
    df = df.with_columns([
        pl.when(pl.col("_is_overweight"))
        .then(pl.lit(None))
        .otherwise(pl.col("cost_base"))
        .alias("cost_base"),
        pl.when(pl.col("_is_overweight"))
        .then(pl.lit(None))
        .otherwise(pl.col("cost_ahs"))
        .alias("cost_ahs"),
        pl.when(pl.col("_is_overweight"))
        .then(pl.lit(None))
        .otherwise(pl.col("cost_oversize"))
        .alias("cost_oversize"),
        pl.when(pl.col("_is_overweight"))
        .then(pl.lit(None))
        .otherwise(pl.col("cost_subtotal"))
        .alias("cost_subtotal"),
        pl.when(pl.col("_is_overweight"))
        .then(pl.lit(None))
        .otherwise(pl.col("cost_total"))
        .alias("cost_total"),
    ])

    # Set out-of-coverage shipments (ZIP not in P2P US zone file) to null (P2P cannot service them)
    out_of_coverage_count = df.filter(~pl.col("zone_covered")).height
    if out_of_coverage_count > 0:
        print(f"  Marked {out_of_coverage_count:,} shipments with uncovered ZIPs (will set cost to null)")

    df = df.with_columns([
        pl.when(~pl.col("zone_covered"))
        .then(pl.lit(None))
        .otherwise(pl.col("cost_base"))
        .alias("cost_base"),
        pl.when(~pl.col("zone_covered"))
        .then(pl.lit(None))
        .otherwise(pl.col("cost_ahs"))
        .alias("cost_ahs"),
        pl.when(~pl.col("zone_covered"))
        .then(pl.lit(None))
        .otherwise(pl.col("cost_oversize"))
        .alias("cost_oversize"),
        pl.when(~pl.col("zone_covered"))
        .then(pl.lit(None))
        .otherwise(pl.col("cost_subtotal"))
        .alias("cost_subtotal"),
        pl.when(~pl.col("zone_covered"))
        .then(pl.lit(None))
        .otherwise(pl.col("cost_total"))
        .alias("cost_total"),
    ])

    # Calculate multishipment cost (cost_total * trackingnumber_count)
    # For orders with multiple tracking numbers, this gives total expected cost
    # Defaults to cost_total if trackingnumber_count is 0 or null
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
    """
    Common logic for calculating costs and uploading results.

    Args:
        start_date: Date to start calculation from (YYYY-MM-DD)
        rows_deleted: Number of rows deleted in previous step (for summary)
        batch_size: Rows per INSERT batch
        dry_run: If True, don't upload
        end_date: Date to end calculation at (YYYY-MM-DD), optional
        date_range_suffix: Extra text for date range line (e.g., " (7 days)")
        show_net_change: If True, show net change in summary
        calc_step_num: Step number for calculation step
        upload_step_num: Step number for upload step
        parquet_data: Path to parquet file with PCS data, optional

    Returns:
        Number of rows uploaded (or would be uploaded if dry_run)
    """
    print(f"\nStep {calc_step_num}: Calculating expected costs from {start_date} to {end_date or 'today'}...")
    df = run_pipeline(
        start_date=start_date,
        end_date=end_date,
        parquet_data=parquet_data,
    )

    if len(df) == 0:
        print("\nNo shipments found.")
        return 0

    # Print summary
    print("\n" + "=" * 60)
    print("UPLOAD SUMMARY")
    print("=" * 60)
    print(f"Rows deleted: {rows_deleted:,}")
    print(f"New rows to upload: {len(df):,}")
    if show_net_change:
        print(f"Net change: {len(df) - rows_deleted:+,}")
    print(f"Date range: {start_date} to {end_date or 'today'}{date_range_suffix}")
    print(f"Total expected cost: ${df['cost_total'].sum():,.2f}")
    print(f"Avg per shipment: ${df['cost_total'].mean():,.2f}")

    if dry_run:
        print(f"\n[DRY RUN] Would upload to: {TABLE_NAME}")
        return len(df)

    # Upload
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
    """Full mode: Delete all, recalculate from start_date (default 2025-01-01)."""
    start = start_date or DEFAULT_START_DATE

    print("=" * 60)
    print("FULL MODE - P2P US EXPECTED COSTS (ALL US)")
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


def run_incremental_mode(
    batch_size: int,
    dry_run: bool,
) -> int:
    """Incremental mode: Find max date, delete that day, recalculate from there."""
    print("=" * 60)
    print("INCREMENTAL MODE - P2P US EXPECTED COSTS (ALL US)")
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


def run_days_mode(
    days: int,
    batch_size: int,
    dry_run: bool,
) -> int:
    """Days mode: Delete and recalculate last N days."""
    print("=" * 60)
    print(f"DAYS MODE ({days} days) - P2P US EXPECTED COSTS (ALL US)")
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
    """Parquet mode: Calculate costs and save to parquet file instead of database."""
    start = start_date or DEFAULT_START_DATE

    print("=" * 60)
    print("PARQUET MODE - P2P US EXPECTED COSTS (ALL US)")
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

    # Print summary
    print("\n" + "=" * 60)
    print("CALCULATION SUMMARY")
    print("=" * 60)
    print(f"Rows calculated: {len(df):,}")
    print(f"Date range: {start} to {end_date or 'today'}")
    print(f"Total expected cost: ${df['cost_total'].sum():,.2f}")
    print(f"Avg per shipment: ${df['cost_total'].mean():,.2f}")

    # Create output directory if it doesn't exist
    PARQUET_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate filename with date range
    end_str = end_date or datetime.now().strftime("%Y-%m-%d")
    filename = f"p2p_us_all_us_{start}_{end_str}.parquet"
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
        description="Upload expected P2P US shipping costs to database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  --full          Full calculation since 2025-01-01, delete existing and reupload
  --incremental   Find max date, delete that day's data, recalculate from there
  --days N        Delete and recalculate last N days (by pcs_created)

Examples:
  python -m carriers.p2p_us.scripts.upload_expected_all_us --full
  python -m carriers.p2p_us.scripts.upload_expected_all_us --incremental
  python -m carriers.p2p_us.scripts.upload_expected_all_us --days 7
  python -m carriers.p2p_us.scripts.upload_expected_all_us --full --dry-run
        """
    )

    # Mode selection (mutually exclusive, required)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--full",
        action="store_true",
        help="Full calculation since 2025-01-01, delete existing and reupload"
    )
    mode_group.add_argument(
        "--incremental",
        action="store_true",
        help="Find max date, delete that day's data, recalculate from there"
    )
    mode_group.add_argument(
        "--days",
        type=int,
        metavar="N",
        help="Delete and recalculate last N days (by pcs_created)"
    )

    # Common options
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Number of rows per INSERT batch (default: 5000)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't modify database, just show what would happen"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="Override start date (YYYY-MM-DD). For --full mode only."
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date (YYYY-MM-DD). For --full mode only."
    )
    parser.add_argument(
        "--parquet",
        action="store_true",
        help="Save to parquet file instead of uploading to database"
    )
    parser.add_argument(
        "--parquet-data",
        type=str,
        metavar="PATH",
        help="Load PCS shipments from parquet file instead of database"
    )

    args = parser.parse_args()

    # Run appropriate mode
    try:
        if args.parquet:
            # Parquet mode - save to file instead of database
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
        else:  # args.days
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
