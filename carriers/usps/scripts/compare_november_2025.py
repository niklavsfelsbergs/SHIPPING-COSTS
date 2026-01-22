"""
USPS Cost Comparison - November 2025

Compares our calculated costs against actual invoice data for November 2025.
Uses base_rates_oct2025.csv (with peak surcharges) for the comparison.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import polars as pl
from shared.database import pull_data
from carriers.usps.calculate_costs import calculate_costs


def load_november_data() -> pl.DataFrame:
    """Load November 2025 USPS invoice data from database."""
    query = """
    SELECT
        impb,
        mailing_date,
        entry_zip_code,
        destination_zip_code,
        manifest_length,
        manifest_width,
        manifest_height,
        manifest_weight,
        zone as invoice_zone,
        base_postage as actual_base_cost,
        final_postage_usd as actual_total_cost
    FROM poc_staging.usps
    WHERE mailing_date >= '2025-11-01' AND mailing_date < '2025-12-01'
        AND entry_zip_code IS NOT NULL
        AND destination_zip_code IS NOT NULL
        AND manifest_weight IS NOT NULL
        AND manifest_weight > 0
        AND manifest_weight <= 20
        AND manifest_length IS NOT NULL
        AND manifest_width IS NOT NULL
        AND manifest_height IS NOT NULL
    """
    return pull_data(query)


def transform_to_calculator_input(df: pl.DataFrame) -> pl.DataFrame:
    """Transform database columns to calculator input format."""
    return df.with_columns([
        # ship_date from mailing_date
        pl.col("mailing_date").cast(pl.Date).alias("ship_date"),

        # production_site from entry_zip_code
        pl.when(pl.col("entry_zip_code") == "85027")
        .then(pl.lit("Phoenix"))
        .when(pl.col("entry_zip_code") == "43194")
        .then(pl.lit("Columbus"))
        .otherwise(pl.lit("Unknown"))
        .alias("production_site"),

        # shipping_zip_code from destination
        pl.col("destination_zip_code").alias("shipping_zip_code"),

        # Dimensions
        pl.col("manifest_length").cast(pl.Float64).alias("length_in"),
        pl.col("manifest_width").cast(pl.Float64).alias("width_in"),
        pl.col("manifest_height").cast(pl.Float64).alias("height_in"),

        # Weight
        pl.col("manifest_weight").cast(pl.Float64).alias("weight_lbs"),

        # shipping_region - will use fallback (not critical for USPS)
        pl.lit("").alias("shipping_region"),
    ])


def add_weight_bracket(df: pl.DataFrame) -> pl.DataFrame:
    """Add weight bracket column for analysis."""
    return df.with_columns([
        pl.when(pl.col("weight_lbs") <= 1)
        .then(pl.lit("0-1 lbs"))
        .when(pl.col("weight_lbs") <= 5)
        .then(pl.lit("1-5 lbs"))
        .when(pl.col("weight_lbs") <= 10)
        .then(pl.lit("5-10 lbs"))
        .when(pl.col("weight_lbs") <= 15)
        .then(pl.lit("10-15 lbs"))
        .otherwise(pl.lit("15-20 lbs"))
        .alias("weight_bracket")
    ])


def compare_costs(df: pl.DataFrame, tolerance: float = 0.01) -> pl.DataFrame:
    """Add comparison columns for base and total costs."""
    return df.with_columns([
        # Base cost comparison
        (pl.col("cost_base") - pl.col("actual_base_cost")).alias("base_diff"),
        (
            (pl.col("cost_base") - pl.col("actual_base_cost")).abs() <= tolerance
        ).alias("base_match"),

        # Total cost comparison
        (pl.col("cost_total") - pl.col("actual_total_cost")).alias("total_diff"),
        (
            (pl.col("cost_total") - pl.col("actual_total_cost")).abs() <= tolerance
        ).alias("total_match"),
    ])


def print_summary(df: pl.DataFrame) -> None:
    """Print overall comparison summary."""
    total = len(df)
    base_matches = df["base_match"].sum()
    total_matches = df["total_match"].sum()

    print("=" * 70)
    print("USPS COST COMPARISON - NOVEMBER 2025")
    print("=" * 70)
    print(f"\nTotal shipments analyzed: {total:,}")
    print(f"Tolerance: $0.01")
    print()
    print(f"BASE COST MATCH RATE:")
    print(f"  Matches: {base_matches:,} / {total:,} ({100*base_matches/total:.2f}%)")
    print()
    print(f"TOTAL COST MATCH RATE:")
    print(f"  Matches: {total_matches:,} / {total:,} ({100*total_matches/total:.2f}%)")
    print()


def print_zone_breakdown(df: pl.DataFrame) -> None:
    """Print match rates by zone."""
    print("-" * 70)
    print("BREAKDOWN BY ZONE")
    print("-" * 70)

    zone_stats = (
        df
        .group_by("rate_zone")
        .agg([
            pl.len().alias("count"),
            pl.col("base_match").sum().alias("base_matches"),
            pl.col("total_match").sum().alias("total_matches"),
            pl.col("base_diff").mean().alias("avg_base_diff"),
            pl.col("total_diff").mean().alias("avg_total_diff"),
        ])
        .sort("rate_zone")
    )

    print(f"\n{'Zone':<6} {'Count':>8} {'Base Match':>12} {'Total Match':>12} {'Avg Base Diff':>14} {'Avg Total Diff':>15}")
    print("-" * 70)

    for row in zone_stats.iter_rows(named=True):
        zone = row["rate_zone"]
        count = row["count"]
        base_pct = 100 * row["base_matches"] / count
        total_pct = 100 * row["total_matches"] / count
        avg_base = row["avg_base_diff"]
        avg_total = row["avg_total_diff"]
        print(f"{zone:<6} {count:>8,} {base_pct:>11.1f}% {total_pct:>11.1f}% ${avg_base:>12.2f} ${avg_total:>13.2f}")
    print()


def print_weight_breakdown(df: pl.DataFrame) -> None:
    """Print match rates by weight bracket."""
    print("-" * 70)
    print("BREAKDOWN BY WEIGHT BRACKET")
    print("-" * 70)

    # Define order for weight brackets
    weight_order = ["0-1 lbs", "1-5 lbs", "5-10 lbs", "10-15 lbs", "15-20 lbs"]

    weight_stats = (
        df
        .group_by("weight_bracket")
        .agg([
            pl.len().alias("count"),
            pl.col("base_match").sum().alias("base_matches"),
            pl.col("total_match").sum().alias("total_matches"),
            pl.col("base_diff").mean().alias("avg_base_diff"),
            pl.col("total_diff").mean().alias("avg_total_diff"),
        ])
    )

    print(f"\n{'Weight':>12} {'Count':>8} {'Base Match':>12} {'Total Match':>12} {'Avg Base Diff':>14} {'Avg Total Diff':>15}")
    print("-" * 78)

    for bracket in weight_order:
        row = weight_stats.filter(pl.col("weight_bracket") == bracket)
        if len(row) > 0:
            row = row.row(0, named=True)
            count = row["count"]
            base_pct = 100 * row["base_matches"] / count
            total_pct = 100 * row["total_matches"] / count
            avg_base = row["avg_base_diff"]
            avg_total = row["avg_total_diff"]
            print(f"{bracket:>12} {count:>8,} {base_pct:>11.1f}% {total_pct:>11.1f}% ${avg_base:>12.2f} ${avg_total:>13.2f}")
    print()


def print_mismatches(df: pl.DataFrame, n: int = 20) -> None:
    """Print sample of mismatches for investigation."""
    mismatches = df.filter(~pl.col("base_match") | ~pl.col("total_match"))

    if len(mismatches) == 0:
        print("-" * 70)
        print("No mismatches found!")
        print("-" * 70)
        return

    print("-" * 70)
    print(f"SAMPLE MISMATCHES (showing {min(n, len(mismatches))} of {len(mismatches):,})")
    print("-" * 70)

    sample = mismatches.head(n)

    cols_to_show = [
        "impb",
        "production_site",
        "rate_zone",
        "invoice_zone",
        "weight_lbs",
        "billable_weight_lbs",
        "actual_base_cost",
        "cost_base",
        "base_diff",
        "actual_total_cost",
        "cost_total",
        "total_diff",
    ]

    # Only show columns that exist
    cols_to_show = [c for c in cols_to_show if c in sample.columns]

    print(sample.select(cols_to_show))
    print()

    # Analyze mismatch patterns
    print("MISMATCH ANALYSIS:")

    # Base cost mismatches
    base_mismatches = df.filter(~pl.col("base_match"))
    if len(base_mismatches) > 0:
        print(f"\nBase cost mismatches: {len(base_mismatches):,}")
        print(f"  - Our cost higher: {len(base_mismatches.filter(pl.col('base_diff') > 0)):,}")
        print(f"  - Our cost lower: {len(base_mismatches.filter(pl.col('base_diff') < 0)):,}")

        # Zone mismatch analysis
        zone_mismatch = base_mismatches.filter(
            pl.col("rate_zone").cast(pl.Utf8) != pl.col("invoice_zone")
        )
        print(f"  - Zone mismatch (our zone != invoice zone): {len(zone_mismatch):,}")

    # Total cost mismatches only (base matched)
    total_only_mismatches = df.filter(pl.col("base_match") & ~pl.col("total_match"))
    if len(total_only_mismatches) > 0:
        print(f"\nTotal cost mismatches (base matched): {len(total_only_mismatches):,}")
        print("  These likely have surcharges we're not calculating correctly")
    print()


def print_surcharge_analysis(df: pl.DataFrame) -> None:
    """Analyze surcharges for mismatches."""
    print("-" * 70)
    print("SURCHARGE ANALYSIS")
    print("-" * 70)

    # Check for NSL (Non-Standard Length) surcharges
    surcharge_cols = [c for c in df.columns if c.startswith("surcharge_")]

    if not surcharge_cols:
        print("No surcharge columns found")
        return

    for col in surcharge_cols:
        count = df[col].sum()
        surcharge_name = col.replace("surcharge_", "").upper()
        print(f"{surcharge_name}: {count:,} shipments flagged")
    print()


def main():
    print("\nLoading November 2025 data from database...")
    raw_df = load_november_data()
    print(f"Loaded {len(raw_df):,} shipments")

    print("\nTransforming data to calculator input format...")
    input_df = transform_to_calculator_input(raw_df)

    # Filter out unknown production sites
    input_df = input_df.filter(pl.col("production_site") != "Unknown")
    print(f"After filtering: {len(input_df):,} shipments (known production sites)")

    print("\nRunning cost calculator...")
    try:
        result_df = calculate_costs(input_df)
    except Exception as e:
        print(f"ERROR during calculation: {e}")
        # Try to diagnose
        print("\nDiagnostics:")
        print(f"  Weight range: {input_df['weight_lbs'].min():.3f} - {input_df['weight_lbs'].max():.3f}")
        print(f"  Null weights: {input_df['weight_lbs'].null_count()}")
        raise

    print("\nAdding weight brackets and comparing costs...")
    result_df = add_weight_bracket(result_df)
    result_df = compare_costs(result_df)

    # Print reports
    print()
    print_summary(result_df)
    print_zone_breakdown(result_df)
    print_weight_breakdown(result_df)
    print_surcharge_analysis(result_df)
    print_mismatches(result_df, n=20)

    print("=" * 70)
    print("COMPARISON COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
