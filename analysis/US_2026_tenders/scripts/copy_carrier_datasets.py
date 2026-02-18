"""
Copy the latest parquet file from each carrier's all_us output folder
to the carrier_datasets directory.
"""

import shutil
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
CARRIERS_DIR = PROJECT_ROOT / "carriers"
OUTPUT_DIR = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "carrier_datasets"

# Carriers to process
CARRIERS = ["ontrac", "usps", "fedex", "p2p_us", "p2p_us2", "maersk_us"]


def get_latest_parquet(carrier: str) -> Path | None:
    """Get the most recently modified parquet file for a carrier."""
    all_us_dir = CARRIERS_DIR / carrier / "scripts" / "output" / "all_us"

    if not all_us_dir.exists():
        return None

    parquet_files = list(all_us_dir.glob("*.parquet"))

    if not parquet_files:
        return None

    # Return the most recently modified file
    return max(parquet_files, key=lambda p: p.stat().st_mtime)


def main():
    # Create output directory if it doesn't exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Copying latest parquet files to: {OUTPUT_DIR}\n")

    for carrier in CARRIERS:
        latest_file = get_latest_parquet(carrier)

        if latest_file is None:
            print(f"  {carrier}: No parquet files found")
            continue

        dest_path = OUTPUT_DIR / latest_file.name
        shutil.copy2(latest_file, dest_path)

        print(f"  {carrier}: {latest_file.name}")

    print("\nDone.")


if __name__ == "__main__":
    main()
