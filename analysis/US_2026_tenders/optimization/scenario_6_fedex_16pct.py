"""
Scenario 6: Constrained Optimization with FedEx 16% Earned Discount

Like S4 but with two key differences:
1. FedEx costs calculated at 16% earned discount (not 0%)
2. Additional constraint: FedEx must maintain enough volume to qualify for
   the 16% earned discount tier ($4.5M true undiscounted transportation)

FedEx earned discount tiers (true undiscounted transportation charges):
  < $4.5M:       0% earned discount
  $4.5M - $6.5M: 16% earned discount  <-- target tier
  $6.5M - $9.5M: 18% earned discount  (baked into rate tables)

The multiplier to adjust from baked 18% to target 16%:
  (1 - PP - 0.16) / (1 - PP - 0.18) = 0.39 / 0.37 = 1.0541

Algorithm: Greedy + Adjustment (same as S4) + FedEx threshold enforcement
1. Greedy: assign each group to cheapest carrier
2. Enforce OnTrac/USPS volume minimums (same as S4)
3. Enforce FedEx threshold: shift groups to FedEx if needed to maintain 16% tier
"""

import polars as pl
import sys
from pathlib import Path

from analysis.US_2026_tenders.optimization.fedex_adjustment import (
    adjust_and_aggregate, compute_undiscounted,
)

sys.stdout.reconfigure(encoding='utf-8')

# FedEx earned discount parameters
FEDEX_TARGET_EARNED = 0.16
FEDEX_UNDISCOUNTED_THRESHOLD = 4_500_000  # $4.5M for 16% tier
# Constraint combinations
VARIANTS = [
    {
        "name": "Both constraints",
        "short": "OUF",
        "available": ["ONTRAC", "USPS", "FEDEX"],
        "minimums": {"ONTRAC": 279_080, "USPS": 140_000},
    },
    {
        "name": "Drop OnTrac",
        "short": "UF",
        "available": ["USPS", "FEDEX"],
        "minimums": {"USPS": 140_000},
    },
    {
        "name": "Drop USPS",
        "short": "OF",
        "available": ["ONTRAC", "FEDEX"],
        "minimums": {"ONTRAC": 279_080},
    },
    {
        "name": "Drop both",
        "short": "F",
        "available": ["FEDEX"],
        "minimums": {},
    },
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
    """Get total shipment count assigned to a carrier."""
    vol = df.filter(pl.col("assigned_carrier") == carrier)["shipment_count"].sum()
    return int(vol) if vol else 0


def get_fedex_base_rate(df: pl.DataFrame) -> float:
    """Get total FedEx base rate for assigned FedEx groups."""
    fedex_groups = df.filter(pl.col("assigned_carrier") == "FEDEX")
    if fedex_groups.height == 0:
        return 0.0
    return float(fedex_groups["fedex_cost_base_rate_total"].sum())


def adjust_for_volume_constraints(
    df: pl.DataFrame,
    available_carriers: list[str],
    enforced_minimums: dict[str, int],
) -> tuple[pl.DataFrame, list[dict]]:
    """Shift groups to meet volume minimums (OnTrac/USPS). Same as S4."""
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

        print(f"\n  {carrier} has shortfall of {shortfall:,} shipments")

        cost_col_to = f"{carrier.lower()}_cost_avg"
        other_carriers = [c for c in available_carriers if c != carrier]

        all_penalties = []
        for from_carrier in other_carriers:
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
            print(f"    No groups available to shift to {carrier}")
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

        print(f"    Shifting {len(shift_indices):,} groups ({shifted_volume:,} shipments) to {carrier}")
        print(f"    Cost penalty: ${shifted_cost:,.2f}")

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

        df = df.with_columns([
            pl.when(pl.col("assigned_carrier") == carrier)
              .then(pl.lit(True))
              .otherwise(pl.col("locked"))
              .alias("locked")
        ])

        shift_log.append({
            "carrier": carrier,
            "groups_shifted": len(shift_indices),
            "shipments_shifted": shifted_volume,
            "cost_penalty": shifted_cost,
        })

    df = df.drop(["_row_idx", "locked"])
    return df, shift_log


def get_fedex_undiscounted(df: pl.DataFrame) -> float:
    """Get FedEx undiscounted spend for assigned FedEx groups using split HD/SP baked factors."""
    fedex_groups = df.filter(pl.col("assigned_carrier") == "FEDEX")
    if fedex_groups.height == 0:
        return 0.0
    hd = float(fedex_groups["fedex_hd_base_rate_total"].sum())
    sp = float(fedex_groups["fedex_sp_base_rate_total"].sum())
    return compute_undiscounted(hd, sp)


def adjust_for_fedex_threshold(
    df: pl.DataFrame,
    available_carriers: list[str],
    enforced_minimums: dict[str, int],
    threshold: float,
) -> tuple[pl.DataFrame, list[dict]]:
    """Shift groups to FedEx to meet undiscounted transportation threshold.

    After volume constraints are satisfied, checks if FedEx has enough
    undiscounted spend to qualify for the 16% earned discount tier.
    If not, shifts lowest-efficiency-penalty groups from surplus carriers.
    """
    current_undiscounted = get_fedex_undiscounted(df)

    print(f"\n  FedEx undiscounted transportation: ${current_undiscounted:,.0f} (threshold: ${threshold:,.0f})")

    if current_undiscounted >= threshold:
        print(f"  FedEx 16% threshold: MET")
        return df, []

    shortfall = threshold - current_undiscounted
    print(f"  FedEx 16% threshold: NOT MET (shortfall ${shortfall:,.0f} undiscounted)")

    shift_log = []
    df = df.with_row_index("_row_idx")

    # Try shifting from each carrier's surplus (USPS first - usually larger surplus)
    for carrier in ["USPS", "ONTRAC"]:
        if carrier not in available_carriers or carrier == "FEDEX":
            continue

        current_undiscounted = get_fedex_undiscounted(df)
        if current_undiscounted >= threshold:
            break

        min_required = enforced_minimums.get(carrier, 0)
        carrier_volume = get_carrier_volume(df, carrier)
        surplus = carrier_volume - min_required

        if surplus <= 0:
            print(f"    {carrier}: no surplus (at minimum {min_required:,})")
            continue

        print(f"    {carrier}: {surplus:,} surplus shipments available")

        cost_col = f"{carrier.lower()}_cost_total"
        candidates = df.filter(
            (pl.col("assigned_carrier") == carrier) &
            (pl.col("fedex_cost_avg").is_not_null()) &
            (pl.col("fedex_cost_base_rate_total") > 0)
        ).with_columns([
            (pl.col("fedex_cost_total") - pl.col(cost_col)).alias("_shift_penalty"),
            compute_undiscounted(
                pl.col("fedex_hd_base_rate_total"),
                pl.col("fedex_sp_base_rate_total"),
            ).alias("_contribution"),
        ])

        if candidates.height == 0:
            continue

        # Sort by efficiency: penalty per unit of threshold contribution
        # Groups where FedEx is cheaper (negative penalty) sort first
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

        # Accumulate contribution and find cutoff for threshold
        remaining_shortfall = threshold - current_undiscounted
        candidates = candidates.with_columns([
            pl.col("_contribution").cum_sum().alias("_cum_contrib"),
        ])

        needed = candidates.filter(pl.col("_cum_contrib") >= remaining_shortfall)
        if needed.height > 0:
            cutoff = candidates.height - needed.height + 1
        else:
            cutoff = candidates.height  # Shift all available

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

        print(f"    Shifted {len(shift_indices):,} groups ({shifted_volume:,} shipments) from {carrier} to FedEx")
        print(f"    Contribution: ${shifted_contribution:,.0f} undiscounted, penalty: ${shifted_penalty:,.2f}")

        shift_log.append({
            "from": carrier,
            "groups_shifted": len(shift_indices),
            "shipments_shifted": shifted_volume,
            "contribution_undiscounted": shifted_contribution,
            "cost_penalty": shifted_penalty,
        })

    df = df.drop(["_row_idx"])

    # Final check
    final_undiscounted = get_fedex_undiscounted(df)
    if final_undiscounted >= threshold:
        print(f"\n  FedEx 16% threshold: MET (${final_undiscounted:,.0f} >= ${threshold:,.0f})")
    else:
        gap = threshold - final_undiscounted
        print(f"\n  FedEx 16% threshold: NOT MET (${final_undiscounted:,.0f}, gap ${gap:,.0f})")
        print(f"  Insufficient surplus to meet threshold with current volume constraints")

    return df, shift_log


def calculate_costs(df: pl.DataFrame, available_carriers: list[str]) -> dict:
    """Calculate total costs by carrier based on assignments."""
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


def run_variant(df: pl.DataFrame, variant: dict) -> dict:
    """Run a complete optimization variant with FedEx threshold enforcement."""
    name = variant["name"]
    available = variant["available"]
    minimums = variant["minimums"]

    print(f"\n{'=' * 70}")
    print(f"  {name} ({variant['short']}): carriers = {', '.join(available)}")
    if minimums:
        mins_str = ", ".join(f"{k} >= {v:,}" for k, v in minimums.items())
        print(f"  Volume minimums: {mins_str}")
    else:
        print(f"  Volume minimums: none")
    print(f"  FedEx threshold: ${FEDEX_UNDISCOUNTED_THRESHOLD:,.0f} undiscounted transportation")
    print(f"{'=' * 70}")

    # Step 1: Greedy assignment
    df_result = greedy_assignment(df.clone(), available)

    # Print initial assignment
    for carrier in available:
        vol = get_carrier_volume(df_result, carrier)
        min_req = minimums.get(carrier, 0)
        status = "OK" if vol >= min_req else f"SHORT: {min_req - vol:,}"
        print(f"    {carrier}: {vol:,} (min: {min_req:,}) - {status}")

    initial_undiscounted = get_fedex_undiscounted(df_result)
    print(f"    FedEx undiscounted: ${initial_undiscounted:,.0f} (need ${FEDEX_UNDISCOUNTED_THRESHOLD:,.0f})")

    # Step 2: Enforce volume constraints (OnTrac/USPS)
    df_result, volume_shift_log = adjust_for_volume_constraints(df_result, available, minimums)

    # Step 3: Enforce FedEx threshold
    df_result, threshold_shift_log = adjust_for_fedex_threshold(
        df_result, available, minimums, threshold=FEDEX_UNDISCOUNTED_THRESHOLD
    )

    # Calculate costs
    costs = calculate_costs(df_result, available)
    total_shipments = sum(c["shipments"] for c in costs.values())
    total_cost = sum(c["cost"] for c in costs.values())

    # Print result
    print(f"\n  Result: ${total_cost:,.2f} ({total_shipments:,} shipments)")
    for carrier in available:
        info = costs[carrier]
        pct = info["shipments"] / total_shipments * 100 if total_shipments > 0 else 0
        print(f"    {carrier}: {info['shipments']:,} ({pct:.1f}%) - ${info['cost']:,.2f}")

    # Verify all constraints
    for carrier, min_req in minimums.items():
        vol = costs[carrier]["shipments"]
        status = "MET" if vol >= min_req else f"VIOLATION: {vol:,} < {min_req:,}"
        print(f"    Volume {carrier} >= {min_req:,}: {status}")

    final_undiscounted = get_fedex_undiscounted(df_result)
    threshold_status = "MET" if final_undiscounted >= FEDEX_UNDISCOUNTED_THRESHOLD else "NOT MET"
    print(f"    FedEx threshold ${FEDEX_UNDISCOUNTED_THRESHOLD:,.0f}: {threshold_status} (${final_undiscounted:,.0f})")

    return {
        "name": name,
        "short": variant["short"],
        "available": available,
        "minimums": minimums,
        "df": df_result,
        "costs": costs,
        "total_shipments": total_shipments,
        "total_cost": total_cost,
        "volume_shift_log": volume_shift_log,
        "threshold_shift_log": threshold_shift_log,
        "fedex_undiscounted": final_undiscounted,
        "fedex_threshold_met": final_undiscounted >= FEDEX_UNDISCOUNTED_THRESHOLD,
    }


def main():
    print("=" * 70)
    print("Scenario 6: Constrained Optimization with FedEx 16% Earned Discount")
    print(f"FedEx rates adjusted: earned discount 18% -> {FEDEX_TARGET_EARNED:.0%}")
    print(f"FedEx threshold: ${FEDEX_UNDISCOUNTED_THRESHOLD:,.0f} undiscounted transportation")
    print("=" * 70)

    # Load data (with FedEx at 16% earned)
    print("\n[1] Loading data (FedEx at 16% earned discount)...")
    df, SCENARIO_1_BASELINE = load_data()
    total_shipments = int(df["shipment_count"].sum())
    print(f"    {df.shape[0]:,} groups, {total_shipments:,} shipments")

    # Carrier serviceability
    print("\n[2] Carrier serviceability...")
    for carrier in ["ONTRAC", "USPS", "FEDEX"]:
        svc = int(df.filter(pl.col(f"{carrier.lower()}_cost_avg").is_not_null())["shipment_count"].sum())
        pct = svc / total_shipments * 100
        print(f"    {carrier}: {svc:,} serviceable ({pct:.1f}%)")

    print(f"\n    S1 baseline (at 16% earned): ${SCENARIO_1_BASELINE:,.2f}")

    # Run all variants
    print("\n[3] Running optimization variants...")
    results = {}
    for variant in VARIANTS:
        results[variant["short"]] = run_variant(df, variant)

    # ====================
    # COMPARISON TABLE
    # ====================
    print("\n" + "=" * 100)
    print("COMPARISON TABLE")
    print("=" * 100)
    print(f"\n{'Variant':<30} {'Carriers':<8} {'Total Cost':>14} {'vs S1':>14} {'Savings %':>10} {'FedEx Tier':>12}")
    print("-" * 92)
    print(f"{'S1 Baseline (16% earned)':<30} {'-':<8} ${SCENARIO_1_BASELINE:>13,.0f} {'-':>14} {'-':>10} {'16%':>12}")

    for variant in VARIANTS:
        r = results[variant["short"]]
        savings = SCENARIO_1_BASELINE - r["total_cost"]
        pct = savings / SCENARIO_1_BASELINE * 100
        tier = "MET" if r["fedex_threshold_met"] else "NOT MET"
        print(f"{r['name']:<30} {r['short']:<8} ${r['total_cost']:>13,.0f} ${savings:>+13,.0f} {pct:>9.1f}% {tier:>12}")

    # ====================
    # COST OF COMMITMENT
    # ====================
    both = results["OUF"]["total_cost"]
    no_ontrac = results["UF"]["total_cost"]
    no_usps = results["OF"]["total_cost"]
    no_both = results["F"]["total_cost"]

    print("\n" + "=" * 100)
    print("COST OF COMMITMENT")
    print("=" * 100)
    print("\nMarginal cost of each carrier commitment (positive = costs extra):\n")

    ontrac_cost = both - no_ontrac
    usps_cost = both - no_usps
    print(f"  OnTrac commitment: ${ontrac_cost:>+12,.0f}  (Both vs Drop OnTrac)")
    print(f"  USPS commitment:   ${usps_cost:>+12,.0f}  (Both vs Drop USPS)")
    print(f"  Both commitments:  ${both - no_both:>+12,.0f}  (Both vs Drop both)")

    if ontrac_cost > 0:
        print(f"\n  --> OnTrac minimum costs ${ontrac_cost:,.0f}/year extra")
    else:
        print(f"\n  --> OnTrac minimum saves ${-ontrac_cost:,.0f}/year")

    if usps_cost > 0:
        print(f"  --> USPS minimum costs ${usps_cost:,.0f}/year extra")
    else:
        print(f"  --> USPS minimum saves ${-usps_cost:,.0f}/year")

    # ====================
    # DETAILED: RECOMMENDED VARIANT
    # ====================
    recommended = results["OUF"]
    print("\n" + "=" * 90)
    print("DETAILED: Both Constraints + FedEx 16% Tier")
    print("=" * 90)

    print("\n### Optimal Carrier Mix")
    print("-" * 60)
    print(f"{'Carrier':<12} {'Shipments':>12} {'% of Total':>12} {'Total Cost':>15}")
    print("-" * 60)

    for carrier in recommended["available"]:
        info = recommended["costs"][carrier]
        pct = info["shipments"] / recommended["total_shipments"] * 100 if recommended["total_shipments"] > 0 else 0
        print(f"{carrier:<12} {info['shipments']:>12,} {pct:>11.1f}% ${info['cost']:>14,.2f}")

    print("-" * 60)
    print(f"{'TOTAL':<12} {recommended['total_shipments']:>12,} {'100.0%':>12} ${recommended['total_cost']:>14,.2f}")

    # Constraint satisfaction
    print("\n### Constraint Satisfaction")
    print("-" * 60)
    print(f"{'Constraint':<35} {'Actual':>14} {'Required':>14} {'Status':>10}")
    print("-" * 60)
    for carrier in recommended["available"]:
        vol = recommended["costs"][carrier]["shipments"]
        min_req = recommended["minimums"].get(carrier, 0)
        status = "MET" if vol >= min_req else f"SHORT"
        if min_req > 0:
            print(f"{carrier + ' volume':<35} {vol:>14,} {min_req:>14,} {status:>10}")
    print(f"{'FedEx undiscounted transport.':<35} ${recommended['fedex_undiscounted']:>13,.0f} ${FEDEX_UNDISCOUNTED_THRESHOLD:>13,.0f} {'MET' if recommended['fedex_threshold_met'] else 'NOT MET':>10}")

    # FedEx HD vs SmartPost
    fedex_groups = recommended["df"].filter(pl.col("assigned_carrier") == "FEDEX")
    if fedex_groups.height > 0:
        fedex_hd_count = int(fedex_groups["fedex_hd_shipment_count"].sum())
        fedex_sp_count = int(fedex_groups["fedex_sp_shipment_count"].sum())
        fedex_total_assigned = fedex_hd_count + fedex_sp_count
        print("\n### FedEx Service Breakdown")
        print(f"  Home Delivery: {fedex_hd_count:>12,} ({fedex_hd_count/fedex_total_assigned*100:.1f}%)")
        print(f"  SmartPost:     {fedex_sp_count:>12,} ({fedex_sp_count/fedex_total_assigned*100:.1f}%)")

    # Shift details
    print("\n### Volume Constraint Shifts")
    if recommended["volume_shift_log"]:
        for shift in recommended["volume_shift_log"]:
            print(f"  To {shift['carrier']}: {shift['groups_shifted']:,} groups ({shift['shipments_shifted']:,} shipments), penalty ${shift['cost_penalty']:,.2f}")
    else:
        print("  No shifts required")

    print("\n### FedEx Threshold Shifts")
    if recommended["threshold_shift_log"]:
        for shift in recommended["threshold_shift_log"]:
            print(f"  {shift['from']} -> FedEx: {shift['groups_shifted']:,} groups ({shift['shipments_shifted']:,} shipments)")
            print(f"    Contribution: ${shift['contribution_undiscounted']:,.0f} undiscounted, penalty: ${shift['cost_penalty']:,.2f}")
    else:
        print("  No shifts required (threshold met naturally)")

    # Comparison
    savings = SCENARIO_1_BASELINE - recommended["total_cost"]
    savings_pct = savings / SCENARIO_1_BASELINE * 100
    print(f"\n### Comparison")
    print(f"  S1 baseline (16% earned): ${SCENARIO_1_BASELINE:,.2f}")
    print(f"  S6 optimized:             ${recommended['total_cost']:,.2f}")
    print(f"  Savings vs S1:            ${savings:,.2f} ({savings_pct:.1f}%)")

    # Save assignments
    output_dir = Path("analysis/US_2026_tenders/results/scenario_6_fedex_16pct")
    output_dir.mkdir(parents=True, exist_ok=True)

    save_cols = [
        "packagetype", "shipping_zip_code", "weight_bracket",
        "shipment_count", "assigned_carrier",
        "ontrac_cost_avg", "usps_cost_avg", "fedex_cost_avg",
        "ontrac_cost_total", "usps_cost_total", "fedex_cost_total",
        "fedex_cost_base_rate_total",
    ]
    result_df = recommended["df"].select(save_cols)
    result_df.write_parquet(output_dir / "assignments.parquet")
    print(f"\n[9] Saved assignments to {output_dir / 'assignments.parquet'}")

    return results


if __name__ == "__main__":
    results = main()
