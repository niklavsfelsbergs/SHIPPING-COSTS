"""
Scenario 15: 3-Group Static Rules for P2P + FedEx (Implementable S14)

Same 3-group approach as S11, but with P2P US2 replacing USPS:

    Light  (small/flat):   P2P US zone → P2P US if wt ≤ X  |  other → P2P US2 if wt ≤ Y
    Medium (mid-size):     P2P US zone → P2P US if wt ≤ X  |  other → P2P US2 if wt ≤ Y
    Heavy  (oversized):    FedEx always

Only 2 carrier relationships (P2P + FedEx). FedEx at 16% earned discount,
constrained to >= $5.1M undiscounted (safely above $5M penalty threshold).

Group definitions reuse S10's package type classification (Light/Medium/Heavy).
Cutoffs found by brute-force search over all (P2P US, P2P US2) combinations
subject to the FedEx undiscounted spend constraint.
"""

import polars as pl
import sys
from pathlib import Path

from analysis.US_2026_tenders.optimization.fedex_adjustment import (
    adjust_fedex_costs, PP_DISCOUNT, BAKED_FACTOR_HD, BAKED_FACTOR_SP, compute_undiscounted,
)
from analysis.US_2026_tenders.optimization.baseline import apply_s1_adjustments, compute_s1_baseline

sys.stdout.reconfigure(encoding="utf-8")

# FedEx earned discount parameters
FEDEX_TARGET_EARNED_HD = 0.16
FEDEX_TARGET_EARNED_SP = 0.04
FEDEX_UNDISCOUNTED_THRESHOLD = 5_100_000  # $5.1M to stay safely above $5M penalty

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
COMBINED_DATASETS = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "combined_datasets"
OUTPUT_DIR = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "results" / "scenario_15_p2p_fedex_3group"
S10_RESULTS = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "results" / "scenario_10_static_rules"

# Search ranges for cutoffs
P2P_US_SEARCH_MAX = 30    # P2P US max weight is 30 lbs
P2P_US2_SEARCH_MAX = 10   # P2P US2 only competitive at very light weights


def load_shipment_data() -> tuple[pl.DataFrame, float]:
    """Load shipment-level data with FedEx at 16% HD / 4% SP earned discount."""
    input_path = COMBINED_DATASETS / "shipments_unified.parquet"
    print(f"    Loading: {input_path.name}")
    df = pl.read_parquet(input_path)
    print(f"    {df.shape[0]:,} shipments loaded")

    df = adjust_fedex_costs(df, FEDEX_TARGET_EARNED_HD, FEDEX_TARGET_EARNED_SP)

    s1_baseline = compute_s1_baseline()
    print(f"\n    S1 baseline: ${s1_baseline:,.2f}")

    df = df.with_columns([
        pl.col("weight_lbs").ceil().cast(pl.Int32).alias("weight_bracket"),
        (pl.col("p2p_cost_total").is_not_null() & (pl.col("p2p_cost_total") > 0))
        .alias("p2p_us_available"),
        (pl.col("p2p_us2_cost_total").is_not_null() & (pl.col("p2p_us2_cost_total") > 0))
        .alias("p2p_us2_available"),
    ])

    return df, s1_baseline


def define_groups() -> tuple[list[str], list[str], list[str]]:
    """Define Light / Medium / Heavy package type groups from S10 routing rules."""
    rules = pl.read_csv(S10_RESULTS / "routing_rules.csv")

    light_pkgs = []
    medium_pkgs = []
    heavy_pkgs = []

    for row in rules.iter_rows(named=True):
        pkg = row["packagetype"]
        p2p = row["p2p_max_weight"]
        usps = row["usps_max_weight"]
        if p2p == 0 and usps <= 1:
            heavy_pkgs.append(pkg)
        elif p2p <= 7:
            light_pkgs.append(pkg)
        else:
            medium_pkgs.append(pkg)

    return light_pkgs, medium_pkgs, heavy_pkgs


def compute_group_costs(
    df_group: pl.DataFrame, p2p_us_cut: int, p2p_us2_cut: int
) -> tuple[float, float, float]:
    """Compute total cost and FedEx HD/SP base rates for a group with given cutoffs.

    Routing logic:
      - P2P US zone AND weight <= p2p_us_cut -> P2P US
      - Non-P2P US zone AND P2P US2 available AND weight <= p2p_us2_cut -> P2P US2
      - Otherwise -> FedEx

    Returns (total_cost, fedex_hd_base, fedex_sp_base).
    """
    is_fedex = (
        ~(pl.col("p2p_us_available") & (pl.col("weight_bracket") <= p2p_us_cut))
        & ~(
            (~pl.col("p2p_us_available"))
            & pl.col("p2p_us2_available")
            & (pl.col("weight_bracket") <= p2p_us2_cut)
        )
    )
    carrier = (
        pl.when(pl.col("p2p_us_available") & (pl.col("weight_bracket") <= p2p_us_cut))
        .then(pl.lit("P2P_US"))
        .when(
            (~pl.col("p2p_us_available"))
            & pl.col("p2p_us2_available")
            & (pl.col("weight_bracket") <= p2p_us2_cut)
        )
        .then(pl.lit("P2P_US2"))
        .otherwise(pl.lit("FEDEX"))
    )
    cost = (
        pl.when(carrier == "P2P_US").then(pl.col("p2p_cost_total"))
        .when(carrier == "P2P_US2").then(pl.col("p2p_us2_cost_total"))
        .otherwise(pl.col("fedex_cost_total"))
    )
    is_sp = pl.col("fedex_service_selected") == "FXSP"
    fedex_hd_base = (
        pl.when(is_fedex & ~is_sp).then(pl.col("fedex_cost_base_rate"))
        .otherwise(pl.lit(0.0))
    )
    fedex_sp_base = (
        pl.when(is_fedex & is_sp).then(pl.col("fedex_cost_base_rate"))
        .otherwise(pl.lit(0.0))
    )
    row = df_group.select(
        cost.sum().alias("total_cost"),
        fedex_hd_base.sum().alias("fedex_hd_base"),
        fedex_sp_base.sum().alias("fedex_sp_base"),
    ).row(0)
    return row[0], row[1], row[2]


def precompute_group_grid(
    df_group: pl.DataFrame, max_p2p_us: int, max_p2p_us2: int
) -> dict[tuple[int, int], tuple[float, float, float]]:
    """Precompute (total_cost, fedex_hd_base, fedex_sp_base) for all cutoff combinations."""
    grid = {}
    for p in range(0, max_p2p_us + 1):
        for u in range(0, max_p2p_us2 + 1):
            grid[(p, u)] = compute_group_costs(df_group, p, u)
    return grid


def find_best_cutoffs(
    light_grid: dict, medium_grid: dict,
    heavy_cost: float, heavy_hd_base: float, heavy_sp_base: float,
    threshold: float,
) -> tuple[dict, dict]:
    """Find best (p2p_us, p2p_us2) cutoffs per group, with and without FedEx threshold.

    Threshold is on undiscounted spend, computed from HD base / 0.37 + SP base / 0.505.
    Returns (best_constrained, best_unconstrained).
    """
    best_unc = None
    best_con = None

    for (lp, lu), (lc, l_hd, l_sp) in light_grid.items():
        for (mp, mu), (mc, m_hd, m_sp) in medium_grid.items():
            tc = lc + mc + heavy_cost
            total_hd_base = l_hd + m_hd + heavy_hd_base
            total_sp_base = l_sp + m_sp + heavy_sp_base
            undiscounted = compute_undiscounted(total_hd_base, total_sp_base)

            if best_unc is None or tc < best_unc["total_cost"]:
                best_unc = dict(
                    lp=lp, lu=lu, mp=mp, mu=mu, total_cost=tc,
                    hd_base=total_hd_base, sp_base=total_sp_base,
                    undiscounted=undiscounted,
                )

            if undiscounted >= threshold and (best_con is None or tc < best_con["total_cost"]):
                best_con = dict(
                    lp=lp, lu=lu, mp=mp, mu=mu, total_cost=tc,
                    hd_base=total_hd_base, sp_base=total_sp_base,
                    undiscounted=undiscounted,
                )

    return best_con, best_unc


def apply_group_rules(
    df: pl.DataFrame,
    light_set: set, medium_set: set,
    lp: int, lu: int, mp: int, mu: int,
) -> pl.DataFrame:
    """Apply 3-group routing rules and return df with assigned_carrier, assigned_cost."""
    carrier = (
        pl.when(
            pl.col("packagetype").is_in(light_set)
            & pl.col("p2p_us_available")
            & (pl.col("weight_bracket") <= lp)
        ).then(pl.lit("P2P_US"))
        .when(
            pl.col("packagetype").is_in(light_set)
            & (~pl.col("p2p_us_available"))
            & pl.col("p2p_us2_available")
            & (pl.col("weight_bracket") <= lu)
        ).then(pl.lit("P2P_US2"))
        .when(
            pl.col("packagetype").is_in(medium_set)
            & pl.col("p2p_us_available")
            & (pl.col("weight_bracket") <= mp)
        ).then(pl.lit("P2P_US"))
        .when(
            pl.col("packagetype").is_in(medium_set)
            & (~pl.col("p2p_us_available"))
            & pl.col("p2p_us2_available")
            & (pl.col("weight_bracket") <= mu)
        ).then(pl.lit("P2P_US2"))
        .otherwise(pl.lit("FEDEX"))
    )
    cost = (
        pl.when(carrier == "P2P_US").then(pl.col("p2p_cost_total"))
        .when(carrier == "P2P_US2").then(pl.col("p2p_us2_cost_total"))
        .otherwise(pl.col("fedex_cost_total"))
    )
    return df.with_columns(
        carrier.alias("assigned_carrier"),
        cost.alias("assigned_cost"),
    )


def main():
    print("=" * 90)
    print("SCENARIO 15: 3-Group Static Rules for P2P + FedEx (Implementable S14)")
    print("=" * 90)

    # -- [1] Load data --------------------------------------------------------
    print("\n[1] Loading shipment data...")
    df, SCENARIO_1_BASELINE = load_shipment_data()
    total_shipments = df.shape[0]

    # -- [2] Define groups from S10 cutoffs -----------------------------------
    print("\n[2] Defining package type groups from S10 cutoffs...")
    light_pkgs, medium_pkgs, heavy_pkgs = define_groups()

    # Any package type not in S10's rules -> Heavy (default to FedEx)
    all_pkgs_in_groups = set(light_pkgs) | set(medium_pkgs) | set(heavy_pkgs)
    all_pkgs = set(df["packagetype"].unique().to_list())
    unlisted = all_pkgs - all_pkgs_in_groups
    heavy_pkgs.extend(list(unlisted))

    light_set = set(light_pkgs)
    medium_set = set(medium_pkgs)
    heavy_set = set(heavy_pkgs)

    for name, pkgs in [("Light", light_pkgs), ("Medium", medium_pkgs), ("Heavy", heavy_pkgs)]:
        n = df.filter(pl.col("packagetype").is_in(pkgs)).shape[0]
        print(f"    {name:8s}: {len(pkgs):>3} package types, {n:>7,} shipments")

    # -- [3] Precompute cost grids --------------------------------------------
    print("\n[3] Precomputing cost grids for Light and Medium groups...")

    df_light = df.filter(pl.col("packagetype").is_in(light_set))
    df_medium = df.filter(pl.col("packagetype").is_in(medium_set))
    df_heavy = df.filter(pl.col("packagetype").is_in(heavy_set))

    light_grid = precompute_group_grid(df_light, P2P_US_SEARCH_MAX, P2P_US2_SEARCH_MAX)
    print(f"    Light grid: {len(light_grid)} combinations computed")
    medium_grid = precompute_group_grid(df_medium, P2P_US_SEARCH_MAX, P2P_US2_SEARCH_MAX)
    print(f"    Medium grid: {len(medium_grid)} combinations computed")

    heavy_cost = float(df_heavy["fedex_cost_total"].sum())
    heavy_fedex_hd = float(
        df_heavy.filter(pl.col("fedex_service_selected") == "FXEHD")["fedex_cost_base_rate"].sum()
    )
    heavy_fedex_sp = float(
        df_heavy.filter(pl.col("fedex_service_selected") == "FXSP")["fedex_cost_base_rate"].sum()
    )
    heavy_undiscounted = compute_undiscounted(heavy_fedex_hd, heavy_fedex_sp)
    print(f"    Heavy (always FedEx): cost=${heavy_cost:,.0f}")
    print(f"      HD base=${heavy_fedex_hd:,.0f}, SP base=${heavy_fedex_sp:,.0f}, undiscounted=${heavy_undiscounted:,.0f}")

    # -- [4] Find optimal cutoffs ---------------------------------------------
    print("\n[4] Searching for optimal cutoffs...")
    print(f"    FedEx undiscounted threshold: ${FEDEX_UNDISCOUNTED_THRESHOLD:,.0f}")
    print(f"    HD baked factor: {BAKED_FACTOR_HD:.3f}, SP baked factor: {BAKED_FACTOR_SP:.3f}")

    best_con, best_unc = find_best_cutoffs(
        light_grid, medium_grid, heavy_cost, heavy_fedex_hd, heavy_fedex_sp,
        FEDEX_UNDISCOUNTED_THRESHOLD,
    )

    print(f"\n    Unconstrained optimum (ignoring FedEx threshold):")
    print(f"      Light:  P2P US <= {best_unc['lp']},  P2P US2 <= {best_unc['lu']}")
    print(f"      Medium: P2P US <= {best_unc['mp']},  P2P US2 <= {best_unc['mu']}")
    print(f"      Heavy:  FedEx always")
    print(f"      Total cost: ${best_unc['total_cost']:,.0f}")
    print(f"      Undiscounted: ${best_unc['undiscounted']:,.0f} (threshold: ${FEDEX_UNDISCOUNTED_THRESHOLD:,.0f})")
    threshold_met_unc = best_unc["undiscounted"] >= FEDEX_UNDISCOUNTED_THRESHOLD
    print(f"      Threshold met: {'YES' if threshold_met_unc else 'NO'}")

    if best_con is None:
        print("\n    WARNING: No feasible solution meets FedEx threshold!")
        best = best_unc
    else:
        print(f"\n    Constrained optimum (FedEx threshold met):")
        print(f"      Light:  P2P US <= {best_con['lp']},  P2P US2 <= {best_con['lu']}")
        print(f"      Medium: P2P US <= {best_con['mp']},  P2P US2 <= {best_con['mu']}")
        print(f"      Heavy:  FedEx always")
        print(f"      Total cost: ${best_con['total_cost']:,.0f}")
        print(f"      Undiscounted: ${best_con['undiscounted']:,.0f} (threshold: ${FEDEX_UNDISCOUNTED_THRESHOLD:,.0f})")
        margin_undisc = best_con["undiscounted"] - FEDEX_UNDISCOUNTED_THRESHOLD
        print(f"      Margin (undiscounted): ${margin_undisc:+,.0f}")

        if not threshold_met_unc:
            penalty = best_con["total_cost"] - best_unc["total_cost"]
            print(f"\n    Threshold enforcement cost: ${penalty:+,.0f}")
        best = best_con

    # -- [5] Apply final rules ------------------------------------------------
    print(f"\n[5] Applying final rules...")
    lp, lu, mp, mu = best["lp"], best["lu"], best["mp"], best["mu"]
    result = apply_group_rules(df, light_set, medium_set, lp, lu, mp, mu)

    total_cost = float(result["assigned_cost"].sum())
    fedex_rows = result.filter(pl.col("assigned_carrier") == "FEDEX")
    fedex_hd_base = float(
        fedex_rows.filter(pl.col("fedex_service_selected") == "FXEHD")["fedex_cost_base_rate"].sum()
    )
    fedex_sp_base = float(
        fedex_rows.filter(pl.col("fedex_service_selected") == "FXSP")["fedex_cost_base_rate"].sum()
    )
    fedex_undiscounted = compute_undiscounted(fedex_hd_base, fedex_sp_base)
    savings = SCENARIO_1_BASELINE - total_cost

    print(f"\n{'=' * 90}")
    print(f"SCENARIO 15 RESULTS")
    print(f"{'=' * 90}")

    print(f"\n    Total cost:        ${total_cost:,.0f}")
    print(f"    S1 baseline:       ${SCENARIO_1_BASELINE:,.0f}")
    print(f"    Savings vs S1:     ${savings:,.0f} ({savings / SCENARIO_1_BASELINE * 100:.1f}%)")

    print(f"\n    FedEx earned discount:")
    print(f"      HD base rate:       ${fedex_hd_base:,.0f} (÷{BAKED_FACTOR_HD:.3f} = ${fedex_hd_base / BAKED_FACTOR_HD:,.0f} undiscounted)")
    print(f"      SP base rate:       ${fedex_sp_base:,.0f} (÷{BAKED_FACTOR_SP:.3f} = ${fedex_sp_base / BAKED_FACTOR_SP:,.0f} undiscounted)")
    print(f"      Undiscounted total: ${fedex_undiscounted:,.0f}")
    print(f"      Threshold:          ${FEDEX_UNDISCOUNTED_THRESHOLD:,}")
    print(f"      Margin:             ${fedex_undiscounted - FEDEX_UNDISCOUNTED_THRESHOLD:+,.0f}")
    print(f"      $5M penalty clear:  {'YES' if fedex_undiscounted >= 5_000_000 else 'NO'}")

    # Carrier mix
    print(f"\n    {'Carrier':<14} {'Shipments':>12} {'%':>8} {'Cost':>15} {'Avg':>10}")
    print(f"    {'-' * 64}")
    for carrier_name in ["P2P_US", "P2P_US2", "FEDEX"]:
        c_df = result.filter(pl.col("assigned_carrier") == carrier_name)
        n = c_df.shape[0]
        cost = float(c_df["assigned_cost"].sum())
        avg = cost / n if n > 0 else 0
        pct = n / total_shipments * 100
        print(f"    {carrier_name:<14} {n:>12,} {pct:>7.1f}% ${cost:>14,.0f} ${avg:>9.2f}")
        if carrier_name == "FEDEX":
            for svc, svc_label in [("FXEHD", "  FedEx HD"), ("FXSP", "  FedEx SP")]:
                svc_df = c_df.filter(pl.col("fedex_service_selected") == svc)
                sn = svc_df.shape[0]
                sc = float(svc_df["assigned_cost"].sum())
                sa = sc / sn if sn > 0 else 0
                sp = sn / total_shipments * 100
                print(f"    {svc_label:<14} {sn:>12,} {sp:>7.1f}% ${sc:>14,.0f} ${sa:>9.2f}")
    print(f"    {'-' * 64}")
    print(f"    {'TOTAL':<14} {total_shipments:>12,} {'100.0%':>8} ${total_cost:>14,.0f}")

    # Per-group breakdown
    print(f"\n    Per-group breakdown:")
    for name, pkgs, pc, uc in [("Light", light_pkgs, lp, lu), ("Medium", medium_pkgs, mp, mu), ("Heavy", heavy_pkgs, 0, 0)]:
        sub = result.filter(pl.col("packagetype").is_in(pkgs))
        n = sub.shape[0]
        cost = float(sub["assigned_cost"].sum())
        carrier_counts = sub.group_by("assigned_carrier").agg(pl.len().alias("n")).sort("assigned_carrier")
        print(f"\n    {name} (P2P US<={pc}, P2P US2<={uc}): {n:,} ships, ${cost:,.0f}")
        for r in carrier_counts.iter_rows(named=True):
            pct = r["n"] / n * 100
            print(f"      {r['assigned_carrier']:8s}  {r['n']:>8,}  ({pct:5.1f}%)")
            if r["assigned_carrier"] == "FEDEX":
                fedex_sub = sub.filter(pl.col("assigned_carrier") == "FEDEX")
                for svc, svc_label in [("FXEHD", "  HD"), ("FXSP", "  SP")]:
                    svc_n = fedex_sub.filter(pl.col("fedex_service_selected") == svc).shape[0]
                    svc_pct = svc_n / n * 100
                    print(f"      {svc_label:8s}  {svc_n:>8,}  ({svc_pct:5.1f}%)")

    # P2P coverage stats
    p2p_us_zips = result.filter(pl.col("p2p_us_available"))["shipping_zip_code"].n_unique()
    p2p_us_ships = result.filter(pl.col("assigned_carrier") == "P2P_US").shape[0]
    p2p_us2_ships = result.filter(pl.col("assigned_carrier") == "P2P_US2").shape[0]
    print(f"\n    P2P coverage:")
    print(f"      P2P US zones:    {p2p_us_zips:,} ZIPs")
    print(f"      P2P US routed:   {p2p_us_ships:,} ({p2p_us_ships / total_shipments * 100:.1f}%)")
    print(f"      P2P US2 routed:  {p2p_us2_ships:,} ({p2p_us2_ships / total_shipments * 100:.1f}%)")

    # -- [6] Comparison vs other scenarios ------------------------------------
    print(f"\n[6] Comparison vs other scenarios")

    scenarios = [
        ("S1  Current mix", SCENARIO_1_BASELINE),
        ("S7  USPS+FedEx+P2P (optimal)", 4_433_040.0),
        ("S11 3-Group USPS+FedEx+P2P", 4_516_218.0),
        ("S14 P2P+FedEx constrained", 4_858_916.0),
        ("S15 P2P+FedEx 3-group", total_cost),
        ("S13 P2P+FedEx unconstrained", 4_942_666.0),
    ]

    print(f"\n    {'Scenario':<35} {'Cost':>12} {'vs S1':>10} {'Carriers':>10}")
    print(f"    {'-' * 70}")
    for name, cost in sorted(scenarios, key=lambda x: x[1]):
        vs_s1 = (cost - SCENARIO_1_BASELINE) / SCENARIO_1_BASELINE * 100
        carriers = "2" if "P2P+FedEx" in name else "3" if any(s in name for s in ["S7", "S11"]) else "4"
        marker = " ***" if "S15" in name else ""
        print(f"    {name:<35} ${cost:>11,.0f} {vs_s1:>+9.1f}% {carriers:>10}{marker}")

    print(f"\n    vs S14 (per-shipment constrained): ${total_cost - 4_858_916:+,.0f}/year")
    print(f"    vs S11 (3-group USPS+FedEx+P2P):   ${total_cost - 4_516_218:+,.0f}/year")
    print(f"    vs S13 (unconstrained 0% earned):   ${total_cost - 4_942_666:+,.0f}/year")

    # -- [7] Save results -----------------------------------------------------
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Routing rules CSV
    pkg_counts = df.group_by("packagetype").agg(pl.len().alias("n"))
    rule_rows = []
    for name, pkgs, pc, uc in [("Light", light_pkgs, lp, lu), ("Medium", medium_pkgs, mp, mu), ("Heavy", heavy_pkgs, 0, 0)]:
        for pkg in pkgs:
            n = int(pkg_counts.filter(pl.col("packagetype") == pkg)["n"].item()) if pkg_counts.filter(pl.col("packagetype") == pkg).shape[0] > 0 else 0
            rule_rows.append({
                "packagetype": pkg,
                "group": name,
                "shipments": n,
                "p2p_us_max_weight": pc,
                "p2p_us2_max_weight": uc,
            })
    rules_df = pl.DataFrame(rule_rows).sort("shipments", descending=True)
    rules_df.write_csv(OUTPUT_DIR / "routing_rules.csv")
    print(f"\n[7] Saved routing rules to {OUTPUT_DIR / 'routing_rules.csv'}")

    # Group summary CSV
    summary_rows = [
        {"group": "Light", "p2p_us_max_weight": lp, "p2p_us2_max_weight": lu, "package_types": len(light_pkgs), "shipments": df_light.shape[0]},
        {"group": "Medium", "p2p_us_max_weight": mp, "p2p_us2_max_weight": mu, "package_types": len(medium_pkgs), "shipments": df_medium.shape[0]},
        {"group": "Heavy", "p2p_us_max_weight": 0, "p2p_us2_max_weight": 0, "package_types": len(heavy_pkgs), "shipments": df_heavy.shape[0]},
    ]
    pl.DataFrame(summary_rows).write_csv(OUTPUT_DIR / "group_summary.csv")
    print(f"    Saved group summary to {OUTPUT_DIR / 'group_summary.csv'}")

    # Carrier selection CSV (with FedEx HD/SP sub-rows)
    carrier_stats = (
        result
        .group_by("assigned_carrier")
        .agg([
            pl.len().alias("shipment_count"),
            pl.col("assigned_cost").sum().alias("total_cost"),
            pl.col("assigned_cost").mean().alias("avg_cost"),
            pl.col("weight_lbs").mean().alias("avg_weight"),
        ])
        .sort("shipment_count", descending=True)
    )
    # Add FedEx HD/SP breakdown rows
    fedex_svc_stats = (
        result
        .filter(pl.col("assigned_carrier") == "FEDEX")
        .group_by("fedex_service_selected")
        .agg([
            pl.len().alias("shipment_count"),
            pl.col("assigned_cost").sum().alias("total_cost"),
            pl.col("assigned_cost").mean().alias("avg_cost"),
            pl.col("weight_lbs").mean().alias("avg_weight"),
        ])
        .with_columns(
            pl.when(pl.col("fedex_service_selected") == "FXEHD").then(pl.lit("FEDEX_HD"))
            .when(pl.col("fedex_service_selected") == "FXSP").then(pl.lit("FEDEX_SP"))
            .otherwise(pl.col("fedex_service_selected"))
            .alias("assigned_carrier")
        )
        .select(carrier_stats.columns)
    )
    carrier_stats = pl.concat([carrier_stats, fedex_svc_stats])
    carrier_stats.write_csv(OUTPUT_DIR / "carrier_selection.csv")
    print(f"    Saved carrier selection to {OUTPUT_DIR / 'carrier_selection.csv'}")

    # P2P US zip list
    p2p_zip_list = df.filter(pl.col("p2p_us_available"))["shipping_zip_code"].unique().sort()
    p2p_zip_list.to_frame().write_csv(OUTPUT_DIR / "p2p_us_zip_codes.csv")
    print(f"    Saved P2P US zip list ({p2p_zip_list.len():,} zips)")

    # Summary metrics (with FedEx HD/SP shipment and cost breakdown)
    fedex_hd_rows = fedex_rows.filter(pl.col("fedex_service_selected") == "FXEHD")
    fedex_sp_rows = fedex_rows.filter(pl.col("fedex_service_selected") == "FXSP")
    fedex_hd_shipments = fedex_hd_rows.shape[0]
    fedex_sp_shipments = fedex_sp_rows.shape[0]
    fedex_hd_cost = float(fedex_hd_rows["assigned_cost"].sum())
    fedex_sp_cost = float(fedex_sp_rows["assigned_cost"].sum())
    summary_data = {
        "metric": [
            "total_shipments", "s1_baseline", "s15_total", "savings_vs_s1",
            "savings_pct", "fedex_earned_discount_hd", "fedex_earned_discount_sp",
            "fedex_undiscounted_spend", "fedex_undiscounted_hd", "fedex_undiscounted_sp",
            "fedex_undiscounted_threshold", "fedex_margin_above_5m",
            "fedex_shipments", "fedex_hd_shipments", "fedex_sp_shipments",
            "fedex_total_cost", "fedex_hd_cost", "fedex_sp_cost",
            "fedex_hd_base_rate", "fedex_sp_base_rate",
            "light_p2p_us_cutoff", "light_p2p_us2_cutoff",
            "medium_p2p_us_cutoff", "medium_p2p_us2_cutoff",
        ],
        "value": [
            float(total_shipments), SCENARIO_1_BASELINE, total_cost, savings,
            savings / SCENARIO_1_BASELINE * 100, FEDEX_TARGET_EARNED_HD, FEDEX_TARGET_EARNED_SP,
            fedex_undiscounted, fedex_hd_base / BAKED_FACTOR_HD, fedex_sp_base / BAKED_FACTOR_SP,
            float(FEDEX_UNDISCOUNTED_THRESHOLD), fedex_undiscounted - FEDEX_UNDISCOUNTED_THRESHOLD,
            float(fedex_rows.shape[0]), float(fedex_hd_shipments), float(fedex_sp_shipments),
            float(fedex_rows["assigned_cost"].sum()), fedex_hd_cost, fedex_sp_cost,
            fedex_hd_base, fedex_sp_base,
            float(lp), float(lu), float(mp), float(mu),
        ],
    }
    pl.DataFrame(summary_data).write_csv(OUTPUT_DIR / "summary_metrics.csv")
    print(f"    Saved summary metrics")

    # Placeholder summary.md
    md_lines = [
        "# Scenario 15: 3-Group Static Rules for P2P + FedEx",
        "",
        "## Overview",
        "Implementable version of S14 using 3 static group rules.",
        f"FedEx HD at {FEDEX_TARGET_EARNED_HD:.0%} earned discount, SP at {FEDEX_TARGET_EARNED_SP:.0%},",
        f"undiscounted spend constrained >= ${FEDEX_UNDISCOUNTED_THRESHOLD/1e6:.1f}M.",
        "",
        "## Rules",
        f"- Light:  P2P US zone -> P2P US if wt <= {lp} lbs | non-P2P US -> P2P US2 if wt <= {lu} lbs | else FedEx",
        f"- Medium: P2P US zone -> P2P US if wt <= {mp} lbs | non-P2P US -> P2P US2 if wt <= {mu} lbs | else FedEx",
        f"- Heavy:  FedEx always",
        "",
        "## Results",
        f"- Total: ${total_cost:,.2f} (-{savings / SCENARIO_1_BASELINE * 100:.1f}% vs S1)",
        f"- FedEx undiscounted: ${fedex_undiscounted:,.0f} (margin: ${fedex_undiscounted - FEDEX_UNDISCOUNTED_THRESHOLD:+,.0f})",
    ]
    (OUTPUT_DIR / "summary.md").write_text("\n".join(md_lines))
    print(f"    Saved summary.md")

    print(f"\n{'=' * 90}")
    print(f"ANALYSIS COMPLETE")
    print(f"{'=' * 90}")

    return result


if __name__ == "__main__":
    main()
