"""
Upload Expected Costs to Database

Calculates expected shipping costs from PCS shipment data and uploads to Redshift.

Usage:
    python -m carriers.usps.scripts.upload_expected --full         # Full recalculation
    python -m carriers.usps.scripts.upload_expected --incremental  # From latest date in DB
    python -m carriers.usps.scripts.upload_expected --days 7       # Last N days
    python -m carriers.usps.scripts.upload_expected --dry-run      # Preview without changes
"""

import argparse

# TODO: Implement upload script


def main():
    parser = argparse.ArgumentParser(description="Upload expected USPS costs to database")
    parser.add_argument("--full", action="store_true", help="Full recalculation")
    parser.add_argument("--incremental", action="store_true", help="From latest date in DB")
    parser.add_argument("--days", type=int, help="Last N days")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")

    args = parser.parse_args()

    print("USPS Upload Expected - Not yet implemented")
    print()
    print("TODO: Implement upload_expected for USPS")


if __name__ == "__main__":
    main()
