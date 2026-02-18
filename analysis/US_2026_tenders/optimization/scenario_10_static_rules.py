"""
Scenario 10: Static Routing Rules (Implementable in PCS)

Unlike S7 which requires per-shipment rate shopping across 353K unique cells,
S10 uses simple, static rules that can be configured in the production system:

    For each package type:
      1. If P2P zone AND weight <= P2P_cutoff → use P2P
      2. If non-P2P zone AND weight <= USPS_cutoff → use USPS
      3. Otherwise → use FedEx

The cutoffs are optimized per package type based on average cost comparison:
  - P2P cutoff: highest weight where P2P avg cost < FedEx avg cost (in P2P zones)
  - USPS cutoff: highest weight where USPS avg cost < FedEx avg cost (in non-P2P zones)

FedEx 16% earned discount constraint: if FedEx undiscounted volume drops below
$4.5M, the cutoffs are tightened (starting from the least impactful package types)
until the threshold is met.

Inputs:
  - P2P zone list: ~38K zip codes where P2P can deliver
  - Per package type: P2P weight cutoff and USPS weight cutoff

This is the closest achievable approximation to S7's optimization that can be
implemented with static routing rules.
"""

import polars as pl
import sys
from pathlib import Path

from analysis.US_2026_tenders.optimization.fedex_adjustment import (
    adjust_fedex_costs, adjust_and_aggregate, PP_DISCOUNT, BAKED_EARNED,
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
        pl.col("weight_lbs").ceil().cast(pl.Int32).alias("weight_bracket")
    )

    # Tag P2P availability
    df = df.with_columns(
        (pl.col("p2p_cost_total").is_not_null() & (pl.col("p2p_cost_total") > 0))
        .alias("p2p_available")
    )

    return df, s1_baseline


def find_optimal_cutoffs(df: pl.DataFrame) -> dict[str, tuple[int, int]]:
    """Find the optimal P2P and USPS weight cutoff for each package type.

    For each package type:
      - P2P cutoff: highest consecutive weight where P2P avg < FedEx avg in P2P zones
      - USPS cutoff: highest consecutive weight where USPS avg < FedEx avg in non-P2P zones

    Returns:
        Dict of packagetype -> (p2p_max_weight, usps_max_weight).
        Only includes package types where at least one cutoff > 0.
    """
    all_pkgs = df["packagetype"].unique().sort().to_list()
    cutoffs = {}

    for pkg in all_pkgs:
        sub = df.filter(pl.col("packagetype") == pkg)
        n = sub.shape[0]
        if n < 50:
            continue

        # P2P cutoff
        p2p_zone = sub.filter(pl.col("p2p_available"))
        best_p2p = 0
        if p2p_zone.shape[0] > 0:
            for wt in range(1, 60):
                w = p2p_zone.filter(pl.col("weight_bracket") == wt)
                if w.shape[0] < 5:
                    continue
                p2p_avg = float(w["p2p_cost_total"].mean())
                fedex_avg = float(w["fedex_cost_total"].mean())
                if p2p_avg < fedex_avg:
                    best_p2p = wt
                else:
                    break

        # USPS cutoff
        nop2p = sub.filter(~pl.col("p2p_available"))
        best_usps = 0
        if nop2p.shape[0] > 0:
            for wt in range(1, 60):
                w = nop2p.filter(pl.col("weight_bracket") == wt)
                if w.shape[0] < 5:
                    continue
                usps_avg = float(w["usps_cost_total"].mean())
                fedex_avg = float(w["fedex_cost_total"].mean())
                if usps_avg < fedex_avg:
                    best_usps = wt
                else:
                    break

        cutoffs[pkg] = (best_p2p, best_usps)

    return cutoffs


def apply_static_rules(
    df: pl.DataFrame,
    cutoffs: dict[str, tuple[int, int]],
) -> pl.DataFrame:
    """Apply static routing rules to assign carriers.

    Rules per package type:
      1. P2P zone + weight <= p2p_cutoff → P2P
      2. Non-P2P zone + weight <= usps_cutoff → USPS
      3. Otherwise → FedEx

    Returns DataFrame with 'assigned_carrier' and 'assigned_cost' columns.
    """
    # Build lookup DataFrame
    all_pkgs = df["packagetype"].unique().to_list()
    lookup_rows = []
    for pkg in all_pkgs:
        p, u = cutoffs.get(pkg, (0, 0))
        lookup_rows.append({"packagetype": pkg, "p2p_max_wt": p, "usps_max_wt": u})
    lookup = pl.DataFrame(lookup_rows)

    df = df.join(lookup, on="packagetype", how="left")

    carrier = (
        pl.when(
            pl.col("p2p_available") & (pl.col("weight_bracket") <= pl.col("p2p_max_wt"))
        )
        .then(pl.lit("P2P"))
        .when(
            (~pl.col("p2p_available"))
            & (pl.col("weight_bracket") <= pl.col("usps_max_wt"))
        )
        .then(pl.lit("USPS"))
        .otherwise(pl.lit("FEDEX"))
    )

    cost = (
        pl.when(carrier == "P2P")
        .then(pl.col("p2p_cost_total"))
        .when(carrier == "USPS")
        .then(pl.col("usps_cost_total"))
        .otherwise(pl.col("fedex_cost_total"))
    )

    df = df.with_columns([
        carrier.alias("assigned_carrier"),
        cost.alias("assigned_cost"),
    ])

    return df


def adjust_for_fedex_threshold(
    df: pl.DataFrame,
    cutoffs: dict[str, tuple[int, int]],
    threshold: float,
) -> tuple[pl.DataFrame, dict[str, tuple[int, int]], list[dict]]:
    """Tighten cutoffs until FedEx base rate threshold is met.

    Strategy: iteratively lower the P2P cutoff (or USPS cutoff) for the package type
    where the shift to FedEx has the lowest cost penalty per dollar of FedEx base rate
    gained. This minimizes the total cost increase needed to meet the threshold.

    Returns:
        (adjusted_df, adjusted_cutoffs, shift_log)
    """
    shift_log = []
    cutoffs = dict(cutoffs)  # copy

    while True:
        result = apply_static_rules(df, cutoffs)
        fedex_base = float(
            result.filter(pl.col("assigned_carrier") == "FEDEX")[
                "fedex_cost_base_rate"
            ].sum()
        )

        if fedex_base >= threshold:
            return result, cutoffs, shift_log

        shortfall = threshold - fedex_base

        # Find the best cutoff to lower: for each active cutoff, compute the
        # cost penalty and FedEx base rate gain from lowering by 1
        candidates = []
        for pkg, (p, u) in cutoffs.items():
            # Try lowering P2P cutoff
            if p > 0:
                new_cutoffs = dict(cutoffs)
                new_cutoffs[pkg] = (p - 1, u)
                new_result = apply_static_rules(df, new_cutoffs)
                new_cost = float(new_result["assigned_cost"].sum())
                new_fedex_base = float(
                    new_result.filter(pl.col("assigned_carrier") == "FEDEX")[
                        "fedex_cost_base_rate"
                    ].sum()
                )
                old_cost = float(result["assigned_cost"].sum())
                cost_penalty = new_cost - old_cost
                base_gain = new_fedex_base - fedex_base
                if base_gain > 0:
                    candidates.append({
                        "pkg": pkg,
                        "type": "P2P",
                        "old_cut": p,
                        "new_cut": p - 1,
                        "cost_penalty": cost_penalty,
                        "base_gain": base_gain,
                        "efficiency": cost_penalty / base_gain,
                    })

            # Try lowering USPS cutoff
            if u > 0:
                new_cutoffs = dict(cutoffs)
                new_cutoffs[pkg] = (p, u - 1)
                new_result = apply_static_rules(df, new_cutoffs)
                new_cost = float(new_result["assigned_cost"].sum())
                new_fedex_base = float(
                    new_result.filter(pl.col("assigned_carrier") == "FEDEX")[
                        "fedex_cost_base_rate"
                    ].sum()
                )
                old_cost = float(result["assigned_cost"].sum())
                cost_penalty = new_cost - old_cost
                base_gain = new_fedex_base - fedex_base
                if base_gain > 0:
                    candidates.append({
                        "pkg": pkg,
                        "type": "USPS",
                        "old_cut": u,
                        "new_cut": u - 1,
                        "cost_penalty": cost_penalty,
                        "base_gain": base_gain,
                        "efficiency": cost_penalty / base_gain,
                    })

        if not candidates:
            print("    WARNING: No more cutoffs to lower, threshold cannot be met")
            return apply_static_rules(df, cutoffs), cutoffs, shift_log

        # Pick the most efficient shift (lowest cost per dollar of base rate gained)
        best = min(candidates, key=lambda x: x["efficiency"])
        pkg = best["pkg"]
        p, u = cutoffs[pkg]
        if best["type"] == "P2P":
            cutoffs[pkg] = (best["new_cut"], u)
        else:
            cutoffs[pkg] = (p, best["new_cut"])

        shift_log.append(best)
        print(
            f"    Shift: {pkg} {best['type']} cutoff {best['old_cut']}→{best['new_cut']} "
            f"(penalty +${best['cost_penalty']:,.0f}, FedEx base +${best['base_gain']:,.0f}, "
            f"ratio {best['efficiency']:.2f})"
        )


def main():
    print("=" * 90)
    print("SCENARIO 10: Static Routing Rules (Implementable in PCS)")
    print("=" * 90)

    # [1] Load data
    print("\n[1] Loading shipment data...")
    df, SCENARIO_1_BASELINE = load_shipment_data()
    total_shipments = df.shape[0]

    # [2] Find optimal per-packagetype cutoffs
    print("\n[2] Finding optimal cutoffs per package type...")
    cutoffs = find_optimal_cutoffs(df)

    # Apply unconstrained
    result_unconstrained = apply_static_rules(df, cutoffs)
    cost_unconstrained = float(result_unconstrained["assigned_cost"].sum())
    fedex_base_unconstrained = float(
        result_unconstrained.filter(pl.col("assigned_carrier") == "FEDEX")[
            "fedex_cost_base_rate"
        ].sum()
    )

    print(f"\n    Unconstrained result:")
    print(f"      Total cost: ${cost_unconstrained:,.0f}")
    print(f"      FedEx base: ${fedex_base_unconstrained:,.0f} (threshold: ${FEDEX_BASE_RATE_THRESHOLD:,.0f})")
    print(f"      Threshold met: {'YES' if fedex_base_unconstrained >= FEDEX_BASE_RATE_THRESHOLD else 'NO'}")

    # Print per-packagetype cutoffs
    active = {k: v for k, v in cutoffs.items() if v[0] > 0 or v[1] > 0}
    print(f"\n    Active rules: {len(active)} package types (others default to FedEx)")
    print(f"    {'Package Type':<42} {'P2P≤':>5} {'USPS≤':>6}")
    print(f"    {'-'*55}")
    # Sort by shipment count
    pkg_counts = df.group_by("packagetype").agg(pl.len().alias("n"))
    for pkg in sorted(active.keys(), key=lambda x: -int(pkg_counts.filter(pl.col("packagetype") == x)["n"].item()) if pkg_counts.filter(pl.col("packagetype") == x).shape[0] > 0 else 0):
        p, u = active[pkg]
        n = int(pkg_counts.filter(pl.col("packagetype") == pkg)["n"].item()) if pkg_counts.filter(pl.col("packagetype") == pkg).shape[0] > 0 else 0
        p_str = str(p) if p > 0 else "-"
        u_str = str(u) if u > 0 else "-"
        print(f"    {pkg:<42} {p_str:>5} {u_str:>6}  ({n:>7,} ships)")

    # [3] Adjust for FedEx threshold if needed
    if fedex_base_unconstrained < FEDEX_BASE_RATE_THRESHOLD:
        print(f"\n[3] Adjusting cutoffs for FedEx threshold (shortfall: ${FEDEX_BASE_RATE_THRESHOLD - fedex_base_unconstrained:,.0f})...")
        result, adjusted_cutoffs, shift_log = adjust_for_fedex_threshold(
            df, cutoffs, FEDEX_BASE_RATE_THRESHOLD
        )
        print(f"\n    Shifts made: {len(shift_log)}")
        total_penalty = sum(s["cost_penalty"] for s in shift_log)
        print(f"    Total cost penalty: ${total_penalty:,.0f}")

        # Show what changed
        changed = {}
        for pkg in set(list(cutoffs.keys()) + list(adjusted_cutoffs.keys())):
            old = cutoffs.get(pkg, (0, 0))
            new = adjusted_cutoffs.get(pkg, (0, 0))
            if old != new:
                changed[pkg] = (old, new)

        if changed:
            print(f"\n    Changed cutoffs:")
            for pkg, (old, new) in sorted(changed.items()):
                print(f"      {pkg:<42} P2P: {old[0]}→{new[0]}  USPS: {old[1]}→{new[1]}")

        cutoffs = adjusted_cutoffs
    else:
        print("\n[3] FedEx threshold already met, no adjustment needed")
        result = result_unconstrained

    # [4] Final results
    total_cost = float(result["assigned_cost"].sum())
    fedex_base = float(
        result.filter(pl.col("assigned_carrier") == "FEDEX")[
            "fedex_cost_base_rate"
        ].sum()
    )
    fedex_undiscounted = fedex_base / BAKED_FACTOR

    print(f"\n{'=' * 90}")
    print(f"SCENARIO 10 RESULTS")
    print(f"{'=' * 90}")

    print(f"\n    Total cost:        ${total_cost:,.0f}")
    print(f"    S1 baseline:       ${SCENARIO_1_BASELINE:,.0f}")
    savings = SCENARIO_1_BASELINE - total_cost
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
    for carrier in ["USPS", "FEDEX", "P2P"]:
        c_df = result.filter(pl.col("assigned_carrier") == carrier)
        n = c_df.shape[0]
        cost = float(c_df["assigned_cost"].sum())
        avg = cost / n if n > 0 else 0
        pct = n / total_shipments * 100
        print(f"    {carrier:<10} {n:>12,} {pct:>7.1f}% ${cost:>14,.0f} ${avg:>9.2f}")
    print(f"    {'-' * 60}")
    print(f"    {'TOTAL':<10} {total_shipments:>12,} {'100.0%':>8} ${total_cost:>14,.0f}")

    # P2P coverage stats
    p2p_zips = result.filter(pl.col("p2p_available"))["shipping_zip_code"].n_unique()
    p2p_ships = result.filter(pl.col("assigned_carrier") == "P2P").shape[0]
    p2p_eligible = result.filter(pl.col("p2p_available")).shape[0]
    print(f"\n    P2P zone coverage:")
    print(f"      Unique zip codes:   {p2p_zips:,}")
    print(f"      Eligible shipments: {p2p_eligible:,} ({p2p_eligible/total_shipments*100:.1f}%)")
    print(f"      Actually routed:    {p2p_ships:,} ({p2p_ships/p2p_eligible*100:.1f}% of eligible)")

    # [5] Comparison vs S7
    # Load S7 assignments to compute S7 cost on same data
    s7_path = Path("analysis/US_2026_tenders/results/scenario_7_with_p2p/assignments.parquet")
    if s7_path.exists():
        print(f"\n[5] Comparison vs S7 (optimal per-shipment routing)")
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
        gap = total_cost - s7_total
        print(f"      S7 total:    ${s7_total:,.0f}")
        print(f"      S10 total:   ${total_cost:,.0f}")
        print(f"      Gap:         ${gap:+,.0f} ({gap / s7_total * 100:+.1f}%)")
        print(f"      S7 savings captured: {savings / (SCENARIO_1_BASELINE - s7_total) * 100:.1f}%")

    # [6] Validate: check every rule is actually saving money
    print(f"\n[6] Rule validation: cost impact per package type")
    active_cutoffs = {k: v for k, v in cutoffs.items() if v[0] > 0 or v[1] > 0}
    print(f"    {'Package Type':<42} {'P2P≤':>5} {'USPS≤':>6} {'Ships':>8} {'Savings':>12} {'Check':>6}")
    print(f"    {'-' * 83}")

    total_rule_savings = 0
    for pkg in sorted(active_cutoffs.keys(), key=lambda x: -int(pkg_counts.filter(pl.col("packagetype") == x)["n"].item()) if pkg_counts.filter(pl.col("packagetype") == x).shape[0] > 0 else 0):
        p, u = active_cutoffs[pkg]
        sub = result.filter(pl.col("packagetype") == pkg)
        n = sub.shape[0]
        cost_static = float(sub["assigned_cost"].sum())
        cost_all_fedex = float(sub["fedex_cost_total"].sum())
        rule_savings = cost_all_fedex - cost_static
        total_rule_savings += rule_savings
        ok = "OK" if rule_savings >= 0 else "WARN"
        p_str = str(p) if p > 0 else "-"
        u_str = str(u) if u > 0 else "-"
        print(f"    {pkg:<42} {p_str:>5} {u_str:>6} {n:>8,} ${rule_savings:>11,.0f} {ok:>6}")

    print(f"    {'-' * 83}")
    print(f"    {'Total rule savings vs all-FedEx':<56} ${total_rule_savings:>11,.0f}")

    # [7] Check for USPS-in-P2P-zone opportunities being missed
    print(f"\n[7] Missed opportunities: USPS cheaper than assigned carrier in P2P zones")
    p2p_assigned = result.filter(pl.col("assigned_carrier") == "P2P")
    usps_cheaper = p2p_assigned.filter(pl.col("usps_cost_total") < pl.col("p2p_cost_total"))
    if usps_cheaper.shape[0] > 0:
        overpay = float((usps_cheaper["p2p_cost_total"] - usps_cheaper["usps_cost_total"]).sum())
        print(f"    P2P assigned but USPS cheaper: {usps_cheaper.shape[0]:,} ships, overpay ${overpay:,.0f}")
    else:
        print(f"    None found")

    # Also check: FedEx assigned but USPS cheaper
    fedex_assigned = result.filter(pl.col("assigned_carrier") == "FEDEX")
    usps_cheaper_than_fedex = fedex_assigned.filter(pl.col("usps_cost_total") < pl.col("fedex_cost_total"))
    if usps_cheaper_than_fedex.shape[0] > 0:
        overpay2 = float((usps_cheaper_than_fedex["fedex_cost_total"] - usps_cheaper_than_fedex["usps_cost_total"]).sum())
        print(f"    FedEx assigned but USPS cheaper: {usps_cheaper_than_fedex.shape[0]:,} ships, overpay ${overpay2:,.0f}")

    # And P2P zones assigned to FedEx where P2P is cheaper
    fedex_in_p2p = fedex_assigned.filter(pl.col("p2p_available") & pl.col("p2p_cost_total").is_not_null())
    p2p_cheaper_than_fedex = fedex_in_p2p.filter(pl.col("p2p_cost_total") < pl.col("fedex_cost_total"))
    if p2p_cheaper_than_fedex.shape[0] > 0:
        overpay3 = float((p2p_cheaper_than_fedex["fedex_cost_total"] - p2p_cheaper_than_fedex["p2p_cost_total"]).sum())
        print(f"    FedEx assigned but P2P cheaper: {p2p_cheaper_than_fedex.shape[0]:,} ships, overpay ${overpay3:,.0f}")

    # [8] Final rule table for implementation
    print(f"\n{'=' * 90}")
    print(f"IMPLEMENTATION RULES")
    print(f"{'=' * 90}")
    print(f"\nStep 1: Configure P2P zone list ({p2p_zips:,} zip codes)")
    print(f"Step 2: Configure per-package-type routing rules:\n")

    final_cutoffs = cutoffs
    all_pkgs_sorted = sorted(
        df["packagetype"].unique().to_list(),
        key=lambda x: -int(pkg_counts.filter(pl.col("packagetype") == x)["n"].item())
        if pkg_counts.filter(pl.col("packagetype") == x).shape[0] > 0
        else 0,
    )

    print(f"    {'Package Type':<42} {'Rule':>50}")
    print(f"    {'-' * 95}")
    for pkg in all_pkgs_sorted:
        p, u = final_cutoffs.get(pkg, (0, 0))
        n = int(pkg_counts.filter(pl.col("packagetype") == pkg)["n"].item()) if pkg_counts.filter(pl.col("packagetype") == pkg).shape[0] > 0 else 0
        if n < 50:
            continue
        if p > 0 and u > 0:
            rule = f"P2P zone: P2P if wt≤{p}, else FedEx | Other: USPS if wt≤{u}, else FedEx"
        elif p > 0:
            rule = f"P2P zone: P2P if wt≤{p}, else FedEx | Other: FedEx"
        elif u > 0:
            rule = f"P2P zone: FedEx | Other: USPS if wt≤{u}, else FedEx"
        else:
            rule = "Always FedEx"
        print(f"    {pkg:<42} {rule}")

    # [9] Save results
    output_dir = Path("analysis/US_2026_tenders/results/scenario_10_static_rules")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Aggregate to (packagetype, zip, weight_bracket) level for assignments
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
    agg.select(save_cols).write_parquet(output_dir / "assignments.parquet")
    print(f"\n[9] Saved assignments to {output_dir / 'assignments.parquet'}")

    # Save the rule table as CSV
    rule_rows = []
    for pkg in all_pkgs_sorted:
        p, u = final_cutoffs.get(pkg, (0, 0))
        n = int(pkg_counts.filter(pl.col("packagetype") == pkg)["n"].item()) if pkg_counts.filter(pl.col("packagetype") == pkg).shape[0] > 0 else 0
        if n < 50:
            continue
        rule_rows.append({
            "packagetype": pkg,
            "shipments": n,
            "p2p_max_weight": p,
            "usps_max_weight": u,
        })
    rules_df = pl.DataFrame(rule_rows)
    rules_df.write_csv(output_dir / "routing_rules.csv")
    print(f"    Saved routing rules to {output_dir / 'routing_rules.csv'}")

    # Save P2P zip list
    p2p_zip_list = df.filter(pl.col("p2p_available"))["shipping_zip_code"].unique().sort()
    p2p_zip_list.to_frame().write_csv(output_dir / "p2p_zip_codes.csv")
    print(f"    Saved P2P zip list to {output_dir / 'p2p_zip_codes.csv'} ({p2p_zip_list.len():,} zips)")

    return cutoffs, result


if __name__ == "__main__":
    main()
