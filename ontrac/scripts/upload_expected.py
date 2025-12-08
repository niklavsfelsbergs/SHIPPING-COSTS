"""
Upload Expected Costs to Database
=================================

Calculates expected OnTrac shipping costs and uploads them to the database.

Modes:
    --full          Full calculation since 2025-01-01, delete existing and reupload
    --incremental   Find max date, delete that day's data, recalculate from there
    --days N        Delete and recalculate last N days (by pcs_created)

Usage:
    python -m ontrac.scripts.upload_expected --full
    python -m ontrac.scripts.upload_expected --incremental
    python -m ontrac.scripts.upload_expected --days 7
    python -m ontrac.scripts.upload_expected --full --dry-run
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta

import polars as pl

# Add root directory to path for imports
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from shared.database import pull_data, execute_query, push_data
from ontrac.data import load_pcs_shipments, DEFAULT_START_DATE, DEFAULT_PRODUCTION_SITES
from ontrac.calculate_costs import calculate_costs


# =============================================================================
# CONFIGURATION
# =============================================================================

TABLE_NAME = "shipping_costs.expected_shipping_costs_ontrac"

# Columns to upload (matches DDL order)
UPLOAD_COLUMNS = [
    # Identification (5)
    "pcs_orderid", "pcs_ordernumber", "latest_trackingnumber",
    "trackingnumber_count", "shop_ordernumber",
    # Dates (2)
    "pcs_created", "ship_date",
    # Location (6)
    "production_site", "shipping_zip_code", "shipping_region",
    "shipping_country", "shipping_zone", "das_zone",
    # Dimensions imperial (4)
    "length_in", "width_in", "height_in", "weight_lbs",
    # Calculated dimensions (4)
    "cubic_in", "longest_side_in", "second_longest_in", "length_plus_girth",
    # Weight calculations (3)
    "dim_weight_lbs", "uses_dim_weight", "billable_weight_lbs",
    # Surcharge flags (10)
    "surcharge_oml", "surcharge_lps", "surcharge_ahs", "surcharge_das",
    "surcharge_edas", "surcharge_res", "surcharge_dem_oml", "surcharge_dem_lps",
    "surcharge_dem_ahs", "surcharge_dem_res",
    # Costs (14)
    "cost_base", "cost_oml", "cost_lps", "cost_ahs", "cost_das", "cost_edas",
    "cost_res", "cost_dem_oml", "cost_dem_lps", "cost_dem_ahs", "cost_dem_res",
    "cost_subtotal", "cost_fuel", "cost_total",
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
    production_sites: list[str] | None = None,
) -> pl.DataFrame:
    """
    Run the full calculation pipeline for a date range.

    Returns DataFrame ready for upload with UPLOAD_COLUMNS.
    """
    if production_sites is None:
        production_sites = DEFAULT_PRODUCTION_SITES

    # Load shipments
    print(f"  Loading shipments from {start_date} to {end_date or 'today'}...")
    df = load_pcs_shipments(
        start_date=start_date,
        end_date=end_date,
        production_sites=production_sites,
    )
    print(f"  Loaded {len(df):,} shipments")

    if len(df) == 0:
        return pl.DataFrame()

    # Calculate costs
    print("  Calculating costs...")
    df = calculate_costs(df)

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

def run_full_mode(
    production_sites: list[str],
    batch_size: int,
    dry_run: bool,
) -> int:
    """Full mode: Delete all, recalculate from 2025-01-01."""
    print("=" * 60)
    print("FULL MODE - EXPECTED COSTS")
    print("=" * 60)

    # Step 1: Delete all existing rows
    print("\nStep 1: Deleting all existing rows...")
    deleted = delete_all(dry_run=dry_run)

    # Step 2: Calculate from default start date
    print(f"\nStep 2: Calculating expected costs from {DEFAULT_START_DATE}...")
    df = run_pipeline(
        start_date=DEFAULT_START_DATE,
        end_date=None,
        production_sites=production_sites,
    )

    if len(df) == 0:
        print("\nNo shipments found.")
        return 0

    # Print summary
    print("\n" + "=" * 60)
    print("UPLOAD SUMMARY")
    print("=" * 60)
    print(f"Rows deleted: {deleted:,}")
    print(f"New rows to upload: {len(df):,}")
    print(f"Date range: {DEFAULT_START_DATE} to today")
    print(f"Total expected cost: ${df['cost_total'].sum():,.2f}")
    print(f"Avg per shipment: ${df['cost_total'].mean():,.2f}")

    if dry_run:
        print(f"\n[DRY RUN] Would upload to: {TABLE_NAME}")
        return len(df)

    # Upload
    print(f"\nStep 3: Uploading to {TABLE_NAME}...")
    push_data(df, TABLE_NAME, batch_size=batch_size)

    return len(df)


def run_incremental_mode(
    production_sites: list[str],
    batch_size: int,
    dry_run: bool,
) -> int:
    """Incremental mode: Find max date, delete that day, recalculate from there."""
    print("=" * 60)
    print("INCREMENTAL MODE - EXPECTED COSTS")
    print("=" * 60)

    # Step 1: Get max pcs_created
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

        # Step 2: Delete rows for that date (handles partial day)
        print(f"\nStep 2: Deleting data from {start_date} onwards...")
        rows_deleted = delete_from_date(start_date, dry_run=dry_run)

    # Step 3: Calculate from start_date onward
    print(f"\nStep 3: Calculating expected costs from {start_date}...")
    df = run_pipeline(
        start_date=start_date,
        end_date=None,
        production_sites=production_sites,
    )

    if len(df) == 0:
        print("\nNo shipments found for the specified date range.")
        return 0

    # Print summary
    print("\n" + "=" * 60)
    print("UPLOAD SUMMARY")
    print("=" * 60)
    print(f"Rows deleted: {rows_deleted:,}")
    print(f"New rows to upload: {len(df):,}")
    print(f"Net change: {len(df) - rows_deleted:+,}")
    print(f"Date range: {start_date} to today")
    print(f"Total expected cost: ${df['cost_total'].sum():,.2f}")
    print(f"Avg per shipment: ${df['cost_total'].mean():,.2f}")

    if dry_run:
        print(f"\n[DRY RUN] Would upload to: {TABLE_NAME}")
        return len(df)

    # Upload
    print(f"\nStep 4: Uploading to {TABLE_NAME}...")
    push_data(df, TABLE_NAME, batch_size=batch_size)

    return len(df)


def run_days_mode(
    days: int,
    production_sites: list[str],
    batch_size: int,
    dry_run: bool,
) -> int:
    """Days mode: Delete and recalculate last N days."""
    print("=" * 60)
    print(f"DAYS MODE ({days} days) - EXPECTED COSTS")
    print("=" * 60)

    # Calculate start date
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    # Step 1: Delete rows from start_date onwards
    print(f"\nStep 1: Deleting rows from {start_date} onwards...")
    rows_deleted = delete_from_date(start_date, dry_run=dry_run)

    # Step 2: Calculate from start_date onward
    print(f"\nStep 2: Calculating expected costs from {start_date}...")
    df = run_pipeline(
        start_date=start_date,
        end_date=None,
        production_sites=production_sites,
    )

    if len(df) == 0:
        print("\nNo shipments found for the specified date range.")
        return 0

    # Print summary
    print("\n" + "=" * 60)
    print("UPLOAD SUMMARY")
    print("=" * 60)
    print(f"Rows deleted: {rows_deleted:,}")
    print(f"New rows to upload: {len(df):,}")
    print(f"Net change: {len(df) - rows_deleted:+,}")
    print(f"Date range: {start_date} to today ({days} days)")
    print(f"Total expected cost: ${df['cost_total'].sum():,.2f}")
    print(f"Avg per shipment: ${df['cost_total'].mean():,.2f}")

    if dry_run:
        print(f"\n[DRY RUN] Would upload to: {TABLE_NAME}")
        return len(df)

    # Upload
    print(f"\nStep 3: Uploading to {TABLE_NAME}...")
    push_data(df, TABLE_NAME, batch_size=batch_size)

    return len(df)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Upload expected OnTrac shipping costs to database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  --full          Full calculation since 2025-01-01, delete existing and reupload
  --incremental   Find max date, delete that day's data, recalculate from there
  --days N        Delete and recalculate last N days (by pcs_created)

Examples:
  python -m ontrac.scripts.upload_expected --full
  python -m ontrac.scripts.upload_expected --incremental
  python -m ontrac.scripts.upload_expected --days 7
  python -m ontrac.scripts.upload_expected --full --dry-run
  python -m ontrac.scripts.upload_expected --incremental --production-sites Phoenix
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
        "--production-sites",
        type=str,
        nargs="+",
        default=DEFAULT_PRODUCTION_SITES,
        help=f"Production sites to include (default: {' '.join(DEFAULT_PRODUCTION_SITES)})"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Number of rows per INSERT batch (default: 1000)"
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
                production_sites=args.production_sites,
                batch_size=args.batch_size,
                dry_run=args.dry_run,
            )
        elif args.incremental:
            rows = run_incremental_mode(
                production_sites=args.production_sites,
                batch_size=args.batch_size,
                dry_run=args.dry_run,
            )
        else:  # args.days
            rows = run_days_mode(
                days=args.days,
                production_sites=args.production_sites,
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
