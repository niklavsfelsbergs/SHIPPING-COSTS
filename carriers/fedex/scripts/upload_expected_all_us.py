"""
Upload Expected Costs for ALL US Shipments
===========================================

Calculates hypothetical FedEx shipping costs for ALL US shipments
(not just FedEx shipments) and uploads them to the database.

This enables carrier cost optimization analysis by comparing what shipments
would cost with FedEx vs what they actually cost with their real carrier.

All shipments are calculated as if originating from Columbus (CMH zones).
Non-FedEx shipments use Home Delivery (FXEHD) service mapping.

Modes:
    --full          Full calculation since 2025-01-01, delete existing and reupload
    --incremental   Find max date, delete that day's data, recalculate from there
    --days N        Delete and recalculate last N days (by pcs_created)

Usage:
    python -m carriers.fedex.scripts.upload_expected_all_us --full
    python -m carriers.fedex.scripts.upload_expected_all_us --incremental
    python -m carriers.fedex.scripts.upload_expected_all_us --days 7
    python -m carriers.fedex.scripts.upload_expected_all_us --full --dry-run
"""

import argparse
import sys
from datetime import datetime, timedelta

import polars as pl

from shared.database import pull_data, execute_query, push_data, get_connection
from carriers.fedex.data import load_pcs_shipments_all_us
from carriers.fedex.calculate_costs import calculate_costs


# =============================================================================
# CONFIGURATION
# =============================================================================

TABLE_NAME = "shipping_costs.expected_shipping_costs_fedex_all_us"

DEFAULT_START_DATE = "2025-01-01"

# FedEx Home Delivery weight limit
MAX_WEIGHT_LBS = 150

# Default service for non-FedEx shipments (Home Delivery)
DEFAULT_SERVICE_CODE = "FXEHD"

# Rename cost columns with carrier prefix
COST_COLUMNS_RENAME = {
    # Rate components
    "cost_base_rate": "fedex_cost_base_rate",
    "cost_performance_pricing": "fedex_cost_performance_pricing",
    "cost_earned_discount": "fedex_cost_earned_discount",
    "cost_grace_discount": "fedex_cost_grace_discount",
    # Surcharges
    "cost_ahs": "fedex_cost_ahs",
    "cost_ahs_weight": "fedex_cost_ahs_weight",
    "cost_oversize": "fedex_cost_oversize",
    "cost_das": "fedex_cost_das",
    "cost_residential": "fedex_cost_residential",
    "cost_dem_base": "fedex_cost_dem_base",
    "cost_dem_ahs": "fedex_cost_dem_ahs",
    "cost_dem_oversize": "fedex_cost_dem_oversize",
    # Totals
    "cost_subtotal": "fedex_cost_subtotal",
    "cost_fuel": "fedex_cost_fuel",
    "cost_total": "fedex_cost_total",
}

# Columns to upload (matches DDL order)
UPLOAD_COLUMNS = [
    # Identification (3)
    "pcs_orderid", "pcs_ordernumber", "pcs_shipping_provider",
    # Dates (2)
    "pcs_created", "ship_date",
    # Dimensions (5)
    "length_in", "width_in", "height_in", "weight_lbs", "billable_weight_lbs",
    # Zone (1)
    "shipping_zone",
    # Cost positions - Rate components (4)
    "fedex_cost_base_rate", "fedex_cost_performance_pricing",
    "fedex_cost_earned_discount", "fedex_cost_grace_discount",
    # Cost positions - Surcharges (8)
    "fedex_cost_ahs", "fedex_cost_ahs_weight", "fedex_cost_oversize",
    "fedex_cost_das", "fedex_cost_residential",
    "fedex_cost_dem_base", "fedex_cost_dem_ahs", "fedex_cost_dem_oversize",
    # Cost positions - Totals (3)
    "fedex_cost_subtotal", "fedex_cost_fuel", "fedex_cost_total",
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
        # Rollback to clear aborted transaction state
        get_connection().rollback()
        return None


def get_row_count() -> int:
    """Get total row count in the table."""
    query = f"SELECT COUNT(*) as cnt FROM {TABLE_NAME}"
    try:
        result = pull_data(query)
        return int(result["cnt"][0])
    except Exception:
        # Rollback to clear aborted transaction state
        get_connection().rollback()
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
        # Rollback to clear aborted transaction state
        get_connection().rollback()
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
) -> pl.DataFrame:
    """
    Run the full calculation pipeline for a date range.

    Pipeline:
    1. Load ALL US shipments (no carrier filter)
    2. Filter out shipments with null dimensions/weight
    3. Filter out overweight shipments (> 150 lbs for FedEx Home Delivery)
    4. Override production_site to Columbus (CMH zones)
    5. Set non-FedEx shipments to use Home Delivery service (FXEHD)
    6. Calculate costs using existing calculator
    7. Rename cost columns with carrier prefix

    Returns DataFrame ready for upload with UPLOAD_COLUMNS.
    """
    # 1. Load ALL US shipments (no carrier filter)
    print(f"  Loading ALL US shipments from {start_date} to {end_date or 'today'}...")
    df = load_pcs_shipments_all_us(
        start_date=start_date,
        end_date=end_date,
    )
    print(f"  Loaded {len(df):,} shipments")

    if len(df) == 0:
        return pl.DataFrame()

    # 2. Filter out shipments with null dimensions/weight
    initial_count = len(df)
    df = df.filter(
        pl.col("weight_lbs").is_not_null() &
        pl.col("length_in").is_not_null() &
        pl.col("width_in").is_not_null() &
        pl.col("height_in").is_not_null()
    )
    filtered_nulls = initial_count - len(df)
    if filtered_nulls > 0:
        print(f"  Filtered {filtered_nulls:,} shipments with null dimensions/weight")

    # 3. Filter out overweight shipments (FedEx Home Delivery max 150 lbs)
    before_weight_filter = len(df)
    df = df.filter(pl.col("weight_lbs") <= MAX_WEIGHT_LBS)
    filtered_overweight = before_weight_filter - len(df)
    if filtered_overweight > 0:
        print(f"  Filtered {filtered_overweight:,} shipments over {MAX_WEIGHT_LBS} lbs")

    print(f"  {len(df):,} shipments remain after filtering")

    if len(df) == 0:
        return pl.DataFrame()

    # 4. Override production_site to Columbus (CMH zones)
    df = df.with_columns(pl.lit("Columbus").alias("production_site"))

    # 5. Set non-FedEx shipments to use Home Delivery service (FXEHD)
    # FedEx codes start with "FX", others get mapped to FXEHD for rate calculation
    df = df.with_columns(
        pl.when(pl.col("pcs_shipping_provider").str.starts_with("FX"))
        .then(pl.col("pcs_shipping_provider"))
        .otherwise(pl.lit(DEFAULT_SERVICE_CODE))
        .alias("pcs_shipping_provider_calc")
    )
    # Use calc column for calculation, keep original for reference
    original_providers = df["pcs_shipping_provider"]
    df = df.with_columns(
        pl.col("pcs_shipping_provider_calc").alias("pcs_shipping_provider")
    )

    # 6. Calculate costs (existing function)
    print("  Calculating costs...")
    df = calculate_costs(df)

    # Restore original shipping provider for tracking
    df = df.with_columns(original_providers.alias("pcs_shipping_provider"))

    # 7. Rename all cost columns with carrier prefix
    df = df.rename(COST_COLUMNS_RENAME)

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
    date_range_suffix: str = "",
    show_net_change: bool = False,
    calc_step_num: int = 2,
    upload_step_num: int = 3,
) -> int:
    """
    Common logic for calculating costs and uploading results.

    Args:
        start_date: Date to start calculation from (YYYY-MM-DD)
        rows_deleted: Number of rows deleted in previous step (for summary)
        batch_size: Rows per INSERT batch
        dry_run: If True, don't upload
        date_range_suffix: Extra text for date range line (e.g., " (7 days)")
        show_net_change: If True, show net change in summary
        calc_step_num: Step number for calculation step
        upload_step_num: Step number for upload step

    Returns:
        Number of rows uploaded (or would be uploaded if dry_run)
    """
    print(f"\nStep {calc_step_num}: Calculating expected costs from {start_date}...")
    df = run_pipeline(
        start_date=start_date,
        end_date=None,
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
    print(f"Date range: {start_date} to today{date_range_suffix}")
    print(f"Total expected cost: ${df['fedex_cost_total'].sum():,.2f}")
    print(f"Avg per shipment: ${df['fedex_cost_total'].mean():,.2f}")

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
) -> int:
    """Full mode: Delete all, recalculate from 2025-01-01."""
    print("=" * 60)
    print("FULL MODE - ALL US EXPECTED COSTS (FedEx)")
    print("=" * 60)

    print("\nStep 1: Deleting all existing rows...")
    deleted = delete_all(dry_run=dry_run)

    return _run_calculation_and_upload(
        start_date=DEFAULT_START_DATE,
        rows_deleted=deleted,
        batch_size=batch_size,
        dry_run=dry_run,
    )


def run_incremental_mode(
    batch_size: int,
    dry_run: bool,
) -> int:
    """Incremental mode: Find max date, delete that day, recalculate from there."""
    print("=" * 60)
    print("INCREMENTAL MODE - ALL US EXPECTED COSTS (FedEx)")
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
    print(f"DAYS MODE ({days} days) - ALL US EXPECTED COSTS (FedEx)")
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


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Upload expected FedEx shipping costs for ALL US shipments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  --full          Full calculation since 2025-01-01, delete existing and reupload
  --incremental   Find max date, delete that day's data, recalculate from there
  --days N        Delete and recalculate last N days (by pcs_created)

Examples:
  python -m carriers.fedex.scripts.upload_expected_all_us --full
  python -m carriers.fedex.scripts.upload_expected_all_us --incremental
  python -m carriers.fedex.scripts.upload_expected_all_us --days 7
  python -m carriers.fedex.scripts.upload_expected_all_us --full --dry-run
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

    args = parser.parse_args()

    # Run appropriate mode
    try:
        if args.full:
            rows = run_full_mode(
                batch_size=args.batch_size,
                dry_run=args.dry_run,
            )
        elif args.incremental:
            rows = run_incremental_mode(
                batch_size=args.batch_size,
                dry_run=args.dry_run,
            )
        else:  # args.days
            rows = run_days_mode(
                days=args.days,
                batch_size=args.batch_size,
                dry_run=args.dry_run,
            )

        # Final summary
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
