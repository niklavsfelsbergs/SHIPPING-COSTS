"""
Scenario 4: Constrained Optimization (OnTrac/FedEx/USPS)

Tests all constraint combinations to find optimal carrier mix:
- Both constraints: OnTrac >= 279K, USPS >= 140K (3 carriers)
- Drop OnTrac: USPS >= 140K (2 carriers: USPS + FedEx)
- Drop USPS: OnTrac >= 279K (2 carriers: OnTrac + FedEx)
- Drop both: No constraints (FedEx only, equivalent to S3)

When a carrier commitment is dropped, the carrier is removed entirely
from routing - without meeting minimums, contract rates wouldn't apply.

Algorithm: Greedy + Adjustment
1. For each group, assign to cheapest available carrier
2. Check if enforced minimums are met
3. If not, shift lowest-cost-penalty groups to underutilized carrier

Note: FedEx base rates already include the earned discount, so no
additional discount calculation is applied.
"""

import polars as pl
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# Constraint combinations to test
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

# Baseline from Scenario 1 (includes DHL @ $6 and OnTrac null imputations)
SCENARIO_1_BASELINE = 5_833_893.77



def load_data() -> pl.DataFrame:
    """Load the aggregated shipment data."""
    path = Path("analysis/US_2026_tenders/combined_datasets/shipments_aggregated.parquet")
    return pl.read_parquet(path)


def greedy_assignment(df: pl.DataFrame, available_carriers: list[str]) -> pl.DataFrame:
    """Assign each group to the cheapest available carrier.

    Only considers carriers in available_carriers. Null costs are ignored
    (carrier can't service that group). FedEx is fallback if available.
    """
    cost_cols = [f"{c.lower()}_cost_avg" for c in available_carriers]

    df = df.with_columns([
        pl.min_horizontal(*cost_cols).alias("min_cost_avg"),
    ])

    # Build when/then chain: check each carrier except the fallback
    fallback = "FEDEX" if "FEDEX" in available_carriers else available_carriers[-1]
    non_fallback = [c for c in available_carriers if c != fallback]

    if not non_fallback:
        # Only one carrier available
        df = df.with_columns([pl.lit(fallback).alias("assigned_carrier")])
    else:
        # Start the chain with the first non-fallback carrier
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
    Only shifts from available carriers. Locks shifted groups to prevent
    them from being taken away by subsequent adjustments.
    """
    if not enforced_minimums:
        return df, []

    shift_log = []
    df = df.with_row_index("_row_idx")
    df = df.with_columns([pl.lit(False).alias("locked")])

    # Process in priority order
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
    """Run a complete optimization variant.

    Args:
        df: Original aggregated data (will be cloned)
        variant: Dict with name, short, available, minimums
    """
    name = variant["name"]
    available = variant["available"]
    minimums = variant["minimums"]

    print(f"\n{'=' * 70}")
    print(f"  {name} ({variant['short']}): carriers = {', '.join(available)}")
    if minimums:
        mins_str = ", ".join(f"{k} >= {v:,}" for k, v in minimums.items())
        print(f"  Minimums: {mins_str}")
    else:
        print(f"  Minimums: none")
    print(f"{'=' * 70}")

    # Greedy assignment
    df_result = greedy_assignment(df.clone(), available)

    # Print initial assignment
    for carrier in available:
        vol = get_carrier_volume(df_result, carrier)
        min_req = minimums.get(carrier, 0)
        status = "OK" if vol >= min_req else f"SHORT: {min_req - vol:,}"
        print(f"    {carrier}: {vol:,} (min: {min_req:,}) - {status}")

    # Adjust for constraints
    df_result, shift_log = adjust_for_constraints(df_result, available, minimums)

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

    # Verify constraints
    for carrier, min_req in minimums.items():
        vol = costs[carrier]["shipments"]
        status = "MET" if vol >= min_req else f"VIOLATION: {vol:,} < {min_req:,}"
        print(f"    Constraint {carrier} >= {min_req:,}: {status}")

    return {
        "name": name,
        "short": variant["short"],
        "available": available,
        "minimums": minimums,
        "df": df_result,
        "costs": costs,
        "total_shipments": total_shipments,
        "total_cost": total_cost,
        "shift_log": shift_log,
    }


def main():
    print("=" * 70)
    print("Scenario 4: Constrained Optimization (OnTrac/FedEx/USPS)")
    print("=" * 70)

    # Load data
    print("\n[1] Loading data...")
    df = load_data()
    total_shipments = int(df["shipment_count"].sum())
    print(f"    {df.shape[0]:,} groups, {total_shipments:,} shipments")

    # Carrier serviceability
    print("\n[2] Carrier serviceability...")
    for carrier in ["ONTRAC", "USPS", "FEDEX"]:
        svc = int(df.filter(pl.col(f"{carrier.lower()}_cost_avg").is_not_null())["shipment_count"].sum())
        pct = svc / total_shipments * 100
        print(f"    {carrier}: {svc:,} serviceable ({pct:.1f}%)")

    # Baseline
    print(f"\n    Current mix cost (from S1): ${SCENARIO_1_BASELINE:,.2f}")

    # Run all variants
    print("\n[3] Running optimization variants...")
    results = {}
    for variant in VARIANTS:
        results[variant["short"]] = run_variant(df, variant)

    # ====================
    # COMPARISON TABLE
    # ====================
    print("\n" + "=" * 90)
    print("COMPARISON TABLE")
    print("=" * 90)
    print(f"\n{'Variant':<30} {'Carriers':<8} {'Total Cost':>14} {'vs Current':>14} {'Savings %':>10}")
    print("-" * 80)
    print(f"{'Current Mix':<30} {'-':<8} ${SCENARIO_1_BASELINE:>13,.0f} {'-':>14} {'-':>10}")

    for variant in VARIANTS:
        r = results[variant["short"]]
        savings = SCENARIO_1_BASELINE - r["total_cost"]
        pct = savings / SCENARIO_1_BASELINE * 100
        sign = "" if savings >= 0 else ""
        print(f"{r['name']:<30} {r['short']:<8} ${r['total_cost']:>13,.0f} {sign}${savings:>13,.0f} {pct:>9.1f}%")

    # ====================
    # COST OF COMMITMENT
    # ====================
    both = results["OUF"]["total_cost"]
    no_ontrac = results["UF"]["total_cost"]
    no_usps = results["OF"]["total_cost"]
    no_both = results["F"]["total_cost"]

    print("\n" + "=" * 90)
    print("COST OF COMMITMENT")
    print("=" * 90)
    print("\nMarginal cost of each carrier commitment (positive = commitment costs extra):\n")

    ontrac_cost = both - no_ontrac
    usps_cost = both - no_usps
    print(f"  OnTrac commitment: ${ontrac_cost:>+12,.0f}  (Both constraints vs Drop OnTrac)")
    print(f"  USPS commitment:   ${usps_cost:>+12,.0f}  (Both constraints vs Drop USPS)")
    print(f"  Both commitments:  ${both - no_both:>+12,.0f}  (Both constraints vs Drop both)")

    if ontrac_cost > 0:
        print(f"\n  --> OnTrac's minimum volume costs an extra ${ontrac_cost:,.0f}/year")
    else:
        print(f"\n  --> OnTrac's minimum volume saves ${-ontrac_cost:,.0f}/year (it's beneficial)")

    if usps_cost > 0:
        print(f"  --> USPS's minimum volume costs an extra ${usps_cost:,.0f}/year")
    else:
        print(f"  --> USPS's minimum volume saves ${-usps_cost:,.0f}/year (it's beneficial)")

    # ====================
    # DETAILED: RECOMMENDED VARIANT (Both Constraints)
    # ====================
    recommended = results["OUF"]
    print("\n" + "=" * 90)
    print("DETAILED: Both Constraints (Recommended)")
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
    print(f"{'Carrier':<12} {'Actual':>12} {'Minimum':>12} {'Status':>15}")
    print("-" * 60)
    for carrier in recommended["available"]:
        vol = recommended["costs"][carrier]["shipments"]
        min_req = recommended["minimums"].get(carrier, 0)
        status = "MET" if vol >= min_req else f"SHORT by {min_req - vol:,}"
        print(f"{carrier:<12} {vol:>12,} {min_req:>12,} {status:>15}")

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
    print("\n### Shifts to Meet Constraints")
    if recommended["shift_log"]:
        for shift in recommended["shift_log"]:
            print(f"  To {shift['carrier']}: {shift['groups_shifted']:,} groups ({shift['shipments_shifted']:,} shipments), penalty ${shift['cost_penalty']:,.2f}")
    else:
        print("  No shifts required")

    # Comparison to baseline
    savings = SCENARIO_1_BASELINE - recommended["total_cost"]
    savings_pct = savings / SCENARIO_1_BASELINE * 100
    print(f"\n### Comparison to Current Mix")
    print(f"  Current mix cost: ${SCENARIO_1_BASELINE:,.2f}")
    print(f"  Optimized cost:   ${recommended['total_cost']:,.2f}")
    print(f"  Savings:          ${savings:,.2f} ({savings_pct:.1f}%)")

    # Save "Both constraints" assignments
    output_dir = Path("analysis/US_2026_tenders/results/scenario_4_constrained")
    output_dir.mkdir(parents=True, exist_ok=True)

    save_cols = [
        "packagetype", "shipping_zip_code", "weight_bracket",
        "shipment_count", "assigned_carrier",
        "ontrac_cost_avg", "usps_cost_avg", "fedex_cost_avg",
        "ontrac_cost_total", "usps_cost_total", "fedex_cost_total",
    ]
    result_df = recommended["df"].select(save_cols)

    result_df.write_parquet(output_dir / "assignments.parquet")
    print(f"\n[9] Saved assignments to {output_dir / 'assignments.parquet'}")

    return results


if __name__ == "__main__":
    results = main()
