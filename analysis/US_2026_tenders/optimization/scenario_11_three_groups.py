"""
Scenario 11: 3-Group Static Routing Rules (Simplified S10)

S10 uses ~50 per-packagetype weight cutoffs. S11 simplifies this to just 3 rules
by grouping package types into Light / Medium / Heavy:

    Light  (small/flat):   P2P zone → P2P if wt ≤ 3   |  non-P2P → USPS if wt ≤ 3
    Medium (mid-size):     P2P zone → P2P if wt ≤ 21   |  non-P2P → USPS if wt ≤ 2
    Heavy  (oversized):    FedEx always

Group assignments are derived from S10's per-packagetype cutoffs:
  - Light:  S10 P2P cutoff 1-7 (small packages where P2P/USPS win only at low weights)
  - Medium: S10 P2P cutoff 8-30 (mid packages where P2P wins up to high weights)
  - Heavy:  S10 P2P cutoff 0 AND USPS cutoff ≤ 1 (oversized, FedEx always cheapest)

The 3 group cutoffs are found via brute-force search over all (P2P, USPS) combinations
per group, subject to the FedEx 16% earned discount threshold constraint.
"""

import polars as pl
import sys
from pathlib import Path

from analysis.US_2026_tenders.optimization.fedex_adjustment import (
    adjust_fedex_costs, PP_DISCOUNT, BAKED_EARNED,
)

sys.stdout.reconfigure(encoding="utf-8")

# FedEx earned discount parameters
FEDEX_TARGET_EARNED = 0.16
FEDEX_UNDISCOUNTED_THRESHOLD = 4_500_000
BAKED_FACTOR = 1 - PP_DISCOUNT - BAKED_EARNED  # 0.37
FEDEX_BASE_RATE_THRESHOLD = FEDEX_UNDISCOUNTED_THRESHOLD * BAKED_FACTOR  # $1,665,000

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
COMBINED_DATASETS = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "combined_datasets"
OUTPUT_DIR = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "results" / "scenario_11_three_groups"
S10_RESULTS = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "results" / "scenario_10_static_rules"

# Search ranges for cutoffs
P2P_SEARCH_MAX = 30
USPS_SEARCH_MAX = 10


def load_shipment_data() -> tuple[pl.DataFrame, float]:
    """Load shipment-level data with FedEx costs adjusted to 16% earned discount."""
    input_path = COMBINED_DATASETS / "shipments_unified.parquet"
    print(f"    Loading: {input_path.name}")
    df = pl.read_parquet(input_path)
    print(f"    {df.shape[0]:,} shipments loaded")

    df = adjust_fedex_costs(df, FEDEX_TARGET_EARNED)

    s1_baseline = float(df["cost_current_carrier"].sum())
    print(f"\n    Adjusted S1 baseline: ${s1_baseline:,.2f}")

    df = df.with_columns(
        pl.col("weight_lbs").ceil().cast(pl.Int32).alias("weight_bracket"),
        (pl.col("p2p_cost_total").is_not_null() & (pl.col("p2p_cost_total") > 0))
        .alias("p2p_available"),
    )

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
    df_group: pl.DataFrame, p2p_cut: int, usps_cut: int
) -> tuple[float, float]:
    """Compute total cost and FedEx base rate for a group with given cutoffs.

    Returns (total_cost, fedex_base_rate).
    """
    carrier = (
        pl.when(pl.col("p2p_available") & (pl.col("weight_bracket") <= p2p_cut))
        .then(pl.lit("P2P"))
        .when((~pl.col("p2p_available")) & (pl.col("weight_bracket") <= usps_cut))
        .then(pl.lit("USPS"))
        .otherwise(pl.lit("FEDEX"))
    )
    cost = (
        pl.when(carrier == "P2P").then(pl.col("p2p_cost_total"))
        .when(carrier == "USPS").then(pl.col("usps_cost_total"))
        .otherwise(pl.col("fedex_cost_total"))
    )
    fedex_base = (
        pl.when(carrier == "FEDEX").then(pl.col("fedex_cost_base_rate"))
        .otherwise(pl.lit(0.0))
    )
    row = df_group.select(
        cost.sum().alias("total_cost"),
        fedex_base.sum().alias("fedex_base"),
    ).row(0)
    return row[0], row[1]


def precompute_group_grid(
    df_group: pl.DataFrame, max_p2p: int, max_usps: int
) -> dict[tuple[int, int], tuple[float, float]]:
    """Precompute (total_cost, fedex_base) for all (p2p_cut, usps_cut) combinations."""
    grid = {}
    for p in range(0, max_p2p + 1):
        for u in range(0, max_usps + 1):
            grid[(p, u)] = compute_group_costs(df_group, p, u)
    return grid


def find_best_cutoffs(
    light_grid: dict, medium_grid: dict,
    heavy_cost: float, heavy_fedex_base: float,
    threshold: float,
) -> tuple[dict, dict]:
    """Find best (p2p, usps) cutoffs per group, with and without FedEx threshold.

    Returns (best_constrained, best_unconstrained) dicts with keys:
      lp, lu, mp, mu, total_cost, fedex_base
    """
    best_unc = None
    best_con = None

    for (lp, lu), (lc, lb) in light_grid.items():
        for (mp, mu), (mc, mb) in medium_grid.items():
            tc = lc + mc + heavy_cost
            fb = lb + mb + heavy_fedex_base

            if best_unc is None or tc < best_unc["total_cost"]:
                best_unc = dict(lp=lp, lu=lu, mp=mp, mu=mu, total_cost=tc, fedex_base=fb)

            if fb >= threshold and (best_con is None or tc < best_con["total_cost"]):
                best_con = dict(lp=lp, lu=lu, mp=mp, mu=mu, total_cost=tc, fedex_base=fb)

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
            & pl.col("p2p_available")
            & (pl.col("weight_bracket") <= lp)
        ).then(pl.lit("P2P"))
        .when(
            pl.col("packagetype").is_in(light_set)
            & (~pl.col("p2p_available"))
            & (pl.col("weight_bracket") <= lu)
        ).then(pl.lit("USPS"))
        .when(
            pl.col("packagetype").is_in(medium_set)
            & pl.col("p2p_available")
            & (pl.col("weight_bracket") <= mp)
        ).then(pl.lit("P2P"))
        .when(
            pl.col("packagetype").is_in(medium_set)
            & (~pl.col("p2p_available"))
            & (pl.col("weight_bracket") <= mu)
        ).then(pl.lit("USPS"))
        .otherwise(pl.lit("FEDEX"))
    )
    cost = (
        pl.when(carrier == "P2P").then(pl.col("p2p_cost_total"))
        .when(carrier == "USPS").then(pl.col("usps_cost_total"))
        .otherwise(pl.col("fedex_cost_total"))
    )
    return df.with_columns(
        carrier.alias("assigned_carrier"),
        cost.alias("assigned_cost"),
    )


def main():
    print("=" * 90)
    print("SCENARIO 11: 3-Group Static Routing Rules (Simplified S10)")
    print("=" * 90)

    # ── [1] Load data ──────────────────────────────────────────────────
    print("\n[1] Loading shipment data...")
    df, SCENARIO_1_BASELINE = load_shipment_data()
    total_shipments = df.shape[0]

    # ── [2] Define groups from S10 cutoffs ─────────────────────────────
    print("\n[2] Defining package type groups from S10 cutoffs...")
    light_pkgs, medium_pkgs, heavy_pkgs = define_groups()

    # Any package type not in S10's rules → Heavy (default to FedEx)
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

    # ── [3] Precompute cost grids ──────────────────────────────────────
    print("\n[3] Precomputing cost grids for Light and Medium groups...")

    df_light = df.filter(pl.col("packagetype").is_in(light_set))
    df_medium = df.filter(pl.col("packagetype").is_in(medium_set))
    df_heavy = df.filter(pl.col("packagetype").is_in(heavy_set))

    light_grid = precompute_group_grid(df_light, P2P_SEARCH_MAX, USPS_SEARCH_MAX)
    print(f"    Light grid: {len(light_grid)} combinations computed")
    medium_grid = precompute_group_grid(df_medium, P2P_SEARCH_MAX, USPS_SEARCH_MAX)
    print(f"    Medium grid: {len(medium_grid)} combinations computed")

    heavy_cost = float(df_heavy["fedex_cost_total"].sum())
    heavy_fedex_base = float(df_heavy["fedex_cost_base_rate"].sum())
    print(f"    Heavy (always FedEx): cost=${heavy_cost:,.0f}, FedEx base=${heavy_fedex_base:,.0f}")

    # ── [4] Find optimal cutoffs ───────────────────────────────────────
    print("\n[4] Searching for optimal cutoffs...")
    best_con, best_unc = find_best_cutoffs(
        light_grid, medium_grid, heavy_cost, heavy_fedex_base,
        FEDEX_BASE_RATE_THRESHOLD,
    )

    print(f"\n    Unconstrained optimum (ignoring FedEx threshold):")
    print(f"      Light:  P2P ≤ {best_unc['lp']},  USPS ≤ {best_unc['lu']}")
    print(f"      Medium: P2P ≤ {best_unc['mp']},  USPS ≤ {best_unc['mu']}")
    print(f"      Heavy:  FedEx always")
    print(f"      Total cost: ${best_unc['total_cost']:,.0f}")
    print(f"      FedEx base: ${best_unc['fedex_base']:,.0f} (threshold: ${FEDEX_BASE_RATE_THRESHOLD:,.0f})")
    threshold_met_unc = best_unc["fedex_base"] >= FEDEX_BASE_RATE_THRESHOLD
    print(f"      Threshold met: {'YES' if threshold_met_unc else 'NO'}")

    if best_con is None:
        print("\n    WARNING: No feasible solution meets FedEx threshold!")
        best = best_unc
    else:
        print(f"\n    Constrained optimum (FedEx threshold met):")
        print(f"      Light:  P2P ≤ {best_con['lp']},  USPS ≤ {best_con['lu']}")
        print(f"      Medium: P2P ≤ {best_con['mp']},  USPS ≤ {best_con['mu']}")
        print(f"      Heavy:  FedEx always")
        print(f"      Total cost: ${best_con['total_cost']:,.0f}")
        print(f"      FedEx base: ${best_con['fedex_base']:,.0f} (threshold: ${FEDEX_BASE_RATE_THRESHOLD:,.0f})")
        margin = best_con["fedex_base"] - FEDEX_BASE_RATE_THRESHOLD
        print(f"      Margin: ${margin:+,.0f}")

        if not threshold_met_unc:
            penalty = best_con["total_cost"] - best_unc["total_cost"]
            print(f"\n    Threshold enforcement cost: ${penalty:+,.0f}")
        best = best_con

    # ── [5] Apply final rules and compute results ──────────────────────
    print(f"\n[5] Applying final rules...")
    lp, lu, mp, mu = best["lp"], best["lu"], best["mp"], best["mu"]
    result = apply_group_rules(df, light_set, medium_set, lp, lu, mp, mu)

    total_cost = float(result["assigned_cost"].sum())
    fedex_base = float(
        result.filter(pl.col("assigned_carrier") == "FEDEX")["fedex_cost_base_rate"].sum()
    )
    fedex_undiscounted = fedex_base / BAKED_FACTOR
    savings = SCENARIO_1_BASELINE - total_cost

    print(f"\n{'=' * 90}")
    print(f"SCENARIO 11 RESULTS")
    print(f"{'=' * 90}")

    print(f"\n    Total cost:        ${total_cost:,.0f}")
    print(f"    S1 baseline:       ${SCENARIO_1_BASELINE:,.0f}")
    print(f"    Savings vs S1:     ${savings:,.0f} ({savings / SCENARIO_1_BASELINE * 100:.1f}%)")

    print(f"\n    FedEx earned discount:")
    print(f"      Base rate total:    ${fedex_base:,.0f}")
    print(f"      Undiscounted equiv: ${fedex_undiscounted:,.0f}")
    print(f"      Threshold:          ${FEDEX_UNDISCOUNTED_THRESHOLD:,}")
    print(f"      Margin:             ${fedex_undiscounted - FEDEX_UNDISCOUNTED_THRESHOLD:+,.0f}")
    print(f"      16% tier met:       {'YES' if fedex_base >= FEDEX_BASE_RATE_THRESHOLD else 'NO'}")

    # Carrier mix
    print(f"\n    {'Carrier':<10} {'Shipments':>12} {'%':>8} {'Cost':>15} {'Avg':>10}")
    print(f"    {'-' * 60}")
    for carrier_name in ["USPS", "FEDEX", "P2P"]:
        c_df = result.filter(pl.col("assigned_carrier") == carrier_name)
        n = c_df.shape[0]
        cost = float(c_df["assigned_cost"].sum())
        avg = cost / n if n > 0 else 0
        pct = n / total_shipments * 100
        print(f"    {carrier_name:<10} {n:>12,} {pct:>7.1f}% ${cost:>14,.0f} ${avg:>9.2f}")
    print(f"    {'-' * 60}")
    print(f"    {'TOTAL':<10} {total_shipments:>12,} {'100.0%':>8} ${total_cost:>14,.0f}")

    # Per-group breakdown
    print(f"\n    Per-group breakdown:")
    for name, pkgs, pc, uc in [("Light", light_pkgs, lp, lu), ("Medium", medium_pkgs, mp, mu), ("Heavy", heavy_pkgs, 0, 0)]:
        sub = result.filter(pl.col("packagetype").is_in(pkgs))
        n = sub.shape[0]
        cost = float(sub["assigned_cost"].sum())
        carrier_counts = sub.group_by("assigned_carrier").agg(pl.len().alias("n")).sort("assigned_carrier")
        print(f"\n    {name} (P2P≤{pc}, USPS≤{uc}): {n:,} ships, ${cost:,.0f}")
        for r in carrier_counts.iter_rows(named=True):
            pct = r["n"] / n * 100
            print(f"      {r['assigned_carrier']:8s}  {r['n']:>8,}  ({pct:5.1f}%)")

    # P2P coverage stats
    p2p_zips = result.filter(pl.col("p2p_available"))["shipping_zip_code"].n_unique()
    p2p_ships = result.filter(pl.col("assigned_carrier") == "P2P").shape[0]
    p2p_eligible = result.filter(pl.col("p2p_available")).shape[0]
    print(f"\n    P2P zone coverage:")
    print(f"      Unique zip codes:   {p2p_zips:,}")
    print(f"      Eligible shipments: {p2p_eligible:,} ({p2p_eligible / total_shipments * 100:.1f}%)")
    print(f"      Actually routed:    {p2p_ships:,} ({p2p_ships / p2p_eligible * 100:.1f}% of eligible)")

    # ── [6] Comparison vs S7 and S10 ───────────────────────────────────
    s7_path = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "results" / "scenario_7_with_p2p" / "assignments.parquet"
    if s7_path.exists():
        print(f"\n[6] Comparison vs S7 and S10")
        s7_agg = pl.read_parquet(s7_path)
        s7_carriers = s7_agg.select([
            "packagetype", "shipping_zip_code", "weight_bracket",
            pl.col("assigned_carrier").alias("s7_carrier"),
        ])
        s7_joined = df.join(
            s7_carriers,
            on=["packagetype", "shipping_zip_code", "weight_bracket"],
            how="left",
        )
        s7_cost_expr = (
            pl.when(pl.col("s7_carrier") == "USPS").then(pl.col("usps_cost_total"))
            .when(pl.col("s7_carrier") == "FEDEX").then(pl.col("fedex_cost_total"))
            .when(pl.col("s7_carrier") == "P2P").then(pl.col("p2p_cost_total"))
            .otherwise(pl.col("cost_current_carrier"))
        )
        s7_total = float(s7_joined.select(s7_cost_expr.sum()).item())
        s7_savings = SCENARIO_1_BASELINE - s7_total

        s10_cost = 4_450_862  # from S10 output
        s10_savings = SCENARIO_1_BASELINE - s10_cost

        print(f"\n    {'Approach':<35} {'Cost':>12} {'Savings':>10} {'vs S1':>8} {'S7 captured':>13}")
        print(f"    {'-' * 82}")
        for label, c in [
            ("S1 Baseline", SCENARIO_1_BASELINE),
            ("S11 3-Group rules", total_cost),
            ("S10 Per-packagetype (~50 rules)", s10_cost),
            ("S7 Per-shipment optimal", s7_total),
        ]:
            sv = SCENARIO_1_BASELINE - c
            pct = sv / SCENARIO_1_BASELINE * 100 if sv > 0 else 0
            captured = sv / s7_savings * 100 if s7_savings > 0 and sv > 0 else 0
            print(f"    {label:<35} ${c:>11,.0f} ${sv:>9,.0f} {pct:>7.1f}% {captured:>12.1f}%")

        print(f"\n    S11 gap vs S10: ${total_cost - s10_cost:+,.0f}/year")
        print(f"    S11 gap vs S7:  ${total_cost - s7_total:+,.0f}/year")

    # ── [7] Missed opportunities ───────────────────────────────────────
    print(f"\n[7] Missed opportunities (inherent to 3-group static rules)")

    # FedEx assigned but P2P cheaper
    fedex_assigned = result.filter(pl.col("assigned_carrier") == "FEDEX")
    fedex_in_p2p = fedex_assigned.filter(
        pl.col("p2p_available") & pl.col("p2p_cost_total").is_not_null()
    )
    p2p_cheaper = fedex_in_p2p.filter(pl.col("p2p_cost_total") < pl.col("fedex_cost_total"))
    if p2p_cheaper.shape[0] > 0:
        overpay = float((p2p_cheaper["fedex_cost_total"] - p2p_cheaper["p2p_cost_total"]).sum())
        print(f"    FedEx assigned, P2P cheaper:  {p2p_cheaper.shape[0]:>7,} ships, overpay ${overpay:>10,.0f}")

    # FedEx assigned but USPS cheaper
    usps_cheaper = fedex_assigned.filter(pl.col("usps_cost_total") < pl.col("fedex_cost_total"))
    if usps_cheaper.shape[0] > 0:
        overpay = float((usps_cheaper["fedex_cost_total"] - usps_cheaper["usps_cost_total"]).sum())
        print(f"    FedEx assigned, USPS cheaper: {usps_cheaper.shape[0]:>7,} ships, overpay ${overpay:>10,.0f}")

    # P2P assigned but USPS cheaper
    p2p_assigned = result.filter(pl.col("assigned_carrier") == "P2P")
    usps_better = p2p_assigned.filter(pl.col("usps_cost_total") < pl.col("p2p_cost_total"))
    if usps_better.shape[0] > 0:
        overpay = float((usps_better["p2p_cost_total"] - usps_better["usps_cost_total"]).sum())
        print(f"    P2P assigned, USPS cheaper:   {usps_better.shape[0]:>7,} ships, overpay ${overpay:>10,.0f}")

    # ── [8] Rule validation: verify each group rule saves vs all-FedEx ─
    print(f"\n[8] Rule validation: savings per group vs all-FedEx")
    total_rule_savings = 0
    for name, pkgs, pc, uc in [("Light", light_pkgs, lp, lu), ("Medium", medium_pkgs, mp, mu)]:
        sub = result.filter(pl.col("packagetype").is_in(pkgs))
        cost_static = float(sub["assigned_cost"].sum())
        cost_all_fedex = float(sub["fedex_cost_total"].sum())
        rule_savings = cost_all_fedex - cost_static
        total_rule_savings += rule_savings
        print(f"    {name:8s} (P2P≤{pc}, USPS≤{uc}):  ${rule_savings:>12,.0f} saved vs all-FedEx")
    print(f"    {'Total':8s}                   ${total_rule_savings:>12,.0f} saved vs all-FedEx")

    # ── [9] Save results ───────────────────────────────────────────────
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Assignments parquet
    agg = result.group_by(["packagetype", "shipping_zip_code", "weight_bracket"]).agg([
        pl.len().alias("shipment_count"),
        pl.col("assigned_carrier").first().alias("assigned_carrier"),
        pl.col("assigned_cost").sum().alias("assigned_cost_total"),
        pl.col("usps_cost_total").sum().alias("usps_cost_total"),
        pl.col("fedex_cost_total").sum().alias("fedex_cost_total"),
        pl.col("p2p_cost_total").sum().alias("p2p_cost_total"),
        pl.col("fedex_cost_base_rate").sum().alias("fedex_cost_base_rate_total"),
    ])
    save_cols = [
        "packagetype", "shipping_zip_code", "weight_bracket",
        "shipment_count", "assigned_carrier",
        "usps_cost_total", "fedex_cost_total", "p2p_cost_total",
        "fedex_cost_base_rate_total",
    ]
    agg.select(save_cols).write_parquet(OUTPUT_DIR / "assignments.parquet")
    print(f"\n[9] Saved assignments to {OUTPUT_DIR / 'assignments.parquet'}")

    # Routing rules CSV (per packagetype, sorted by shipments desc)
    pkg_counts = df.group_by("packagetype").agg(pl.len().alias("n"))
    rule_rows = []
    for name, pkgs, pc, uc in [("Light", light_pkgs, lp, lu), ("Medium", medium_pkgs, mp, mu), ("Heavy", heavy_pkgs, 0, 0)]:
        for pkg in pkgs:
            n = int(pkg_counts.filter(pl.col("packagetype") == pkg)["n"].item()) if pkg_counts.filter(pl.col("packagetype") == pkg).shape[0] > 0 else 0
            rule_rows.append({
                "packagetype": pkg,
                "group": name,
                "shipments": n,
                "p2p_max_weight": pc,
                "usps_max_weight": uc,
            })
    rules_df = pl.DataFrame(rule_rows).sort("shipments", descending=True)
    rules_df.write_csv(OUTPUT_DIR / "routing_rules.csv")
    print(f"    Saved routing rules to {OUTPUT_DIR / 'routing_rules.csv'}")

    # Group summary CSV (3 rows)
    summary_rows = [
        {"group": "Light", "p2p_max_weight": lp, "usps_max_weight": lu, "package_types": len(light_pkgs), "shipments": df.filter(pl.col("packagetype").is_in(light_set)).shape[0]},
        {"group": "Medium", "p2p_max_weight": mp, "usps_max_weight": mu, "package_types": len(medium_pkgs), "shipments": df.filter(pl.col("packagetype").is_in(medium_set)).shape[0]},
        {"group": "Heavy", "p2p_max_weight": 0, "usps_max_weight": 0, "package_types": len(heavy_pkgs), "shipments": df.filter(pl.col("packagetype").is_in(heavy_set)).shape[0]},
    ]
    pl.DataFrame(summary_rows).write_csv(OUTPUT_DIR / "group_summary.csv")
    print(f"    Saved group summary to {OUTPUT_DIR / 'group_summary.csv'}")

    # P2P zip list (same as S10)
    p2p_zip_list = df.filter(pl.col("p2p_available"))["shipping_zip_code"].unique().sort()
    p2p_zip_list.to_frame().write_csv(OUTPUT_DIR / "p2p_zip_codes.csv")
    print(f"    Saved P2P zip list to {OUTPUT_DIR / 'p2p_zip_codes.csv'} ({p2p_zip_list.len():,} zips)")

    return result


if __name__ == "__main__":
    main()
