"""
Run all 5 carrier calculators and build combined dataset.

This script:
1. Runs each carrier's upload_expected_all_us script with --parquet output
2. Copies the outputs to carrier_datasets/
3. Builds the unified shipments dataset

Usage:
    # Using pre-exported PCS data (recommended for faster iteration):
    python -m shared.scripts.export_pcs_shipments --start-date 2025-01-01 --end-date 2025-12-31
    python -m analysis.US_2026_tenders.scripts.run_all_carriers --parquet-data shared/data/pcs_shipments_all_us_2025-01-01_2025-12-31.parquet --start-date 2025-01-01 --end-date 2025-12-31

    # Or let each script query the database directly:
    python -m analysis.US_2026_tenders.scripts.run_all_carriers --start-date 2025-01-01 --end-date 2025-12-31
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
CARRIER_DATASETS = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "carrier_datasets"

# Carriers and their script modules
CARRIERS = [
    ("ontrac", "carriers.ontrac.scripts.upload_expected_all_us"),
    ("usps", "carriers.usps.scripts.upload_expected_all_us"),
    ("fedex", "carriers.fedex.scripts.upload_expected_all_us"),
    ("p2p_us", "carriers.p2p_us.scripts.upload_expected_all_us"),
    ("p2p_us2", "carriers.p2p_us2.scripts.upload_expected_all_us"),
    ("maersk_us", "carriers.maersk_us.scripts.upload_expected_all_us"),
]


def run_carrier_calculator(
    carrier_name: str,
    module_name: str,
    start_date: str,
    end_date: str | None = None,
    parquet_data: str | None = None,
) -> Path | None:
    """
    Run a carrier's upload_expected_all_us script with --parquet output.

    Returns the path to the output parquet file, or None if failed.
    """
    print(f"\n{'='*60}")
    print(f"Running {carrier_name.upper()} calculator")
    print("="*60)

    # Build command
    cmd = [
        sys.executable, "-m", module_name,
        "--full", "--parquet",
        "--start-date", start_date,
    ]

    if end_date:
        cmd.extend(["--end-date", end_date])

    if parquet_data:
        cmd.extend(["--parquet-data", parquet_data])

    print(f"Command: {' '.join(cmd)}")
    print()

    # Run the command
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode != 0:
        print(f"ERROR: {carrier_name} calculator failed with return code {result.returncode}")
        return None

    # Find the output file
    output_dir = PROJECT_ROOT / "carriers" / carrier_name / "scripts" / "output" / "all_us"
    parquet_files = list(output_dir.glob("*.parquet"))

    if not parquet_files:
        print(f"ERROR: No parquet files found in {output_dir}")
        return None

    # Return the most recently modified file
    return max(parquet_files, key=lambda p: p.stat().st_mtime)


def copy_to_carrier_datasets(source_path: Path, carrier_name: str) -> Path:
    """Copy the parquet file to the carrier_datasets directory."""
    CARRIER_DATASETS.mkdir(parents=True, exist_ok=True)
    dest_path = CARRIER_DATASETS / source_path.name
    shutil.copy2(source_path, dest_path)
    return dest_path


def build_combined_dataset():
    """Run the build_shipment_dataset script to create unified dataset."""
    print(f"\n{'='*60}")
    print("Building combined dataset")
    print("="*60)

    cmd = [sys.executable, "-m", "analysis.US_2026_tenders.scripts.build_shipment_dataset"]
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode != 0:
        print(f"ERROR: build_shipment_dataset failed with return code {result.returncode}")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Run all carrier calculators and build combined dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Using pre-exported PCS data (faster):
    python -m analysis.US_2026_tenders.scripts.run_all_carriers \\
        --parquet-data shared/data/pcs_shipments_all_us_2025-01-01_2025-12-31.parquet \\
        --start-date 2025-01-01 --end-date 2025-12-31

    # Query database directly:
    python -m analysis.US_2026_tenders.scripts.run_all_carriers \\
        --start-date 2025-01-01 --end-date 2025-12-31
        """
    )

    parser.add_argument(
        "--start-date",
        type=str,
        required=True,
        help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date (YYYY-MM-DD), defaults to today"
    )
    parser.add_argument(
        "--parquet-data",
        type=str,
        metavar="PATH",
        help="Load PCS shipments from parquet file instead of database"
    )
    parser.add_argument(
        "--skip-calculation",
        action="store_true",
        help="Skip carrier calculations, only build combined dataset from existing files"
    )

    args = parser.parse_args()

    print("="*60)
    print("US 2026 Tenders - Run All Carriers")
    print("="*60)
    print(f"Start date: {args.start_date}")
    print(f"End date: {args.end_date or 'today'}")
    if args.parquet_data:
        print(f"Data source: {args.parquet_data}")
    else:
        print("Data source: database")

    if not args.skip_calculation:
        # Run each carrier calculator
        successful = []
        failed = []

        for carrier_name, module_name in CARRIERS:
            output_path = run_carrier_calculator(
                carrier_name=carrier_name,
                module_name=module_name,
                start_date=args.start_date,
                end_date=args.end_date,
                parquet_data=args.parquet_data,
            )

            if output_path:
                dest_path = copy_to_carrier_datasets(output_path, carrier_name)
                print(f"  Copied to: {dest_path}")
                successful.append(carrier_name)
            else:
                failed.append(carrier_name)

        # Summary
        print(f"\n{'='*60}")
        print("Carrier Calculation Summary")
        print("="*60)
        print(f"Successful: {len(successful)} - {', '.join(successful)}")
        if failed:
            print(f"Failed: {len(failed)} - {', '.join(failed)}")

        if failed:
            print("\nWARNING: Some carriers failed. Combined dataset may be incomplete.")

    # Build combined dataset
    if build_combined_dataset():
        print(f"\n{'='*60}")
        print("SUCCESS - All tasks completed")
        print("="*60)
        print(f"Carrier datasets: {CARRIER_DATASETS}")
        print(f"Combined dataset: {PROJECT_ROOT / 'analysis' / 'US_2026_tenders' / 'combined_datasets' / 'shipments_unified.parquet'}")
    else:
        print("\nERROR: Failed to build combined dataset")
        sys.exit(1)


if __name__ == "__main__":
    main()
