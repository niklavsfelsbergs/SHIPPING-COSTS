"""
Scenario 13: P2P + FedEx (No USPS, No OnTrac)

Per-shipment cheapest selection among:
  - P2P US: Better rates, limited coverage (~10,430 ZIPs)
  - P2P US2: Full US coverage (~93,100 ZIPs), higher rates
  - FedEx: Nationwide coverage (Home Delivery + SmartPost)

Only 2 carrier relationships (P2P + FedEx).

FedEx earned discount: With P2P taking most light shipments, FedEx undiscounted
spend falls below the $4.5M threshold for the 16% tier. We use 0% earned discount
for FedEx to reflect this reality.
"""

import polars as pl
from pathlib import Path

from analysis.US_2026_tenders.optimization.baseline import compute_s1_baseline, apply_s1_adjustments

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
COMBINED_DATASETS = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "combined_datasets"
RESULTS_DIR = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "results" / "scenario_13_p2p_fedex"


# FedEx earned discount for this scenario (0% - below $4.5M threshold)
FEDEX_EARNED = 0.0


def load_data():
    """Load unified dataset with S1 baseline adjustments and FedEx at 0% earned."""
    unified_path = COMBINED_DATASETS / "shipments_unified.parquet"

    print("Loading dataset...")
    df = pl.read_parquet(unified_path)
    # Apply S1 adjustments (DHL flat estimate, OnTrac null imputation)
    # with FedEx at 0% earned — we won't meet $4.5M undiscounted threshold
    df = apply_s1_adjustments(df, target_earned=FEDEX_EARNED)
    print(f"  Unified: {df.shape[0]:,} shipments")
    print(f"  FedEx earned discount: {FEDEX_EARNED:.0%}")

    return df


def add_scenario_cost(df: pl.DataFrame) -> pl.DataFrame:
    """Add scenario cost: cheapest of P2P US, P2P US2, FedEx per shipment.

    Selection logic:
      - Compare all available carrier costs (nulls = no coverage)
      - Select minimum cost per shipment
      - Track which carrier was selected
    """
    cost_cols = ["p2p_cost_total", "p2p_us2_cost_total", "fedex_cost_total"]
    carrier_labels = ["P2P_US", "P2P_US2", "FEDEX"]

    # Cheapest cost across all 3 carriers (min_horizontal ignores nulls)
    df = df.with_columns(
        pl.min_horizontal(*cost_cols).alias("s13_cost_total"),
    )

    # Track which carrier was selected (first match wins on ties)
    carrier_expr = pl.lit(None).cast(pl.Utf8)
    for label, col in reversed(list(zip(carrier_labels, cost_cols))):
        carrier_expr = (
            pl.when(
                pl.col(col).is_not_null() & (pl.col(col) == pl.col("s13_cost_total"))
            )
            .then(pl.lit(label))
            .otherwise(carrier_expr)
        )

    df = df.with_columns(carrier_expr.alias("s13_selected_carrier"))

    return df


def analyze_totals(df, s1_baseline):
    """Calculate overall cost comparison."""
    print("\n" + "=" * 60)
    print("TOTAL COST ANALYSIS")
    print("=" * 60)

    total_shipments = df.shape[0]
    current_total = s1_baseline
    s13_total = df["s13_cost_total"].sum()
    null_count = df.filter(pl.col("s13_cost_total").is_null()).height

    diff = s13_total - current_total
    diff_pct = (diff / current_total) * 100

    print(f"\nTotal shipments: {total_shipments:,}")
    if null_count > 0:
        print(f"Shipments with no coverage: {null_count:,}")
    print(f"\nCurrent mix total (S1 baseline): ${current_total:,.2f}")
    print(f"S13 P2P+FedEx total:             ${s13_total:,.2f}")
    print(f"Difference:                      ${diff:+,.2f} ({diff_pct:+.1f}%)")

    # Reference: each carrier alone
    print(f"\nFor reference (100% single carrier):")
    for label, col in [("OnTrac", "ontrac_cost_total"), ("FedEx", "fedex_cost_total"),
                        ("P2P US", "p2p_cost_total"), ("P2P US2", "p2p_us2_cost_total"),
                        ("USPS", "usps_cost_total"), ("Maersk", "maersk_cost_total")]:
        total = df[col].sum()
        pct = (total - current_total) / current_total * 100
        print(f"  100% {label:<8}: ${total:>12,.2f} ({pct:+.1f}%)")

    avg_current = current_total / total_shipments
    avg_s13 = s13_total / total_shipments
    print(f"\nAvg cost per shipment:")
    print(f"  Current mix:    ${avg_current:.2f}")
    print(f"  P2P+FedEx:      ${avg_s13:.2f}")

    return {
        "total_shipments": total_shipments,
        "current_total": current_total,
        "s13_total": s13_total,
        "diff": diff,
        "diff_pct": diff_pct,
        "avg_current": avg_current,
        "avg_s13": avg_s13,
        "null_count": null_count,
    }


def analyze_carrier_selection(df):
    """Analyze which carrier was selected per shipment."""
    print("\n" + "=" * 60)
    print("CARRIER SELECTION BREAKDOWN")
    print("=" * 60)

    total = df.shape[0]

    carrier_stats = (
        df
        .group_by("s13_selected_carrier")
        .agg([
            pl.len().alias("shipment_count"),
            pl.col("s13_cost_total").sum().alias("total_cost"),
            pl.col("s13_cost_total").mean().alias("avg_cost"),
            pl.col("weight_lbs").mean().alias("avg_weight"),
        ])
        .sort("shipment_count", descending=True)
    )

    print(f"\n{'Carrier':<12} {'Shipments':>12} {'% Total':>10} {'Total Cost':>14} {'Avg Cost':>10} {'Avg Wt':>8}")
    print("-" * 68)
    for row in carrier_stats.iter_rows(named=True):
        carrier = row["s13_selected_carrier"] or "None"
        pct = row["shipment_count"] / total * 100
        total_cost = row["total_cost"] or 0.0
        avg_cost = row["avg_cost"] or 0.0
        avg_weight = row["avg_weight"] or 0.0
        print(f"{carrier:<12} {row['shipment_count']:>12,} {pct:>9.1f}% ${total_cost:>12,.2f} ${avg_cost:>8.2f} {avg_weight:>7.1f}")

    return carrier_stats


def analyze_vs_other_mixes(df, s1_baseline):
    """Compare this scenario vs alternative carrier mixes."""
    print("\n" + "=" * 60)
    print("COMPARISON VS OTHER CARRIER MIXES")
    print("=" * 60)

    s13_total = df["s13_cost_total"].sum()
    total = df.shape[0]

    # USPS+FedEx+OnTrac (current 3-carrier mix, cheapest per shipment)
    df = df.with_columns(
        pl.min_horizontal("usps_cost_total", "fedex_cost_total", "ontrac_cost_total").alias("usps_mix_cost"),
    )
    usps_mix_total = df["usps_mix_cost"].sum()

    # USPS+FedEx (2 carriers, no OnTrac)
    df = df.with_columns(
        pl.min_horizontal("usps_cost_total", "fedex_cost_total").alias("usps_fedex_cost"),
    )
    usps_fedex_total = df["usps_fedex_cost"].sum()

    print(f"\n  {'Carrier Mix':<35} {'Total':>14} {'vs S1':>10} {'vs S13':>12}")
    print("  " + "-" * 73)

    mixes = [
        ("S1 Current mix", s1_baseline),
        ("USPS+FedEx+OnTrac (3 carriers)", usps_mix_total),
        ("USPS+FedEx (2 carriers)", usps_fedex_total),
        ("P2P+FedEx [S13] (2 carriers)", s13_total),
    ]

    for name, total_cost in mixes:
        vs_s1 = (total_cost - s1_baseline) / s1_baseline * 100
        vs_s13 = (total_cost - s13_total) / s13_total * 100
        marker = " ***" if "S13" in name else ""
        print(f"  {name:<35} ${total_cost:>12,.2f} {vs_s1:>+9.1f}% {vs_s13:>+11.1f}%{marker}")

    # Per-shipment: P2P+FedEx vs USPS+FedEx
    df = df.with_columns(
        (pl.col("s13_cost_total") - pl.col("usps_fedex_cost")).alias("s13_vs_usps_fedex_diff")
    )
    p2p_wins = df.filter(pl.col("s13_vs_usps_fedex_diff") < 0)
    usps_wins = df.filter(pl.col("s13_vs_usps_fedex_diff") > 0)
    ties = df.filter(pl.col("s13_vs_usps_fedex_diff") == 0)

    print(f"\n  P2P+FedEx vs USPS+FedEx (per-shipment):")
    print(f"    P2P+FedEx cheaper:  {p2p_wins.height:>8,} ({p2p_wins.height/total*100:.1f}%) saving ${-p2p_wins['s13_vs_usps_fedex_diff'].sum():,.2f}")
    print(f"    USPS+FedEx cheaper: {usps_wins.height:>8,} ({usps_wins.height/total*100:.1f}%) saving ${usps_wins['s13_vs_usps_fedex_diff'].sum():,.2f}")
    print(f"    Tied:               {ties.height:>8,} ({ties.height/total*100:.1f}%)")

    return {
        "usps_mix_total": usps_mix_total,
        "usps_fedex_total": usps_fedex_total,
        "s13_total": s13_total,
    }


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
            pl.col("s13_cost_total").sum().alias("s13_total"),
            pl.col("cost_current_carrier").mean().alias("current_avg"),
            pl.col("s13_cost_total").mean().alias("s13_avg"),
            (pl.col("s13_selected_carrier") == "P2P_US").sum().alias("p2p_us_count"),
            (pl.col("s13_selected_carrier") == "P2P_US2").sum().alias("p2p_us2_count"),
            (pl.col("s13_selected_carrier") == "FEDEX").sum().alias("fedex_count"),
        ])
        .sort("weight_bracket")
        .filter(pl.col("weight_bracket") <= 70)
    )

    weight_analysis = weight_analysis.with_columns([
        (pl.col("s13_total") - pl.col("current_total")).alias("diff"),
        ((pl.col("s13_total") - pl.col("current_total")) / pl.col("current_total") * 100).alias("diff_pct"),
    ])

    print(f"\n{'Bracket':<10} {'Ships':>8} {'Current':>10} {'S13':>10} {'Diff %':>8} {'P2P_US':>7} {'P2P_US2':>8} {'FedEx':>7}")
    print("-" * 72)

    for row in weight_analysis.iter_rows(named=True):
        if row["shipment_count"] >= 100:
            bracket = f"{row['weight_bracket']-1}-{row['weight_bracket']}" if row["weight_bracket"] > 1 else "0-1"
            print(f"{bracket:<10} {row['shipment_count']:>8,} ${row['current_avg']:>8.2f} ${row['s13_avg']:>8.2f} {row['diff_pct']:>7.1f}% {row['p2p_us_count']:>7,} {row['p2p_us2_count']:>8,} {row['fedex_count']:>7,}")

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
            pl.col("s13_cost_total").sum().alias("s13_total"),
            pl.col("cost_current_carrier").mean().alias("current_avg"),
            pl.col("s13_cost_total").mean().alias("s13_avg"),
            pl.col("weight_lbs").mean().alias("avg_weight"),
            (pl.col("s13_selected_carrier") == "P2P_US").sum().alias("p2p_us_count"),
            (pl.col("s13_selected_carrier") == "P2P_US2").sum().alias("p2p_us2_count"),
            (pl.col("s13_selected_carrier") == "FEDEX").sum().alias("fedex_count"),
        ])
        .sort("shipment_count", descending=True)
    )

    pkg_analysis = pkg_analysis.with_columns([
        (pl.col("s13_total") - pl.col("current_total")).alias("diff"),
        ((pl.col("s13_total") - pl.col("current_total")) / pl.col("current_total") * 100).alias("diff_pct"),
    ])

    print(f"\n{'Package Type':<25} {'Ships':>8} {'Wt':>6} {'Current':>10} {'S13':>10} {'Diff %':>8}")
    print("-" * 72)

    for row in pkg_analysis.head(20).iter_rows(named=True):
        print(f"{row['packagetype'][:25]:<25} {row['shipment_count']:>8,} {row['avg_weight']:>5.1f} ${row['current_avg']:>8.2f} ${row['s13_avg']:>8.2f} {row['diff_pct']:>7.1f}%")

    return pkg_analysis


def save_results(totals, carrier_stats, vs_mixes, weight_analysis, pkg_analysis):
    """Save analysis results."""
    print("\n" + "=" * 60)
    print("SAVING RESULTS")
    print("=" * 60)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Carrier selection
    carrier_path = RESULTS_DIR / "carrier_selection.csv"
    carrier_stats.write_csv(carrier_path)
    print(f"  Saved: {carrier_path}")

    # Weight analysis
    weight_path = RESULTS_DIR / "cost_by_weight_bracket.csv"
    weight_analysis.write_csv(weight_path)
    print(f"  Saved: {weight_path}")

    # Package type analysis
    pkg_path = RESULTS_DIR / "cost_by_packagetype.csv"
    pkg_analysis.write_csv(pkg_path)
    print(f"  Saved: {pkg_path}")

    # Summary metrics
    summary_data = {
        "metric": [
            "total_shipments",
            "current_mix_total",
            "s13_total",
            "cost_difference",
            "cost_diff_percent",
            "avg_per_shipment_current",
            "avg_per_shipment_s13",
            "shipments_no_coverage",
            "usps_mix_total",
            "usps_fedex_total",
        ],
        "value": [
            float(totals["total_shipments"]),
            float(totals["current_total"]),
            float(totals["s13_total"]),
            float(totals["diff"]),
            float(totals["diff_pct"]),
            float(totals["avg_current"]),
            float(totals["avg_s13"]),
            float(totals["null_count"]),
            float(vs_mixes["usps_mix_total"]),
            float(vs_mixes["usps_fedex_total"]),
        ],
    }
    summary_df = pl.DataFrame(summary_data)
    summary_path = RESULTS_DIR / "summary_metrics.csv"
    summary_df.write_csv(summary_path)
    print(f"  Saved: {summary_path}")

    # Summary markdown
    md_lines = [
        "# Scenario 13: P2P + FedEx (No USPS, No OnTrac)",
        "",
        "## Overview",
        "Per-shipment cheapest selection among P2P US, P2P US2, and FedEx.",
        "Only 2 carrier relationships (P2P + FedEx).",
        f"FedEx at {FEDEX_EARNED:.0%} earned discount (below $4.5M undiscounted threshold).",
        "",
        "## Results",
        f"- Total shipments: {totals['total_shipments']:,}",
        f"- Current mix (S1): ${totals['current_total']:,.2f}",
        f"- S13 P2P+FedEx: ${totals['s13_total']:,.2f}",
        f"- **Difference: ${totals['diff']:+,.2f} ({totals['diff_pct']:+.1f}%)**",
        f"- Avg per shipment: ${totals['avg_s13']:.2f} (vs ${totals['avg_current']:.2f} current)",
        "",
        "## Carrier Selection",
    ]

    for row in carrier_stats.iter_rows(named=True):
        carrier = row["s13_selected_carrier"] or "None"
        pct = row["shipment_count"] / totals["total_shipments"] * 100
        total_cost = row["total_cost"] or 0.0
        md_lines.append(f"- {carrier}: {row['shipment_count']:,} shipments ({pct:.1f}%), ${total_cost:,.2f}")

    md_lines.extend([
        "",
        "## vs Alternative Mixes",
        f"- S1 Current mix: ${totals['current_total']:,.2f}",
        f"- USPS+FedEx+OnTrac (3 carriers): ${vs_mixes['usps_mix_total']:,.2f}",
        f"- USPS+FedEx (2 carriers): ${vs_mixes['usps_fedex_total']:,.2f}",
        f"- **P2P+FedEx [S13] (2 carriers): ${totals['s13_total']:,.2f}**",
    ])

    summary_md_path = RESULTS_DIR / "summary.md"
    summary_md_path.write_text("\n".join(md_lines))
    print(f"  Saved: {summary_md_path}")


def main():
    """Run complete Scenario 13 analysis."""
    print("=" * 60)
    print("SCENARIO 13: P2P + FEDEX (NO USPS, NO ONTRAC)")
    print("=" * 60)
    print("\nPer-shipment cheapest of P2P US, P2P US2, FedEx.")
    print("2 carrier relationships, no volume commitments.")

    # Load data
    df = load_data()

    # Add scenario cost
    df = add_scenario_cost(df)

    # Run analyses
    s1_baseline = compute_s1_baseline()
    totals = analyze_totals(df, s1_baseline)
    carrier_stats = analyze_carrier_selection(df)
    vs_mixes = analyze_vs_other_mixes(df, s1_baseline)
    weight_analysis = analyze_weight_brackets(df)
    pkg_analysis = analyze_packagetype(df)

    # Save results
    save_results(totals, carrier_stats, vs_mixes, weight_analysis, pkg_analysis)

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)

    return totals, carrier_stats, vs_mixes, weight_analysis, pkg_analysis


if __name__ == "__main__":
    main()
