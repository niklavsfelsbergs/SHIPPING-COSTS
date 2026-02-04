"""
Scenario 5: Optimal Carrier Mix with P2P Added

Extends Scenario 4 to include P2P US as a fourth carrier option.
P2P is not currently used - this is a future assessment.

Constraints:
- USPS minimum: 140,000 shipments/year (35,000/quarter Tier 1)
- OnTrac minimum: 279,080 shipments/year (5,365/week x 52)
- P2P: No volume commitment
- FedEx: Earned Discount tiers apply based on transportation charges
"""

import polars as pl
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# Constants
USPS_MIN_ANNUAL = 140_000  # 35,000/quarter x 4 (Tier 1)
ONTRAC_MIN_ANNUAL = 279_080  # 5,365/week x 52

# FedEx Earned Discount Tiers
FEDEX_EARNED_DISCOUNT_TIERS = [
    (0, 4_500_000, 0.00),
    (4_500_000, 6_500_000, 0.16),
    (6_500_000, 9_500_000, 0.18),
    (9_500_000, 12_500_000, 0.19),
    (12_500_000, 15_500_000, 0.20),
    (15_500_000, 24_500_000, 0.205),
    (24_500_000, float('inf'), 0.21),
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
    return pl.read_parquet(path)


def greedy_assignment_with_p2p(df: pl.DataFrame) -> pl.DataFrame:
    """Assign each group to cheapest among OnTrac, USPS, FedEx, P2P.

    Handles null costs - a carrier with null cost cannot be assigned.
    min_horizontal ignores nulls, so it picks cheapest available.
    """
    df = df.with_columns([
        pl.min_horizontal("ontrac_cost_avg", "usps_cost_avg", "fedex_cost_avg", "p2p_cost_avg").alias("min_cost_avg"),
    ])

    df = df.with_columns([
        pl.when(
            (pl.col("ontrac_cost_avg") == pl.col("min_cost_avg")) &
            (pl.col("ontrac_cost_avg").is_not_null())
        )
          .then(pl.lit("ONTRAC"))
          .when(
            (pl.col("usps_cost_avg") == pl.col("min_cost_avg")) &
            (pl.col("usps_cost_avg").is_not_null())
        )
          .then(pl.lit("USPS"))
          .when(
            (pl.col("fedex_cost_avg") == pl.col("min_cost_avg")) &
            (pl.col("fedex_cost_avg").is_not_null())
        )
          .then(pl.lit("FEDEX"))
          .when(
            (pl.col("p2p_cost_avg") == pl.col("min_cost_avg")) &
            (pl.col("p2p_cost_avg").is_not_null())
        )
          .then(pl.lit("P2P"))
          .otherwise(pl.lit("FEDEX"))  # FedEx is fallback (100% coverage)
          .alias("assigned_carrier")
    ])

    return df


def check_constraints(df: pl.DataFrame) -> dict:
    """Check if volume constraints are met."""
    volume_by_carrier = df.group_by("assigned_carrier").agg(
        pl.col("shipment_count").sum().alias("total_shipments")
    )

    volumes = {row["assigned_carrier"]: row["total_shipments"] for row in volume_by_carrier.to_dicts()}

    return {
        "USPS": {"volume": volumes.get("USPS", 0), "min": USPS_MIN_ANNUAL, "shortfall": max(0, USPS_MIN_ANNUAL - volumes.get("USPS", 0))},
        "ONTRAC": {"volume": volumes.get("ONTRAC", 0), "min": ONTRAC_MIN_ANNUAL, "shortfall": max(0, ONTRAC_MIN_ANNUAL - volumes.get("ONTRAC", 0))},
        "FEDEX": {"volume": volumes.get("FEDEX", 0), "min": 0, "shortfall": 0},
        "P2P": {"volume": volumes.get("P2P", 0), "min": 0, "shortfall": 0},
    }


def adjust_for_constraints(df: pl.DataFrame) -> tuple[pl.DataFrame, list]:
    """
    Shift groups to meet constraints using vectorized operations.
    Priority: Meet OnTrac first, then USPS. Don't shift FROM P2P unless necessary.

    Only shifts to carriers that can service the shipment (non-null cost).
    """
    shift_log = []
    df = df.with_row_index("_row_idx")
    df = df.with_columns([pl.lit(False).alias("locked")])

    for carrier, min_required in [("ONTRAC", ONTRAC_MIN_ANNUAL), ("USPS", USPS_MIN_ANNUAL)]:
        constraints = check_constraints(df)
        shortfall = constraints[carrier]["shortfall"]

        if shortfall <= 0:
            df = df.with_columns([
                pl.when(pl.col("assigned_carrier") == carrier)
                  .then(pl.lit(True))
                  .otherwise(pl.col("locked"))
                  .alias("locked")
            ])
            continue

        print(f"\n{carrier} has shortfall of {shortfall:,} shipments")

        # Calculate shift penalties from non-P2P carriers first
        # IMPORTANT: Only consider groups where target carrier can service (non-null cost)
        cost_col_to = f"{carrier.lower()}_cost_avg"
        other_carriers = ["ONTRAC", "USPS", "FEDEX"]
        other_carriers.remove(carrier)

        all_penalties = []
        for from_carrier in other_carriers:
            cost_col_from = f"{from_carrier.lower()}_cost_avg"
            # Filter: assigned to from_carrier, not locked, AND target carrier can service (non-null)
            available = df.filter(
                (pl.col("assigned_carrier") == from_carrier) &
                (~pl.col("locked")) &
                (pl.col(cost_col_to).is_not_null())  # Target carrier must be able to service
            )
            if available.shape[0] > 0:
                penalties = available.with_columns([
                    ((pl.col(cost_col_to) - pl.col(cost_col_from)) * pl.col("shipment_count")).alias("shift_penalty"),
                    pl.lit(from_carrier).alias("from_carrier"),
                ])
                all_penalties.append(penalties)

        # If still need more, consider P2P
        if all_penalties:
            combined = pl.concat(all_penalties).sort("shift_penalty")
            combined = combined.with_columns([pl.col("shipment_count").cum_sum().alias("cumulative")])

            groups_needed = combined.filter(pl.col("cumulative") >= shortfall)
            if groups_needed.shape[0] > 0:
                cutoff_idx = combined.shape[0] - groups_needed.shape[0] + 1
            else:
                cutoff_idx = combined.shape[0]

            groups_to_shift = combined.head(cutoff_idx)
            shift_indices = groups_to_shift["_row_idx"].to_list()

            shifted_volume = int(groups_to_shift["shipment_count"].sum())
            shifted_cost = float(groups_to_shift["shift_penalty"].sum())

            print(f"  Shifting {len(shift_indices):,} groups ({shifted_volume:,} shipments) to {carrier}")
            print(f"  Cost penalty: ${shifted_cost:,.2f}")

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

            shift_log.append({"carrier": carrier, "groups": len(shift_indices), "shipments": shifted_volume, "penalty": shifted_cost})

            # Check if still short - if so, need to shift from P2P
            constraints = check_constraints(df)
            if constraints[carrier]["shortfall"] > 0:
                print(f"  Still short, shifting from P2P...")
                remaining_shortfall = constraints[carrier]["shortfall"]

                # Only consider P2P shipments where target carrier can service (non-null)
                p2p_available = df.filter(
                    (pl.col("assigned_carrier") == "P2P") &
                    (~pl.col("locked")) &
                    (pl.col(cost_col_to).is_not_null())  # Target carrier must be able to service
                )
                if p2p_available.shape[0] > 0:
                    p2p_penalties = p2p_available.with_columns([
                        ((pl.col(cost_col_to) - pl.col("p2p_cost_avg")) * pl.col("shipment_count")).alias("shift_penalty"),
                    ]).sort("shift_penalty")
                    p2p_penalties = p2p_penalties.with_columns([pl.col("shipment_count").cum_sum().alias("cumulative")])

                    p2p_needed = p2p_penalties.filter(pl.col("cumulative") >= remaining_shortfall)
                    if p2p_needed.shape[0] > 0:
                        p2p_cutoff = p2p_penalties.shape[0] - p2p_needed.shape[0] + 1
                    else:
                        p2p_cutoff = p2p_penalties.shape[0]

                    p2p_to_shift = p2p_penalties.head(p2p_cutoff)
                    p2p_indices = p2p_to_shift["_row_idx"].to_list()

                    df = df.with_columns([
                        pl.when(pl.col("_row_idx").is_in(p2p_indices))
                          .then(pl.lit(carrier))
                          .otherwise(pl.col("assigned_carrier"))
                          .alias("assigned_carrier"),
                    ])

                    p2p_shifted = int(p2p_to_shift["shipment_count"].sum())
                    print(f"  Shifted {len(p2p_indices):,} groups ({p2p_shifted:,} shipments) from P2P")

        df = df.with_columns([
            pl.when(pl.col("assigned_carrier") == carrier)
              .then(pl.lit(True))
              .otherwise(pl.col("locked"))
              .alias("locked")
        ])

    df = df.drop(["_row_idx", "locked"])
    return df, shift_log


def calculate_costs(df: pl.DataFrame) -> dict:
    """Calculate total costs by carrier."""
    results = {}
    for carrier in ["ONTRAC", "USPS", "FEDEX", "P2P"]:
        carrier_df = df.filter(pl.col("assigned_carrier") == carrier)
        cost_col = f"{carrier.lower()}_cost_total"

        shipments = carrier_df["shipment_count"].sum()
        total_cost = carrier_df[cost_col].sum()

        results[carrier] = {
            "shipments": int(shipments) if shipments else 0,
            "cost": float(total_cost) if total_cost else 0.0,
        }

    return results


def get_serviceability(df: pl.DataFrame) -> dict:
    """Calculate how many shipments each carrier can service (non-null costs)."""
    total = int(df["shipment_count"].sum())
    return {
        "total": total,
        "ONTRAC": int(df.filter(pl.col("ontrac_cost_avg").is_not_null())["shipment_count"].sum()),
        "USPS": int(df.filter(pl.col("usps_cost_avg").is_not_null())["shipment_count"].sum()),
        "FEDEX": int(df.filter(pl.col("fedex_cost_avg").is_not_null())["shipment_count"].sum()),
        "P2P": int(df.filter(pl.col("p2p_cost_avg").is_not_null())["shipment_count"].sum()),
    }


def main():
    print("=" * 70)
    print("Scenario 5: Optimal with P2P")
    print("=" * 70)

    # Load data
    print("\n[1] Loading data...")
    df = load_data()
    total_shipments = int(df["shipment_count"].sum())
    print(f"    {df.shape[0]:,} groups, {total_shipments:,} shipments")

    # Check serviceability
    print("\n[1b] Carrier serviceability...")
    serviceability = get_serviceability(df)
    for carrier in ["ONTRAC", "USPS", "FEDEX", "P2P"]:
        svc = serviceability[carrier]
        pct = svc / total_shipments * 100
        print(f"    {carrier}: {svc:,} serviceable ({pct:.1f}%)")

    # Use consistent baseline from Scenario 1
    SCENARIO_1_BASELINE = 6_389_595.72
    print(f"\n    Current mix cost (from S1): ${SCENARIO_1_BASELINE:,.2f}")

    # Greedy assignment with P2P
    print("\n[2] Greedy assignment (4 carriers)...")
    df_greedy = greedy_assignment_with_p2p(df.clone())
    constraints = check_constraints(df_greedy)

    print("\n    Initial assignment:")
    for carrier, info in constraints.items():
        status = "OK" if info["shortfall"] == 0 else f"SHORT: {info['shortfall']:,}"
        print(f"      {carrier}: {info['volume']:,} (min: {info['min']:,}) - {status}")

    # Adjust for constraints
    print("\n[3] Adjusting for constraints...")
    df_adjusted, shift_log = adjust_for_constraints(df_greedy)

    # Verify constraints
    print("\n[4] Verifying constraints...")
    final_constraints = check_constraints(df_adjusted)
    for carrier, info in final_constraints.items():
        status = "MET" if info["shortfall"] == 0 else f"SHORT: {info['shortfall']:,}"
        print(f"    {carrier}: {info['volume']:,} - {status}")

    # Calculate costs
    costs = calculate_costs(df_adjusted)

    # FedEx earned discount (based on FedEx cost as proxy for transportation charges)
    fedex_cost = costs["FEDEX"]["cost"]
    discount_rate, tier_name = get_fedex_earned_discount(fedex_cost)
    discount_amount = fedex_cost * discount_rate

    total_cost = sum(c["cost"] for c in costs.values()) - discount_amount

    # Results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    print("\n### Optimal Carrier Mix")
    print("-" * 60)
    print(f"{'Carrier':<10} {'Shipments':>12} {'%':>8} {'Cost':>15}")
    print("-" * 60)

    for carrier in ["ONTRAC", "USPS", "FEDEX", "P2P"]:
        info = costs[carrier]
        pct = info["shipments"] / total_shipments * 100 if total_shipments > 0 else 0
        print(f"{carrier:<10} {info['shipments']:>12,} {pct:>7.1f}% ${info['cost']:>14,.2f}")

    print("-" * 60)
    subtotal = sum(c["cost"] for c in costs.values())
    print(f"{'Subtotal':<10} {total_shipments:>12,} {'100.0%':>8} ${subtotal:>14,.2f}")
    print(f"{'FedEx Disc':<10} {'':<12} {'':<8} -${discount_amount:>13,.2f}")
    print("-" * 60)
    print(f"{'TOTAL':<10} {total_shipments:>12,} {'100.0%':>8} ${total_cost:>14,.2f}")

    # FedEx discount info
    print(f"\n### FedEx Earned Discount")
    print(f"    Tier: {tier_name}")
    print(f"    Rate: {discount_rate*100:.1f}%")
    print(f"    Amount: ${discount_amount:,.2f}")

    # Comparison to Scenario 4 (run it for comparison)
    print("\n### Comparison to Scenario 4 (without P2P)")

    # Quick Scenario 4 calculation
    df_s4 = df.with_columns([
        pl.min_horizontal("ontrac_cost_avg", "usps_cost_avg", "fedex_cost_avg").alias("min_cost_avg_s4"),
    ])
    df_s4 = df_s4.with_columns([
        pl.when(pl.col("ontrac_cost_avg") == pl.col("min_cost_avg_s4"))
          .then(pl.lit("ONTRAC"))
          .when(pl.col("usps_cost_avg") == pl.col("min_cost_avg_s4"))
          .then(pl.lit("USPS"))
          .otherwise(pl.lit("FEDEX"))
          .alias("s4_carrier")
    ])

    # Apply same constraint adjustment logic for S4
    # (simplified - just calculate the cost after meeting OnTrac min)
    s4_costs = {}
    for carrier in ["ONTRAC", "USPS", "FEDEX"]:
        carrier_df = df_s4.filter(pl.col("s4_carrier") == carrier)
        cost_col = f"{carrier.lower()}_cost_total"
        s4_costs[carrier] = carrier_df[cost_col].sum() if len(carrier_df) > 0 else 0

    # Use S4 result from actual scenario 4 run (from previous output)
    s4_total = 5_389_973.56  # From scenario 4 output

    savings = s4_total - total_cost
    savings_pct = savings / s4_total * 100 if s4_total > 0 else 0

    print(f"    Scenario 4 cost: ${s4_total:,.2f}")
    print(f"    Scenario 5 cost: ${total_cost:,.2f}")
    print(f"    Savings with P2P: ${savings:,.2f} ({savings_pct:.1f}%)")

    # P2P analysis
    print("\n### Where P2P Wins")
    p2p_df = df_adjusted.filter(pl.col("assigned_carrier") == "P2P")

    if p2p_df.shape[0] > 0:
        p2p_shipments = costs["P2P"]["shipments"]
        p2p_cost = costs["P2P"]["cost"]

        # What would these cost with other carriers?
        alt_ontrac = p2p_df["ontrac_cost_total"].sum()
        alt_usps = p2p_df["usps_cost_total"].sum()
        alt_fedex = p2p_df["fedex_cost_total"].sum()

        print(f"    P2P captures: {p2p_shipments:,} shipments")
        print(f"    P2P cost: ${p2p_cost:,.2f} (${p2p_cost/p2p_shipments:.2f}/shipment)")
        print(f"    vs OnTrac: ${alt_ontrac:,.2f} (${alt_ontrac/p2p_shipments:.2f}/shipment)")
        print(f"    vs USPS:   ${alt_usps:,.2f} (${alt_usps/p2p_shipments:.2f}/shipment)")
        print(f"    vs FedEx:  ${alt_fedex:,.2f} (${alt_fedex/p2p_shipments:.2f}/shipment)")

        # By weight bracket
        print("\n    P2P by weight bracket:")
        by_weight = p2p_df.group_by("weight_bracket").agg(pl.col("shipment_count").sum()).sort("weight_bracket")
        for row in by_weight.head(10).iter_rows():
            print(f"      {row[0]} lbs: {row[1]:,} shipments")
    else:
        print("    P2P did not capture any segments")

    # Save results
    output_dir = Path("analysis/US_2026_tenders/results/scenario_5_with_p2p")
    output_dir.mkdir(parents=True, exist_ok=True)

    df_adjusted.write_parquet(output_dir / "assignments.parquet")
    print(f"\n[5] Saved to {output_dir}")

    return {
        "total_cost": total_cost,
        "costs": costs,
        "savings_vs_s4": savings,
    }


if __name__ == "__main__":
    main()
