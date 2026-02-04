"""
Scenario 1: Current Carrier Mix Baseline

Calculates the total expected shipping cost using the current carrier routing
(as recorded in pcs_shipping_provider) with 2026 calculated rates.

This serves as the baseline for comparing optimization scenarios.
"""

import polars as pl
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
COMBINED_DATASETS = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "combined_datasets"
RESULTS_DIR = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "results" / "scenario_1_current_mix"


def map_provider_to_carrier(provider: str) -> str:
    """Map pcs_shipping_provider to carrier name."""
    if provider == "ONTRAC":
        return "OnTrac"
    elif provider == "USPS":
        return "USPS"
    elif provider and "FX" in provider:
        return "FedEx"
    elif provider and "DHL" in provider:
        return "DHL (unmapped)"
    else:
        return "Other"


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Scenario 1: Current Carrier Mix Baseline")
    print("=" * 60)

    # Load unified dataset (shipment-level data with actual carrier assignments)
    print("\nLoading shipments_unified.parquet...")
    df = pl.read_parquet(COMBINED_DATASETS / "shipments_unified.parquet")
    print(f"  Total shipments: {df.shape[0]:,}")

    # Add carrier mapping
    df = df.with_columns(
        pl.col("pcs_shipping_provider")
        .map_elements(map_provider_to_carrier, return_dtype=pl.Utf8)
        .alias("carrier")
    )

    # =================================================================
    # TOTAL COST
    # =================================================================
    print("\n" + "-" * 60)
    print("TOTAL COST")
    print("-" * 60)

    total_shipments = df.shape[0]
    total_cost = df["cost_current_carrier"].sum()
    dhl_shipments = df.filter(pl.col("carrier") == "DHL (unmapped)").shape[0]
    mapped_shipments = total_shipments - dhl_shipments

    print(f"\n  Total shipments:      {total_shipments:>12,}")
    print(f"  Mapped shipments:     {mapped_shipments:>12,} ({mapped_shipments/total_shipments*100:.1f}%)")
    print(f"  Unmapped (DHL):       {dhl_shipments:>12,} ({dhl_shipments/total_shipments*100:.1f}%)")
    print(f"\n  Total expected cost:  ${total_cost:>15,.2f}")
    print(f"  Average cost/shipment: ${total_cost/mapped_shipments:>13,.2f} (mapped only)")

    # =================================================================
    # BREAKDOWN BY CARRIER
    # =================================================================
    print("\n" + "-" * 60)
    print("BREAKDOWN BY CARRIER")
    print("-" * 60)

    carrier_summary = df.group_by("carrier").agg([
        pl.len().alias("shipment_count"),
        pl.col("cost_current_carrier").sum().alias("total_cost"),
        pl.col("cost_current_carrier").mean().alias("avg_cost"),
        pl.col("cost_current_carrier").is_null().sum().alias("null_costs"),
    ]).sort("total_cost", descending=True)

    print("\n  {:20} {:>12} {:>10} {:>15} {:>12}".format(
        "Carrier", "Shipments", "Share", "Total Cost", "Avg Cost"
    ))
    print("  " + "-" * 71)

    carrier_data = []
    for row in carrier_summary.iter_rows(named=True):
        carrier = row["carrier"]
        count = row["shipment_count"]
        cost = row["total_cost"] if row["total_cost"] else 0
        avg = row["avg_cost"] if row["avg_cost"] else 0
        share = count / total_shipments * 100

        carrier_data.append({
            "carrier": carrier,
            "shipment_count": count,
            "share_pct": share,
            "total_cost": cost,
            "avg_cost": avg
        })

        print("  {:20} {:>12,} {:>9.1f}% ${:>14,.2f} ${:>11,.2f}".format(
            carrier, count, share, cost, avg
        ))

    # =================================================================
    # BREAKDOWN BY PROVIDER (detailed FedEx services)
    # =================================================================
    print("\n" + "-" * 60)
    print("BREAKDOWN BY PROVIDER (detailed)")
    print("-" * 60)

    provider_summary = df.group_by("pcs_shipping_provider").agg([
        pl.len().alias("shipment_count"),
        pl.col("cost_current_carrier").sum().alias("total_cost"),
        pl.col("cost_current_carrier").mean().alias("avg_cost"),
    ]).sort("shipment_count", descending=True)

    print("\n  {:25} {:>12} {:>10} {:>15} {:>12}".format(
        "Provider", "Shipments", "Share", "Total Cost", "Avg Cost"
    ))
    print("  " + "-" * 76)

    provider_data = []
    for row in provider_summary.iter_rows(named=True):
        provider = row["pcs_shipping_provider"]
        count = row["shipment_count"]
        cost = row["total_cost"] if row["total_cost"] else 0
        avg = row["avg_cost"] if row["avg_cost"] else 0
        share = count / total_shipments * 100

        provider_data.append({
            "provider": provider,
            "shipment_count": count,
            "share_pct": share,
            "total_cost": cost,
            "avg_cost": avg
        })

        print("  {:25} {:>12,} {:>9.1f}% ${:>14,.2f} ${:>11,.2f}".format(
            provider, count, share, cost, avg
        ))

    # =================================================================
    # BREAKDOWN BY PACKAGE TYPE
    # =================================================================
    print("\n" + "-" * 60)
    print("BREAKDOWN BY PACKAGE TYPE (Top 15)")
    print("-" * 60)

    # Filter to mapped shipments only for package type analysis
    df_mapped = df.filter(pl.col("carrier") != "DHL (unmapped)")

    packagetype_summary = df_mapped.group_by("packagetype").agg([
        pl.len().alias("shipment_count"),
        pl.col("cost_current_carrier").sum().alias("total_cost"),
        pl.col("cost_current_carrier").mean().alias("avg_cost"),
    ]).sort("total_cost", descending=True).head(15)

    print("\n  {:40} {:>10} {:>15} {:>10}".format(
        "Package Type", "Shipments", "Total Cost", "Avg Cost"
    ))
    print("  " + "-" * 77)

    packagetype_data = []
    for row in packagetype_summary.iter_rows(named=True):
        pkg = row["packagetype"]
        count = row["shipment_count"]
        cost = row["total_cost"]
        avg = row["avg_cost"]

        packagetype_data.append({
            "packagetype": pkg,
            "shipment_count": count,
            "total_cost": cost,
            "avg_cost": avg
        })

        # Truncate long package names
        pkg_display = pkg[:38] + ".." if len(pkg) > 40 else pkg
        print("  {:40} {:>10,} ${:>14,.2f} ${:>9,.2f}".format(
            pkg_display, count, cost, avg
        ))

    # =================================================================
    # BREAKDOWN BY CARRIER AND PACKAGE TYPE
    # =================================================================
    print("\n" + "-" * 60)
    print("BREAKDOWN BY CARRIER AND PACKAGE TYPE (Top 10 per carrier)")
    print("-" * 60)

    carrier_pkg_data = []
    for carrier in ["FedEx", "OnTrac", "USPS"]:
        df_carrier = df_mapped.filter(pl.col("carrier") == carrier)

        print(f"\n  {carrier}:")
        print("  {:40} {:>10} {:>15} {:>10}".format(
            "  Package Type", "Shipments", "Total Cost", "Avg Cost"
        ))
        print("  " + "-" * 77)

        pkg_summary = df_carrier.group_by("packagetype").agg([
            pl.len().alias("shipment_count"),
            pl.col("cost_current_carrier").sum().alias("total_cost"),
            pl.col("cost_current_carrier").mean().alias("avg_cost"),
        ]).sort("total_cost", descending=True).head(10)

        for row in pkg_summary.iter_rows(named=True):
            pkg = row["packagetype"]
            count = row["shipment_count"]
            cost = row["total_cost"]
            avg = row["avg_cost"]

            carrier_pkg_data.append({
                "carrier": carrier,
                "packagetype": pkg,
                "shipment_count": count,
                "total_cost": cost,
                "avg_cost": avg
            })

            pkg_display = pkg[:38] + ".." if len(pkg) > 40 else pkg
            print("  {:40} {:>10,} ${:>14,.2f} ${:>9,.2f}".format(
                pkg_display, count, cost, avg
            ))

    # =================================================================
    # WEIGHT DISTRIBUTION
    # =================================================================
    print("\n" + "-" * 60)
    print("WEIGHT DISTRIBUTION (mapped shipments)")
    print("-" * 60)

    # Create weight brackets
    df_mapped = df_mapped.with_columns(
        pl.when(pl.col("weight_lbs") <= 1).then(pl.lit("0-1 lbs"))
        .when(pl.col("weight_lbs") <= 5).then(pl.lit("1-5 lbs"))
        .when(pl.col("weight_lbs") <= 10).then(pl.lit("5-10 lbs"))
        .when(pl.col("weight_lbs") <= 20).then(pl.lit("10-20 lbs"))
        .when(pl.col("weight_lbs") <= 30).then(pl.lit("20-30 lbs"))
        .otherwise(pl.lit("30+ lbs"))
        .alias("weight_bracket")
    )

    weight_summary = df_mapped.group_by("weight_bracket").agg([
        pl.len().alias("shipment_count"),
        pl.col("cost_current_carrier").sum().alias("total_cost"),
        pl.col("cost_current_carrier").mean().alias("avg_cost"),
    ]).sort("weight_bracket")

    # Sort by weight bracket order
    weight_order = ["0-1 lbs", "1-5 lbs", "5-10 lbs", "10-20 lbs", "20-30 lbs", "30+ lbs"]

    print("\n  {:15} {:>12} {:>10} {:>15} {:>12}".format(
        "Weight Bracket", "Shipments", "Share", "Total Cost", "Avg Cost"
    ))
    print("  " + "-" * 66)

    weight_data = []
    for bracket in weight_order:
        row = weight_summary.filter(pl.col("weight_bracket") == bracket)
        if row.shape[0] > 0:
            count = row["shipment_count"][0]
            cost = row["total_cost"][0]
            avg = row["avg_cost"][0]
            share = count / mapped_shipments * 100

            weight_data.append({
                "weight_bracket": bracket,
                "shipment_count": count,
                "share_pct": share,
                "total_cost": cost,
                "avg_cost": avg
            })

            print("  {:15} {:>12,} {:>9.1f}% ${:>14,.2f} ${:>11,.2f}".format(
                bracket, count, share, cost, avg
            ))

    # =================================================================
    # PRODUCTION SITE DISTRIBUTION
    # =================================================================
    print("\n" + "-" * 60)
    print("PRODUCTION SITE DISTRIBUTION (mapped shipments)")
    print("-" * 60)

    site_summary = df_mapped.group_by("production_site").agg([
        pl.len().alias("shipment_count"),
        pl.col("cost_current_carrier").sum().alias("total_cost"),
        pl.col("cost_current_carrier").mean().alias("avg_cost"),
    ]).sort("total_cost", descending=True)

    print("\n  {:15} {:>12} {:>10} {:>15} {:>12}".format(
        "Site", "Shipments", "Share", "Total Cost", "Avg Cost"
    ))
    print("  " + "-" * 66)

    site_data = []
    for row in site_summary.iter_rows(named=True):
        site = row["production_site"]
        count = row["shipment_count"]
        cost = row["total_cost"]
        avg = row["avg_cost"]
        share = count / mapped_shipments * 100

        site_data.append({
            "production_site": site,
            "shipment_count": count,
            "share_pct": share,
            "total_cost": cost,
            "avg_cost": avg
        })

        print("  {:15} {:>12,} {:>9.1f}% ${:>14,.2f} ${:>11,.2f}".format(
            site, count, share, cost, avg
        ))

    # =================================================================
    # COMPARISON WITH SINGLE-CARRIER SCENARIOS
    # =================================================================
    print("\n" + "-" * 60)
    print("COMPARISON: Current Mix vs 100% Single Carrier (all shipments)")
    print("-" * 60)

    # Calculate costs for 100% of each carrier
    comparison_data = []
    for carrier, col in [("OnTrac", "ontrac_cost_total"),
                          ("USPS", "usps_cost_total"),
                          ("FedEx", "fedex_cost_total")]:
        carrier_total = df[col].sum()
        diff = carrier_total - total_cost
        diff_pct = diff / total_cost * 100

        comparison_data.append({
            "scenario": f"100% {carrier}",
            "total_cost": carrier_total,
            "diff_vs_current": diff,
            "diff_pct": diff_pct
        })

    print("\n  {:25} {:>18} {:>18} {:>10}".format(
        "Scenario", "Total Cost", "vs Current Mix", "Diff %"
    ))
    print("  " + "-" * 73)
    print("  {:25} ${:>17,.2f} {:>18} {:>10}".format(
        "Current Mix (baseline)", total_cost, "-", "-"
    ))

    for c in comparison_data:
        print("  {:25} ${:>17,.2f} ${:>17,.2f} {:>+9.1f}%".format(
            c["scenario"], c["total_cost"], c["diff_vs_current"], c["diff_pct"]
        ))

    # =================================================================
    # DHL HANDLING NOTE
    # =================================================================
    print("\n" + "-" * 60)
    print("NOTE: DHL SHIPMENTS HANDLING")
    print("-" * 60)
    print(f"""
  DHL eCommerce America shipments: {dhl_shipments:,} ({dhl_shipments/total_shipments*100:.1f}% of total)

  These shipments have NULL cost_current_carrier because DHL is not one of the
  carriers with calculated costs in this analysis. The total cost figure above
  ($6,218,604.91) represents only the {mapped_shipments:,} mapped shipments.

  For scenario comparisons, DHL shipments ARE included when calculating costs
  for 100% single-carrier scenarios (e.g., "100% FedEx" includes all {total_shipments:,}
  shipments costed as FedEx).
""")

    # =================================================================
    # SAVE RESULTS
    # =================================================================
    print("-" * 60)
    print("SAVING RESULTS")
    print("-" * 60)

    # Save carrier summary
    carrier_df = pl.DataFrame(carrier_data)
    carrier_df.write_csv(RESULTS_DIR / "breakdown_by_carrier.csv")
    print(f"  Saved: breakdown_by_carrier.csv")

    # Save provider summary
    provider_df = pl.DataFrame(provider_data)
    provider_df.write_csv(RESULTS_DIR / "breakdown_by_provider.csv")
    print(f"  Saved: breakdown_by_provider.csv")

    # Save packagetype summary (full, not just top 15)
    packagetype_full = df_mapped.group_by("packagetype").agg([
        pl.len().alias("shipment_count"),
        pl.col("cost_current_carrier").sum().alias("total_cost"),
        pl.col("cost_current_carrier").mean().alias("avg_cost"),
    ]).sort("total_cost", descending=True)
    packagetype_full.write_csv(RESULTS_DIR / "breakdown_by_packagetype.csv")
    print(f"  Saved: breakdown_by_packagetype.csv")

    # Save weight summary
    weight_df = pl.DataFrame(weight_data)
    weight_df.write_csv(RESULTS_DIR / "breakdown_by_weight.csv")
    print(f"  Saved: breakdown_by_weight.csv")

    # Save site summary
    site_df = pl.DataFrame(site_data)
    site_df.write_csv(RESULTS_DIR / "breakdown_by_site.csv")
    print(f"  Saved: breakdown_by_site.csv")

    # Save comparison summary
    comparison_df = pl.DataFrame(comparison_data)
    comparison_df.write_csv(RESULTS_DIR / "comparison_single_carrier.csv")
    print(f"  Saved: comparison_single_carrier.csv")

    print("\n" + "=" * 60)
    print("Scenario 1 Analysis Complete")
    print("=" * 60)

    return {
        "total_shipments": total_shipments,
        "mapped_shipments": mapped_shipments,
        "dhl_shipments": dhl_shipments,
        "total_cost": total_cost,
        "carrier_data": carrier_data,
        "provider_data": provider_data,
        "comparison_data": comparison_data,
    }


if __name__ == "__main__":
    main()
