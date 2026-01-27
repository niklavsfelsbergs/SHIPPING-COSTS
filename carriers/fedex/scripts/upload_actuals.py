"""
Upload Actual Costs to Database
===============================

Loads FedEx invoice data and uploads actual costs to the database.

Modes:
    --full          Full refresh - delete all actuals and repull from invoices
    --incremental   Only process orders without actuals (insert only)
    --days N        Delete and repull actuals for last N days

Usage:
    python -m carriers.fedex.scripts.upload_actuals --full
    python -m carriers.fedex.scripts.upload_actuals --incremental
    python -m carriers.fedex.scripts.upload_actuals --incremental --limit 1000
    python -m carriers.fedex.scripts.upload_actuals --days 30
    python -m carriers.fedex.scripts.upload_actuals --full --dry-run
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl

from shared.database import pull_data, execute_query, push_data
from carriers.fedex.data.reference.charge_mapping import (
    CHARGE_MAPPING,
    DEFAULT_COLUMN,
    ACTUAL_COLUMNS,
)


# =============================================================================
# CONFIGURATION
# =============================================================================

TABLE_NAME = "shipping_costs.actual_shipping_costs_fedex"
EXPECTED_TABLE = "shipping_costs.expected_shipping_costs_fedex"
DATE_WINDOW_DAYS = 120  # Match invoice to shipment within this window

SQL_DIR = Path(__file__).parent / "sql"

# Columns to upload (matches DDL order)
UPLOAD_COLUMNS = [
    # Identification
    "pcs_orderid", "trackingnumber", "invoice_number", "invoice_date",
    # Shipment info
    "shipment_date", "service_type", "actual_zone",
    "actual_weight_lbs", "rated_weight_lbs",
    # Expected charges
    "actual_base", "actual_ahs", "actual_ahs_weight", "actual_das",
    "actual_residential", "actual_oversize",
    "actual_dem_base", "actual_dem_ahs", "actual_dem_oversize", "actual_dem_residential",
    "actual_fuel",
    # Discounts
    "actual_performance_pricing", "actual_earned_discount",
    "actual_grace_discount", "actual_discount",
    # Unpredictable
    "actual_unpredictable",
    # Totals
    "actual_net_charge", "actual_transportation",
    # Metadata
    "dw_timestamp",
]


# =============================================================================
# DATABASE HELPERS
# =============================================================================

def get_orderids_without_actuals(limit: int | None = None) -> list[int]:
    """Get orderids from expected table that don't have actuals yet."""
    limit_clause = f"LIMIT {limit}" if limit else ""
    query = f"""
        SELECT DISTINCT e.pcs_orderid
        FROM {EXPECTED_TABLE} e
        LEFT JOIN {TABLE_NAME} a ON e.pcs_orderid = a.pcs_orderid
        WHERE a.pcs_orderid IS NULL
        {limit_clause}
    """
    result = pull_data(query)
    return result["pcs_orderid"].to_list() if len(result) > 0 else []


def get_orderids_from_expected(start_date: str | None = None) -> list[int]:
    """Get all orderids from expected table, optionally filtered by date."""
    date_filter = f"WHERE pcs_created::date >= '{start_date}'::date" if start_date else ""
    query = f"""
        SELECT DISTINCT pcs_orderid
        FROM {EXPECTED_TABLE}
        {date_filter}
    """
    result = pull_data(query)
    return result["pcs_orderid"].to_list() if len(result) > 0 else []


def get_tracking_numbers(orderids: list[int]) -> pl.DataFrame:
    """Get tracking numbers for given orderids from PCS."""
    if not orderids:
        return pl.DataFrame()

    # Batch to avoid query size limits
    all_results = []
    batch_size = 5000
    for i in range(0, len(orderids), batch_size):
        batch = orderids[i:i + batch_size]
        ids_str = ", ".join(str(oid) for oid in batch)
        query = f"""
            SELECT orderid AS pcs_orderid, trackingnumber
            FROM bi_stage_dev_dbo.pcsu_sentparcels
            WHERE orderid IN ({ids_str})
        """
        result = pull_data(query)
        if len(result) > 0:
            all_results.append(result)

    if not all_results:
        return pl.DataFrame()

    return pl.concat(all_results)


def get_ship_dates(orderids: list[int]) -> pl.DataFrame:
    """Get ship dates for given orderids from expected table."""
    if not orderids:
        return pl.DataFrame()

    batch_size = 5000
    all_results = []
    for i in range(0, len(orderids), batch_size):
        batch = orderids[i:i + batch_size]
        ids_str = ", ".join(str(oid) for oid in batch)
        query = f"""
            SELECT pcs_orderid, ship_date
            FROM {EXPECTED_TABLE}
            WHERE pcs_orderid IN ({ids_str})
        """
        result = pull_data(query)
        if len(result) > 0:
            all_results.append(result)

    if not all_results:
        return pl.DataFrame()

    return pl.concat(all_results).unique(subset=["pcs_orderid"])


def get_row_count() -> int:
    """Get total row count in the actuals table."""
    query = f"SELECT COUNT(*) as cnt FROM {TABLE_NAME}"
    try:
        result = pull_data(query)
        return int(result["cnt"][0])
    except Exception:
        return 0


def get_row_count_for_orderids(orderids: list[int]) -> int:
    """Get count of rows for specific orderids."""
    if not orderids:
        return 0

    batch_size = 5000
    total = 0
    for i in range(0, len(orderids), batch_size):
        batch = orderids[i:i + batch_size]
        ids_str = ", ".join(str(oid) for oid in batch)
        query = f"SELECT COUNT(*) as cnt FROM {TABLE_NAME} WHERE pcs_orderid IN ({ids_str})"
        try:
            result = pull_data(query)
            total += int(result["cnt"][0])
        except Exception:
            pass
    return total


def delete_all(dry_run: bool = False) -> int:
    """Delete all rows from the actuals table."""
    count = get_row_count()

    if count == 0:
        return 0

    if dry_run:
        print(f"  [DRY RUN] Would delete {count:,} rows")
        return count

    execute_query(f"DELETE FROM {TABLE_NAME}", commit=True)
    print(f"  Deleted {count:,} rows")
    return count


def delete_for_orderids(orderids: list[int], dry_run: bool = False) -> int:
    """Delete rows for specific orderids."""
    if not orderids:
        return 0

    count = get_row_count_for_orderids(orderids)

    if count == 0:
        return 0

    if dry_run:
        print(f"  [DRY RUN] Would delete {count:,} rows for {len(orderids):,} orders")
        return count

    # Batch deletions
    batch_size = 5000
    for i in range(0, len(orderids), batch_size):
        batch = orderids[i:i + batch_size]
        ids_str = ", ".join(str(oid) for oid in batch)
        execute_query(f"DELETE FROM {TABLE_NAME} WHERE pcs_orderid IN ({ids_str})", commit=True)

    print(f"  Deleted {count:,} rows for {len(orderids):,} orders")
    return count


# =============================================================================
# INVOICE DATA PROCESSING
# =============================================================================

def load_invoice_data(tracking_numbers: list[str], start_date: str | None = None) -> pl.DataFrame:
    """Load invoice data for given tracking numbers."""
    if not tracking_numbers:
        return pl.DataFrame()

    sql_template = (SQL_DIR / "get_invoice_actuals.sql").read_text()

    # Build date filter
    date_filter = ""
    if start_date:
        date_filter = f"AND invoice_date::date >= '{start_date}'::date"

    all_results = []
    batch_size = 5000

    for i in range(0, len(tracking_numbers), batch_size):
        batch = tracking_numbers[i:i + batch_size]
        # Escape single quotes in tracking numbers
        escaped = [str(tn).replace("'", "''") for tn in batch]
        tracking_list = ", ".join(f"'{tn}'" for tn in escaped)
        tracking_filter = f"AND trackingnumber IN ({tracking_list})"

        query = sql_template.format(
            date_filter=date_filter,
            tracking_numbers_filter=tracking_filter,
        )

        result = pull_data(query)
        if len(result) > 0:
            all_results.append(result)

    if not all_results:
        return pl.DataFrame()

    return pl.concat(all_results)


def map_and_pivot_charges(invoice_df: pl.DataFrame) -> pl.DataFrame:
    """
    Map charge descriptions to actual columns and pivot to one row per shipment.

    Input: Unpivoted charges (multiple rows per tracking number)
    Output: One row per tracking number with all actual_* columns
    """
    if len(invoice_df) == 0:
        return pl.DataFrame()

    # Map charge_description to actual column
    invoice_df = invoice_df.with_columns(
        pl.col("charge_description")
        .replace_strict(CHARGE_MAPPING, default=DEFAULT_COLUMN)
        .alias("actual_column")
    )

    # Group by tracking number and shipment info, pivot charges to columns
    group_cols = [
        "trackingnumber", "invoice_number", "invoice_date", "shipment_date",
        "service_type", "ground_service", "shipping_zone",
        "actual_weight", "actual_weight_units", "rated_weight", "rated_weight_units",
        "net_charge_usd", "transportation_charge_usd",
    ]

    # Pivot: sum charges by actual_column
    pivoted = (
        invoice_df
        .group_by(group_cols + ["actual_column"])
        .agg(pl.col("charge_amount").sum().alias("amount"))
        .pivot(
            on="actual_column",
            index=group_cols,
            values="amount",
        )
    )

    # Ensure all actual columns exist (fill missing with 0)
    for col in ACTUAL_COLUMNS:
        if col not in pivoted.columns:
            pivoted = pivoted.with_columns(pl.lit(0.0).alias(col))

    # Rename columns to match expected names
    pivoted = pivoted.rename({
        "shipping_zone": "actual_zone",
        "net_charge_usd": "actual_net_charge",
        "transportation_charge_usd": "actual_transportation",
    })

    # Convert weights to lbs if needed (cast from string first)
    pivoted = pivoted.with_columns([
        pl.when(pl.col("actual_weight_units") == "K")
        .then(pl.col("actual_weight").cast(pl.Float64) * 2.20462)
        .otherwise(pl.col("actual_weight").cast(pl.Float64))
        .alias("actual_weight_lbs"),

        pl.when(pl.col("rated_weight_units") == "K")
        .then(pl.col("rated_weight").cast(pl.Float64) * 2.20462)
        .otherwise(pl.col("rated_weight").cast(pl.Float64))
        .alias("rated_weight_lbs"),
    ])

    # Drop intermediate columns
    drop_cols = ["actual_weight", "actual_weight_units", "rated_weight", "rated_weight_units", "ground_service"]
    pivoted = pivoted.drop([c for c in drop_cols if c in pivoted.columns])

    return pivoted


def join_with_pcs(
    invoice_df: pl.DataFrame,
    tracking_df: pl.DataFrame,
    ship_dates_df: pl.DataFrame,
) -> pl.DataFrame:
    """
    Join invoice data with PCS data, validating date window.

    Args:
        invoice_df: Pivoted invoice data with actual charges
        tracking_df: PCS orderid -> tracking number mapping
        ship_dates_df: PCS orderid -> ship_date mapping

    Returns:
        DataFrame ready for upload with pcs_orderid
    """
    if len(invoice_df) == 0 or len(tracking_df) == 0:
        return pl.DataFrame()

    # Join tracking numbers to get pcs_orderid
    joined = invoice_df.join(
        tracking_df,
        on="trackingnumber",
        how="inner",
    )

    if len(joined) == 0:
        return pl.DataFrame()

    # Join ship dates for date window validation
    joined = joined.join(
        ship_dates_df,
        on="pcs_orderid",
        how="left",
    )

    # Filter by date window: invoice_date should be within DATE_WINDOW_DAYS of ship_date
    joined = joined.filter(
        (pl.col("invoice_date") >= pl.col("ship_date")) &
        (pl.col("invoice_date") <= pl.col("ship_date") + pl.duration(days=DATE_WINDOW_DAYS))
    )

    # Drop ship_date (used only for filtering)
    joined = joined.drop("ship_date")

    return joined


# =============================================================================
# PIPELINE
# =============================================================================

def run_pipeline(
    orderids: list[int],
    start_date: str | None = None,
) -> pl.DataFrame:
    """
    Run the full actuals pipeline for given orderids.

    Returns DataFrame ready for upload with UPLOAD_COLUMNS.
    """
    if not orderids:
        return pl.DataFrame()

    # Step 1: Get tracking numbers
    print(f"  Getting tracking numbers for {len(orderids):,} orders...")
    tracking_df = get_tracking_numbers(orderids)
    if len(tracking_df) == 0:
        print("  No tracking numbers found")
        return pl.DataFrame()
    print(f"  Found {len(tracking_df):,} tracking numbers")

    # Step 2: Get ship dates for date window validation
    print("  Getting ship dates...")
    ship_dates_df = get_ship_dates(orderids)

    # Step 3: Load invoice data
    tracking_numbers = tracking_df["trackingnumber"].unique().to_list()
    print(f"  Loading invoice data for {len(tracking_numbers):,} tracking numbers...")
    invoice_df = load_invoice_data(tracking_numbers, start_date)
    if len(invoice_df) == 0:
        print("  No invoice data found")
        return pl.DataFrame()
    print(f"  Found {len(invoice_df):,} charge records")

    # Step 4: Map charges and pivot
    print("  Mapping charges and pivoting...")
    pivoted_df = map_and_pivot_charges(invoice_df)
    if len(pivoted_df) == 0:
        print("  No data after pivot")
        return pl.DataFrame()
    print(f"  Pivoted to {len(pivoted_df):,} shipment records")

    # Step 5: Join with PCS
    print("  Joining with PCS data...")
    joined_df = join_with_pcs(pivoted_df, tracking_df, ship_dates_df)
    if len(joined_df) == 0:
        print("  No data after join")
        return pl.DataFrame()
    print(f"  Matched {len(joined_df):,} shipments")

    # Step 6: Add timestamp and select columns
    joined_df = joined_df.with_columns(
        pl.lit(datetime.now()).alias("dw_timestamp")
    )

    # Ensure all upload columns exist
    for col in UPLOAD_COLUMNS:
        if col not in joined_df.columns:
            joined_df = joined_df.with_columns(pl.lit(None).alias(col))

    return joined_df.select(UPLOAD_COLUMNS)


# =============================================================================
# MODE HANDLERS
# =============================================================================

def run_full_mode(batch_size: int, dry_run: bool) -> int:
    """Full mode: Delete all actuals, repull from invoices."""
    print("=" * 60)
    print("FULL MODE - ACTUAL COSTS")
    print("=" * 60)

    print("\nStep 1: Getting all orderids from expected table...")
    orderids = get_orderids_from_expected()
    print(f"  Found {len(orderids):,} orders")

    if not orderids:
        print("\nNo orders found in expected table.")
        return 0

    print("\nStep 2: Deleting all existing actuals...")
    deleted = delete_all(dry_run=dry_run)

    print("\nStep 3: Processing invoice data...")
    df = run_pipeline(orderids)

    if len(df) == 0:
        print("\nNo invoice data found.")
        return 0

    # Print summary
    print("\n" + "=" * 60)
    print("UPLOAD SUMMARY")
    print("=" * 60)
    print(f"Rows deleted: {deleted:,}")
    print(f"New rows to upload: {len(df):,}")
    print(f"Total actual cost: ${df['actual_net_charge'].sum():,.2f}")

    if dry_run:
        print(f"\n[DRY RUN] Would upload to: {TABLE_NAME}")
        return len(df)

    # Upload
    print(f"\nStep 4: Uploading to {TABLE_NAME}...")
    push_data(df, TABLE_NAME, batch_size=batch_size)

    return len(df)


def run_incremental_mode(limit: int | None, batch_size: int, dry_run: bool) -> int:
    """Incremental mode: Only process orders without actuals."""
    print("=" * 60)
    print("INCREMENTAL MODE - ACTUAL COSTS")
    print("=" * 60)

    print("\nStep 1: Finding orders without actuals...")
    orderids = get_orderids_without_actuals(limit=limit)
    print(f"  Found {len(orderids):,} orders without actuals")

    if not orderids:
        print("\nAll orders already have actuals.")
        return 0

    print("\nStep 2: Processing invoice data...")
    df = run_pipeline(orderids)

    if len(df) == 0:
        print("\nNo invoice data found for these orders.")
        return 0

    # Print summary
    print("\n" + "=" * 60)
    print("UPLOAD SUMMARY")
    print("=" * 60)
    print(f"Orders processed: {len(orderids):,}")
    print(f"New rows to upload: {len(df):,}")
    print(f"Total actual cost: ${df['actual_net_charge'].sum():,.2f}")

    if dry_run:
        print(f"\n[DRY RUN] Would upload to: {TABLE_NAME}")
        return len(df)

    # Upload
    print(f"\nStep 3: Uploading to {TABLE_NAME}...")
    push_data(df, TABLE_NAME, batch_size=batch_size)

    return len(df)


def run_days_mode(days: int, batch_size: int, dry_run: bool) -> int:
    """Days mode: Delete and repull actuals for last N days."""
    print("=" * 60)
    print(f"DAYS MODE ({days} days) - ACTUAL COSTS")
    print("=" * 60)

    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    print(f"\nStep 1: Getting orderids from {start_date} onwards...")
    orderids = get_orderids_from_expected(start_date=start_date)
    print(f"  Found {len(orderids):,} orders")

    if not orderids:
        print("\nNo orders found for this date range.")
        return 0

    print(f"\nStep 2: Deleting existing actuals for these orders...")
    deleted = delete_for_orderids(orderids, dry_run=dry_run)

    print(f"\nStep 3: Processing invoice data...")
    df = run_pipeline(orderids, start_date=start_date)

    if len(df) == 0:
        print("\nNo invoice data found.")
        return 0

    # Print summary
    print("\n" + "=" * 60)
    print("UPLOAD SUMMARY")
    print("=" * 60)
    print(f"Rows deleted: {deleted:,}")
    print(f"New rows to upload: {len(df):,}")
    print(f"Net change: {len(df) - deleted:+,}")
    print(f"Date range: {start_date} to today ({days} days)")
    print(f"Total actual cost: ${df['actual_net_charge'].sum():,.2f}")

    if dry_run:
        print(f"\n[DRY RUN] Would upload to: {TABLE_NAME}")
        return len(df)

    # Upload
    print(f"\nStep 4: Uploading to {TABLE_NAME}...")
    push_data(df, TABLE_NAME, batch_size=batch_size)

    return len(df)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Upload actual FedEx shipping costs to database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  --full          Full refresh - delete all actuals and repull from invoices
  --incremental   Only process orders without actuals (insert only)
  --days N        Delete and repull actuals for last N days

Examples:
  python -m carriers.fedex.scripts.upload_actuals --full
  python -m carriers.fedex.scripts.upload_actuals --incremental
  python -m carriers.fedex.scripts.upload_actuals --incremental --limit 1000
  python -m carriers.fedex.scripts.upload_actuals --days 30
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
        help="Only process orders without actuals (insert only)"
    )
    mode_group.add_argument(
        "--days",
        type=int,
        metavar="N",
        help="Delete and repull actuals for last N days"
    )

    # Common options
    parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        help="Limit number of orders to process (incremental mode only)"
    )
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
