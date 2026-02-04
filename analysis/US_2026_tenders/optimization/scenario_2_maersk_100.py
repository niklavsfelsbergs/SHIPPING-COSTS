"""
Scenario 2: 100% Maersk Analysis

Calculates what shipping costs would be if all US shipments went to Maersk.
Analyzes cost drivers including weight brackets, zones, and surcharges.

Maersk US is NOT currently used - this is a future assessment scenario.
"""

import polars as pl
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
COMBINED_DATASETS = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "combined_datasets"
RESULTS_DIR = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "results" / "scenario_2_maersk_100"


def load_data():
    """Load both aggregated and unified datasets."""
    agg_path = COMBINED_DATASETS / "shipments_aggregated.parquet"
    unified_path = COMBINED_DATASETS / "shipments_unified.parquet"

    print("Loading datasets...")
    df_agg = pl.read_parquet(agg_path)
    df_unified = pl.read_parquet(unified_path)

    print(f"  Aggregated: {df_agg.shape[0]:,} groups")
    print(f"  Unified: {df_unified.shape[0]:,} shipments")

    return df_agg, df_unified


def analyze_totals(df_agg):
    """Calculate overall cost comparison."""
    print("\n" + "=" * 60)
    print("TOTAL COST ANALYSIS")
    print("=" * 60)

    total_shipments = df_agg["shipment_count"].sum()
    current_total = df_agg["cost_current_carrier_total"].sum()
    maersk_total = df_agg["maersk_cost_total"].sum()

    diff = maersk_total - current_total
    diff_pct = (diff / current_total) * 100
    avg_per_shipment_current = current_total / total_shipments
    avg_per_shipment_maersk = maersk_total / total_shipments

    print(f"\nTotal shipments: {total_shipments:,}")
    print(f"\nCurrent mix total:     ${current_total:,.2f}")
    print(f"100% Maersk total:     ${maersk_total:,.2f}")
    print(f"Difference:            ${diff:+,.2f} ({diff_pct:+.1f}%)")
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


def analyze_weight_brackets(df_unified):
    """Analyze costs by weight bracket, highlighting the 30 lb rate jump."""
    print("\n" + "=" * 60)
    print("COST BY WEIGHT BRACKET")
    print("=" * 60)

    # Add weight bracket column
    df = df_unified.with_columns(
        pl.col("weight_lbs").ceil().cast(pl.Int32).alias("weight_bracket")
    )

    # Group by weight bracket
    weight_analysis = (
        df
        .group_by("weight_bracket")
        .agg([
            pl.len().alias("shipment_count"),
            pl.col("cost_current_carrier").sum().alias("current_total"),
            pl.col("maersk_cost_total").sum().alias("maersk_total"),
            pl.col("cost_current_carrier").mean().alias("current_avg"),
            pl.col("maersk_cost_total").mean().alias("maersk_avg"),
            pl.col("maersk_cost_base").mean().alias("maersk_base_avg"),
        ])
        .sort("weight_bracket")
        .filter(pl.col("weight_bracket") <= 70)  # Max Maersk weight
    )

    # Calculate difference
    weight_analysis = weight_analysis.with_columns([
        (pl.col("maersk_total") - pl.col("current_total")).alias("diff"),
        ((pl.col("maersk_total") - pl.col("current_total")) / pl.col("current_total") * 100).alias("diff_pct"),
    ])

    # Print summary table
    print("\nWeight bracket analysis (1 lb increments):")
    print(f"{'Bracket':<10} {'Shipments':>12} {'Current Avg':>12} {'Maersk Avg':>12} {'Diff':>10} {'Diff %':>10}")
    print("-" * 68)

    for row in weight_analysis.iter_rows(named=True):
        if row["shipment_count"] >= 100:  # Only show brackets with significant volume
            bracket = f"{row['weight_bracket']-1}-{row['weight_bracket']} lbs" if row["weight_bracket"] > 1 else "0-1 lbs"
            print(f"{bracket:<10} {row['shipment_count']:>12,} ${row['current_avg']:>10.2f} ${row['maersk_avg']:>10.2f} ${row['maersk_avg'] - row['current_avg']:>8.2f} {row['diff_pct']:>9.1f}%")

    # Highlight the 30 lb rate jump
    print("\n*** 30 lb Rate Jump Analysis ***")
    before_30 = weight_analysis.filter(pl.col("weight_bracket") <= 30)
    after_30 = weight_analysis.filter(pl.col("weight_bracket") > 30)

    shipments_under_30 = before_30["shipment_count"].sum()
    shipments_over_30 = after_30["shipment_count"].sum()
    total_shipments = shipments_under_30 + shipments_over_30

    cost_under_30 = before_30["maersk_total"].sum()
    cost_over_30 = after_30["maersk_total"].sum()
    total_maersk = cost_under_30 + cost_over_30

    print(f"\nShipments <= 30 lbs: {shipments_under_30:,} ({shipments_under_30/total_shipments*100:.1f}%)")
    print(f"Shipments > 30 lbs:  {shipments_over_30:,} ({shipments_over_30/total_shipments*100:.1f}%)")
    print(f"\nMaersk cost <= 30 lbs: ${cost_under_30:,.2f} ({cost_under_30/total_maersk*100:.1f}%)")
    print(f"Maersk cost > 30 lbs:  ${cost_over_30:,.2f} ({cost_over_30/total_maersk*100:.1f}%)")

    # Average cost comparison around 30 lb boundary
    around_30 = weight_analysis.filter(
        (pl.col("weight_bracket") >= 28) & (pl.col("weight_bracket") <= 33)
    )
    print("\nDetailed view around 30 lb boundary:")
    print(f"{'Bracket':<12} {'Shipments':>10} {'Maersk Base':>12} {'Maersk Total':>12}")
    print("-" * 48)
    for row in around_30.iter_rows(named=True):
        bracket = f"{row['weight_bracket']-1}-{row['weight_bracket']} lbs"
        print(f"{bracket:<12} {row['shipment_count']:>10,} ${row['maersk_base_avg']:>10.2f} ${row['maersk_avg']:>10.2f}")

    return weight_analysis


def analyze_zones(df_unified):
    """Analyze costs by shipping zone."""
    print("\n" + "=" * 60)
    print("COST BY ZONE")
    print("=" * 60)

    zone_analysis = (
        df_unified
        .group_by("maersk_shipping_zone")
        .agg([
            pl.len().alias("shipment_count"),
            pl.col("cost_current_carrier").sum().alias("current_total"),
            pl.col("maersk_cost_total").sum().alias("maersk_total"),
            pl.col("cost_current_carrier").mean().alias("current_avg"),
            pl.col("maersk_cost_total").mean().alias("maersk_avg"),
            pl.col("maersk_cost_base").mean().alias("maersk_base_avg"),
            pl.col("maersk_cost_pickup").mean().alias("maersk_pickup_avg"),
        ])
        .sort("maersk_shipping_zone")
    )

    zone_analysis = zone_analysis.with_columns([
        (pl.col("maersk_total") - pl.col("current_total")).alias("diff"),
        ((pl.col("maersk_total") - pl.col("current_total")) / pl.col("current_total") * 100).alias("diff_pct"),
    ])

    print(f"\n{'Zone':>6} {'Shipments':>12} {'Current Avg':>12} {'Maersk Avg':>12} {'Diff':>10} {'Diff %':>10}")
    print("-" * 64)

    for row in zone_analysis.iter_rows(named=True):
        zone = row["maersk_shipping_zone"]
        print(f"{zone:>6} {row['shipment_count']:>12,} ${row['current_avg']:>10.2f} ${row['maersk_avg']:>10.2f} ${row['maersk_avg'] - row['current_avg']:>8.2f} {row['diff_pct']:>9.1f}%")

    # Zone distribution
    total_shipments = zone_analysis["shipment_count"].sum()
    print("\nZone distribution:")
    for row in zone_analysis.iter_rows(named=True):
        pct = row["shipment_count"] / total_shipments * 100
        print(f"  Zone {row['maersk_shipping_zone']}: {row['shipment_count']:,} shipments ({pct:.1f}%)")

    return zone_analysis


def analyze_surcharges(df_unified):
    """Analyze Maersk surcharge breakdown."""
    print("\n" + "=" * 60)
    print("SURCHARGE BREAKDOWN")
    print("=" * 60)

    # Calculate surcharge totals
    total_base = df_unified["maersk_cost_base"].sum()
    total_nsl1 = df_unified["maersk_cost_nsl1"].sum()
    total_nsl2 = df_unified["maersk_cost_nsl2"].sum()
    total_nsd = df_unified["maersk_cost_nsd"].sum()
    total_pickup = df_unified["maersk_cost_pickup"].sum()
    total_cost = df_unified["maersk_cost_total"].sum()

    # Count shipments with each surcharge
    count_nsl1 = df_unified.filter(pl.col("maersk_cost_nsl1") > 0).shape[0]
    count_nsl2 = df_unified.filter(pl.col("maersk_cost_nsl2") > 0).shape[0]
    count_nsd = df_unified.filter(pl.col("maersk_cost_nsd") > 0).shape[0]
    total_shipments = df_unified.shape[0]

    print("\nCost component breakdown:")
    print(f"{'Component':<20} {'Total Cost':>14} {'% of Total':>12} {'Shipments':>12} {'% Shipments':>12}")
    print("-" * 72)
    print(f"{'Base Rate':<20} ${total_base:>12,.2f} {total_base/total_cost*100:>11.1f}% {total_shipments:>12,} {'100.0%':>12}")
    print(f"{'NSL1 (>21\")':<20} ${total_nsl1:>12,.2f} {total_nsl1/total_cost*100:>11.1f}% {count_nsl1:>12,} {count_nsl1/total_shipments*100:>11.1f}%")
    print(f"{'NSL2 (>30\")':<20} ${total_nsl2:>12,.2f} {total_nsl2/total_cost*100:>11.1f}% {count_nsl2:>12,} {count_nsl2/total_shipments*100:>11.1f}%")
    print(f"{'NSD (>3456 cu in)':<20} ${total_nsd:>12,.2f} {total_nsd/total_cost*100:>11.1f}% {count_nsd:>12,} {count_nsd/total_shipments*100:>11.1f}%")
    print(f"{'Pickup ($0.04/lb)':<20} ${total_pickup:>12,.2f} {total_pickup/total_cost*100:>11.1f}% {total_shipments:>12,} {'100.0%':>12}")
    print("-" * 72)
    print(f"{'TOTAL':<20} ${total_cost:>12,.2f} {'100.0%':>12}")

    # Surcharge overlap analysis
    print("\nSurcharge overlap analysis:")
    both_nsl_nsd = df_unified.filter(
        ((pl.col("maersk_cost_nsl1") > 0) | (pl.col("maersk_cost_nsl2") > 0)) &
        (pl.col("maersk_cost_nsd") > 0)
    ).shape[0]
    print(f"  Shipments with NSL (1 or 2) + NSD: {both_nsl_nsd:,} ({both_nsl_nsd/total_shipments*100:.2f}%)")

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
            pl.col("maersk_billable_weight").mean().alias("avg_billable_weight"),
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


def analyze_top_cost_drivers(df_unified, df_agg):
    """Identify segments where Maersk is most expensive vs cheapest."""
    print("\n" + "=" * 60)
    print("TOP COST DRIVER SEGMENTS")
    print("=" * 60)

    # Add weight bracket
    df = df_agg.with_columns([
        (pl.col("maersk_cost_total") - pl.col("cost_current_carrier_total")).alias("cost_diff"),
        ((pl.col("maersk_cost_total") - pl.col("cost_current_carrier_total")) / pl.col("cost_current_carrier_total") * 100).alias("cost_diff_pct"),
    ])

    # Top segments where Maersk is more expensive
    print("\n--- Segments where Maersk is MOST EXPENSIVE (top 10 by cost difference) ---")
    expensive_segments = (
        df
        .filter(pl.col("shipment_count") >= 50)  # Minimum volume threshold
        .sort("cost_diff", descending=True)
        .head(10)
    )

    print(f"{'Package Type':<20} {'ZIP':>6} {'Weight':>7} {'Ships':>8} {'Diff':>12} {'Diff %':>10}")
    print("-" * 65)
    for row in expensive_segments.iter_rows(named=True):
        print(f"{row['packagetype'][:20]:<20} {row['shipping_zip_code']:>6} {row['weight_bracket']:>5} lb {row['shipment_count']:>8,} ${row['cost_diff']:>10,.2f} {row['cost_diff_pct']:>9.1f}%")

    # Top segments where Maersk is cheaper
    print("\n--- Segments where Maersk is CHEAPEST (top 10 by cost savings) ---")
    cheap_segments = (
        df
        .filter(pl.col("shipment_count") >= 50)
        .sort("cost_diff")
        .head(10)
    )

    print(f"{'Package Type':<20} {'ZIP':>6} {'Weight':>7} {'Ships':>8} {'Savings':>12} {'Diff %':>10}")
    print("-" * 65)
    for row in cheap_segments.iter_rows(named=True):
        print(f"{row['packagetype'][:20]:<20} {row['shipping_zip_code']:>6} {row['weight_bracket']:>5} lb {row['shipment_count']:>8,} ${-row['cost_diff']:>10,.2f} {row['cost_diff_pct']:>9.1f}%")

    return expensive_segments, cheap_segments


def compare_carriers(df_agg):
    """Compare Maersk to other carriers."""
    print("\n" + "=" * 60)
    print("CARRIER COMPARISON")
    print("=" * 60)

    total_shipments = df_agg["shipment_count"].sum()

    # Calculate totals for all carriers
    carriers = {
        "Current Mix": df_agg["cost_current_carrier_total"].sum(),
        "OnTrac": df_agg["ontrac_cost_total"].sum(),
        "USPS": df_agg["usps_cost_total"].sum(),
        "FedEx": df_agg["fedex_cost_total"].sum(),
        "P2P": df_agg["p2p_cost_total"].sum(),
        "Maersk": df_agg["maersk_cost_total"].sum(),
    }

    current = carriers["Current Mix"]

    print(f"\n{'Carrier':<15} {'Total Cost':>14} {'Avg/Ship':>10} {'vs Current':>12} {'Diff %':>10}")
    print("-" * 63)
    for carrier, total in carriers.items():
        avg = total / total_shipments
        diff = total - current
        diff_pct = (diff / current) * 100
        print(f"{carrier:<15} ${total:>12,.2f} ${avg:>8.2f} ${diff:>10,.2f} {diff_pct:>9.1f}%")

    # Maersk rank
    sorted_carriers = sorted([(k, v) for k, v in carriers.items() if k != "Current Mix"], key=lambda x: x[1])
    maersk_rank = next(i+1 for i, (k, v) in enumerate(sorted_carriers) if k == "Maersk")
    print(f"\nMaersk rank: #{maersk_rank} out of 5 carriers (by total cost)")

    return carriers


def save_results(totals, weight_analysis, zone_analysis, surcharges, pkg_analysis):
    """Save analysis results to CSV files."""
    print("\n" + "=" * 60)
    print("SAVING RESULTS")
    print("=" * 60)

    # Ensure results directory exists
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Save weight analysis
    weight_path = RESULTS_DIR / "cost_by_weight_bracket.csv"
    weight_analysis.write_csv(weight_path)
    print(f"  Saved: {weight_path}")

    # Save zone analysis
    zone_path = RESULTS_DIR / "cost_by_zone.csv"
    zone_analysis.write_csv(zone_path)
    print(f"  Saved: {zone_path}")

    # Save package type analysis
    pkg_path = RESULTS_DIR / "cost_by_packagetype.csv"
    pkg_analysis.write_csv(pkg_path)
    print(f"  Saved: {pkg_path}")

    # Save summary metrics
    summary_data = {
        "metric": [
            "total_shipments",
            "current_mix_total",
            "maersk_total",
            "cost_difference",
            "cost_diff_percent",
            "avg_per_shipment_current",
            "avg_per_shipment_maersk",
            "surcharge_nsl1_total",
            "surcharge_nsl2_total",
            "surcharge_nsd_total",
            "surcharge_pickup_total",
            "base_rate_total",
        ],
        "value": [
            float(totals["total_shipments"]),
            float(totals["current_total"]),
            float(totals["maersk_total"]),
            float(totals["diff"]),
            float(totals["diff_pct"]),
            float(totals["avg_current"]),
            float(totals["avg_maersk"]),
            float(surcharges["total_nsl1"]),
            float(surcharges["total_nsl2"]),
            float(surcharges["total_nsd"]),
            float(surcharges["total_pickup"]),
            float(surcharges["total_base"]),
        ],
    }
    summary_df = pl.DataFrame(summary_data)
    summary_path = RESULTS_DIR / "summary_metrics.csv"
    summary_df.write_csv(summary_path)
    print(f"  Saved: {summary_path}")


def main():
    """Run complete Scenario 2 analysis."""
    print("=" * 60)
    print("SCENARIO 2: 100% MAERSK ANALYSIS")
    print("=" * 60)
    print("\nThis scenario calculates what shipping costs would be if all")
    print("US shipments were routed to Maersk (currently not used).")

    # Load data
    df_agg, df_unified = load_data()

    # Run analyses
    totals = analyze_totals(df_agg)
    weight_analysis = analyze_weight_brackets(df_unified)
    zone_analysis = analyze_zones(df_unified)
    surcharges = analyze_surcharges(df_unified)
    pkg_analysis = analyze_packagetype(df_unified)
    analyze_top_cost_drivers(df_unified, df_agg)
    compare_carriers(df_agg)

    # Save results
    save_results(totals, weight_analysis, zone_analysis, surcharges, pkg_analysis)

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)

    return totals, weight_analysis, zone_analysis, surcharges, pkg_analysis


if __name__ == "__main__":
    main()
