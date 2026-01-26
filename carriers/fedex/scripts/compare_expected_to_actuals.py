"""
Compare Expected to Actual Costs
================================

Generates HTML comparison reports between expected and actual FedEx shipping costs.

Usage:
    python -m carriers.fedex.scripts.compare_expected_to_actuals
    python -m carriers.fedex.scripts.compare_expected_to_actuals --date_from 2025-01-01
    python -m carriers.fedex.scripts.compare_expected_to_actuals --invoice ABC123
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

import polars as pl

from shared.database import pull_data


# =============================================================================
# CONFIGURATION
# =============================================================================

EXPECTED_TABLE = "shipping_costs.expected_shipping_costs_fedex"
ACTUAL_TABLE = "shipping_costs.actual_shipping_costs_fedex"
OUTPUT_DIR = Path(__file__).parent / "output" / "accuracy_reports"
SQL_DIR = Path(__file__).parent / "sql"


# =============================================================================
# DATA EXTRACTION
# =============================================================================

def get_comparison_data(
    date_from: str | None = None,
    date_to: str | None = None,
    invoice: str | None = None,
) -> pl.DataFrame:
    """
    Get joined expected vs actual data for comparison.

    TODO: Implement comparison query based on FedEx table structure.

    Args:
        date_from: Start date filter (YYYY-MM-DD)
        date_to: End date filter (YYYY-MM-DD)
        invoice: Specific invoice number filter

    Returns:
        DataFrame with expected and actual cost data joined
    """
    # TODO: Implement FedEx comparison query
    # This will need to join expected and actual tables
    raise NotImplementedError(
        "FedEx comparison query not yet implemented. "
        "Need to finalize table structure first."
    )


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_summary_stats(df: pl.DataFrame) -> dict:
    """
    Generate summary statistics for the comparison.

    Returns dict with:
        - total_expected, total_actual, variance, variance_pct
        - by_category breakdowns (base, surcharges, fuel)
        - accuracy metrics
    """
    # TODO: Implement stats calculation
    return {}


def generate_html_report(
    df: pl.DataFrame,
    stats: dict,
    date_from: str | None,
    date_to: str | None,
    invoice: str | None,
) -> str:
    """
    Generate HTML comparison report.

    Returns HTML string.
    """
    # TODO: Implement HTML report generation
    # See ontrac/scripts/compare_expected_to_actuals.py for reference
    return "<html><body><h1>FedEx Comparison Report</h1><p>Not yet implemented</p></body></html>"


def save_report(html: str, invoice: str | None = None) -> Path:
    """Save HTML report to file and return path."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if invoice:
        filename = f"comparison_report_{invoice}_{timestamp}.html"
    else:
        filename = f"comparison_report_{timestamp}.html"

    filepath = OUTPUT_DIR / filename
    filepath.write_text(html)
    return filepath


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Compare expected vs actual FedEx shipping costs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m carriers.fedex.scripts.compare_expected_to_actuals
  python -m carriers.fedex.scripts.compare_expected_to_actuals --date_from 2025-01-01
  python -m carriers.fedex.scripts.compare_expected_to_actuals --date_from 2025-01-01 --date_to 2025-01-31
  python -m carriers.fedex.scripts.compare_expected_to_actuals --invoice ABC123
        """
    )

    parser.add_argument(
        "--date_from",
        type=str,
        help="Start date filter (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--date_to",
        type=str,
        help="End date filter (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--invoice",
        type=str,
        help="Filter to specific invoice number"
    )

    args = parser.parse_args()

    try:
        print("=" * 60)
        print("FEDEX EXPECTED VS ACTUAL COMPARISON")
        print("=" * 60)

        # Get data
        print("\nStep 1: Loading comparison data...")
        df = get_comparison_data(
            date_from=args.date_from,
            date_to=args.date_to,
            invoice=args.invoice,
        )
        print(f"  Loaded {len(df):,} rows")

        if len(df) == 0:
            print("\nNo matching data found.")
            return

        # Generate stats
        print("\nStep 2: Calculating statistics...")
        stats = generate_summary_stats(df)

        # Generate report
        print("\nStep 3: Generating HTML report...")
        html = generate_html_report(
            df=df,
            stats=stats,
            date_from=args.date_from,
            date_to=args.date_to,
            invoice=args.invoice,
        )

        # Save report
        filepath = save_report(html, invoice=args.invoice)
        print(f"\nReport saved to: {filepath}")

        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        # TODO: Print summary stats

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
