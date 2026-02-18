"""
Scenario 7: Optimal with P2P + FedEx 16% Earned Discount

Extends Scenario 6 by adding P2P as a fourth carrier option.
FedEx costs at 16% earned discount (like S6), with the constraint that
FedEx must maintain enough volume for the 16% tier ($4.5M undiscounted).

Dual-method approach (same concept as S5):
  Method A: Greedy with all carriers + constraint adjustment + FedEx threshold
  Method B: Take S6's solution and improve by switching to P2P where cheaper

Method B respects both volume minimums and FedEx threshold:
  - FedEx -> P2P: only within FedEx's base rate surplus above threshold
  - USPS -> P2P: only within USPS surplus above minimum
  - OnTrac -> P2P: only within OnTrac surplus above minimum
"""

import polars as pl
import sys
from pathlib import Path

from analysis.US_2026_tenders.optimization.fedex_adjustment import (
    adjust_and_aggregate, PP_DISCOUNT, BAKED_EARNED,
)

sys.stdout.reconfigure(encoding='utf-8')

# FedEx earned discount parameters
FEDEX_TARGET_EARNED = 0.16
FEDEX_UNDISCOUNTED_THRESHOLD = 4_500_000  # $4.5M for 16% tier
BAKED_FACTOR = 1 - PP_DISCOUNT - BAKED_EARNED  # 0.37
FEDEX_BASE_RATE_THRESHOLD = FEDEX_UNDISCOUNTED_THRESHOLD * BAKED_FACTOR  # $1,665,000

# S6 variants (without P2P)
S6_VARIANTS = [
    {"name": "Both constraints", "short": "OUF", "available": ["ONTRAC", "USPS", "FEDEX"], "minimums": {"ONTRAC": 279_080, "USPS": 140_000}},
    {"name": "Drop OnTrac", "short": "UF", "available": ["USPS", "FEDEX"], "minimums": {"USPS": 140_000}},
    {"name": "Drop USPS", "short": "OF", "available": ["ONTRAC", "FEDEX"], "minimums": {"ONTRAC": 279_080}},
    {"name": "Drop both", "short": "F", "available": ["FEDEX"], "minimums": {}},
]

# S7 variants (with P2P added)
S7_VARIANTS = [
    {"name": "Both constraints", "short": "OUFP", "available": ["ONTRAC", "USPS", "FEDEX", "P2P"], "minimums": {"ONTRAC": 279_080, "USPS": 140_000}},
    {"name": "Drop OnTrac", "short": "UFP", "available": ["USPS", "FEDEX", "P2P"], "minimums": {"USPS": 140_000}},
    {"name": "Drop USPS", "short": "OFP", "available": ["ONTRAC", "FEDEX", "P2P"], "minimums": {"ONTRAC": 279_080}},
    {"name": "Drop both", "short": "FP", "available": ["FEDEX", "P2P"], "minimums": {}},
]


def load_data() -> tuple[pl.DataFrame, float]:
    """Load and adjust shipment data with FedEx at 16% earned discount."""
    return adjust_and_aggregate(target_earned=FEDEX_TARGET_EARNED)


def greedy_assignment(df: pl.DataFrame, available_carriers: list[str]) -> pl.DataFrame:
    """Assign each group to the cheapest available carrier."""
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
    vol = df.filter(pl.col("assigned_carrier") == carrier)["shipment_count"].sum()
    return int(vol) if vol else 0


def get_fedex_base_rate(df: pl.DataFrame) -> float:
    fedex_groups = df.filter(pl.col("assigned_carrier") == "FEDEX")
    if fedex_groups.height == 0:
        return 0.0
    return float(fedex_groups["fedex_cost_base_rate_total"].sum())


def adjust_for_volume_constraints(
    df: pl.DataFrame,
    available_carriers: list[str],
    enforced_minimums: dict[str, int],
) -> tuple[pl.DataFrame, list[dict]]:
    """Shift groups to meet volume minimums. Prefers non-P2P sources first."""
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

        # Prefer non-P2P sources first, then P2P
        non_p2p = [c for c in available_carriers if c != carrier and c != "P2P"]
        p2p_list = ["P2P"] if "P2P" in available_carriers else []

        for source_group_name, source_carriers in [("non-P2P", non_p2p), ("P2P", p2p_list)]:
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


def adjust_for_fedex_threshold(
    df: pl.DataFrame,
    available_carriers: list[str],
    enforced_minimums: dict[str, int],
    base_rate_threshold: float,
) -> tuple[pl.DataFrame, list[dict]]:
    """Shift groups to FedEx to meet undiscounted transportation threshold.

    Includes P2P as a source carrier (all P2P groups are shiftable since
    P2P has no minimum commitment).
    """
    current_base_rate = get_fedex_base_rate(df)
    undiscounted = current_base_rate / BAKED_FACTOR
    threshold_undiscounted = base_rate_threshold / BAKED_FACTOR

    print(f"\n  FedEx undiscounted: ${undiscounted:,.0f} / ${threshold_undiscounted:,.0f} threshold")

    if current_base_rate >= base_rate_threshold:
        print(f"  FedEx 16% threshold: MET")
        return df, []

    shortfall = base_rate_threshold - current_base_rate
    print(f"  FedEx 16% threshold: NOT MET (shortfall ${shortfall / BAKED_FACTOR:,.0f} undiscounted)")

    shift_log = []
    df = df.with_row_index("_row_idx")

    # Source carriers: P2P first (no minimum), then USPS, then ONTRAC
    source_order = ["P2P", "USPS", "ONTRAC"]
    for carrier in source_order:
        if carrier not in available_carriers or carrier == "FEDEX":
            continue

        current_base_rate = get_fedex_base_rate(df)
        if current_base_rate >= base_rate_threshold:
            break

        min_required = enforced_minimums.get(carrier, 0)
        carrier_volume = get_carrier_volume(df, carrier)
        surplus = carrier_volume - min_required

        if surplus <= 0:
            print(f"    {carrier}: no surplus")
            continue

        print(f"    {carrier}: {surplus:,} surplus shipments available")

        cost_col = f"{carrier.lower()}_cost_total"
        candidates = df.filter(
            (pl.col("assigned_carrier") == carrier) &
            (pl.col("fedex_cost_avg").is_not_null()) &
            (pl.col("fedex_cost_base_rate_total") > 0)
        ).with_columns([
            (pl.col("fedex_cost_total") - pl.col(cost_col)).alias("_shift_penalty"),
            pl.col("fedex_cost_base_rate_total").alias("_contribution"),
        ])

        if candidates.height == 0:
            continue

        candidates = candidates.with_columns([
            (pl.col("_shift_penalty") / pl.col("_contribution")).alias("_efficiency"),
        ]).sort("_efficiency")

        # Limit to surplus volume
        candidates = candidates.with_columns([
            pl.col("shipment_count").cum_sum().alias("_cum_vol"),
        ])
        candidates = candidates.filter(pl.col("_cum_vol") <= surplus)

        if candidates.height == 0:
            continue

        remaining_shortfall = base_rate_threshold - current_base_rate
        candidates = candidates.with_columns([
            pl.col("_contribution").cum_sum().alias("_cum_contrib"),
        ])

        needed = candidates.filter(pl.col("_cum_contrib") >= remaining_shortfall)
        if needed.height > 0:
            cutoff = candidates.height - needed.height + 1
        else:
            cutoff = candidates.height

        to_shift = candidates.head(cutoff)
        shift_indices = to_shift["_row_idx"].to_list()
        shifted_volume = int(to_shift["shipment_count"].sum())
        shifted_contribution = float(to_shift["_contribution"].sum())
        shifted_penalty = float(to_shift["_shift_penalty"].sum())

        df = df.with_columns([
            pl.when(pl.col("_row_idx").is_in(shift_indices))
              .then(pl.lit("FEDEX"))
              .otherwise(pl.col("assigned_carrier"))
              .alias("assigned_carrier")
        ])

        current_base_rate += shifted_contribution

        print(f"    Shifted {len(shift_indices):,} groups ({shifted_volume:,} shipments) from {carrier} to FedEx")
        print(f"    Contribution: ${shifted_contribution / BAKED_FACTOR:,.0f} undiscounted, penalty: ${shifted_penalty:,.2f}")

        shift_log.append({
            "from": carrier,
            "groups_shifted": len(shift_indices),
            "shipments_shifted": shifted_volume,
            "contribution_undiscounted": shifted_contribution / BAKED_FACTOR,
            "cost_penalty": shifted_penalty,
        })

    df = df.drop(["_row_idx"])

    final_base_rate = get_fedex_base_rate(df)
    final_undiscounted = final_base_rate / BAKED_FACTOR
    if final_base_rate >= base_rate_threshold:
        print(f"\n  FedEx 16% threshold: MET (${final_undiscounted:,.0f})")
    else:
        gap = (base_rate_threshold - final_base_rate) / BAKED_FACTOR
        print(f"\n  FedEx 16% threshold: NOT MET (${final_undiscounted:,.0f}, gap ${gap:,.0f})")

    return df, shift_log


def calculate_costs(df: pl.DataFrame, available_carriers: list[str]) -> dict:
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


def run_variant_s6(df: pl.DataFrame, variant: dict) -> dict:
    """Run a S6 variant (without P2P) to establish baseline."""
    available = variant["available"]
    minimums = variant["minimums"]

    df_result = greedy_assignment(df.clone(), available)
    df_result, vol_log = adjust_for_volume_constraints(df_result, available, minimums)
    df_result, thresh_log = adjust_for_fedex_threshold(df_result, available, minimums, FEDEX_BASE_RATE_THRESHOLD)
    costs = calculate_costs(df_result, available)

    total_shipments = sum(c["shipments"] for c in costs.values())
    total_cost = sum(c["cost"] for c in costs.values())

    fedex_base = get_fedex_base_rate(df_result)

    return {
        "df": df_result,
        "costs": costs,
        "total_shipments": total_shipments,
        "total_cost": total_cost,
        "fedex_base_rate": fedex_base,
        "fedex_threshold_met": fedex_base >= FEDEX_BASE_RATE_THRESHOLD,
    }


def method_a_greedy(df: pl.DataFrame, variant: dict) -> dict:
    """Method A: Greedy assignment with all carriers (including P2P) + constraints."""
    available = variant["available"]
    minimums = variant["minimums"]

    df_result = greedy_assignment(df.clone(), available)
    df_result, vol_log = adjust_for_volume_constraints(df_result, available, minimums)
    df_result, thresh_log = adjust_for_fedex_threshold(df_result, available, minimums, FEDEX_BASE_RATE_THRESHOLD)

    all_carriers = list(set(
        [c for c in available if get_carrier_volume(df_result, c) > 0]
    ))
    costs = calculate_costs(df_result, all_carriers)

    total_shipments = sum(c["shipments"] for c in costs.values())
    total_cost = sum(c["cost"] for c in costs.values())

    fedex_base = get_fedex_base_rate(df_result)

    return {
        "method": "A",
        "df": df_result,
        "costs": costs,
        "total_shipments": total_shipments,
        "total_cost": total_cost,
        "shift_log": vol_log + thresh_log,
        "fedex_base_rate": fedex_base,
        "fedex_threshold_met": fedex_base >= FEDEX_BASE_RATE_THRESHOLD,
    }


def method_b_improve_s6(df: pl.DataFrame, s6_result: dict, enforced_minimums: dict) -> dict:
    """Method B: Take S6's solution and improve by switching to P2P where cheaper.

    Respects:
    - FedEx base rate threshold (FedEx -> P2P limited by base rate surplus)
    - USPS volume minimum (USPS -> P2P limited by volume surplus)
    - OnTrac volume minimum (OnTrac -> P2P limited by volume surplus)
    """
    df_result = s6_result["df"].clone()

    # Current cost per group based on assigned carrier
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

    for carrier in ["FEDEX", "USPS", "ONTRAC"]:
        if carrier == "FEDEX":
            # Limited by base rate surplus above threshold
            fedex_base = get_fedex_base_rate(df_result)
            base_surplus = fedex_base - FEDEX_BASE_RATE_THRESHOLD

            if base_surplus <= 0:
                continue

            candidates = df_result.filter(
                (pl.col("assigned_carrier") == "FEDEX") &
                (pl.col("p2p_cost_avg").is_not_null()) &
                (pl.col("_p2p_savings") > 0)
            ).sort("_p2p_savings", descending=True)

            if candidates.height == 0:
                continue

            # Accumulate base rate reduction; stop at surplus
            candidates = candidates.with_columns([
                pl.col("fedex_cost_base_rate_total").cum_sum().alias("_cum_base_rate"),
            ])
            switchable = candidates.filter(pl.col("_cum_base_rate") <= base_surplus)

        else:
            # Limited by volume surplus
            min_required = enforced_minimums.get(carrier, 0)
            carrier_volume = get_carrier_volume(df_result, carrier)
            surplus = carrier_volume - min_required

            if surplus <= 0:
                continue

            candidates = df_result.filter(
                (pl.col("assigned_carrier") == carrier) &
                (pl.col("p2p_cost_avg").is_not_null()) &
                (pl.col("_p2p_savings") > 0)
            ).sort("_p2p_savings", descending=True)

            if candidates.height == 0:
                continue

            candidates = candidates.with_columns([
                pl.col("shipment_count").cum_sum().alias("_cumulative")
            ])
            switchable = candidates.filter(pl.col("_cumulative") <= surplus)

        if switchable.height == 0:
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
    temp_cols = ["_current_cost_avg", "_p2p_savings", "_row_idx", "_cumulative", "_cum_base_rate"]
    for col in temp_cols:
        if col in df_result.columns:
            df_result = df_result.drop(col)

    all_carriers = list(set(
        [c for c in ["ONTRAC", "USPS", "FEDEX"] if get_carrier_volume(df_result, c) > 0] + ["P2P"]
    ))
    costs = calculate_costs(df_result, all_carriers)

    total_shipments = sum(c["shipments"] for c in costs.values())
    total_cost = sum(c["cost"] for c in costs.values())

    fedex_base = get_fedex_base_rate(df_result)

    return {
        "method": "B",
        "df": df_result,
        "costs": costs,
        "total_shipments": total_shipments,
        "total_cost": total_cost,
        "switches": switches,
        "shift_log": [],
        "fedex_base_rate": fedex_base,
        "fedex_threshold_met": fedex_base >= FEDEX_BASE_RATE_THRESHOLD,
    }


def run_s7_variant(df: pl.DataFrame, s7_variant: dict, s6_variant: dict) -> dict:
    """Run a S7 variant using dual-method approach."""
    name = s7_variant["name"]
    minimums = s7_variant["minimums"]

    print(f"\n  {'=' * 66}")
    print(f"  {name} ({s7_variant['short']}): carriers = {', '.join(s7_variant['available'])}")
    if minimums:
        print(f"  Minimums: {', '.join(f'{k} >= {v:,}' for k, v in minimums.items())}")
    else:
        print(f"  Minimums: none")
    print(f"  FedEx threshold: ${FEDEX_UNDISCOUNTED_THRESHOLD:,.0f} undiscounted")
    print(f"  {'=' * 66}")

    # Run S6 baseline
    print(f"\n    Running S6 baseline ({s6_variant['short']})...")
    s6_result = run_variant_s6(df, s6_variant)
    s6_tier = "MET" if s6_result["fedex_threshold_met"] else "NOT MET"
    print(f"    S6 baseline: ${s6_result['total_cost']:,.2f} (FedEx tier: {s6_tier})")

    # Method A: Greedy with P2P
    print(f"\n    Method A: Greedy with P2P...")
    result_a = method_a_greedy(df, s7_variant)
    a_tier = "MET" if result_a["fedex_threshold_met"] else "NOT MET"
    print(f"    Method A: ${result_a['total_cost']:,.2f} (FedEx tier: {a_tier})")

    # Method B: Improve S6 with P2P
    print(f"\n    Method B: Improve S6 with P2P switches...")
    result_b = method_b_improve_s6(df, s6_result, minimums)
    b_tier = "MET" if result_b["fedex_threshold_met"] else "NOT MET"
    print(f"    Method B: ${result_b['total_cost']:,.2f} (FedEx tier: {b_tier})")
    if result_b.get("switches"):
        for sw in result_b["switches"]:
            print(f"      {sw['from']} -> P2P: {sw['groups']:,} groups ({sw['shipments']:,} shipments), saves ${sw['savings']:,.2f}")

    # Pick cheaper, preferring threshold-met results
    candidates = []
    for r in [result_a, result_b]:
        candidates.append(r)

    # Prefer results that meet the FedEx threshold
    met = [r for r in candidates if r["fedex_threshold_met"]]
    not_met = [r for r in candidates if not r["fedex_threshold_met"]]

    if met:
        best = min(met, key=lambda r: r["total_cost"])
    else:
        # Neither meets threshold — pick cheapest anyway (report as infeasible)
        best = min(not_met, key=lambda r: r["total_cost"])

    tier_str = "MET" if best["fedex_threshold_met"] else "NOT MET"
    print(f"\n    Best: Method {best['method']} at ${best['total_cost']:,.2f} (FedEx tier: {tier_str})")
    print(f"    vs S6: ${s6_result['total_cost'] - best['total_cost']:+,.2f}")

    # Verify constraints
    for carrier, min_req in minimums.items():
        vol = best["costs"].get(carrier, {"shipments": 0})["shipments"]
        status = "MET" if vol >= min_req else f"VIOLATION: {vol:,} < {min_req:,}"
        print(f"    Volume {carrier} >= {min_req:,}: {status}")

    best["name"] = name
    best["short"] = s7_variant["short"]
    best["s6_cost"] = s6_result["total_cost"]
    best["s6_fedex_threshold_met"] = s6_result["fedex_threshold_met"]
    best["minimums"] = minimums
    best["available"] = s7_variant["available"]

    return best


def main():
    print("=" * 70)
    print("Scenario 7: Optimal with P2P + FedEx 16% Earned Discount")
    print(f"FedEx rates adjusted: earned discount 18% -> {FEDEX_TARGET_EARNED:.0%}")
    print(f"FedEx threshold: ${FEDEX_UNDISCOUNTED_THRESHOLD:,.0f} undiscounted transportation")
    print("=" * 70)

    # Load data
    print("\n[1] Loading data (FedEx at 16% earned discount)...")
    df, SCENARIO_1_BASELINE = load_data()
    total_shipments = int(df["shipment_count"].sum())
    print(f"    {df.shape[0]:,} groups, {total_shipments:,} shipments")

    # Carrier serviceability
    print("\n[2] Carrier serviceability...")
    for carrier in ["ONTRAC", "USPS", "FEDEX", "P2P"]:
        svc = int(df.filter(pl.col(f"{carrier.lower()}_cost_avg").is_not_null())["shipment_count"].sum())
        pct = svc / total_shipments * 100
        print(f"    {carrier}: {svc:,} serviceable ({pct:.1f}%)")

    print(f"\n    S1 baseline (at 16% earned): ${SCENARIO_1_BASELINE:,.2f}")

    # Run all S7 variants
    print("\n[3] Running S7 optimization variants...")
    results = {}
    for s7_var, s6_var in zip(S7_VARIANTS, S6_VARIANTS):
        result = run_s7_variant(df, s7_var, s6_var)
        results[s7_var["short"]] = result

    # ====================
    # COMPARISON TABLE
    # ====================
    print("\n" + "=" * 120)
    print("COMPARISON TABLE")
    print("=" * 120)
    print(f"\n{'Variant':<30} {'Short':<8} {'S7 Cost':>14} {'S6 Cost':>14} {'vs S6':>12} {'vs S1':>14} {'FedEx Tier':>12} {'Method':>8}")
    print("-" * 116)
    print(f"{'S1 Baseline (16%)':<30} {'-':<8} {'-':>14} {'-':>14} {'-':>12} {'-':>14} {'-':>12} {'-':>8}")

    for s7_var in S7_VARIANTS:
        r = results[s7_var["short"]]
        s7_cost = r["total_cost"]
        s6_cost = r["s6_cost"]
        vs_s6 = s6_cost - s7_cost
        vs_s1 = SCENARIO_1_BASELINE - s7_cost
        vs_s1_pct = vs_s1 / SCENARIO_1_BASELINE * 100
        tier = "MET" if r["fedex_threshold_met"] else "NOT MET"
        print(
            f"{r['name']:<30} {r['short']:<8} "
            f"${s7_cost:>13,.0f} ${s6_cost:>13,.0f} "
            f"${vs_s6:>+11,.0f} "
            f"${vs_s1:>13,.0f} ({vs_s1_pct:.1f}%) "
            f"{tier:>10} "
            f"{r['method']:>5}"
        )

    # S7 <= S6 guarantee check
    print("\n### S7 <= S6 Guarantee Check")
    for s7_var in S7_VARIANTS:
        r = results[s7_var["short"]]
        ok = r["total_cost"] <= r["s6_cost"] + 0.01
        status = "OK" if ok else "VIOLATION"
        print(f"    {r['name']}: S7=${r['total_cost']:,.2f} vs S6=${r['s6_cost']:,.2f} - {status}")

    # ====================
    # DETAILED: DROP ONTRAC (key variant where FedEx 16% is feasible)
    # ====================
    key_variant = results["UFP"]
    print(f"\n{'=' * 90}")
    print(f"DETAILED: Drop OnTrac + P2P (FedEx 16% tier feasible)")
    print(f"{'=' * 90}")

    print("\n### Optimal Carrier Mix")
    print("-" * 60)
    print(f"{'Carrier':<10} {'Shipments':>12} {'%':>8} {'Cost':>15}")
    print("-" * 60)

    for carrier in ["USPS", "FEDEX", "P2P"]:
        info = key_variant["costs"].get(carrier, {"shipments": 0, "cost": 0.0})
        if info["shipments"] > 0:
            pct = info["shipments"] / key_variant["total_shipments"] * 100
            print(f"{carrier:<10} {info['shipments']:>12,} {pct:>7.1f}% ${info['cost']:>14,.2f}")

    print("-" * 60)
    print(f"{'TOTAL':<10} {key_variant['total_shipments']:>12,} {'100.0%':>8} ${key_variant['total_cost']:>14,.2f}")

    # Constraint satisfaction
    print("\n### Constraint Satisfaction")
    for carrier in ["USPS"]:
        if carrier in key_variant["minimums"]:
            vol = key_variant["costs"].get(carrier, {"shipments": 0})["shipments"]
            min_req = key_variant["minimums"][carrier]
            status = "MET" if vol >= min_req else f"SHORT"
            print(f"    {carrier} volume: {vol:,} (min: {min_req:,}) - {status}")

    fedex_undiscounted = key_variant["fedex_base_rate"] / BAKED_FACTOR
    tier_status = "MET" if key_variant["fedex_threshold_met"] else "NOT MET"
    print(f"    FedEx threshold: ${fedex_undiscounted:,.0f} / ${FEDEX_UNDISCOUNTED_THRESHOLD:,.0f} - {tier_status}")

    # FedEx Service Breakdown
    fedex_groups = key_variant["df"].filter(pl.col("assigned_carrier") == "FEDEX")
    if fedex_groups.height > 0:
        fedex_hd_count = int(fedex_groups["fedex_hd_shipment_count"].sum())
        fedex_sp_count = int(fedex_groups["fedex_sp_shipment_count"].sum())
        fedex_total = fedex_hd_count + fedex_sp_count
        print(f"\n### FedEx Service Breakdown")
        print(f"    Home Delivery: {fedex_hd_count:,} ({fedex_hd_count/fedex_total*100:.1f}%)")
        print(f"    SmartPost:     {fedex_sp_count:,} ({fedex_sp_count/fedex_total*100:.1f}%)")

    # P2P analysis
    p2p_info = key_variant["costs"].get("P2P", {"shipments": 0, "cost": 0})
    if p2p_info["shipments"] > 0:
        print(f"\n### P2P Analysis")
        print(f"    P2P shipments: {p2p_info['shipments']:,}")
        print(f"    P2P cost: ${p2p_info['cost']:,.2f} (${p2p_info['cost']/p2p_info['shipments']:.2f}/shipment)")
        print(f"    Method used: {key_variant['method']}")

    # Comparison
    savings_vs_s6 = key_variant["s6_cost"] - key_variant["total_cost"]
    savings_vs_s1 = SCENARIO_1_BASELINE - key_variant["total_cost"]
    print(f"\n### Comparison")
    print(f"    vs S6 (no P2P):    ${savings_vs_s6:+,.2f}")
    print(f"    vs S1 (baseline):  -${savings_vs_s1:,.2f} ({savings_vs_s1/SCENARIO_1_BASELINE*100:.1f}%)")

    # ====================
    # ALSO DETAIL: BOTH CONSTRAINTS (even if infeasible)
    # ====================
    both = results["OUFP"]
    print(f"\n{'=' * 90}")
    print(f"DETAILED: Both Constraints + P2P")
    tier_note = " (FedEx 16% tier NOT MET)" if not both["fedex_threshold_met"] else ""
    print(f"{'=' * 90}")

    print(f"\n### Optimal Carrier Mix{tier_note}")
    print("-" * 60)
    print(f"{'Carrier':<10} {'Shipments':>12} {'%':>8} {'Cost':>15}")
    print("-" * 60)

    for carrier in ["ONTRAC", "USPS", "FEDEX", "P2P"]:
        info = both["costs"].get(carrier, {"shipments": 0, "cost": 0.0})
        if info["shipments"] > 0:
            pct = info["shipments"] / both["total_shipments"] * 100
            print(f"{carrier:<10} {info['shipments']:>12,} {pct:>7.1f}% ${info['cost']:>14,.2f}")

    print("-" * 60)
    print(f"{'TOTAL':<10} {both['total_shipments']:>12,} {'100.0%':>8} ${both['total_cost']:>14,.2f}")

    if not both["fedex_threshold_met"]:
        print(f"\n  NOTE: FedEx 16% tier NOT MET. This cost uses 16% rates but the volume")
        print(f"  doesn't qualify. In reality, FedEx earned discount drops to 0% (see S4/S5).")

    # Save "Drop OnTrac" assignments (key feasible variant)
    output_dir = Path("analysis/US_2026_tenders/results/scenario_7_with_p2p")
    output_dir.mkdir(parents=True, exist_ok=True)

    save_cols = [
        "packagetype", "shipping_zip_code", "weight_bracket",
        "shipment_count", "assigned_carrier",
        "ontrac_cost_avg", "usps_cost_avg", "fedex_cost_avg", "p2p_cost_avg",
        "ontrac_cost_total", "usps_cost_total", "fedex_cost_total", "p2p_cost_total",
        "fedex_cost_base_rate_total",
    ]
    save_cols = [c for c in save_cols if c in key_variant["df"].columns]
    key_variant["df"].select(save_cols).write_parquet(output_dir / "assignments.parquet")
    print(f"\n[9] Saved Drop OnTrac assignments to {output_dir / 'assignments.parquet'}")

    # Also save Both Constraints assignments
    save_cols_both = [c for c in save_cols if c in both["df"].columns]
    both["df"].select(save_cols_both).write_parquet(output_dir / "assignments_both_constraints.parquet")
    print(f"    Saved Both Constraints assignments to {output_dir / 'assignments_both_constraints.parquet'}")

    return results


if __name__ == "__main__":
    main()
