"""
Scenario 9: 100% Maersk with Discounted NSD Surcharge

Same as Scenario 2 (100% Maersk) but with the NSD (Non-Standard Dimensions)
surcharge reduced from $18 to $9.

All other rates and surcharges remain unchanged.
"""

import polars as pl
from pathlib import Path

from analysis.US_2026_tenders.optimization.baseline import compute_s1_baseline

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
COMBINED_DATASETS = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "combined_datasets"
RESULTS_DIR = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "results" / "scenario_9_maersk_discounted"

# NSD surcharge adjustment
NSD_ORIGINAL = 18.00
NSD_DISCOUNTED = 9.00


def load_data():
    """Load unified dataset with NSD adjustment, then re-aggregate."""
    agg_path = COMBINED_DATASETS / "shipments_aggregated.parquet"
    unified_path = COMBINED_DATASETS / "shipments_unified.parquet"

    print("Loading datasets...")
    df_agg = pl.read_parquet(agg_path)
    df_unified = pl.read_parquet(unified_path)

    print(f"  Aggregated: {df_agg.shape[0]:,} groups")
    print(f"  Unified: {df_unified.shape[0]:,} shipments")

    # Apply NSD discount: $18 -> $9 on unified (has per-shipment breakdown)
    nsd_affected = df_unified.filter(pl.col("maersk_cost_nsd") > 0).height

    print(f"\n  NSD adjustment: ${NSD_ORIGINAL:.0f} -> ${NSD_DISCOUNTED:.0f}")
    print(f"  Affected shipments: {nsd_affected:,}")

    df_unified = df_unified.with_columns(
        pl.when(pl.col("maersk_cost_nsd") > 0)
        .then(pl.lit(NSD_DISCOUNTED))
        .otherwise(pl.col("maersk_cost_nsd"))
        .alias("maersk_cost_nsd")
    ).with_columns(
        (pl.col("maersk_cost_base") + pl.col("maersk_cost_nsl1") +
         pl.col("maersk_cost_nsl2") + pl.col("maersk_cost_nsd") +
         pl.col("maersk_cost_pickup")).alias("maersk_cost_total")
    )

    # Re-aggregate maersk_cost_total in the aggregated dataset
    # Compute new group totals from unified
    maersk_agg = (
        df_unified
        .with_columns(pl.col("weight_lbs").ceil().cast(pl.Int32).alias("weight_bracket"))
        .group_by(["packagetype", "shipping_zip_code", "weight_bracket"])
        .agg(
            pl.col("maersk_cost_total").sum().alias("maersk_cost_total_new"),
            pl.col("maersk_cost_total").mean().alias("maersk_cost_avg_new"),
        )
    )

    df_agg = (
        df_agg
        .drop(["maersk_cost_total", "maersk_cost_avg"])
        .join(maersk_agg, on=["packagetype", "shipping_zip_code", "weight_bracket"], how="left")
        .rename({"maersk_cost_total_new": "maersk_cost_total", "maersk_cost_avg_new": "maersk_cost_avg"})
    )

    total_saving = nsd_affected * (NSD_ORIGINAL - NSD_DISCOUNTED)
    print(f"  Total NSD saving: ${total_saving:,.2f}")

    return df_agg, df_unified


def analyze_totals(df_agg, s1_baseline):
    """Calculate overall cost comparison using the S1 baseline."""
    print("\n" + "=" * 60)
    print("TOTAL COST ANALYSIS")
    print("=" * 60)

    total_shipments = df_agg["shipment_count"].sum()
    current_total = s1_baseline
    maersk_total = df_agg["maersk_cost_total"].sum()

    diff = maersk_total - current_total
    diff_pct = (diff / current_total) * 100
    avg_per_shipment_current = current_total / total_shipments
    avg_per_shipment_maersk = maersk_total / total_shipments

    print(f"\nTotal shipments: {total_shipments:,}")
    print(f"\nCurrent mix total (S1 baseline): ${current_total:,.2f}")
    print(f"100% Maersk (NSD discounted):    ${maersk_total:,.2f}")
    print(f"Difference:                      ${diff:+,.2f} ({diff_pct:+.1f}%)")
    print(f"\nAvg cost per shipment:")
    print(f"  Current mix: ${avg_per_shipment_current:.2f}")
    print(f"  Maersk:      ${avg_per_shipment_maersk:.2f}")

    return {
        "total_shipments": total_shipments,
        "current_total": current_total,
        "maersk_total": maersk_total,
        "diff": diff,
        "diff_pct": diff_pct,
        "avg_current": avg_per_shipment_current,
        "avg_maersk": avg_per_shipment_maersk,
    }


def analyze_surcharges(df_unified):
    """Analyze Maersk surcharge breakdown with discounted NSD."""
    print("\n" + "=" * 60)
    print("SURCHARGE BREAKDOWN")
    print("=" * 60)

    total_base = df_unified["maersk_cost_base"].sum()
    total_nsl1 = df_unified["maersk_cost_nsl1"].sum()
    total_nsl2 = df_unified["maersk_cost_nsl2"].sum()
    total_nsd = df_unified["maersk_cost_nsd"].sum()
    total_pickup = df_unified["maersk_cost_pickup"].sum()
    total_cost = df_unified["maersk_cost_total"].sum()

    count_nsl1 = df_unified.filter(pl.col("maersk_cost_nsl1") > 0).shape[0]
    count_nsl2 = df_unified.filter(pl.col("maersk_cost_nsl2") > 0).shape[0]
    count_nsd = df_unified.filter(pl.col("maersk_cost_nsd") > 0).shape[0]
    total_shipments = df_unified.shape[0]

    print("\nCost component breakdown:")
    print(f"{'Component':<25} {'Total Cost':>14} {'% of Total':>12} {'Shipments':>12} {'% Shipments':>12}")
    print("-" * 77)
    print(f"{'Base Rate':<25} ${total_base:>12,.2f} {total_base/total_cost*100:>11.1f}% {total_shipments:>12,} {'100.0%':>12}")
    print(f"{'NSL1 (>21\")':<25} ${total_nsl1:>12,.2f} {total_nsl1/total_cost*100:>11.1f}% {count_nsl1:>12,} {count_nsl1/total_shipments*100:>11.1f}%")
    print(f"{'NSL2 (>30\")':<25} ${total_nsl2:>12,.2f} {total_nsl2/total_cost*100:>11.1f}% {count_nsl2:>12,} {count_nsl2/total_shipments*100:>11.1f}%")
    print(f"{'NSD (>3456 cu in) @$9':<25} ${total_nsd:>12,.2f} {total_nsd/total_cost*100:>11.1f}% {count_nsd:>12,} {count_nsd/total_shipments*100:>11.1f}%")
    print(f"{'Pickup ($0.04/lb)':<25} ${total_pickup:>12,.2f} {total_pickup/total_cost*100:>11.1f}% {total_shipments:>12,} {'100.0%':>12}")
    print("-" * 77)
    print(f"{'TOTAL':<25} ${total_cost:>12,.2f} {'100.0%':>12}")

    return {
        "total_base": total_base,
        "total_nsl1": total_nsl1,
        "total_nsl2": total_nsl2,
        "total_nsd": total_nsd,
        "total_pickup": total_pickup,
        "total_cost": total_cost,
        "count_nsl1": count_nsl1,
        "count_nsl2": count_nsl2,
        "count_nsd": count_nsd,
    }


def analyze_packagetype(df_unified):
    """Analyze costs by package type."""
    print("\n" + "=" * 60)
    print("COST BY PACKAGE TYPE")
    print("=" * 60)

    pkg_analysis = (
        df_unified
        .group_by("packagetype")
        .agg([
            pl.len().alias("shipment_count"),
            pl.col("cost_current_carrier").sum().alias("current_total"),
            pl.col("maersk_cost_total").sum().alias("maersk_total"),
            pl.col("cost_current_carrier").mean().alias("current_avg"),
            pl.col("maersk_cost_total").mean().alias("maersk_avg"),
            pl.col("weight_lbs").mean().alias("avg_weight"),
        ])
        .sort("shipment_count", descending=True)
    )

    pkg_analysis = pkg_analysis.with_columns([
        (pl.col("maersk_total") - pl.col("current_total")).alias("diff"),
        ((pl.col("maersk_total") - pl.col("current_total")) / pl.col("current_total") * 100).alias("diff_pct"),
    ])

    print(f"\n{'Package Type':<25} {'Shipments':>10} {'Avg Wt':>8} {'Current':>10} {'Maersk':>10} {'Diff %':>10}")
    print("-" * 75)

    for row in pkg_analysis.head(20).iter_rows(named=True):
        print(f"{row['packagetype'][:25]:<25} {row['shipment_count']:>10,} {row['avg_weight']:>7.1f} ${row['current_avg']:>8.2f} ${row['maersk_avg']:>8.2f} {row['diff_pct']:>9.1f}%")

    return pkg_analysis


def save_results(totals, surcharges, pkg_analysis):
    """Save analysis results."""
    print("\n" + "=" * 60)
    print("SAVING RESULTS")
    print("=" * 60)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Save package type analysis
    pkg_path = RESULTS_DIR / "cost_by_packagetype.csv"
    pkg_analysis.write_csv(pkg_path)
    print(f"  Saved: {pkg_path}")

    # Save summary
    summary_lines = [
        "# Scenario 9: 100% Maersk with Discounted NSD",
        "",
        "## Overview",
        f"Same as S2 (100% Maersk) but NSD surcharge reduced from ${NSD_ORIGINAL:.0f} to ${NSD_DISCOUNTED:.0f}.",
        "",
        "## Results",
        f"- Total shipments: {totals['total_shipments']:,}",
        f"- S1 baseline (current mix): ${totals['current_total']:,.0f}",
        f"- S9 Maersk discounted: ${totals['maersk_total']:,.0f}",
        f"- Difference vs S1: ${totals['diff']:+,.0f} ({totals['diff_pct']:+.1f}%)",
        f"- Avg per shipment: ${totals['avg_maersk']:.2f} (vs ${totals['avg_current']:.2f} current)",
        "",
        "## Surcharge Breakdown",
        f"- Base rate: ${surcharges['total_base']:,.0f}",
        f"- NSL1: ${surcharges['total_nsl1']:,.0f} ({surcharges['count_nsl1']:,} shipments)",
        f"- NSL2: ${surcharges['total_nsl2']:,.0f} ({surcharges['count_nsl2']:,} shipments)",
        f"- NSD @$9: ${surcharges['total_nsd']:,.0f} ({surcharges['count_nsd']:,} shipments)",
        f"- Pickup: ${surcharges['total_pickup']:,.0f}",
        f"- **Total: ${surcharges['total_cost']:,.0f}**",
    ]

    summary_path = RESULTS_DIR / "summary.md"
    summary_path.write_text("\n".join(summary_lines))
    print(f"  Saved: {summary_path}")


def main():
    """Run Scenario 9 analysis."""
    print("=" * 60)
    print("SCENARIO 9: 100% MAERSK WITH DISCOUNTED NSD")
    print(f"  NSD surcharge: ${NSD_ORIGINAL:.0f} -> ${NSD_DISCOUNTED:.0f}")
    print("=" * 60)

    df_agg, df_unified = load_data()

    s1_baseline = compute_s1_baseline()
    totals = analyze_totals(df_agg, s1_baseline)
    surcharges = analyze_surcharges(df_unified)
    pkg_analysis = analyze_packagetype(df_unified)

    save_results(totals, surcharges, pkg_analysis)

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)

    return totals, surcharges, pkg_analysis


if __name__ == "__main__":
    main()
