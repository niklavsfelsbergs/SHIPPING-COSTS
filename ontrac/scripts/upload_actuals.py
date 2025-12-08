"""
Upload Actual Costs to Database
===============================

Pulls actual invoice costs from OnTrac invoices and uploads them to the database.

Modes:
    --full          Full refresh - delete all actuals and repull from invoices
    --incremental   Only process orders without actuals (insert only, no delete)
    --days N        Delete actuals for last N days and repull (by expected pcs_created)

Usage:
    python -m ontrac.scripts.upload_actuals --full
    python -m ontrac.scripts.upload_actuals --incremental
    python -m ontrac.scripts.upload_actuals --incremental --limit 1000
    python -m ontrac.scripts.upload_actuals --days 7
    python -m ontrac.scripts.upload_actuals --full --dry-run
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta

import polars as pl

import shared
from shared.database import pull_data, execute_query, push_data, get_connection


# =============================================================================
# CONFIGURATION
# =============================================================================

EXPECTED_TABLE = "shipping_costs.expected_shipping_costs_ontrac"
ACTUAL_TABLE = "shipping_costs.actual_shipping_costs_ontrac"

SHARED_SQL_DIR = Path(shared.__file__).parent / "sql"
ONTRAC_SQL_DIR = Path(__file__).parent / "sql"

# Date window for matching tracking numbers to invoices
# Prevents wrong matches if tracking numbers are reused over time
DATE_WINDOW_DAYS = 120

# Columns to upload (matches original table order)
UPLOAD_COLUMNS = [
    "pcs_orderid",
    "trackingnumber",
    "invoice_number",
    "billing_date",
    "actual_zone",
    "actual_billed_weight_lbs",
    "actual_base",
    "actual_oml",
    "actual_lps",
    "actual_ahs",
    "actual_das",
    "actual_edas",
    "actual_res",
    "actual_dem_res",
    "actual_dem_ahs",
    "actual_dem_lps",
    "actual_dem_oml",
    "actual_fuel",
    "actual_total",
    "actual_unresolved_address",
    "actual_address_correction",
    "return_to_sender",
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


def get_actual_count_for_orderids(orderids: list[int]) -> int:
    """Get count of actuals for specific orderids."""
    if not orderids:
        return 0
    orderids_str = ", ".join(str(x) for x in orderids)
    query = f"""
        SELECT COUNT(*) as cnt FROM {ACTUAL_TABLE}
        WHERE pcs_orderid IN ({orderids_str})
    """
    try:
        result = pull_data(query)
        return int(result["cnt"][0])
    except Exception:
        return 0


def delete_all_actuals(dry_run: bool = False) -> int:
    """Delete all rows from actual costs table."""
    count = get_actual_row_count()

    if count == 0:
        return 0

    if dry_run:
        print(f"  [DRY RUN] Would delete {count:,} rows from {ACTUAL_TABLE}")
        return count

    print(f"  Deleting {count:,} rows from {ACTUAL_TABLE}...")
    execute_query(f"DELETE FROM {ACTUAL_TABLE}", commit=True)
    print(f"  Deleted {count:,} rows")
    return count


def delete_actuals_for_orderids(orderids: list[int], dry_run: bool = False) -> int:
    """Delete actuals for specific orderids."""
    if not orderids:
        return 0

    count = get_actual_count_for_orderids(orderids)

    if count == 0:
        return 0

    if dry_run:
        print(f"  [DRY RUN] Would delete {count:,} rows for {len(orderids):,} orderids")
        return count

    # Delete in batches to avoid query size limits
    batch_size = 5000
    for i in range(0, len(orderids), batch_size):
        batch = orderids[i:i+batch_size]
        batch_str = ", ".join(str(x) for x in batch)
        delete_query = f"DELETE FROM {ACTUAL_TABLE} WHERE pcs_orderid IN ({batch_str})"
        execute_query(delete_query, commit=True)

    print(f"  Deleted {count:,} rows for {len(orderids):,} orderids")
    return count


# =============================================================================
# DATA RETRIEVAL
# =============================================================================

def get_orderids_from_expected(start_date: str | None = None) -> pl.DataFrame:
    """Get pcs_orderids and ship_dates from expected costs table."""
    query = f"SELECT DISTINCT pcs_orderid, ship_date FROM {EXPECTED_TABLE}"
    if start_date:
        query += f" WHERE pcs_created::date >= '{start_date}'::date"
    return pull_data(query)


def get_orderids_without_actuals(limit: int | None = None) -> pl.DataFrame:
    """Get pcs_orderids without actuals, including ship_date for date-range matching."""
    query = f"""
        SELECT e.pcs_orderid, e.ship_date
        FROM {EXPECTED_TABLE} e
        LEFT JOIN {ACTUAL_TABLE} a ON e.pcs_orderid = a.pcs_orderid
        WHERE a.pcs_orderid IS NULL
    """
    if limit:
        query += f" LIMIT {limit}"
    return pull_data(query)


def get_tracking_numbers(pcs_orderids: list[int]) -> pl.DataFrame:
    """Get tracking numbers for given orderids from PCS."""
    if not pcs_orderids:
        return pl.DataFrame({"pcs_orderid": [], "trackingnumber": []})

    query_template = (SHARED_SQL_DIR / "get_tracking_numbers.sql").read_text()
    pcs_orderids_str = ", ".join(str(x) for x in pcs_orderids)
    query = query_template.format(pcs_orderids=pcs_orderids_str)

    return pull_data(query)


def get_invoice_data(tracking_numbers: list[str]) -> pl.DataFrame:
    """Pull actual costs from OnTrac invoices for given tracking numbers."""
    if not tracking_numbers:
        return pl.DataFrame()

    query_template = (ONTRAC_SQL_DIR / "get_invoice_actuals.sql").read_text()
    tracking_numbers_str = ", ".join(f"'{tn}'" for tn in tracking_numbers)
    query = query_template.format(tracking_numbers=tracking_numbers_str)

    return pull_data(query)


def get_invoice_data_batched(tracking_numbers: list[str], batch_size: int = 5000) -> pl.DataFrame:
    """Pull invoice data in batches to avoid query size limits."""
    if not tracking_numbers:
        return pl.DataFrame()

    all_results = []
    total = len(tracking_numbers)

    for i in range(0, total, batch_size):
        batch = tracking_numbers[i:i+batch_size]
        print(f"    Fetching invoice batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}...")
        df = get_invoice_data(batch)
        if len(df) > 0:
            all_results.append(df)

    if not all_results:
        return pl.DataFrame()

    return pl.concat(all_results)


def join_tracking_with_invoices(
    tracking_df: pl.DataFrame,
    invoice_df: pl.DataFrame,
    orderids_df: pl.DataFrame,
) -> pl.DataFrame:
    """
    Join tracking numbers with invoice data using a date window.

    Matches where billing_date is within DATE_WINDOW_DAYS of ship_date.
    This prevents incorrect matches if tracking numbers are reused over time.

    Args:
        tracking_df: DataFrame with pcs_orderid, trackingnumber
        invoice_df: DataFrame with trackingnumber, billing_date, and cost columns
        orderids_df: DataFrame with pcs_orderid, ship_date

    Returns:
        Merged DataFrame with only matches within the date window
    """
    # Add ship_date to tracking_df via orderids_df
    tracking_with_date = tracking_df.join(
        orderids_df.select(["pcs_orderid", "ship_date"]),
        on="pcs_orderid",
        how="left"
    )

    # Join with invoice data on trackingnumber
    merged = tracking_with_date.join(invoice_df, on="trackingnumber", how="inner")

    # Filter to date window: billing_date between ship_date and ship_date + N days
    merged = merged.filter(
        (pl.col("billing_date") >= pl.col("ship_date")) &
        (pl.col("billing_date") <= pl.col("ship_date") + pl.duration(days=DATE_WINDOW_DAYS))
    )

    # Drop the ship_date column (not needed for upload)
    merged = merged.drop("ship_date")

    return merged


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

    # Step 1: Get all orderids from expected
    print("\nStep 1: Getting orderids from expected costs...")
    orderids_df = get_orderids_from_expected()
    print(f"  Found {len(orderids_df):,} unique orderids")

    if len(orderids_df) == 0:
        print("No orderids found in expected costs table. Nothing to process.")
        return 0

    # Step 2: Get tracking numbers
    print("\nStep 2: Getting tracking numbers...")
    pcs_orderids = orderids_df["pcs_orderid"].to_list()
    tracking_df = get_tracking_numbers(pcs_orderids)
    print(f"  Found {len(tracking_df):,} tracking numbers")

    if len(tracking_df) == 0:
        print("No tracking numbers found. Nothing to process.")
        return 0

    # Step 3: Get invoice data
    print("\nStep 3: Pulling invoice data...")
    tracking_numbers = tracking_df["trackingnumber"].to_list()
    invoice_df = get_invoice_data_batched(tracking_numbers)
    print(f"  Found {len(invoice_df):,} invoice records")

    if len(invoice_df) == 0:
        print("No invoice data found. Nothing to insert.")
        return 0

    # Step 4: Join tracking_df with invoice_df using date window
    print("\nStep 4: Preparing data for upload...")
    merged_df = join_tracking_with_invoices(tracking_df, invoice_df, orderids_df)
    print(f"  {len(merged_df):,} rows matched within {DATE_WINDOW_DAYS}-day window")

    if len(merged_df) == 0:
        print("No invoice data matched within date window. Nothing to insert.")
        return 0

    # Add timestamp
    merged_df = merged_df.with_columns(
        pl.lit(datetime.now()).alias("dw_timestamp")
    )

    # Select columns in order
    merged_df = merged_df.select(UPLOAD_COLUMNS)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Orderids in expected costs: {len(orderids_df):,}")
    print(f"Tracking numbers found: {len(tracking_df):,}")
    print(f"Invoice records matched (within {DATE_WINDOW_DAYS}-day window): {len(merged_df):,}")

    if len(merged_df) > 0:
        total_actual = merged_df["actual_total"].sum()
        avg_actual = merged_df["actual_total"].mean()
        print(f"Total actual cost: ${total_actual:,.2f}")
        print(f"Avg actual cost: ${avg_actual:,.2f}")

    # Step 5: Delete existing and insert fresh
    print("\nStep 5: Refreshing actual costs table...")
    delete_all_actuals(dry_run=dry_run)

    if dry_run:
        print(f"  [DRY RUN] Would insert {len(merged_df):,} rows into {ACTUAL_TABLE}")
        return len(merged_df)

    push_data(merged_df, ACTUAL_TABLE, batch_size=batch_size)
    return len(merged_df)


def run_incremental_mode(
    limit: int | None,
    batch_size: int,
    dry_run: bool,
) -> int:
    """Incremental mode: Only process orders without actuals."""
    print("=" * 60)
    print("INCREMENTAL MODE - ACTUAL COSTS")
    print("=" * 60)

    # Step 1: Get orderids without actuals
    print("\nStep 1: Finding orders without actual costs...")
    orderids_df = get_orderids_without_actuals(limit=limit)
    print(f"  Found {len(orderids_df):,} orders without actuals")

    if len(orderids_df) == 0:
        print("\nAll orders already have actual costs. Nothing to process.")
        return 0

    # Step 2: Get tracking numbers
    print("\nStep 2: Getting tracking numbers...")
    pcs_orderids = orderids_df["pcs_orderid"].to_list()
    tracking_df = get_tracking_numbers(pcs_orderids)
    print(f"  Found {len(tracking_df):,} tracking numbers")

    if len(tracking_df) == 0:
        print("\nNo tracking numbers found. Nothing to process.")
        return 0

    # Step 3: Pull invoice data
    print("\nStep 3: Pulling invoice data...")
    tracking_numbers = tracking_df["trackingnumber"].to_list()
    invoice_df = get_invoice_data_batched(tracking_numbers)
    print(f"  Found {len(invoice_df):,} invoice records")

    if len(invoice_df) == 0:
        print("\nNo invoice data found. Nothing to insert.")
        return 0

    # Step 4: Join tracking_df with invoice_df using date window
    print("\nStep 4: Preparing data for upload...")
    merged_df = join_tracking_with_invoices(tracking_df, invoice_df, orderids_df)
    print(f"  {len(merged_df):,} rows matched within {DATE_WINDOW_DAYS}-day window")

    if len(merged_df) == 0:
        print("\nNo invoice data matched within date window. Nothing to insert.")
        return 0

    # Add timestamp
    merged_df = merged_df.with_columns(
        pl.lit(datetime.now()).alias("dw_timestamp")
    )

    # Select columns in order
    merged_df = merged_df.select(UPLOAD_COLUMNS)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Orders without actuals: {len(orderids_df):,}")
    print(f"Tracking numbers found: {len(tracking_df):,}")
    print(f"Invoice records matched (within {DATE_WINDOW_DAYS}-day window): {len(merged_df):,}")

    if len(merged_df) > 0:
        total_actual = merged_df["actual_total"].sum()
        avg_actual = merged_df["actual_total"].mean()
        print(f"Total actual cost: ${total_actual:,.2f}")
        print(f"Avg actual cost: ${avg_actual:,.2f}")

    # Step 5: Insert
    print("\nStep 5: Uploading to database...")

    if dry_run:
        print(f"  [DRY RUN] Would insert {len(merged_df):,} rows into {ACTUAL_TABLE}")
        return len(merged_df)

    push_data(merged_df, ACTUAL_TABLE, batch_size=batch_size)
    return len(merged_df)


def run_days_mode(
    days: int,
    batch_size: int,
    dry_run: bool,
) -> int:
    """Days mode: Delete and repull actuals for last N days."""
    print("=" * 60)
    print(f"DAYS MODE ({days} days) - ACTUAL COSTS")
    print("=" * 60)

    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    # Step 1: Get orderids for date range
    print(f"\nStep 1: Getting orderids from {start_date} onwards...")
    orderids_df = get_orderids_from_expected(start_date=start_date)
    print(f"  Found {len(orderids_df):,} unique orderids")

    if len(orderids_df) == 0:
        print("No orderids found for date range. Nothing to process.")
        return 0

    pcs_orderids = orderids_df["pcs_orderid"].to_list()

    # Step 2: Delete existing actuals for these orderids
    print(f"\nStep 2: Deleting existing actuals for {len(pcs_orderids):,} orderids...")
    deleted = delete_actuals_for_orderids(pcs_orderids, dry_run=dry_run)

    # Step 3: Get tracking numbers
    print("\nStep 3: Getting tracking numbers...")
    tracking_df = get_tracking_numbers(pcs_orderids)
    print(f"  Found {len(tracking_df):,} tracking numbers")

    if len(tracking_df) == 0:
        print("No tracking numbers found. Nothing to process.")
        return 0

    # Step 4: Get invoice data
    print("\nStep 4: Pulling invoice data...")
    tracking_numbers = tracking_df["trackingnumber"].to_list()
    invoice_df = get_invoice_data_batched(tracking_numbers)
    print(f"  Found {len(invoice_df):,} invoice records")

    if len(invoice_df) == 0:
        print("No invoice data found. Nothing to insert.")
        return 0

    # Step 5: Join and prepare using date window
    print("\nStep 5: Preparing data for upload...")
    merged_df = join_tracking_with_invoices(tracking_df, invoice_df, orderids_df)
    print(f"  {len(merged_df):,} rows matched within {DATE_WINDOW_DAYS}-day window")

    if len(merged_df) == 0:
        print("\nNo invoice data matched within date window. Nothing to insert.")
        return 0

    # Add timestamp
    merged_df = merged_df.with_columns(
        pl.lit(datetime.now()).alias("dw_timestamp")
    )

    # Select columns in order
    merged_df = merged_df.select(UPLOAD_COLUMNS)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Date range: {start_date} to today ({days} days)")
    print(f"Orderids in range: {len(orderids_df):,}")
    print(f"Rows deleted: {deleted:,}")
    print(f"Tracking numbers found: {len(tracking_df):,}")
    print(f"Invoice records matched (within {DATE_WINDOW_DAYS}-day window): {len(merged_df):,}")

    if len(merged_df) > 0:
        total_actual = merged_df["actual_total"].sum()
        avg_actual = merged_df["actual_total"].mean()
        print(f"Total actual cost: ${total_actual:,.2f}")
        print(f"Avg actual cost: ${avg_actual:,.2f}")

    # Step 6: Insert
    print("\nStep 6: Uploading to database...")

    if dry_run:
        print(f"  [DRY RUN] Would insert {len(merged_df):,} rows into {ACTUAL_TABLE}")
        return len(merged_df)

    push_data(merged_df, ACTUAL_TABLE, batch_size=batch_size)
    return len(merged_df)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Upload actual OnTrac invoice costs to database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  --full          Full refresh - delete all actuals and repull from invoices
  --incremental   Only process orders without actuals (insert only)
  --days N        Delete actuals for last N days and repull (by expected pcs_created)

Examples:
  python -m ontrac.scripts.upload_actuals --full
  python -m ontrac.scripts.upload_actuals --incremental
  python -m ontrac.scripts.upload_actuals --incremental --limit 1000
  python -m ontrac.scripts.upload_actuals --days 7
  python -m ontrac.scripts.upload_actuals --full --dry-run
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
        help="Only process orders without actuals (insert only)"
    )
    mode_group.add_argument(
        "--days",
        type=int,
        metavar="N",
        help="Delete actuals for last N days and repull (by expected pcs_created)"
    )

    # Common options
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Number of rows per INSERT statement (default: 5000)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit orderids to process (for --incremental mode)"
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
                limit=args.limit,
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
            print(f"[DRY RUN] Would have inserted {rows:,} rows into {ACTUAL_TABLE}")
        else:
            print(f"Successfully inserted {rows:,} rows into {ACTUAL_TABLE}")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        raise


if __name__ == "__main__":
    main()
