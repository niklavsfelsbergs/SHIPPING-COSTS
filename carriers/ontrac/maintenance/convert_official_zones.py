"""
Convert Official OnTrac Zones to zones.csv
==========================================

Converts the official OnTrac_Zones.xlsx file to the zones.csv format
used by the calculator.

Usage:
    python -m carriers.ontrac.maintenance.convert_official_zones
"""

import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
import polars as pl

CONTRACTS_DIR = Path(__file__).parent.parent / "data" / "reference" / "contracts" / "current"
REFERENCE_DIR = Path(__file__).parent.parent / "data" / "reference"
ARCHIVE_DIR = REFERENCE_DIR / "archive"

ZONES_FILE = REFERENCE_DIR / "zones.csv"
OFFICIAL_ZONES_FILE = CONTRACTS_DIR / "OnTrac_Zones.xlsx"


def archive_current_zones():
    """Archive the current zones file with a timestamp."""
    if not ZONES_FILE.exists():
        print("No existing zones file to archive")
        return None

    ARCHIVE_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d")
    archive_name = f"zones_{timestamp}_pre_official.csv"
    archive_path = ARCHIVE_DIR / archive_name

    # If archive already exists, add a counter
    counter = 1
    while archive_path.exists():
        archive_name = f"zones_{timestamp}_pre_official_{counter}.csv"
        archive_path = ARCHIVE_DIR / archive_name
        counter += 1

    shutil.copy(ZONES_FILE, archive_path)
    print(f"Archived current zones file to: {archive_path}")
    return archive_path


def convert_official_zones() -> pl.DataFrame:
    """
    Convert official OnTrac zones Excel file to zones.csv format.

    The Excel file has two sheets:
    - "OnTrac Zones PHX" with columns: ZipCode, DAS/EDAS, Zone from Origin Zipcode: 85027, ...
    - "OnTrac Zones CMH" with columns: ZipCode, DAS/EDAS, Zone from Origin Zipcode: 43194, ...

    Output format:
    - zip_code, shipping_state, phx_zone, cmh_zone, das
    """
    print(f"Reading official zones file: {OFFICIAL_ZONES_FILE}")

    # Read both sheets
    phx_df = pd.read_excel(OFFICIAL_ZONES_FILE, sheet_name="OnTrac Zones PHX")
    cmh_df = pd.read_excel(OFFICIAL_ZONES_FILE, sheet_name="OnTrac Zones CMH")

    print(f"  PHX sheet: {len(phx_df):,} rows")
    print(f"  CMH sheet: {len(cmh_df):,} rows")

    # Standardize column names
    phx_df = phx_df.rename(columns={
        "ZipCode": "zip_code",
        "DAS/EDAS": "das",
        "Zone from Origin Zipcode: 85027": "phx_zone",
        "State": "shipping_state",
    })

    cmh_df = cmh_df.rename(columns={
        "ZipCode": "zip_code",
        "DAS/EDAS": "das",
        "Zone from Origin Zipcode: 43194": "cmh_zone",
        "State": "shipping_state",
    })

    # Select relevant columns
    phx_df = phx_df[["zip_code", "shipping_state", "phx_zone", "das"]]
    cmh_df = cmh_df[["zip_code", "cmh_zone"]]

    # Merge on zip_code
    merged = phx_df.merge(cmh_df, on="zip_code", how="outer")

    # Format zip_code as 5-digit string with leading zeros
    merged["zip_code"] = merged["zip_code"].astype(str).str.zfill(5)

    # Convert zones to int
    merged["phx_zone"] = merged["phx_zone"].astype(int)
    merged["cmh_zone"] = merged["cmh_zone"].astype(int)

    # Standardize DAS values (NO, DAS, EDAS)
    # Note: Official file uses "EAS" instead of "EDAS"
    merged["das"] = merged["das"].str.upper().replace({"NO": "NO", "DAS": "DAS", "EAS": "EDAS", "EDAS": "EDAS"})

    # Reorder columns to match expected format
    merged = merged[["zip_code", "shipping_state", "phx_zone", "cmh_zone", "das"]]

    # Sort by zip_code
    merged = merged.sort_values("zip_code").reset_index(drop=True)

    # Convert to polars
    result = pl.from_pandas(merged)

    print(f"\nConverted zones: {len(result):,} rows")

    return result


def print_summary(zones: pl.DataFrame):
    """Print summary statistics."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print(f"\nTotal ZIP codes: {zones.height:,}")

    # Zone distribution for Phoenix
    print("\nPhoenix zone distribution:")
    phx_dist = zones.group_by("phx_zone").agg(pl.len().alias("count")).sort("phx_zone")
    for row in phx_dist.iter_rows(named=True):
        print(f"  Zone {row['phx_zone']}: {row['count']:,} ZIPs")

    # Zone distribution for Columbus
    print("\nColumbus zone distribution:")
    cmh_dist = zones.group_by("cmh_zone").agg(pl.len().alias("count")).sort("cmh_zone")
    for row in cmh_dist.iter_rows(named=True):
        print(f"  Zone {row['cmh_zone']}: {row['count']:,} ZIPs")

    # DAS distribution
    print("\nDAS classification:")
    das_dist = zones.group_by("das").agg(pl.len().alias("count")).sort("das")
    for row in das_dist.iter_rows(named=True):
        print(f"  {row['das']}: {row['count']:,} ZIPs")


def main():
    print("=" * 60)
    print("CONVERT OFFICIAL ONTRAC ZONES")
    print("=" * 60)

    # Check if official file exists
    if not OFFICIAL_ZONES_FILE.exists():
        print(f"ERROR: Official zones file not found: {OFFICIAL_ZONES_FILE}")
        return

    # Archive current zones
    print()
    archive_current_zones()

    # Convert official zones
    print()
    zones = convert_official_zones()

    # Save to zones.csv
    zones.write_csv(ZONES_FILE)
    print(f"\nSaved to: {ZONES_FILE}")

    # Print summary
    print_summary(zones)

    print("\n" + "=" * 60)
    print("DONE - Official zones converted successfully")
    print("=" * 60)


if __name__ == "__main__":
    main()
