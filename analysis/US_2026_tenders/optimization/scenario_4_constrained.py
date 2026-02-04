"""
Scenario 4: Constrained Optimization (OnTrac/FedEx/USPS)

Finds the optimal carrier mix while respecting volume commitments:
- USPS: minimum 140,000 shipments/year (35,000/quarter Tier 1)
- OnTrac: minimum 279,080 shipments/year
- FedEx: no minimum, but earned discount tiers apply

Algorithm: Greedy + Adjustment
1. For each group, assign to cheapest carrier (OnTrac, USPS, or FedEx)
2. Check if USPS and OnTrac minimums are met
3. If not, shift lowest-cost-penalty groups to underutilized carrier
4. After final allocation, calculate FedEx earned discount tier
5. Report final costs
"""

import polars as pl
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# Constants
USPS_MIN_ANNUAL = 140_000  # 35,000/quarter x 4 (Tier 1)
ONTRAC_MIN_ANNUAL = 279_080  # 5,365/week x 52

# FedEx Earned Discount Tiers (Ground / Home Delivery)
FEDEX_EARNED_DISCOUNT_TIERS = [
    (0, 4_500_000, 0.00),          # < $4.5M: 0%
    (4_500_000, 6_500_000, 0.16),   # $4.5M - $6.5M: 16%
    (6_500_000, 9_500_000, 0.18),   # $6.5M - $9.5M: 18%
    (9_500_000, 12_500_000, 0.19),  # $9.5M - $12.5M: 19%
    (12_500_000, 15_500_000, 0.20), # $12.5M - $15.5M: 20%
    (15_500_000, 24_500_000, 0.205), # $15.5M - $24.5M: 20.5%
    (24_500_000, float('inf'), 0.21), # $24.5M+: 21%
]

def get_fedex_earned_discount(transportation_charges: float) -> tuple[float, str]:
    """Get FedEx earned discount rate based on annual transportation charges."""
    for min_val, max_val, discount in FEDEX_EARNED_DISCOUNT_TIERS:
        if min_val <= transportation_charges < max_val:
            if max_val == float('inf'):
                tier_name = f"${min_val/1e6:.1f}M+"
            else:
                tier_name = f"${min_val/1e6:.1f}M - ${max_val/1e6:.1f}M"
            return discount, tier_name
    return 0.0, "Unknown"


def load_data() -> pl.DataFrame:
    """Load the aggregated shipment data."""
    path = Path("analysis/US_2026_tenders/combined_datasets/shipments_aggregated.parquet")
    df = pl.read_parquet(path)
    return df


def greedy_assignment(df: pl.DataFrame) -> pl.DataFrame:
    """Step 1: Assign each group to the cheapest carrier."""
    # For each row, find the cheapest among OnTrac, USPS, FedEx
    df = df.with_columns([
        pl.min_horizontal("ontrac_cost_avg", "usps_cost_avg", "fedex_cost_avg").alias("min_cost_avg"),
    ])

    # Determine which carrier is cheapest
    df = df.with_columns([
        pl.when(pl.col("ontrac_cost_avg") == pl.col("min_cost_avg"))
          .then(pl.lit("ONTRAC"))
          .when(pl.col("usps_cost_avg") == pl.col("min_cost_avg"))
          .then(pl.lit("USPS"))
          .otherwise(pl.lit("FEDEX"))
          .alias("assigned_carrier")
    ])

    return df


def check_constraints(df: pl.DataFrame) -> dict:
    """Check if volume constraints are met."""
    volume_by_carrier = df.group_by("assigned_carrier").agg(
        pl.col("shipment_count").sum().alias("total_shipments")
    )

    volumes = {row["assigned_carrier"]: row["total_shipments"] for row in volume_by_carrier.to_dicts()}

    usps_vol = volumes.get("USPS", 0)
    ontrac_vol = volumes.get("ONTRAC", 0)
    fedex_vol = volumes.get("FEDEX", 0)

    return {
        "USPS": {"volume": usps_vol, "min_required": USPS_MIN_ANNUAL, "shortfall": max(0, USPS_MIN_ANNUAL - usps_vol)},
        "ONTRAC": {"volume": ontrac_vol, "min_required": ONTRAC_MIN_ANNUAL, "shortfall": max(0, ONTRAC_MIN_ANNUAL - ontrac_vol)},
        "FEDEX": {"volume": fedex_vol, "min_required": 0, "shortfall": 0},
    }


def calculate_shift_penalty(df: pl.DataFrame, from_carrier: str, to_carrier: str) -> pl.DataFrame:
    """
    Calculate the cost penalty for shifting each group from one carrier to another.

    Penalty = (target_cost_avg - current_cost_avg) * shipment_count
    """
    cost_col_from = f"{from_carrier.lower()}_cost_avg"
    cost_col_to = f"{to_carrier.lower()}_cost_avg"

    # Filter to groups currently assigned to from_carrier
    groups_to_shift = df.filter(pl.col("assigned_carrier") == from_carrier)

    # Calculate penalty
    groups_to_shift = groups_to_shift.with_columns([
        ((pl.col(cost_col_to) - pl.col(cost_col_from)) * pl.col("shipment_count")).alias("shift_penalty"),
        pl.lit(to_carrier).alias("shift_to_carrier"),
    ])

    return groups_to_shift


def check_constraint_feasibility(total_shipments: int) -> dict:
    """
    Check if both USPS and OnTrac minimums can be satisfied simultaneously.

    Returns feasibility info and recommended approach.
    """
    combined_minimum = USPS_MIN_ANNUAL + ONTRAC_MIN_ANNUAL
    feasible = total_shipments >= combined_minimum

    return {
        "feasible": feasible,
        "total_shipments": total_shipments,
        "combined_minimum": combined_minimum,
        "shortfall": max(0, combined_minimum - total_shipments),
        "usps_min": USPS_MIN_ANNUAL,
        "ontrac_min": ONTRAC_MIN_ANNUAL,
    }


def adjust_for_constraints(df: pl.DataFrame, constraints: dict, enforce_usps: bool = True) -> tuple[pl.DataFrame, list, dict]:
    """
    Step 3: Shift groups to meet constraints.

    Uses vectorized operations for performance.
    Returns the adjusted dataframe, a log of shifts made, and feasibility info.

    Args:
        df: DataFrame with greedy assignments
        constraints: Current constraint status
        enforce_usps: If True, also try to meet USPS minimum. If False, only enforce OnTrac.

    Strategy when constraints are infeasible (combined minimums > total shipments):
    - OnTrac minimum is contractual, so prioritize meeting it
    - USPS gets remaining volume after OnTrac minimum is satisfied (if enforce_usps=True)
    - FedEx receives whatever is left (no minimum requirement)
    """
    shift_log = []
    total_shipments = int(df["shipment_count"].sum())

    # Check if constraints are feasible
    feasibility = check_constraint_feasibility(total_shipments)

    if not feasibility["feasible"] and enforce_usps:
        print(f"\n  WARNING: Constraints are infeasible!")
        print(f"    Total shipments: {total_shipments:,}")
        print(f"    Combined minimum (USPS + OnTrac): {feasibility['combined_minimum']:,}")
        print(f"    Shortfall: {feasibility['shortfall']:,}")
        print(f"\n  Strategy: Prioritize OnTrac minimum (contractual), then maximize USPS")

    # Add a unique row index for efficient joins
    df = df.with_row_index("_row_idx")
    # Track which groups have been locked to a carrier (shouldn't be shifted away)
    df = df.with_columns([pl.lit(False).alias("locked")])

    # Determine which carriers to process
    carriers_to_process = ["ONTRAC"]
    if enforce_usps:
        carriers_to_process.append("USPS")

    # Process OnTrac FIRST (contractual commitment), then USPS (if enforced)
    for carrier in carriers_to_process:
        # Recalculate constraints after each adjustment
        constraints = check_constraints(df)
        shortfall = constraints[carrier]["shortfall"]

        if shortfall <= 0:
            # Lock the groups already assigned to this carrier so they can't be shifted away
            df = df.with_columns([
                pl.when(pl.col("assigned_carrier") == carrier)
                  .then(pl.lit(True))
                  .otherwise(pl.col("locked"))
                  .alias("locked")
            ])
            continue

        print(f"\n{carrier} has shortfall of {shortfall:,} shipments")

        # Find groups to shift from other carriers (only those not locked)
        other_carriers = ["ONTRAC", "USPS", "FEDEX"]
        other_carriers.remove(carrier)

        # Calculate penalties for shifting from all other carriers
        all_penalties = []
        for from_carrier in other_carriers:
            # Only consider groups that aren't locked
            available_df = df.filter(~pl.col("locked"))
            penalties = calculate_shift_penalty(available_df, from_carrier, carrier)
            if penalties.shape[0] > 0:
                all_penalties.append(penalties)

        if not all_penalties:
            print(f"  No groups available to shift to {carrier}")
            continue

        # Combine and sort by penalty (lowest first)
        combined = pl.concat(all_penalties).sort("shift_penalty")

        # Use cumulative sum to find the cutoff point
        combined = combined.with_columns([
            pl.col("shipment_count").cum_sum().alias("cumulative_shipments")
        ])

        # Find how many groups we need to shift to meet the shortfall
        # We need cumulative_shipments >= shortfall
        groups_needed = combined.filter(pl.col("cumulative_shipments") >= shortfall)

        if groups_needed.shape[0] == 0:
            # Need all groups but still won't meet constraint
            cutoff_idx = combined.shape[0]
            print(f"  Note: Shifting all available groups, but constraint may not be fully met")
        else:
            # First row where cumulative >= shortfall gives us the cutoff
            cutoff_idx = combined.shape[0] - groups_needed.shape[0] + 1

        # Select groups to shift
        groups_to_shift = combined.head(cutoff_idx)

        shifted_count = groups_to_shift.shape[0]
        shifted_volume = int(groups_to_shift["shipment_count"].sum())
        shifted_cost = float(groups_to_shift["shift_penalty"].sum())

        print(f"  Shifting {shifted_count:,} groups ({shifted_volume:,} shipments) to {carrier}")
        print(f"  Total cost penalty: ${shifted_cost:,.2f}")

        # Get the row indices to update
        shift_indices = groups_to_shift["_row_idx"].to_list()

        # Vectorized update using is_in on row index
        df = df.with_columns([
            pl.when(pl.col("_row_idx").is_in(shift_indices))
              .then(pl.lit(carrier))
              .otherwise(pl.col("assigned_carrier"))
              .alias("assigned_carrier"),
            # Lock the shifted groups so they can't be taken away
            pl.when(pl.col("_row_idx").is_in(shift_indices))
              .then(pl.lit(True))
              .otherwise(pl.col("locked"))
              .alias("locked"),
        ])

        # Also lock groups that were already assigned to this carrier
        df = df.with_columns([
            pl.when(pl.col("assigned_carrier") == carrier)
              .then(pl.lit(True))
              .otherwise(pl.col("locked"))
              .alias("locked")
        ])

        shift_log.append({
            "carrier": carrier,
            "groups_shifted": shifted_count,
            "shipments_shifted": shifted_volume,
            "cost_penalty": shifted_cost,
        })

    # Drop the temporary columns
    df = df.drop(["_row_idx", "locked"])
    # Add was_shifted flag based on whether the group was shifted
    df = df.with_columns([
        (pl.col("assigned_carrier") != pl.col("cheapest_current_carrier")).alias("was_shifted")
    ])

    return df, shift_log, feasibility


def calculate_costs(df: pl.DataFrame) -> dict:
    """Calculate total costs by carrier based on assignments."""
    results = {}

    for carrier in ["ONTRAC", "USPS", "FEDEX"]:
        carrier_df = df.filter(pl.col("assigned_carrier") == carrier)
        cost_col = f"{carrier.lower()}_cost_total"

        shipments = carrier_df["shipment_count"].sum()
        total_cost = carrier_df[cost_col].sum()

        results[carrier] = {
            "shipments": int(shipments) if shipments else 0,
            "cost": float(total_cost) if total_cost else 0.0,
        }

    return results


def apply_fedex_earned_discount(costs: dict) -> tuple[dict, dict]:
    """
    Apply FedEx earned discount based on total FedEx transportation charges.

    Returns updated costs and discount info.
    """
    fedex_cost = costs["FEDEX"]["cost"]
    discount_rate, tier_name = get_fedex_earned_discount(fedex_cost)

    discount_amount = fedex_cost * discount_rate
    adjusted_cost = fedex_cost - discount_amount

    costs["FEDEX"]["cost_before_discount"] = fedex_cost
    costs["FEDEX"]["earned_discount_rate"] = discount_rate
    costs["FEDEX"]["earned_discount_amount"] = discount_amount
    costs["FEDEX"]["cost"] = adjusted_cost

    discount_info = {
        "tier": tier_name,
        "rate": discount_rate,
        "transportation_charges": fedex_cost,
        "discount_amount": discount_amount,
    }

    return costs, discount_info


def get_current_mix_costs(df: pl.DataFrame) -> dict:
    """Get the baseline costs using the current carrier mix."""
    # Use cost_current_carrier_total which represents actual carrier used
    total_cost = df.filter(pl.col("cost_current_carrier_total").is_not_null())["cost_current_carrier_total"].sum()
    total_shipments = df["shipment_count"].sum()

    return {
        "total_shipments": int(total_shipments),
        "total_cost": float(total_cost),
    }


def get_unconstrained_optimal(df: pl.DataFrame) -> dict:
    """Calculate the unconstrained optimal (just pick cheapest for each group)."""
    df_unconstrained = greedy_assignment(df.clone())
    costs = calculate_costs(df_unconstrained)

    # Apply FedEx discount
    costs, _ = apply_fedex_earned_discount(costs)

    total_shipments = sum(c["shipments"] for c in costs.values())
    total_cost = sum(c["cost"] for c in costs.values())

    return {
        "by_carrier": costs,
        "total_shipments": total_shipments,
        "total_cost": total_cost,
    }


def main():
    print("=" * 70)
    print("Scenario 4: Constrained Optimization (OnTrac/FedEx/USPS)")
    print("=" * 70)

    # Load data
    print("\n[1] Loading data...")
    df = load_data()
    total_shipments = df["shipment_count"].sum()
    print(f"    Loaded {df.shape[0]:,} groups representing {total_shipments:,} shipments")

    # Get baseline (current mix)
    print("\n[2] Calculating current mix baseline...")
    current_mix = get_current_mix_costs(df)
    print(f"    Current mix total cost: ${current_mix['total_cost']:,.2f}")

    # Get unconstrained optimal
    print("\n[3] Calculating unconstrained optimal...")
    unconstrained = get_unconstrained_optimal(df)
    print(f"    Unconstrained optimal cost: ${unconstrained['total_cost']:,.2f}")

    # Step 1: Greedy assignment
    print("\n[4] Running greedy assignment...")
    df_greedy = greedy_assignment(df.clone())

    # Check initial constraints
    print("\n[5] Checking constraints after greedy assignment...")
    constraints = check_constraints(df_greedy)

    for carrier, info in constraints.items():
        status = "OK" if info["shortfall"] == 0 else f"SHORTFALL: {info['shortfall']:,}"
        print(f"    {carrier}: {info['volume']:,} shipments (min: {info['min_required']:,}) - {status}")

    # ====================
    # Scenario 4a: OnTrac-only constrained (recommended when USPS can't be met)
    # ====================
    print("\n" + "=" * 70)
    print("Scenario 4a: OnTrac-Only Constrained")
    print("=" * 70)
    print("\n[6a] Adjusting assignments to meet OnTrac minimum only...")

    df_ontrac_only = greedy_assignment(df.clone())
    df_ontrac_only, shift_log_ontrac_only, feasibility = adjust_for_constraints(
        df_ontrac_only, check_constraints(df_ontrac_only), enforce_usps=False
    )

    print("\n[7a] Verifying constraints...")
    constraints_ontrac_only = check_constraints(df_ontrac_only)
    for carrier, info in constraints_ontrac_only.items():
        status = "OK" if info["shortfall"] == 0 else f"SHORT: {info['shortfall']:,}"
        print(f"    {carrier}: {info['volume']:,} shipments - {status}")

    costs_ontrac_only = calculate_costs(df_ontrac_only)
    costs_ontrac_only, fedex_discount_ontrac_only = apply_fedex_earned_discount(costs_ontrac_only)

    total_shipments_4a = sum(c["shipments"] for c in costs_ontrac_only.values())
    total_cost_4a = sum(c["cost"] for c in costs_ontrac_only.values())

    # ====================
    # Scenario 4b: Both constraints (OnTrac + maximize USPS)
    # ====================
    print("\n" + "=" * 70)
    print("Scenario 4b: Both Constraints (OnTrac + Maximize USPS)")
    print("=" * 70)
    print("\n[6b] Adjusting assignments to meet both constraints...")

    df_both = greedy_assignment(df.clone())
    df_both, shift_log_both, _ = adjust_for_constraints(
        df_both, check_constraints(df_both), enforce_usps=True
    )

    print("\n[7b] Verifying constraints...")
    constraints_both = check_constraints(df_both)
    for carrier, info in constraints_both.items():
        status = "OK" if info["shortfall"] == 0 else f"SHORT: {info['shortfall']:,}"
        print(f"    {carrier}: {info['volume']:,} shipments - {status}")

    costs_both = calculate_costs(df_both)
    costs_both, fedex_discount_both = apply_fedex_earned_discount(costs_both)

    total_shipments_4b = sum(c["shipments"] for c in costs_both.values())
    total_cost_4b = sum(c["cost"] for c in costs_both.values())

    # ====================
    # RESULTS SUMMARY
    # ====================
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)

    # Scenario comparison table
    print("\n### Scenario Comparison")
    print("-" * 80)
    print(f"{'Scenario':<35} {'Total Cost':>15} {'vs Current':>15} {'Savings %':>12}")
    print("-" * 80)
    print(f"{'Current Mix':<35} ${current_mix['total_cost']:>14,.2f} {'-':>15} {'-':>12}")
    print(f"{'Unconstrained Optimal':<35} ${unconstrained['total_cost']:>14,.2f} ${current_mix['total_cost'] - unconstrained['total_cost']:>14,.2f} {(current_mix['total_cost'] - unconstrained['total_cost'])/current_mix['total_cost']*100:>11.1f}%")
    print(f"{'4a: OnTrac-Only Constrained':<35} ${total_cost_4a:>14,.2f} ${current_mix['total_cost'] - total_cost_4a:>14,.2f} {(current_mix['total_cost'] - total_cost_4a)/current_mix['total_cost']*100:>11.1f}%")
    print(f"{'4b: Both Constraints':<35} ${total_cost_4b:>14,.2f} ${current_mix['total_cost'] - total_cost_4b:>14,.2f} {(current_mix['total_cost'] - total_cost_4b)/current_mix['total_cost']*100:>11.1f}%")

    # Detailed results for recommended scenario (4a)
    print("\n" + "=" * 70)
    print("RECOMMENDED: Scenario 4a (OnTrac-Only Constrained)")
    print("=" * 70)
    print("\nRationale: OnTrac minimum is contractual; USPS Tier 1 minimum (140K) is easier to meet.")
    print("Meeting OnTrac minimum is contractual; USPS shortfall unavoidable.")

    print("\n### Optimal Carrier Mix")
    print("-" * 60)
    print(f"{'Carrier':<12} {'Shipments':>12} {'% of Total':>12} {'Total Cost':>15}")
    print("-" * 60)

    for carrier in ["ONTRAC", "USPS", "FEDEX"]:
        info = costs_ontrac_only[carrier]
        pct = (info["shipments"] / total_shipments_4a * 100) if total_shipments_4a > 0 else 0
        print(f"{carrier:<12} {info['shipments']:>12,} {pct:>11.1f}% ${info['cost']:>14,.2f}")

    print("-" * 60)
    print(f"{'TOTAL':<12} {total_shipments_4a:>12,} {'100.0%':>12} ${total_cost_4a:>14,.2f}")

    # Constraint satisfaction
    print("\n### Constraint Satisfaction")
    print("-" * 60)
    print(f"{'Carrier':<12} {'Actual':>12} {'Minimum':>12} {'Status':>15}")
    print("-" * 60)
    for carrier, info in constraints_ontrac_only.items():
        status = "MET" if info["shortfall"] == 0 else f"SHORT by {info['shortfall']:,}"
        print(f"{carrier:<12} {info['volume']:>12,} {info['min_required']:>12,} {status:>15}")

    # FedEx Earned Discount
    print("\n### FedEx Earned Discount")
    print("-" * 60)
    print(f"  Transportation charges: ${fedex_discount_ontrac_only['transportation_charges']:,.2f}")
    print(f"  Tier: {fedex_discount_ontrac_only['tier']}")
    print(f"  Discount rate: {fedex_discount_ontrac_only['rate']*100:.1f}%")
    print(f"  Discount amount: ${fedex_discount_ontrac_only['discount_amount']:,.2f}")

    # Groups shifted
    print("\n### Groups Shifted to Meet OnTrac Minimum")
    print("-" * 60)
    if shift_log_ontrac_only:
        total_groups_shifted = sum(s["groups_shifted"] for s in shift_log_ontrac_only)
        total_shipments_shifted = sum(s["shipments_shifted"] for s in shift_log_ontrac_only)
        total_penalty = sum(s["cost_penalty"] for s in shift_log_ontrac_only)

        for shift in shift_log_ontrac_only:
            print(f"  To {shift['carrier']}:")
            print(f"    Groups shifted: {shift['groups_shifted']:,}")
            print(f"    Shipments shifted: {shift['shipments_shifted']:,}")
            print(f"    Cost penalty: ${shift['cost_penalty']:,.2f}")

        print(f"\n  Total groups shifted: {total_groups_shifted:,}")
        print(f"  Total shipments shifted: {total_shipments_shifted:,}")
        print(f"  Total cost penalty: ${total_penalty:,.2f}")
    else:
        print("  No shifts required - OnTrac constraint already met")

    # Comparison to baseline
    savings = current_mix['total_cost'] - total_cost_4a
    savings_pct = (savings / current_mix['total_cost'] * 100) if current_mix['total_cost'] > 0 else 0

    print("\n### Comparison to Current Mix")
    print("-" * 60)
    print(f"  Current mix cost: ${current_mix['total_cost']:,.2f}")
    print(f"  Optimized cost:   ${total_cost_4a:,.2f}")
    print(f"  Savings:          ${savings:,.2f} ({savings_pct:.1f}%)")

    # Save detailed results
    output_dir = Path("analysis/US_2026_tenders/results/scenario_4_constrained")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save assignment results
    result_df = df_ontrac_only.select([
        "packagetype", "shipping_zip_code", "weight_bracket",
        "shipment_count", "assigned_carrier", "was_shifted",
        "ontrac_cost_avg", "usps_cost_avg", "fedex_cost_avg",
        "ontrac_cost_total", "usps_cost_total", "fedex_cost_total",
    ])
    result_df.write_parquet(output_dir / "assignments.parquet")
    print(f"\n[9] Saved assignments to {output_dir / 'assignments.parquet'}")

    # Return results for summary generation
    return {
        "current_mix": current_mix,
        "unconstrained": unconstrained,
        "scenario_4a": {
            "name": "OnTrac-Only Constrained",
            "by_carrier": costs_ontrac_only,
            "total_shipments": total_shipments_4a,
            "total_cost": total_cost_4a,
            "constraints": constraints_ontrac_only,
            "shift_log": shift_log_ontrac_only,
            "fedex_discount": fedex_discount_ontrac_only,
        },
        "scenario_4b": {
            "name": "Both Constraints",
            "by_carrier": costs_both,
            "total_shipments": total_shipments_4b,
            "total_cost": total_cost_4b,
            "constraints": constraints_both,
            "shift_log": shift_log_both,
            "fedex_discount": fedex_discount_both,
        },
        "feasibility": feasibility,
        "savings": savings,
        "savings_pct": savings_pct,
    }


if __name__ == "__main__":
    results = main()
