"""
Scenario 14: P2P + FedEx with FedEx 16% Earned Discount (Constrained)

Per-shipment cheapest selection among P2P US, P2P US2, and FedEx — with a
constraint: FedEx undiscounted spend must be >= $5.1M to stay safely above
the $5M penalty threshold ($500K penalty if below).

Strategy:
  1. Start with unconstrained cheapest-per-shipment (P2P vs FedEx@16%)
  2. If FedEx undiscounted spend < $5.1M, switch lowest-pain P2P shipments
     to FedEx until the threshold is met
  3. "Switch pain" = FedEx@16% cost - best P2P cost (cheapest switches first)

Only 2 carrier relationships (P2P + FedEx). FedEx at 16% earned discount.
"""

import polars as pl
from pathlib import Path

from analysis.US_2026_tenders.optimization.baseline import compute_s1_baseline, apply_s1_adjustments

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
COMBINED_DATASETS = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "combined_datasets"
RESULTS_DIR = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "results" / "scenario_14_p2p_fedex_constrained"

# FedEx configuration
FEDEX_EARNED = 0.16
FEDEX_UNDISCOUNTED_THRESHOLD = 5_100_000  # $5.1M to stay safely above $5M penalty


def load_data():
    """Load unified dataset at both FedEx earned levels (16% for costs, 0% for undiscounted spend)."""
    unified_path = COMBINED_DATASETS / "shipments_unified.parquet"

    print("Loading dataset...")
    df_16 = pl.read_parquet(unified_path)
    df_16 = apply_s1_adjustments(df_16, target_earned=0.16)

    df_0 = pl.read_parquet(unified_path)
    df_0 = apply_s1_adjustments(df_0, target_earned=0.0)

    # Add fedex_cost_undiscounted column (= FedEx cost at 0% earned)
    df = df_16.with_columns(
        df_0["fedex_cost_total"].alias("fedex_cost_undiscounted"),
    )

    print(f"  Unified: {df.shape[0]:,} shipments")
    print(f"  FedEx earned discount: {FEDEX_EARNED:.0%}")
    print(f"  FedEx undiscounted threshold: ${FEDEX_UNDISCOUNTED_THRESHOLD:,.0f}")

    return df


def add_scenario_cost(df: pl.DataFrame) -> pl.DataFrame:
    """Add scenario cost with FedEx undiscounted spend constraint.

    Step 1: Unconstrained — cheapest of P2P US, P2P US2, FedEx@16% per shipment
    Step 2: Check FedEx undiscounted spend
    Step 3: If below threshold, switch cheapest-pain P2P shipments to FedEx
    """
    cost_cols = ["p2p_cost_total", "p2p_us2_cost_total", "fedex_cost_total"]
    carrier_labels = ["P2P_US", "P2P_US2", "FEDEX"]

    # Best P2P cost per shipment
    df = df.with_columns(
        pl.min_horizontal("p2p_cost_total", "p2p_us2_cost_total").alias("best_p2p_cost"),
    )

    # Step 1: Unconstrained cheapest
    df = df.with_columns(
        pl.min_horizontal(*cost_cols).alias("s14_cost_unconstrained"),
    )

    # Track unconstrained winner
    carrier_expr = pl.lit(None).cast(pl.Utf8)
    for label, col in reversed(list(zip(carrier_labels, cost_cols))):
        carrier_expr = (
            pl.when(
                pl.col(col).is_not_null() & (pl.col(col) == pl.col("s14_cost_unconstrained"))
            )
            .then(pl.lit(label))
            .otherwise(carrier_expr)
        )
    df = df.with_columns(carrier_expr.alias("s14_unconstrained_carrier"))

    # Step 2: Check FedEx undiscounted spend
    fedex_undisc_unconstrained = float(
        df.filter(pl.col("s14_unconstrained_carrier") == "FEDEX")["fedex_cost_undiscounted"].sum()
    )

    print(f"\n  Unconstrained FedEx undiscounted: ${fedex_undisc_unconstrained:,.2f}")
    print(f"  Threshold: ${FEDEX_UNDISCOUNTED_THRESHOLD:,.2f}")

    if fedex_undisc_unconstrained >= FEDEX_UNDISCOUNTED_THRESHOLD:
        print(f"  Threshold already met! No constraint needed.")
        df = df.with_columns([
            pl.col("s14_cost_unconstrained").alias("s14_cost_total"),
            pl.col("s14_unconstrained_carrier").alias("s14_selected_carrier"),
            pl.lit(False).alias("s14_forced_to_fedex"),
        ])
        return df

    gap = FEDEX_UNDISCOUNTED_THRESHOLD - fedex_undisc_unconstrained
    print(f"  Gap: ${gap:,.2f}")

    # Step 3: Switch cheapest-pain P2P shipments to FedEx
    # Switch pain = FedEx@16% cost minus best P2P cost
    df = df.with_columns(
        (pl.col("fedex_cost_total") - pl.col("best_p2p_cost")).alias("switch_pain"),
    )

    # Only P2P winners can be switched
    p2p_mask = pl.col("s14_unconstrained_carrier").is_in(["P2P_US", "P2P_US2"])

    # Sort all shipments: P2P winners by switch_pain ascending, FedEx winners get infinity
    df = df.with_columns(
        pl.when(p2p_mask)
        .then(pl.col("switch_pain"))
        .otherwise(pl.lit(float("inf")))
        .alias("_sort_pain"),
    )

    # Add cumulative undiscounted FedEx spend for P2P shipments (sorted by pain)
    # We need to rank P2P shipments by switch_pain and pick the cheapest to switch
    df = df.with_row_index("_row_idx")

    p2p_ships = (
        df.filter(p2p_mask)
        .sort("switch_pain")
        .with_columns(
            pl.col("fedex_cost_undiscounted").cum_sum().alias("_cum_undisc"),
        )
    )

    # Find cutoff: which P2P shipments to force to FedEx
    needs_switch = p2p_ships.filter(pl.col("_cum_undisc") >= gap)
    if needs_switch.height == 0:
        print(f"  WARNING: Cannot reach threshold even by switching all P2P to FedEx!")
        # Switch all P2P to FedEx
        switch_idx_set = set(p2p_ships["_row_idx"].to_list())
    else:
        # Find the row where cumulative undiscounted first exceeds gap
        cutoff_row = p2p_ships.with_row_index("_rank").filter(pl.col("_cum_undisc") >= gap).head(1)
        cutoff_rank = int(cutoff_row["_rank"][0])
        switch_rows = p2p_ships.head(cutoff_rank + 1)
        switch_idx_set = set(switch_rows["_row_idx"].to_list())

    n_switched = len(switch_idx_set)
    switch_idx_series = pl.Series("_row_idx", list(switch_idx_set))

    print(f"  Switching {n_switched:,} P2P shipments to FedEx")

    # Mark forced shipments
    df = df.with_columns(
        pl.col("_row_idx").is_in(switch_idx_series).alias("s14_forced_to_fedex"),
    )

    # Final carrier assignment
    df = df.with_columns(
        pl.when(pl.col("s14_forced_to_fedex"))
        .then(pl.lit("FEDEX"))
        .otherwise(pl.col("s14_unconstrained_carrier"))
        .alias("s14_selected_carrier"),
    )

    # Final cost
    df = df.with_columns(
        pl.when(pl.col("s14_forced_to_fedex"))
        .then(pl.col("fedex_cost_total"))
        .otherwise(pl.col("s14_cost_unconstrained"))
        .alias("s14_cost_total"),
    )

    # Verify threshold
    fedex_final_undisc = float(
        df.filter(pl.col("s14_selected_carrier") == "FEDEX")["fedex_cost_undiscounted"].sum()
    )
    print(f"\n  Final FedEx undiscounted: ${fedex_final_undisc:,.2f}")
    print(f"  Threshold met: {fedex_final_undisc >= FEDEX_UNDISCOUNTED_THRESHOLD}")

    # Report switch cost
    forced = df.filter(pl.col("s14_forced_to_fedex"))
    total_switch_pain = float(forced["switch_pain"].sum())
    avg_switch_pain = float(forced["switch_pain"].mean()) if forced.height > 0 else 0
    max_switch_pain = float(forced["switch_pain"].max()) if forced.height > 0 else 0
    print(f"\n  Switch cost analysis:")
    print(f"    Shipments forced P2P->FedEx: {forced.height:,}")
    print(f"    Total extra cost:           ${total_switch_pain:,.2f}")
    print(f"    Avg extra cost/shipment:    ${avg_switch_pain:.2f}")
    print(f"    Max extra cost/shipment:    ${max_switch_pain:.2f}")

    # Clean up temp columns
    df = df.drop(["_sort_pain", "_row_idx"])

    return df


def analyze_totals(df, s1_baseline):
    """Calculate overall cost comparison."""
    print("\n" + "=" * 60)
    print("TOTAL COST ANALYSIS")
    print("=" * 60)

    total_shipments = df.shape[0]
    current_total = s1_baseline
    s14_total = df["s14_cost_total"].sum()
    null_count = df.filter(pl.col("s14_cost_total").is_null()).height

    diff = s14_total - current_total
    diff_pct = (diff / current_total) * 100

    print(f"\nTotal shipments: {total_shipments:,}")
    if null_count > 0:
        print(f"Shipments with no coverage: {null_count:,}")
    print(f"\nCurrent mix total (S1 baseline): ${current_total:,.2f}")
    print(f"S14 P2P+FedEx@16% constrained:  ${s14_total:,.2f}")
    print(f"Difference:                      ${diff:+,.2f} ({diff_pct:+.1f}%)")

    # Reference single carriers
    print(f"\nFor reference (100% single carrier):")
    for label, col in [("OnTrac", "ontrac_cost_total"), ("FedEx@16%", "fedex_cost_total"),
                        ("P2P US", "p2p_cost_total"), ("P2P US2", "p2p_us2_cost_total"),
                        ("USPS", "usps_cost_total"), ("Maersk", "maersk_cost_total")]:
        total = df[col].sum()
        pct = (total - current_total) / current_total * 100
        print(f"  100% {label:<10}: ${total:>12,.2f} ({pct:+.1f}%)")

    avg_current = current_total / total_shipments
    avg_s14 = s14_total / total_shipments
    print(f"\nAvg cost per shipment:")
    print(f"  Current mix:              ${avg_current:.2f}")
    print(f"  P2P+FedEx@16% constrained: ${avg_s14:.2f}")

    # FedEx threshold summary
    fedex_ships = df.filter(pl.col("s14_selected_carrier") == "FEDEX")
    fedex_undisc = fedex_ships["fedex_cost_undiscounted"].sum()
    fedex_cost_16 = fedex_ships["fedex_cost_total"].sum()
    margin = fedex_undisc - 5_000_000
    print(f"\nFedEx threshold analysis:")
    print(f"  FedEx undiscounted spend: ${fedex_undisc:,.2f}")
    print(f"  $5M penalty threshold:   $5,000,000")
    print(f"  Margin above threshold:  ${margin:+,.2f}")
    print(f"  FedEx cost at 16% earned: ${fedex_cost_16:,.2f}")

    return {
        "total_shipments": total_shipments,
        "current_total": current_total,
        "s14_total": s14_total,
        "diff": diff,
        "diff_pct": diff_pct,
        "avg_current": avg_current,
        "avg_s14": avg_s14,
        "null_count": null_count,
        "fedex_undiscounted": float(fedex_undisc),
        "fedex_margin": float(margin),
    }


def analyze_carrier_selection(df):
    """Analyze which carrier was selected per shipment."""
    print("\n" + "=" * 60)
    print("CARRIER SELECTION BREAKDOWN")
    print("=" * 60)

    total = df.shape[0]

    carrier_stats = (
        df
        .group_by("s14_selected_carrier")
        .agg([
            pl.len().alias("shipment_count"),
            pl.col("s14_cost_total").sum().alias("total_cost"),
            pl.col("s14_cost_total").mean().alias("avg_cost"),
            pl.col("weight_lbs").mean().alias("avg_weight"),
            pl.col("s14_forced_to_fedex").sum().alias("forced_count"),
        ])
        .sort("shipment_count", descending=True)
    )

    print(f"\n{'Carrier':<12} {'Shipments':>12} {'% Total':>10} {'Total Cost':>14} {'Avg Cost':>10} {'Avg Wt':>8} {'Forced':>8}")
    print("-" * 78)
    for row in carrier_stats.iter_rows(named=True):
        carrier = row["s14_selected_carrier"] or "None"
        pct = row["shipment_count"] / total * 100
        total_cost = row["total_cost"] or 0.0
        avg_cost = row["avg_cost"] or 0.0
        avg_weight = row["avg_weight"] or 0.0
        forced = row["forced_count"] or 0
        print(f"{carrier:<12} {row['shipment_count']:>12,} {pct:>9.1f}% ${total_cost:>12,.2f} ${avg_cost:>8.2f} {avg_weight:>7.1f} {forced:>8,}")

    # Forced vs natural FedEx
    fedex_rows = df.filter(pl.col("s14_selected_carrier") == "FEDEX")
    natural = fedex_rows.filter(~pl.col("s14_forced_to_fedex"))
    forced = fedex_rows.filter(pl.col("s14_forced_to_fedex"))
    print(f"\n  FedEx breakdown:")
    print(f"    Natural (cheapest):  {natural.height:,} ships, ${natural['s14_cost_total'].sum():,.2f}, avg ${natural['s14_cost_total'].mean():.2f}")
    print(f"    Forced (threshold):  {forced.height:,} ships, ${forced['s14_cost_total'].sum():,.2f}, avg ${forced['s14_cost_total'].mean():.2f}")

    return carrier_stats


def analyze_constraint_impact(df):
    """Analyze the cost of meeting the FedEx constraint."""
    print("\n" + "=" * 60)
    print("CONSTRAINT IMPACT ANALYSIS")
    print("=" * 60)

    unconstrained_total = df["s14_cost_unconstrained"].sum()
    constrained_total = df["s14_cost_total"].sum()
    constraint_cost = constrained_total - unconstrained_total

    print(f"\n  Unconstrained total (P2P+FedEx@16%, no threshold): ${unconstrained_total:,.2f}")
    print(f"  Constrained total (>=${FEDEX_UNDISCOUNTED_THRESHOLD/1e6:.1f}M undiscounted):  ${constrained_total:,.2f}")
    print(f"  Cost of meeting constraint: ${constraint_cost:+,.2f}")

    # What the forced shipments would have cost with their preferred carrier
    forced = df.filter(pl.col("s14_forced_to_fedex"))
    if forced.height > 0:
        p2p_cost = forced["best_p2p_cost"].sum()
        fedex_cost = forced["fedex_cost_total"].sum()
        print(f"\n  Forced shipments ({forced.height:,}):")
        print(f"    Would have cost (P2P):    ${p2p_cost:,.2f} (avg ${p2p_cost/forced.height:.2f})")
        print(f"    Actual cost (FedEx@16%):  ${fedex_cost:,.2f} (avg ${fedex_cost/forced.height:.2f})")
        print(f"    Penalty for forcing:      ${fedex_cost - p2p_cost:+,.2f}")

        # Show which P2P contract they came from
        from_p2p_us = forced.filter(pl.col("s14_unconstrained_carrier") == "P2P_US").height
        from_p2p_us2 = forced.filter(pl.col("s14_unconstrained_carrier") == "P2P_US2").height
        print(f"\n    Originally assigned to:")
        print(f"      P2P US:  {from_p2p_us:,}")
        print(f"      P2P US2: {from_p2p_us2:,}")

    return {
        "unconstrained_total": float(unconstrained_total),
        "constrained_total": float(constrained_total),
        "constraint_cost": float(constraint_cost),
    }


def analyze_vs_other_scenarios(df, s1_baseline):
    """Compare against other scenarios."""
    print("\n" + "=" * 60)
    print("COMPARISON VS OTHER SCENARIOS")
    print("=" * 60)

    s14_total = df["s14_cost_total"].sum()

    scenarios = [
        ("S1  Current mix", 5_971_748.12),
        ("S7  USPS+FedEx+P2P (optimal)", 4_433_040.0),
        ("S10 Static per-packagetype", 4_450_862.0),
        ("S11 Static 3-group", 4_516_218.0),
        ("S8  Conservative $5M buffer", 4_536_690.0),
        ("S14 P2P+FedEx constrained", float(s14_total)),
        ("S13 P2P+FedEx unconstrained", 4_942_666.0),
        ("S6  USPS+FedEx (Drop OnTrac)", 5_040_871.0),
    ]

    print(f"\n  {'Scenario':<35} {'Total':>14} {'vs S1':>10} {'Carriers':>10}")
    print("  " + "-" * 72)
    for name, cost in sorted(scenarios, key=lambda x: x[1]):
        vs_s1 = (cost - s1_baseline) / s1_baseline * 100
        carriers = "2" if "P2P+FedEx" in name else "3" if any(s in name for s in ["S7", "S8", "S10", "S11"]) else "4"
        marker = " ***" if "S14" in name else ""
        print(f"  {name:<35} ${cost:>12,.2f} {vs_s1:>+9.1f}% {carriers:>10}{marker}")

    return {"s14_total": float(s14_total)}


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
            pl.col("s14_cost_total").sum().alias("s14_total"),
            pl.col("cost_current_carrier").mean().alias("current_avg"),
            pl.col("s14_cost_total").mean().alias("s14_avg"),
            (pl.col("s14_selected_carrier") == "P2P_US").sum().alias("p2p_us_count"),
            (pl.col("s14_selected_carrier") == "P2P_US2").sum().alias("p2p_us2_count"),
            (pl.col("s14_selected_carrier") == "FEDEX").sum().alias("fedex_count"),
            pl.col("s14_forced_to_fedex").sum().alias("forced_count"),
        ])
        .sort("weight_bracket")
        .filter(pl.col("weight_bracket") <= 70)
    )

    weight_analysis = weight_analysis.with_columns([
        (pl.col("s14_total") - pl.col("current_total")).alias("diff"),
        ((pl.col("s14_total") - pl.col("current_total")) / pl.col("current_total") * 100).alias("diff_pct"),
    ])

    print(f"\n{'Bracket':<10} {'Ships':>8} {'Current':>10} {'S14':>10} {'Diff %':>8} {'P2P_US':>7} {'P2P_US2':>8} {'FedEx':>7} {'Forced':>7}")
    print("-" * 80)

    for row in weight_analysis.iter_rows(named=True):
        if row["shipment_count"] >= 100:
            bracket = f"{row['weight_bracket']-1}-{row['weight_bracket']}" if row["weight_bracket"] > 1 else "0-1"
            print(f"{bracket:<10} {row['shipment_count']:>8,} ${row['current_avg']:>8.2f} ${row['s14_avg']:>8.2f} {row['diff_pct']:>7.1f}% {row['p2p_us_count']:>7,} {row['p2p_us2_count']:>8,} {row['fedex_count']:>7,} {row['forced_count']:>7,}")

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
            pl.col("s14_cost_total").sum().alias("s14_total"),
            pl.col("cost_current_carrier").mean().alias("current_avg"),
            pl.col("s14_cost_total").mean().alias("s14_avg"),
            pl.col("weight_lbs").mean().alias("avg_weight"),
            (pl.col("s14_selected_carrier") == "P2P_US").sum().alias("p2p_us_count"),
            (pl.col("s14_selected_carrier") == "P2P_US2").sum().alias("p2p_us2_count"),
            (pl.col("s14_selected_carrier") == "FEDEX").sum().alias("fedex_count"),
            pl.col("s14_forced_to_fedex").sum().alias("forced_count"),
        ])
        .sort("shipment_count", descending=True)
    )

    pkg_analysis = pkg_analysis.with_columns([
        (pl.col("s14_total") - pl.col("current_total")).alias("diff"),
        ((pl.col("s14_total") - pl.col("current_total")) / pl.col("current_total") * 100).alias("diff_pct"),
    ])

    print(f"\n{'Package Type':<25} {'Ships':>8} {'Wt':>6} {'Current':>10} {'S14':>10} {'Diff %':>8} {'Forced':>7}")
    print("-" * 78)

    for row in pkg_analysis.head(20).iter_rows(named=True):
        print(f"{row['packagetype'][:25]:<25} {row['shipment_count']:>8,} {row['avg_weight']:>5.1f} ${row['current_avg']:>8.2f} ${row['s14_avg']:>8.2f} {row['diff_pct']:>7.1f}% {row['forced_count']:>7,}")

    return pkg_analysis


def save_results(totals, carrier_stats, constraint, vs_scenarios, weight_analysis, pkg_analysis):
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
            "s14_total",
            "cost_difference",
            "cost_diff_percent",
            "avg_per_shipment_current",
            "avg_per_shipment_s14",
            "shipments_no_coverage",
            "fedex_earned_discount",
            "fedex_undiscounted_spend",
            "fedex_undiscounted_threshold",
            "fedex_margin_above_5m",
            "unconstrained_total",
            "constraint_cost",
        ],
        "value": [
            float(totals["total_shipments"]),
            float(totals["current_total"]),
            float(totals["s14_total"]),
            float(totals["diff"]),
            float(totals["diff_pct"]),
            float(totals["avg_current"]),
            float(totals["avg_s14"]),
            float(totals["null_count"]),
            FEDEX_EARNED,
            float(totals["fedex_undiscounted"]),
            float(FEDEX_UNDISCOUNTED_THRESHOLD),
            float(totals["fedex_margin"]),
            float(constraint["unconstrained_total"]),
            float(constraint["constraint_cost"]),
        ],
    }
    summary_df = pl.DataFrame(summary_data)
    summary_path = RESULTS_DIR / "summary_metrics.csv"
    summary_df.write_csv(summary_path)
    print(f"  Saved: {summary_path}")

    # Placeholder summary.md (will be rewritten with analysis)
    md_lines = [
        "# Scenario 14: P2P + FedEx with 16% Earned Discount (Constrained)",
        "",
        "## Overview",
        "Per-shipment cheapest of P2P US, P2P US2, and FedEx at 16% earned discount,",
        f"with FedEx undiscounted spend constrained to >= ${FEDEX_UNDISCOUNTED_THRESHOLD/1e6:.1f}M",
        "(safely above $5M penalty threshold).",
        "",
        "## Results",
        f"- Total shipments: {totals['total_shipments']:,}",
        f"- Current mix (S1): ${totals['current_total']:,.2f}",
        f"- S14 P2P+FedEx@16%: ${totals['s14_total']:,.2f}",
        f"- **Difference: ${totals['diff']:+,.2f} ({totals['diff_pct']:+.1f}%)**",
        f"- FedEx undiscounted: ${totals['fedex_undiscounted']:,.2f} (margin: ${totals['fedex_margin']:+,.2f} above $5M)",
        f"- Cost of constraint: ${constraint['constraint_cost']:,.2f}",
    ]

    summary_md_path = RESULTS_DIR / "summary.md"
    summary_md_path.write_text("\n".join(md_lines))
    print(f"  Saved: {summary_md_path}")


def main():
    """Run complete Scenario 14 analysis."""
    print("=" * 60)
    print("SCENARIO 14: P2P + FEDEX WITH 16% EARNED (CONSTRAINED)")
    print("=" * 60)
    print(f"\nPer-shipment cheapest of P2P US, P2P US2, FedEx@16%.")
    print(f"FedEx undiscounted spend >= ${FEDEX_UNDISCOUNTED_THRESHOLD/1e6:.1f}M.")
    print(f"2 carrier relationships, FedEx at {FEDEX_EARNED:.0%} earned discount.")

    # Load data
    df = load_data()

    # Add scenario cost with constraint
    df = add_scenario_cost(df)

    # Run analyses
    s1_baseline = compute_s1_baseline()
    totals = analyze_totals(df, s1_baseline)
    carrier_stats = analyze_carrier_selection(df)
    constraint = analyze_constraint_impact(df)
    vs_scenarios = analyze_vs_other_scenarios(df, s1_baseline)
    weight_analysis = analyze_weight_brackets(df)
    pkg_analysis = analyze_packagetype(df)

    # Save results
    save_results(totals, carrier_stats, constraint, vs_scenarios, weight_analysis, pkg_analysis)

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)

    return totals, carrier_stats, constraint, vs_scenarios, weight_analysis, pkg_analysis


if __name__ == "__main__":
    main()
