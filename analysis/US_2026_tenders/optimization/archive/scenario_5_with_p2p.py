"""
Scenario 5: Optimal Carrier Mix with P2P Added

Extends Scenario 4 by adding P2P as a fourth carrier option.
For each constraint combination, uses two methods and picks the cheaper:
  - Method A: Greedy assignment with all carriers (including P2P) + adjust
  - Method B: Take S4's solution and improve by switching to P2P where cheaper
Method B guarantees S5 cost <= S4 cost for every constraint combination.

Constraint combinations (same as S4 but with P2P added):
- Both constraints: OnTrac >= 279K, USPS >= 140K (4 carriers)
- Drop OnTrac: USPS >= 140K (3 carriers: USPS + FedEx + P2P)
- Drop USPS: OnTrac >= 279K (3 carriers: OnTrac + FedEx + P2P)
- Drop both: No constraints (FedEx + P2P)
"""

import polars as pl
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# Baseline from Scenario 1
SCENARIO_1_BASELINE = 5_833_893.77

# S4 variants (without P2P) - mirrored from scenario_4
S4_VARIANTS = [
    {"name": "Both constraints", "short": "OUF", "available": ["ONTRAC", "USPS", "FEDEX"], "minimums": {"ONTRAC": 279_080, "USPS": 140_000}},
    {"name": "Drop OnTrac", "short": "UF", "available": ["USPS", "FEDEX"], "minimums": {"USPS": 140_000}},
    {"name": "Drop USPS", "short": "OF", "available": ["ONTRAC", "FEDEX"], "minimums": {"ONTRAC": 279_080}},
    {"name": "Drop both", "short": "F", "available": ["FEDEX"], "minimums": {}},
]

# S5 variants (with P2P added to each S4 variant)
S5_VARIANTS = [
    {"name": "Both constraints", "short": "OUFP", "available": ["ONTRAC", "USPS", "FEDEX", "P2P"], "minimums": {"ONTRAC": 279_080, "USPS": 140_000}},
    {"name": "Drop OnTrac", "short": "UFP", "available": ["USPS", "FEDEX", "P2P"], "minimums": {"USPS": 140_000}},
    {"name": "Drop USPS", "short": "OFP", "available": ["ONTRAC", "FEDEX", "P2P"], "minimums": {"ONTRAC": 279_080}},
    {"name": "Drop both", "short": "FP", "available": ["FEDEX", "P2P"], "minimums": {}},
]


def load_data() -> pl.DataFrame:
    """Load the aggregated shipment data."""
    path = Path("analysis/US_2026_tenders/combined_datasets/shipments_aggregated.parquet")
    return pl.read_parquet(path)


def greedy_assignment(df: pl.DataFrame, available_carriers: list[str]) -> pl.DataFrame:
    """Assign each group to the cheapest available carrier.

    Null costs are ignored (carrier can't service that group).
    FedEx is fallback if available (100% coverage).
    """
    cost_cols = [f"{c.lower()}_cost_avg" for c in available_carriers]

    df = df.with_columns([
        pl.min_horizontal(*cost_cols).alias("min_cost_avg"),
    ])

    fallback = "FEDEX" if "FEDEX" in available_carriers else available_carriers[-1]
    non_fallback = [c for c in available_carriers if c != fallback]

    if not non_fallback:
        df = df.with_columns([pl.lit(fallback).alias("assigned_carrier")])
    else:
        first = non_fallback[0]
        chain = pl.when(
            (pl.col(f"{first.lower()}_cost_avg") == pl.col("min_cost_avg")) &
            (pl.col(f"{first.lower()}_cost_avg").is_not_null())
        ).then(pl.lit(first))

        for carrier in non_fallback[1:]:
            cost_col = f"{carrier.lower()}_cost_avg"
            chain = chain.when(
                (pl.col(cost_col) == pl.col("min_cost_avg")) &
                (pl.col(cost_col).is_not_null())
            ).then(pl.lit(carrier))

        df = df.with_columns([chain.otherwise(pl.lit(fallback)).alias("assigned_carrier")])

    return df


def get_carrier_volume(df: pl.DataFrame, carrier: str) -> int:
    """Get total shipment count assigned to a carrier."""
    vol = df.filter(pl.col("assigned_carrier") == carrier)["shipment_count"].sum()
    return int(vol) if vol else 0


def adjust_for_constraints(
    df: pl.DataFrame,
    available_carriers: list[str],
    enforced_minimums: dict[str, int],
) -> tuple[pl.DataFrame, list[dict]]:
    """Shift groups to meet enforced minimums.

    Priority: OnTrac first (contractual), then USPS.
    Prefers shifting from non-P2P carriers first, then P2P if needed.
    """
    if not enforced_minimums:
        return df, []

    shift_log = []
    df = df.with_row_index("_row_idx")
    df = df.with_columns([pl.lit(False).alias("locked")])

    for carrier in ["ONTRAC", "USPS"]:
        if carrier not in enforced_minimums:
            continue
        min_required = enforced_minimums[carrier]
        volume = get_carrier_volume(df, carrier)
        shortfall = max(0, min_required - volume)

        if shortfall <= 0:
            df = df.with_columns([
                pl.when(pl.col("assigned_carrier") == carrier)
                  .then(pl.lit(True))
                  .otherwise(pl.col("locked"))
                  .alias("locked")
            ])
            continue

        print(f"\n    {carrier} has shortfall of {shortfall:,} shipments")

        cost_col_to = f"{carrier.lower()}_cost_avg"
        # Prefer shifting from non-P2P first, then P2P
        non_p2p = [c for c in available_carriers if c != carrier and c != "P2P"]
        p2p_list = ["P2P"] if "P2P" in available_carriers else []

        for source_group_name, source_carriers in [("non-P2P", non_p2p), ("P2P", p2p_list)]:
            # Recalculate shortfall
            volume = get_carrier_volume(df, carrier)
            shortfall = max(0, min_required - volume)
            if shortfall <= 0:
                break

            all_penalties = []
            for from_carrier in source_carriers:
                cost_col_from = f"{from_carrier.lower()}_cost_avg"
                available = df.filter(
                    (pl.col("assigned_carrier") == from_carrier) &
                    (~pl.col("locked")) &
                    (pl.col(cost_col_to).is_not_null())
                )
                if available.shape[0] > 0:
                    penalties = available.with_columns([
                        ((pl.col(cost_col_to) - pl.col(cost_col_from)) * pl.col("shipment_count")).alias("shift_penalty"),
                    ])
                    all_penalties.append(penalties)

            if not all_penalties:
                continue

            combined = pl.concat(all_penalties).sort("shift_penalty")
            combined = combined.with_columns([
                pl.col("shipment_count").cum_sum().alias("cumulative_shipments")
            ])

            groups_needed = combined.filter(pl.col("cumulative_shipments") >= shortfall)
            if groups_needed.shape[0] > 0:
                cutoff_idx = combined.shape[0] - groups_needed.shape[0] + 1
            else:
                cutoff_idx = combined.shape[0]

            groups_to_shift = combined.head(cutoff_idx)
            shift_indices = groups_to_shift["_row_idx"].to_list()
            shifted_volume = int(groups_to_shift["shipment_count"].sum())
            shifted_cost = float(groups_to_shift["shift_penalty"].sum())

            print(f"      Shifting {len(shift_indices):,} groups ({shifted_volume:,} shipments) from {source_group_name} to {carrier}")
            print(f"      Cost penalty: ${shifted_cost:,.2f}")

            df = df.with_columns([
                pl.when(pl.col("_row_idx").is_in(shift_indices))
                  .then(pl.lit(carrier))
                  .otherwise(pl.col("assigned_carrier"))
                  .alias("assigned_carrier"),
                pl.when(pl.col("_row_idx").is_in(shift_indices))
                  .then(pl.lit(True))
                  .otherwise(pl.col("locked"))
                  .alias("locked"),
            ])

            shift_log.append({
                "carrier": carrier,
                "source": source_group_name,
                "groups_shifted": len(shift_indices),
                "shipments_shifted": shifted_volume,
                "cost_penalty": shifted_cost,
            })

        df = df.with_columns([
            pl.when(pl.col("assigned_carrier") == carrier)
              .then(pl.lit(True))
              .otherwise(pl.col("locked"))
              .alias("locked")
        ])

    df = df.drop(["_row_idx", "locked"])
    return df, shift_log


def calculate_costs(df: pl.DataFrame, available_carriers: list[str]) -> dict:
    """Calculate total costs by carrier."""
    results = {}
    for carrier in available_carriers:
        carrier_df = df.filter(pl.col("assigned_carrier") == carrier)
        cost_col = f"{carrier.lower()}_cost_total"
        shipments = carrier_df["shipment_count"].sum()
        total_cost = carrier_df[cost_col].sum()
        results[carrier] = {
            "shipments": int(shipments) if shipments else 0,
            "cost": float(total_cost) if total_cost else 0.0,
        }
    return results


def run_variant_s4(df: pl.DataFrame, variant: dict) -> dict:
    """Run a S4 variant (without P2P) to establish baseline."""
    available = variant["available"]
    minimums = variant["minimums"]

    df_result = greedy_assignment(df.clone(), available)
    df_result, shift_log = adjust_for_constraints(df_result, available, minimums)
    costs = calculate_costs(df_result, available)

    total_shipments = sum(c["shipments"] for c in costs.values())
    total_cost = sum(c["cost"] for c in costs.values())

    return {
        "df": df_result,
        "costs": costs,
        "total_shipments": total_shipments,
        "total_cost": total_cost,
    }


def method_a_greedy(df: pl.DataFrame, variant: dict) -> dict:
    """Method A: Greedy assignment with all carriers (including P2P) + adjust."""
    available = variant["available"]
    minimums = variant["minimums"]

    df_result = greedy_assignment(df.clone(), available)
    df_result, shift_log = adjust_for_constraints(df_result, available, minimums)
    costs = calculate_costs(df_result, available)

    total_shipments = sum(c["shipments"] for c in costs.values())
    total_cost = sum(c["cost"] for c in costs.values())

    return {
        "method": "A",
        "df": df_result,
        "costs": costs,
        "total_shipments": total_shipments,
        "total_cost": total_cost,
        "shift_log": shift_log,
    }


def method_b_improve_s4(df: pl.DataFrame, s4_result: dict, enforced_minimums: dict) -> dict:
    """Method B: Take S4's solution and improve by switching to P2P where cheaper.

    Guarantees S5 cost <= S4 cost because we only make beneficial switches.

    Strategy:
    - FedEx -> P2P: switch all where P2P is cheaper (always safe, no FedEx minimum)
    - USPS -> P2P: switch where P2P is cheaper, up to USPS surplus above minimum
    - OnTrac -> P2P: switch where P2P is cheaper, up to OnTrac surplus above minimum
    """
    df_result = s4_result["df"].clone()

    # The S4 result has all cost columns from the original data (including p2p_cost_avg/total)
    # because greedy_assignment only changes assigned_carrier, not cost columns

    # Determine current cost for each group based on assigned carrier
    df_result = df_result.with_columns([
        pl.when(pl.col("assigned_carrier") == "ONTRAC").then(pl.col("ontrac_cost_avg"))
          .when(pl.col("assigned_carrier") == "USPS").then(pl.col("usps_cost_avg"))
          .when(pl.col("assigned_carrier") == "FEDEX").then(pl.col("fedex_cost_avg"))
          .otherwise(None)
          .alias("_current_cost_avg"),
    ])

    # P2P savings per group (positive = P2P is cheaper)
    df_result = df_result.with_columns([
        ((pl.col("_current_cost_avg") - pl.col("p2p_cost_avg")) * pl.col("shipment_count")).alias("_p2p_savings"),
    ])

    df_result = df_result.with_row_index("_row_idx")
    switches = []

    # Process carriers: FedEx first (no minimum), then USPS, then OnTrac
    for carrier in ["FEDEX", "USPS", "ONTRAC"]:
        min_required = enforced_minimums.get(carrier, 0)
        carrier_volume = get_carrier_volume(df_result, carrier)
        surplus = carrier_volume - min_required

        if surplus <= 0:
            continue

        # Find groups where P2P is cheaper and can service
        candidates = df_result.filter(
            (pl.col("assigned_carrier") == carrier) &
            (pl.col("p2p_cost_avg").is_not_null()) &
            (pl.col("_p2p_savings") > 0)
        ).sort("_p2p_savings", descending=True)  # Best savings first

        if candidates.shape[0] == 0:
            continue

        # Use cumsum to find groups we can switch within surplus
        candidates = candidates.with_columns([
            pl.col("shipment_count").cum_sum().alias("_cumulative")
        ])

        # Only switch up to surplus
        switchable = candidates.filter(pl.col("_cumulative") <= surplus)

        if switchable.shape[0] == 0:
            continue

        switch_indices = switchable["_row_idx"].to_list()
        switched_volume = int(switchable["shipment_count"].sum())
        switched_savings = float(switchable["_p2p_savings"].sum())

        df_result = df_result.with_columns([
            pl.when(pl.col("_row_idx").is_in(switch_indices))
              .then(pl.lit("P2P"))
              .otherwise(pl.col("assigned_carrier"))
              .alias("assigned_carrier")
        ])

        switches.append({
            "from": carrier,
            "groups": len(switch_indices),
            "shipments": switched_volume,
            "savings": switched_savings,
        })

    # Drop temp columns
    temp_cols = ["_current_cost_avg", "_p2p_savings", "_row_idx", "_cumulative"]
    for col in temp_cols:
        if col in df_result.columns:
            df_result = df_result.drop(col)

    # Calculate costs with P2P included
    all_carriers = list(set(
        [c for c in ["ONTRAC", "USPS", "FEDEX"] if get_carrier_volume(df_result, c) > 0] + ["P2P"]
    ))
    costs = calculate_costs(df_result, all_carriers)

    total_shipments = sum(c["shipments"] for c in costs.values())
    total_cost = sum(c["cost"] for c in costs.values())

    return {
        "method": "B",
        "df": df_result,
        "costs": costs,
        "total_shipments": total_shipments,
        "total_cost": total_cost,
        "switches": switches,
        "shift_log": [],  # Method B doesn't have shift_log, it has switches
    }


def run_s5_variant(df: pl.DataFrame, s5_variant: dict, s4_variant: dict) -> dict:
    """Run a S5 variant using dual-method approach: min(Method A, Method B)."""
    name = s5_variant["name"]
    minimums = s5_variant["minimums"]

    print(f"\n  {'=' * 66}")
    print(f"  {name} ({s5_variant['short']}): carriers = {', '.join(s5_variant['available'])}")
    if minimums:
        print(f"  Minimums: {', '.join(f'{k} >= {v:,}' for k, v in minimums.items())}")
    else:
        print(f"  Minimums: none")
    print(f"  {'=' * 66}")

    # Run S4 baseline for this constraint combo
    print(f"\n    Running S4 baseline ({s4_variant['short']})...")
    s4_result = run_variant_s4(df, s4_variant)
    print(f"    S4 baseline: ${s4_result['total_cost']:,.2f}")

    # Method A: Greedy with P2P + adjust
    print(f"\n    Method A: Greedy with P2P...")
    result_a = method_a_greedy(df, s5_variant)
    print(f"    Method A cost: ${result_a['total_cost']:,.2f}")

    # Method B: Improve S4 with P2P
    print(f"\n    Method B: Improve S4 with P2P switches...")
    result_b = method_b_improve_s4(df, s4_result, minimums)
    print(f"    Method B cost: ${result_b['total_cost']:,.2f}")
    if result_b.get("switches"):
        for sw in result_b["switches"]:
            print(f"      {sw['from']} -> P2P: {sw['groups']:,} groups ({sw['shipments']:,} shipments), saves ${sw['savings']:,.2f}")

    # Pick the cheaper method
    if result_a["total_cost"] <= result_b["total_cost"]:
        best = result_a
        best["method"] = "A"
    else:
        best = result_b
        best["method"] = "B"

    print(f"\n    Best: Method {best['method']} at ${best['total_cost']:,.2f}")
    print(f"    vs S4: ${s4_result['total_cost'] - best['total_cost']:+,.2f}")

    # Verify constraints
    for carrier, min_req in minimums.items():
        vol = best["costs"].get(carrier, {"shipments": 0})["shipments"]
        status = "MET" if vol >= min_req else f"VIOLATION: {vol:,} < {min_req:,}"
        print(f"    Constraint {carrier} >= {min_req:,}: {status}")

    best["name"] = name
    best["short"] = s5_variant["short"]
    best["s4_cost"] = s4_result["total_cost"]
    best["minimums"] = minimums
    best["available"] = s5_variant["available"]

    return best


def main():
    print("=" * 70)
    print("Scenario 5: Optimal with P2P")
    print("=" * 70)

    # Load data
    print("\n[1] Loading data...")
    df = load_data()
    total_shipments = int(df["shipment_count"].sum())
    print(f"    {df.shape[0]:,} groups, {total_shipments:,} shipments")

    # Carrier serviceability
    print("\n[2] Carrier serviceability...")
    for carrier in ["ONTRAC", "USPS", "FEDEX", "P2P"]:
        svc = int(df.filter(pl.col(f"{carrier.lower()}_cost_avg").is_not_null())["shipment_count"].sum())
        pct = svc / total_shipments * 100
        print(f"    {carrier}: {svc:,} serviceable ({pct:.1f}%)")

    print(f"\n    Current mix cost (from S1): ${SCENARIO_1_BASELINE:,.2f}")

    # Run all S5 variants
    print("\n[3] Running S5 optimization variants...")
    results = {}
    s4_costs = {}
    for s5_var, s4_var in zip(S5_VARIANTS, S4_VARIANTS):
        result = run_s5_variant(df, s5_var, s4_var)
        results[s5_var["short"]] = result
        s4_costs[s5_var["short"]] = result["s4_cost"]

    # ====================
    # COMPARISON TABLE
    # ====================
    print("\n" + "=" * 110)
    print("COMPARISON TABLE")
    print("=" * 110)
    print(f"\n{'Variant':<30} {'Carriers':<8} {'S5 Cost':>14} {'S4 Cost':>14} {'vs S4':>12} {'vs Current':>14} {'Method':>8}")
    print("-" * 100)
    print(f"{'Current Mix':<30} {'-':<8} {'-':>14} {'-':>14} {'-':>12} {'-':>14} {'-':>8}")

    for s5_var, s4_var in zip(S5_VARIANTS, S4_VARIANTS):
        r = results[s5_var["short"]]
        s4_cost = r["s4_cost"]
        s5_cost = r["total_cost"]
        vs_s4 = s4_cost - s5_cost
        vs_current = SCENARIO_1_BASELINE - s5_cost
        vs_current_pct = vs_current / SCENARIO_1_BASELINE * 100
        print(
            f"{r['name']:<30} {r['short']:<8} "
            f"${s5_cost:>13,.0f} ${s4_cost:>13,.0f} "
            f"${vs_s4:>+11,.0f} "
            f"${vs_current:>13,.0f} ({vs_current_pct:.1f}%) "
            f"{r['method']:>3}"
        )

    # Check S5 <= S4 guarantee
    print("\n### S5 <= S4 Guarantee Check")
    all_ok = True
    for s5_var in S5_VARIANTS:
        r = results[s5_var["short"]]
        ok = r["total_cost"] <= r["s4_cost"] + 0.01  # Small tolerance for float
        status = "OK" if ok else "VIOLATION"
        if not ok:
            all_ok = False
        print(f"    {r['name']}: S5=${r['total_cost']:,.2f} vs S4=${r['s4_cost']:,.2f} - {status}")
    if all_ok:
        print("    All variants: S5 <= S4 GUARANTEED")

    # ====================
    # DETAILED: RECOMMENDED (Both Constraints)
    # ====================
    recommended = results["OUFP"]
    print(f"\n{'=' * 90}")
    print(f"DETAILED: Both Constraints + P2P (Recommended)")
    print(f"{'=' * 90}")

    print("\n### Optimal Carrier Mix")
    print("-" * 60)
    print(f"{'Carrier':<10} {'Shipments':>12} {'%':>8} {'Cost':>15}")
    print("-" * 60)

    for carrier in ["ONTRAC", "USPS", "FEDEX", "P2P"]:
        info = recommended["costs"].get(carrier, {"shipments": 0, "cost": 0.0})
        if info["shipments"] > 0:
            pct = info["shipments"] / recommended["total_shipments"] * 100
            print(f"{carrier:<10} {info['shipments']:>12,} {pct:>7.1f}% ${info['cost']:>14,.2f}")

    print("-" * 60)
    print(f"{'TOTAL':<10} {recommended['total_shipments']:>12,} {'100.0%':>8} ${recommended['total_cost']:>14,.2f}")

    # FedEx Service Breakdown
    fedex_groups = recommended["df"].filter(pl.col("assigned_carrier") == "FEDEX")
    if fedex_groups.height > 0:
        fedex_hd_count = int(fedex_groups["fedex_hd_shipment_count"].sum())
        fedex_sp_count = int(fedex_groups["fedex_sp_shipment_count"].sum())
        fedex_total = fedex_hd_count + fedex_sp_count
        print(f"\n### FedEx Service Breakdown")
        print(f"    Home Delivery: {fedex_hd_count:,} ({fedex_hd_count/fedex_total*100:.1f}%)")
        print(f"    SmartPost:     {fedex_sp_count:,} ({fedex_sp_count/fedex_total*100:.1f}%)")

    # Constraint satisfaction
    print("\n### Constraint Satisfaction")
    for carrier in ["ONTRAC", "USPS"]:
        if carrier in recommended["minimums"]:
            vol = recommended["costs"].get(carrier, {"shipments": 0})["shipments"]
            min_req = recommended["minimums"][carrier]
            status = "MET" if vol >= min_req else f"SHORT by {min_req - vol:,}"
            print(f"    {carrier}: {vol:,} (min: {min_req:,}) - {status}")

    # P2P analysis
    p2p_info = recommended["costs"].get("P2P", {"shipments": 0, "cost": 0})
    if p2p_info["shipments"] > 0:
        print(f"\n### P2P Analysis")
        print(f"    P2P captures: {p2p_info['shipments']:,} shipments")
        print(f"    P2P cost: ${p2p_info['cost']:,.2f} (${p2p_info['cost']/p2p_info['shipments']:.2f}/shipment)")
        print(f"    Method used: {recommended['method']}")

    # Comparison to S4
    savings_vs_s4 = recommended["s4_cost"] - recommended["total_cost"]
    savings_vs_current = SCENARIO_1_BASELINE - recommended["total_cost"]
    print(f"\n### Comparison")
    print(f"    vs S4 (no P2P):    ${savings_vs_s4:+,.2f}")
    print(f"    vs Current Mix:    -${savings_vs_current:,.2f} ({savings_vs_current/SCENARIO_1_BASELINE*100:.1f}%)")

    # Save recommended assignments
    output_dir = Path("analysis/US_2026_tenders/results/scenario_5_with_p2p")
    output_dir.mkdir(parents=True, exist_ok=True)

    save_cols = [
        "packagetype", "shipping_zip_code", "weight_bracket",
        "shipment_count", "assigned_carrier",
        "ontrac_cost_avg", "usps_cost_avg", "fedex_cost_avg", "p2p_cost_avg",
        "ontrac_cost_total", "usps_cost_total", "fedex_cost_total", "p2p_cost_total",
    ]
    # Only include columns that exist
    save_cols = [c for c in save_cols if c in recommended["df"].columns]
    recommended["df"].select(save_cols).write_parquet(output_dir / "assignments.parquet")
    print(f"\n[9] Saved to {output_dir / 'assignments.parquet'}")

    return results


if __name__ == "__main__":
    main()
