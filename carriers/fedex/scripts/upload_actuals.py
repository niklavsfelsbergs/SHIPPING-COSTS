"""
Upload Actual Costs to Database
===============================

Pulls actual invoice costs from FedEx invoices and uploads them to the database.

Modes:
    --full          Full refresh - delete all actuals and repull from invoices
    --incremental   Only process orders without actuals (insert only, no delete)
    --days N        Delete actuals for last N days and repull (by expected pcs_created)

Usage:
    python -m carriers.fedex.scripts.upload_actuals --full
    python -m carriers.fedex.scripts.upload_actuals --incremental
    python -m carriers.fedex.scripts.upload_actuals --days 7
    python -m carriers.fedex.scripts.upload_actuals --full --dry-run
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta

import polars as pl

import shared
from shared.database import pull_data, execute_query, push_data


# =============================================================================
# CONFIGURATION
# =============================================================================

EXPECTED_TABLE = "shipping_costs.expected_shipping_costs_fedex"
ACTUAL_TABLE = "shipping_costs.actual_shipping_costs_fedex"

SHARED_SQL_DIR = Path(shared.__file__).parent / "sql"
FEDEX_SQL_DIR = Path(__file__).parent / "sql"

# Date window for matching tracking numbers to invoices
# Prevents wrong matches if tracking numbers are reused over time
DATE_WINDOW_DAYS = 120

# Columns to upload (matches table order)
# TODO: Update column list based on actual FedEx invoice structure
UPLOAD_COLUMNS = [
    "pcs_orderid",
    "trackingnumber",
    "invoice_number",
    "billing_date",
    "actual_zone",
    "actual_billed_weight_lbs",
    "actual_base",
    # TODO: Add surcharge columns based on FedEx invoice structure
    "actual_fuel",
    "actual_total",
    "dw_timestamp",
]


# =============================================================================
# DATABASE HELPERS
# =============================================================================

def get_actual_row_count() -> int:
    """Get total row count in the actual costs table."""
    query = f"SELECT COUNT(*) as cnt FROM {ACTUAL_TABLE}"
    try:
        result = pull_data(query)
        return int(result["cnt"][0])
    except Exception:
        return 0


def delete_all_actuals(dry_run: bool = False) -> int:
    """Delete all rows from the actual costs table."""
    count = get_actual_row_count()

    if count == 0:
        return 0

    if dry_run:
        print(f"  [DRY RUN] Would delete {count:,} rows")
        return count

    execute_query(f"DELETE FROM {ACTUAL_TABLE}", commit=True)
    print(f"  Deleted {count:,} rows")
    return count


# =============================================================================
# DATA EXTRACTION
# =============================================================================

def get_invoice_actuals(
    orderids: list[int] | None = None,
    limit: int | None = None,
) -> pl.DataFrame:
    """
    Get actual costs from FedEx invoices.

    TODO: Implement FedEx invoice data extraction.

    Args:
        orderids: Specific order IDs to look up (None = all)
        limit: Max rows to return

    Returns:
        DataFrame with actual cost data
    """
    # TODO: Implement FedEx invoice extraction
    # This will depend on how FedEx invoice data is stored
    raise NotImplementedError(
        "FedEx invoice extraction not yet implemented. "
        "Need to identify invoice data source and structure."
    )


# =============================================================================
# MODE HANDLERS
# =============================================================================

def run_full_mode(
    batch_size: int,
    dry_run: bool,
) -> int:
    """Full mode: Delete all actuals, repull from invoices."""
    print("=" * 60)
    print("FULL MODE - ACTUAL COSTS")
    print("=" * 60)

    print("\nStep 1: Deleting all existing actuals...")
    deleted = delete_all_actuals(dry_run=dry_run)

    print("\nStep 2: Extracting actual costs from invoices...")
    df = get_invoice_actuals()

    if len(df) == 0:
        print("\nNo invoice data found.")
        return 0

    # Add timestamp
    df = df.with_columns(
        pl.lit(datetime.now()).alias("dw_timestamp")
    )

    # Print summary
    print("\n" + "=" * 60)
    print("UPLOAD SUMMARY")
    print("=" * 60)
    print(f"Rows deleted: {deleted:,}")
    print(f"New rows to upload: {len(df):,}")
    print(f"Total actual cost: ${df['actual_total'].sum():,.2f}")

    if dry_run:
        print(f"\n[DRY RUN] Would upload to: {ACTUAL_TABLE}")
        return len(df)

    # Upload
    print(f"\nStep 3: Uploading to {ACTUAL_TABLE}...")
    push_data(df, ACTUAL_TABLE, batch_size=batch_size)

    return len(df)


def run_incremental_mode(
    batch_size: int,
    limit: int | None,
    dry_run: bool,
) -> int:
    """Incremental mode: Only process orders without actuals."""
    print("=" * 60)
    print("INCREMENTAL MODE - ACTUAL COSTS")
    print("=" * 60)

    # TODO: Implement incremental logic
    raise NotImplementedError(
        "Incremental mode not yet implemented for FedEx."
    )


def run_days_mode(
    days: int,
    batch_size: int,
    dry_run: bool,
) -> int:
    """Days mode: Delete actuals for last N days and repull."""
    print("=" * 60)
    print(f"DAYS MODE ({days} days) - ACTUAL COSTS")
    print("=" * 60)

    # TODO: Implement days mode logic
    raise NotImplementedError(
        "Days mode not yet implemented for FedEx."
    )


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Upload actual FedEx invoice costs to database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  --full          Full refresh - delete all actuals and repull from invoices
  --incremental   Only process orders without actuals (insert only, no delete)
  --days N        Delete actuals for last N days and repull (by expected pcs_created)

Examples:
  python -m carriers.fedex.scripts.upload_actuals --full
  python -m carriers.fedex.scripts.upload_actuals --incremental
  python -m carriers.fedex.scripts.upload_actuals --days 7
  python -m carriers.fedex.scripts.upload_actuals --full --dry-run
        """
    )

    # Mode selection (mutually exclusive, required)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--full",
        action="store_true",
        help="Full refresh - delete all actuals and repull from invoices"
    )
    mode_group.add_argument(
        "--incremental",
        action="store_true",
        help="Only process orders without actuals (insert only, no delete)"
    )
    mode_group.add_argument(
        "--days",
        type=int,
        metavar="N",
        help="Delete actuals for last N days and repull"
    )

    # Common options
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Number of rows per INSERT batch (default: 5000)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Max orders to process (for testing)"
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
                limit=args.limit,
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
            print(f"[DRY RUN] Would have uploaded {rows:,} rows to {ACTUAL_TABLE}")
        else:
            print(f"Successfully uploaded {rows:,} rows to {ACTUAL_TABLE}")
        print("=" * 60)

    except NotImplementedError as e:
        print(f"\n{e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        raise


if __name__ == "__main__":
    main()
