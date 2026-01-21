"""
Compare Expected vs Actual Costs

Compares calculated expected costs against actual invoice costs.

Usage:
    python -m carriers.usps.scripts.compare_expected_to_actuals
    python -m carriers.usps.scripts.compare_expected_to_actuals --invoice INV-12345
    python -m carriers.usps.scripts.compare_expected_to_actuals --date_from 2025-01-01 --date_to 2025-01-31
"""

import argparse

# TODO: Implement comparison script


def main():
    parser = argparse.ArgumentParser(description="Compare expected vs actual USPS costs")
    parser.add_argument("--invoice", help="Filter by invoice number")
    parser.add_argument("--date_from", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--date_to", help="End date (YYYY-MM-DD)")

    args = parser.parse_args()

    print("USPS Compare Expected to Actuals - Not yet implemented")
    print()
    print("TODO: Implement compare_expected_to_actuals for USPS")


if __name__ == "__main__":
    main()
