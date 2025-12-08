"""
Generate Updated Zones File
============================

Analyzes actual invoice data to determine the most common zone
for each ZIP code and production site combination.

This script:
1. Loads invoice data with actual zones from OnTrac
2. Calculates the mode (most common) zone per ZIP + production site
3. Merges with existing zones file (keeps original where no invoice data)
4. Archives the current zones file before overwriting
5. Outputs an updated zones file

Usage:
    python -m ontrac.maintenance.generate_zones
    python -m ontrac.maintenance.generate_zones --start-date 2025-01-01
    python -m ontrac.maintenance.generate_zones --start-date 2025-01-01 --end-date 2025-06-30
"""

import argparse
import shutil
from datetime import datetime
from pathlib import Path

import polars as pl

from shared.database import pull_data
from ontrac.data import load_zones, DATA_DIR


SQL_FILE = Path(__file__).parent / "sql" / "zone_analysis.sql"
ZONES_FILE = DATA_DIR / "zones.csv"
ARCHIVE_DIR = DATA_DIR / "archive"


def load_invoice_data(start_date: str | None = None, end_date: str | None = None) -> pl.DataFrame:
    """Load zone data from invoices joined with PCS."""
    # Build date filter
    filter_parts = []
    if start_date:
        filter_parts.append(f"and po.createddate >= '{start_date}'")
    if end_date:
        filter_parts.append(f"and po.createddate <= '{end_date}'")
    created_filter = "\n    ".join(filter_parts)

    # Load and format SQL
    sql_template = SQL_FILE.read_text()
    query = sql_template.format(created_filter=created_filter)

    date_range = ""
    if start_date and end_date:
        date_range = f" ({start_date} to {end_date})"
    elif start_date:
        date_range = f" (from {start_date})"
    elif end_date:
        date_range = f" (until {end_date})"
    else:
        date_range = " (all time)"

    print(f"Loading zone analysis data from database{date_range}...")
    df = pull_data(query)
    print(f"  Loaded {len(df):,} records")
    return df


def calculate_mode_zones(df: pl.DataFrame) -> pl.DataFrame:
    """
    Calculate the most common zone for each ZIP + production site.

    Returns DataFrame with:
        - zip_code, shipping_state
        - phx_zone (mode zone for Phoenix)
        - cmh_zone (mode zone for Columbus)
        - das (most common DAS classification)
    """
    print("\nCalculating mode zones per ZIP code and production site...")

    # Normalize ZIP codes
    df = df.with_columns(
        pl.col("shipping_zip_code")
        .cast(pl.Utf8)
        .str.slice(0, 5)
        .str.zfill(5)
        .alias("zip_code")
    )

    # Determine DAS status from charges
    df = df.with_columns(
        pl.when(pl.col("edas_charge") > 0)
        .then(pl.lit("EDAS"))
        .when(pl.col("das_charge") > 0)
        .then(pl.lit("DAS"))
        .otherwise(pl.lit("NO"))
        .alias("das_status")
    )

    # Calculate mode zone per ZIP + production site
    # Use explicit counting for deterministic tie-breaking (lowest zone/DAS wins)
    group_cols = ["zip_code", "shipping_region", "production_site"]

    # Mode zone: count occurrences, sort by count desc then zone asc, take first
    zone_counts = (
        df.group_by(group_cols + ["actual_zone"])
        .agg(pl.len().alias("_count"))
        .sort(group_cols + ["_count", "actual_zone"], descending=[False, False, False, True, False])
    )
    zone_mode = (
        zone_counts
        .group_by(group_cols)
        .first()
        .select(group_cols + [pl.col("actual_zone").alias("mode_zone")])
    )

    # Mode DAS: same approach
    das_counts = (
        df.group_by(group_cols + ["das_status"])
        .agg(pl.len().alias("_count"))
        .sort(group_cols + ["_count", "das_status"], descending=[False, False, False, True, False])
    )
    das_mode = (
        das_counts
        .group_by(group_cols)
        .first()
        .select(group_cols + [pl.col("das_status").alias("mode_das")])
    )

    # Shipment counts
    shipment_counts = (
        df.group_by(group_cols)
        .agg(pl.len().alias("shipment_count"))
    )

    # Join all together
    zone_by_site = (
        zone_mode
        .join(das_mode, on=group_cols)
        .join(shipment_counts, on=group_cols)
    )

    # Pivot to get phx_zone and cmh_zone columns
    phoenix_zones = (
        zone_by_site
        .filter(pl.col("production_site") == "Phoenix")
        .select([
            pl.col("zip_code"),
            pl.col("shipping_region"),
            pl.col("mode_zone").alias("phx_zone"),
            pl.col("mode_das").alias("phx_das"),
            pl.col("shipment_count").alias("phx_count"),
        ])
    )

    columbus_zones = (
        zone_by_site
        .filter(pl.col("production_site") == "Columbus")
        .select([
            pl.col("zip_code"),
            pl.col("shipping_region"),
            pl.col("mode_zone").alias("cmh_zone"),
            pl.col("mode_das").alias("cmh_das"),
            pl.col("shipment_count").alias("cmh_count"),
        ])
    )

    print(f"  Phoenix ZIP codes: {phoenix_zones.height:,}")
    print(f"  Columbus ZIP codes: {columbus_zones.height:,}")

    # Full outer join to combine both sites
    combined = phoenix_zones.join(
        columbus_zones,
        on=["zip_code", "shipping_region"],
        how="full",
        coalesce=True
    )

    # Fill nulls for counts
    combined = combined.with_columns([
        pl.coalesce(["phx_count", pl.lit(0)]).alias("phx_count"),
        pl.coalesce(["cmh_count", pl.lit(0)]).alias("cmh_count"),
    ])

    # Determine final DAS (prefer the one with more shipments)
    combined = combined.with_columns(
        pl.when(pl.col("phx_count") >= pl.col("cmh_count"))
        .then(pl.col("phx_das"))
        .otherwise(pl.col("cmh_das"))
        .alias("das")
    )

    # Select final columns
    result = combined.select([
        pl.col("zip_code"),
        pl.coalesce(["das", pl.lit("NO")]).alias("das"),
        pl.col("shipping_region").alias("shipping_state"),
        pl.col("phx_zone").cast(pl.Int64),
        pl.col("cmh_zone").cast(pl.Int64),
        (pl.col("phx_count") + pl.col("cmh_count")).alias("total_shipments"),
    ])

    print(f"  Total unique ZIP codes: {result.height:,}")

    return result.sort("zip_code")


def merge_zones(original: pl.DataFrame, updated: pl.DataFrame) -> pl.DataFrame:
    """
    Merge updated zones with original, keeping original values where no invoice data exists.

    For each ZIP code:
    - If we have invoice data for a site, use the mode zone from invoices
    - If we don't have invoice data, keep the original zone
    """
    print("\nMerging updated zones with original file...")

    # Rename updated columns to avoid conflicts during join
    # Deduplicate by zip_code, keeping the row with most shipments
    updated_renamed = (
        updated
        .sort("total_shipments", descending=True)
        .unique(subset=["zip_code"], keep="first")
        .select([
            pl.col("zip_code"),
            pl.col("das").alias("_updated_das"),
            pl.col("phx_zone").alias("_updated_phx_zone"),
            pl.col("cmh_zone").alias("_updated_cmh_zone"),
        ])
    )

    # Left join original with updated (keep all original ZIP codes)
    merged = original.join(
        updated_renamed,
        on="zip_code",
        how="left"
    )

    # Count actual changes (where updated value differs from original)
    phx_changed = merged.filter(
        pl.col("_updated_phx_zone").is_not_null() &
        (pl.col("_updated_phx_zone") != pl.col("phx_zone"))
    ).height
    cmh_changed = merged.filter(
        pl.col("_updated_cmh_zone").is_not_null() &
        (pl.col("_updated_cmh_zone") != pl.col("cmh_zone"))
    ).height
    das_changed = merged.filter(
        pl.col("_updated_das").is_not_null() &
        (pl.col("_updated_das") != pl.col("das"))
    ).height

    print(f"  Phoenix zones changed: {phx_changed:,} / {merged.height:,}")
    print(f"  Columbus zones changed: {cmh_changed:,} / {merged.height:,}")
    print(f"  DAS classifications changed: {das_changed:,} / {merged.height:,}")

    # Coalesce: use updated value if available, otherwise keep original
    merged = merged.with_columns([
        pl.coalesce(["_updated_phx_zone", "phx_zone"]).alias("phx_zone"),
        pl.coalesce(["_updated_cmh_zone", "cmh_zone"]).alias("cmh_zone"),
        pl.coalesce(["_updated_das", "das"]).alias("das"),
    ])

    # Select final columns in original order
    result = merged.select([
        "zip_code",
        "shipping_state",
        pl.col("phx_zone").cast(pl.Int64),
        pl.col("cmh_zone").cast(pl.Int64),
        "das",
    ])

    return result


def archive_zones_file():
    """Archive the current zones file with a timestamp."""
    if not ZONES_FILE.exists():
        print("No existing zones file to archive")
        return None

    ARCHIVE_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d")
    archive_name = f"zones_{timestamp}.csv"
    archive_path = ARCHIVE_DIR / archive_name

    # If archive already exists for today, add a counter
    counter = 1
    while archive_path.exists():
        archive_name = f"zones_{timestamp}_{counter}.csv"
        archive_path = ARCHIVE_DIR / archive_name
        counter += 1

    shutil.copy(ZONES_FILE, archive_path)
    print(f"Archived current zones file to: {archive_path}")
    return archive_path


def print_summary(zones: pl.DataFrame, shipment_count: int):
    """Print summary statistics."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print(f"\nTotal ZIP codes: {zones.height:,}")
    print(f"Total shipments analyzed: {shipment_count:,}")

    # Zone distribution for Phoenix
    phx_zones = zones.filter(pl.col("phx_zone").is_not_null())
    print(f"\nPhoenix zone coverage: {phx_zones.height:,} ZIP codes")
    phx_dist = phx_zones.group_by("phx_zone").agg(pl.len().alias("count")).sort("phx_zone")
    for row in phx_dist.iter_rows(named=True):
        print(f"  Zone {row['phx_zone']}: {row['count']:,} ZIPs")

    # Zone distribution for Columbus
    cmh_zones = zones.filter(pl.col("cmh_zone").is_not_null())
    print(f"\nColumbus zone coverage: {cmh_zones.height:,} ZIP codes")
    cmh_dist = cmh_zones.group_by("cmh_zone").agg(pl.len().alias("count")).sort("cmh_zone")
    for row in cmh_dist.iter_rows(named=True):
        print(f"  Zone {row['cmh_zone']}: {row['count']:,} ZIPs")

    # DAS distribution
    print("\nDAS classification:")
    das_dist = zones.group_by("das").agg(pl.len().alias("count")).sort("das")
    for row in das_dist.iter_rows(named=True):
        print(f"  {row['das']}: {row['count']:,} ZIPs")


def generate_updated_zones(start_date: str | None = None, end_date: str | None = None):
    """Main function to generate the updated zones file."""
    # Load original zones
    print(f"Loading original zones file: {ZONES_FILE}")
    original = load_zones()
    print(f"  Original file has {original.height:,} ZIP codes")

    # Load invoice data
    invoice_df = load_invoice_data(start_date, end_date)
    print(invoice_df)

    # Calculate mode zones from invoices
    updated = calculate_mode_zones(invoice_df)

    # Merge: updated values where available, original values otherwise
    zones = merge_zones(original, updated)

    # Archive existing zones file before overwriting
    print()
    archive_zones_file()

    # Save updated zones
    zones.write_csv(ZONES_FILE)
    print(f"Saved updated zones file to: {ZONES_FILE}")
    print(f"  Final shape: {zones.height:,} rows x {zones.width} columns")

    # Print summary
    print_summary(zones, len(invoice_df))

    return zones


def main():
    parser = argparse.ArgumentParser(
        description="Generate updated zones file from invoice data"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Filter shipments created on or after this date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="Filter shipments created on or before this date (YYYY-MM-DD)"
    )
    args = parser.parse_args()

    generate_updated_zones(start_date=args.start_date, end_date=args.end_date)


if __name__ == "__main__":
    main()
