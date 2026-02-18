"""
Scenario 12: 100% P2P Combined (P2P US + P2P US2)

Routes all US shipments through P2P using both contracts:
  - P2P US: Better rates, limited coverage (~10,430 ZIPs)
  - P2P US2: Full US coverage (~93,100 ZIPs), higher rates

Per-shipment selection: use the cheaper of the two where both are available.
Where only one has coverage, use that one.
"""

import polars as pl
from pathlib import Path

from analysis.US_2026_tenders.optimization.baseline import compute_s1_baseline


# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
COMBINED_DATASETS = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "combined_datasets"
RESULTS_DIR = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "results" / "scenario_12_p2p_combined"


def load_data():
    """Load unified dataset."""
    unified_path = COMBINED_DATASETS / "shipments_unified.parquet"

    print("Loading dataset...")
    df = pl.read_parquet(unified_path)
    print(f"  Unified: {df.shape[0]:,} shipments")

    return df


def add_p2p_combined_cost(df: pl.DataFrame) -> pl.DataFrame:
    """Add combined P2P cost: cheapest of p2p_us vs p2p_us2 per shipment.

    Selection logic:
      - Both available: use the cheaper one
      - Only one available: use that one
      - Neither available: null
    """
    df = df.with_columns([
        # Combined cost: min of the two, handling nulls
        pl.when(
            pl.col("p2p_cost_total").is_not_null() & pl.col("p2p_us2_cost_total").is_not_null()
        )
        .then(pl.min_horizontal("p2p_cost_total", "p2p_us2_cost_total"))
        .when(pl.col("p2p_cost_total").is_not_null())
        .then(pl.col("p2p_cost_total"))
        .when(pl.col("p2p_us2_cost_total").is_not_null())
        .then(pl.col("p2p_us2_cost_total"))
        .otherwise(pl.lit(None))
        .alias("p2p_combined_cost_total"),

        # Track which contract was selected
        pl.when(
            pl.col("p2p_cost_total").is_not_null() & pl.col("p2p_us2_cost_total").is_not_null()
        )
        .then(
            pl.when(pl.col("p2p_cost_total") <= pl.col("p2p_us2_cost_total"))
            .then(pl.lit("P2P_US"))
            .otherwise(pl.lit("P2P_US2"))
        )
        .when(pl.col("p2p_cost_total").is_not_null())
        .then(pl.lit("P2P_US"))
        .when(pl.col("p2p_us2_cost_total").is_not_null())
        .then(pl.lit("P2P_US2"))
        .otherwise(pl.lit(None))
        .alias("p2p_combined_source"),
    ])

    return df


def analyze_totals(df, s1_baseline):
    """Calculate overall cost comparison."""
    print("\n" + "=" * 60)
    print("TOTAL COST ANALYSIS")
    print("=" * 60)

    total_shipments = df.shape[0]
    current_total = s1_baseline
    p2p_combined_total = df["p2p_combined_cost_total"].sum()
    p2p_us_only_total = df["p2p_cost_total"].sum()
    p2p_us2_only_total = df["p2p_us2_cost_total"].sum()

    null_count = df.filter(pl.col("p2p_combined_cost_total").is_null()).height

    diff = p2p_combined_total - current_total
    diff_pct = (diff / current_total) * 100

    print(f"\nTotal shipments: {total_shipments:,}")
    if null_count > 0:
        print(f"Shipments with no P2P coverage: {null_count:,}")
    print(f"\nCurrent mix total (S1 baseline): ${current_total:,.2f}")
    print(f"100% P2P Combined total:         ${p2p_combined_total:,.2f}")
    print(f"Difference:                      ${diff:+,.2f} ({diff_pct:+.1f}%)")

    print(f"\nFor reference:")
    p2p_us_diff_pct = (p2p_us_only_total - current_total) / current_total * 100
    p2p_us2_diff_pct = (p2p_us2_only_total - current_total) / current_total * 100
    print(f"  100% P2P US only:  ${p2p_us_only_total:,.2f} ({p2p_us_diff_pct:+.1f}%)")
    print(f"  100% P2P US2 only: ${p2p_us2_only_total:,.2f} ({p2p_us2_diff_pct:+.1f}%)")

    avg_current = current_total / total_shipments
    avg_combined = p2p_combined_total / total_shipments
    print(f"\nAvg cost per shipment:")
    print(f"  Current mix:    ${avg_current:.2f}")
    print(f"  P2P Combined:   ${avg_combined:.2f}")

    return {
        "total_shipments": total_shipments,
        "current_total": current_total,
        "p2p_combined_total": p2p_combined_total,
        "p2p_us_only_total": p2p_us_only_total,
        "p2p_us2_only_total": p2p_us2_only_total,
        "diff": diff,
        "diff_pct": diff_pct,
        "avg_current": avg_current,
        "avg_combined": avg_combined,
        "null_count": null_count,
    }


def analyze_source_split(df):
    """Analyze P2P US vs P2P US2 selection breakdown."""
    print("\n" + "=" * 60)
    print("CONTRACT SELECTION BREAKDOWN")
    print("=" * 60)

    total = df.shape[0]

    source_stats = (
        df
        .group_by("p2p_combined_source")
        .agg([
            pl.len().alias("shipment_count"),
            pl.col("p2p_combined_cost_total").sum().alias("total_cost"),
            pl.col("p2p_combined_cost_total").mean().alias("avg_cost"),
            pl.col("weight_lbs").mean().alias("avg_weight"),
        ])
        .sort("p2p_combined_source")
    )

    print(f"\n{'Source':<12} {'Shipments':>12} {'% Total':>10} {'Total Cost':>14} {'Avg Cost':>10} {'Avg Wt':>8}")
    print("-" * 68)
    for row in source_stats.iter_rows(named=True):
        src = row["p2p_combined_source"] or "None"
        pct = row["shipment_count"] / total * 100
        total_cost = row["total_cost"] or 0.0
        avg_cost = row["avg_cost"] or 0.0
        avg_weight = row["avg_weight"] or 0.0
        print(f"{src:<12} {row['shipment_count']:>12,} {pct:>9.1f}% ${total_cost:>12,.2f} ${avg_cost:>8.2f} {avg_weight:>7.1f}")

    # Where both are available, show cost comparison
    both_available = df.filter(
        pl.col("p2p_cost_total").is_not_null() & pl.col("p2p_us2_cost_total").is_not_null()
    )
    if both_available.height > 0:
        p2p_us_wins = both_available.filter(pl.col("p2p_combined_source") == "P2P_US").height
        p2p_us2_wins = both_available.height - p2p_us_wins
        savings = (both_available["p2p_us2_cost_total"].sum() - both_available["p2p_cost_total"].sum())

        print(f"\nOverlapping ZIPs ({both_available.height:,} shipments where both have coverage):")
        print(f"  P2P US cheaper:  {p2p_us_wins:,} ({p2p_us_wins/both_available.height*100:.1f}%)")
        print(f"  P2P US2 cheaper: {p2p_us2_wins:,} ({p2p_us2_wins/both_available.height*100:.1f}%)")
        print(f"  P2P US total savings over P2P US2 in overlap: ${savings:,.2f}")

    return source_stats


def analyze_weight_brackets(df):
    """Analyze costs by weight bracket."""
    print("\n" + "=" * 60)
    print("COST BY WEIGHT BRACKET")
    print("=" * 60)

    df_wb = df.with_columns(
        pl.col("weight_lbs").ceil().cast(pl.Int32).alias("weight_bracket")
    )

    weight_analysis = (
        df_wb
        .group_by("weight_bracket")
        .agg([
            pl.len().alias("shipment_count"),
            pl.col("cost_current_carrier").sum().alias("current_total"),
            pl.col("p2p_combined_cost_total").sum().alias("p2p_total"),
            pl.col("cost_current_carrier").mean().alias("current_avg"),
            pl.col("p2p_combined_cost_total").mean().alias("p2p_avg"),
            (pl.col("p2p_combined_source") == "P2P_US").sum().alias("p2p_us_count"),
            (pl.col("p2p_combined_source") == "P2P_US2").sum().alias("p2p_us2_count"),
        ])
        .sort("weight_bracket")
        .filter(pl.col("weight_bracket") <= 70)
    )

    weight_analysis = weight_analysis.with_columns([
        (pl.col("p2p_total") - pl.col("current_total")).alias("diff"),
        ((pl.col("p2p_total") - pl.col("current_total")) / pl.col("current_total") * 100).alias("diff_pct"),
    ])

    print(f"\n{'Bracket':<10} {'Ships':>8} {'Current':>10} {'P2P Comb':>10} {'Diff %':>8} {'P2P US':>8} {'P2P US2':>8}")
    print("-" * 66)

    for row in weight_analysis.iter_rows(named=True):
        if row["shipment_count"] >= 100:
            bracket = f"{row['weight_bracket']-1}-{row['weight_bracket']}" if row["weight_bracket"] > 1 else "0-1"
            print(f"{bracket:<10} {row['shipment_count']:>8,} ${row['current_avg']:>8.2f} ${row['p2p_avg']:>8.2f} {row['diff_pct']:>7.1f}% {row['p2p_us_count']:>8,} {row['p2p_us2_count']:>8,}")

    return weight_analysis


def analyze_packagetype(df):
    """Analyze costs by package type."""
    print("\n" + "=" * 60)
    print("COST BY PACKAGE TYPE")
    print("=" * 60)

    pkg_analysis = (
        df
        .group_by("packagetype")
        .agg([
            pl.len().alias("shipment_count"),
            pl.col("cost_current_carrier").sum().alias("current_total"),
            pl.col("p2p_combined_cost_total").sum().alias("p2p_total"),
            pl.col("cost_current_carrier").mean().alias("current_avg"),
            pl.col("p2p_combined_cost_total").mean().alias("p2p_avg"),
            pl.col("weight_lbs").mean().alias("avg_weight"),
            (pl.col("p2p_combined_source") == "P2P_US").sum().alias("p2p_us_count"),
            (pl.col("p2p_combined_source") == "P2P_US2").sum().alias("p2p_us2_count"),
        ])
        .sort("shipment_count", descending=True)
    )

    pkg_analysis = pkg_analysis.with_columns([
        (pl.col("p2p_total") - pl.col("current_total")).alias("diff"),
        ((pl.col("p2p_total") - pl.col("current_total")) / pl.col("current_total") * 100).alias("diff_pct"),
    ])

    print(f"\n{'Package Type':<25} {'Ships':>8} {'Wt':>6} {'Current':>10} {'P2P':>10} {'Diff %':>8} {'US/US2':>10}")
    print("-" * 80)

    for row in pkg_analysis.head(20).iter_rows(named=True):
        us_pct = row["p2p_us_count"] / row["shipment_count"] * 100 if row["shipment_count"] > 0 else 0
        print(f"{row['packagetype'][:25]:<25} {row['shipment_count']:>8,} {row['avg_weight']:>5.1f} ${row['current_avg']:>8.2f} ${row['p2p_avg']:>8.2f} {row['diff_pct']:>7.1f}% {us_pct:>5.0f}%/{100-us_pct:>2.0f}%")

    return pkg_analysis


def compare_carriers(df):
    """Compare P2P Combined to all other carriers."""
    print("\n" + "=" * 60)
    print("CARRIER COMPARISON")
    print("=" * 60)

    total_shipments = df.shape[0]

    carriers = {
        "Current Mix": df["cost_current_carrier"].sum(),
        "OnTrac": df["ontrac_cost_total"].sum(),
        "USPS": df["usps_cost_total"].sum(),
        "FedEx": df["fedex_cost_total"].sum(),
        "P2P US": df["p2p_cost_total"].sum(),
        "P2P US2": df["p2p_us2_cost_total"].sum(),
        "P2P Combined": df["p2p_combined_cost_total"].sum(),
        "Maersk": df["maersk_cost_total"].sum(),
    }

    current = carriers["Current Mix"]

    print(f"\n{'Carrier':<15} {'Total Cost':>14} {'Avg/Ship':>10} {'vs Current':>12} {'Diff %':>10}")
    print("-" * 63)
    for carrier, total in carriers.items():
        avg = total / total_shipments
        diff = total - current
        diff_pct = (diff / current) * 100
        marker = " ***" if carrier == "P2P Combined" else ""
        print(f"{carrier:<15} ${total:>12,.2f} ${avg:>8.2f} ${diff:>10,.2f} {diff_pct:>9.1f}%{marker}")

    return carriers


def save_results(totals, source_stats, weight_analysis, pkg_analysis):
    """Save analysis results."""
    print("\n" + "=" * 60)
    print("SAVING RESULTS")
    print("=" * 60)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Weight analysis
    weight_path = RESULTS_DIR / "cost_by_weight_bracket.csv"
    weight_analysis.write_csv(weight_path)
    print(f"  Saved: {weight_path}")

    # Package type analysis
    pkg_path = RESULTS_DIR / "cost_by_packagetype.csv"
    pkg_analysis.write_csv(pkg_path)
    print(f"  Saved: {pkg_path}")

    # Source split
    source_path = RESULTS_DIR / "contract_selection.csv"
    source_stats.write_csv(source_path)
    print(f"  Saved: {source_path}")

    # Summary
    summary_data = {
        "metric": [
            "total_shipments",
            "current_mix_total",
            "p2p_combined_total",
            "p2p_us_only_total",
            "p2p_us2_only_total",
            "cost_difference",
            "cost_diff_percent",
            "avg_per_shipment_current",
            "avg_per_shipment_p2p_combined",
            "shipments_no_coverage",
        ],
        "value": [
            float(totals["total_shipments"]),
            float(totals["current_total"]),
            float(totals["p2p_combined_total"]),
            float(totals["p2p_us_only_total"]),
            float(totals["p2p_us2_only_total"]),
            float(totals["diff"]),
            float(totals["diff_pct"]),
            float(totals["avg_current"]),
            float(totals["avg_combined"]),
            float(totals["null_count"]),
        ],
    }
    summary_df = pl.DataFrame(summary_data)
    summary_path = RESULTS_DIR / "summary_metrics.csv"
    summary_df.write_csv(summary_path)
    print(f"  Saved: {summary_path}")

    # Summary markdown
    md_lines = [
        "# Scenario 12: 100% P2P Combined (P2P US + P2P US2)",
        "",
        "## Overview",
        "Routes all US shipments through P2P using both contracts:",
        f"- P2P US: ~10,430 ZIPs, better rates",
        f"- P2P US2: ~93,100 ZIPs (full US), higher rates",
        "Per-shipment selection: cheapest of the two.",
        "",
        "## Results",
        f"- Total shipments: {totals['total_shipments']:,}",
        f"- Current mix (S1): ${totals['current_total']:,.2f}",
        f"- P2P Combined: ${totals['p2p_combined_total']:,.2f}",
        f"- Difference: ${totals['diff']:+,.2f} ({totals['diff_pct']:+.1f}%)",
        f"- Avg per shipment: ${totals['avg_combined']:.2f} (vs ${totals['avg_current']:.2f} current)",
        "",
        "## Contract Split",
    ]

    for row in source_stats.iter_rows(named=True):
        src = row["p2p_combined_source"] or "None"
        pct = row["shipment_count"] / totals["total_shipments"] * 100
        md_lines.append(f"- {src}: {row['shipment_count']:,} shipments ({pct:.1f}%), ${row['total_cost']:,.2f}")

    md_lines.extend([
        "",
        "## Reference",
        f"- P2P US only: ${totals['p2p_us_only_total']:,.2f}",
        f"- P2P US2 only: ${totals['p2p_us2_only_total']:,.2f}",
    ])

    summary_md_path = RESULTS_DIR / "summary.md"
    summary_md_path.write_text("\n".join(md_lines))
    print(f"  Saved: {summary_md_path}")


def main():
    """Run complete Scenario 12 analysis."""
    print("=" * 60)
    print("SCENARIO 12: 100% P2P COMBINED (P2P US + P2P US2)")
    print("=" * 60)
    print("\nRoutes all shipments through P2P using both contracts.")
    print("Per-shipment: cheapest of P2P US vs P2P US2.")

    # Load data
    df = load_data()

    # Add combined P2P cost
    df = add_p2p_combined_cost(df)

    # Run analyses
    s1_baseline = compute_s1_baseline()
    totals = analyze_totals(df, s1_baseline)
    source_stats = analyze_source_split(df)
    weight_analysis = analyze_weight_brackets(df)
    pkg_analysis = analyze_packagetype(df)
    compare_carriers(df)

    # Save results
    save_results(totals, source_stats, weight_analysis, pkg_analysis)

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)

    return totals, source_stats, weight_analysis, pkg_analysis


if __name__ == "__main__":
    main()
