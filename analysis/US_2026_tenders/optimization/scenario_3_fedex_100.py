"""
Scenario 3: 100% FedEx with Earned Discount Analysis

Calculates what shipping costs would be if all volume went to FedEx,
including determination of the achieved Earned Discount tier based on
total transportation charges.
"""

import polars as pl
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
COMBINED_DATASETS = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "combined_datasets"
RESULTS_DIR = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "results" / "scenario_3_fedex_100"

# Earned discount tiers (Ground/Home Delivery Single Piece)
# From FedEx Agreement #491103984-115-04
EARNED_DISCOUNT_TIERS = [
    (0, 4_500_000, 0.00),           # < $4.5M
    (4_500_000, 6_500_000, 0.16),   # $4.5M - $6.5M
    (6_500_000, 9_500_000, 0.18),   # $6.5M - $9.5M
    (9_500_000, 12_500_000, 0.19),  # $9.5M - $12.5M
    (12_500_000, 15_500_000, 0.20), # $12.5M - $15.5M
    (15_500_000, 24_500_000, 0.205),# $15.5M - $24.5M
    (24_500_000, float('inf'), 0.21), # $24.5M+
]


def get_earned_discount_tier(transportation_charges: float) -> tuple[str, float]:
    """
    Determine the earned discount tier based on annual transportation charges.

    Returns:
        Tuple of (tier_description, discount_percentage)
    """
    for min_val, max_val, discount in EARNED_DISCOUNT_TIERS:
        if min_val <= transportation_charges < max_val:
            if max_val == float('inf'):
                tier_desc = f"$24.5M+"
            elif min_val == 0:
                tier_desc = f"< ${max_val/1_000_000:.1f}M"
            else:
                tier_desc = f"${min_val/1_000_000:.1f}M - ${max_val/1_000_000:.1f}M"
            return tier_desc, discount

    return "Unknown", 0.0


def main():
    print("=" * 70)
    print("SCENARIO 3: 100% FedEx with Earned Discount")
    print("=" * 70)

    # Create results directory
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Load unified dataset (has detailed FedEx cost columns)
    unified_path = COMBINED_DATASETS / "shipments_unified.parquet"
    print(f"\nLoading: {unified_path}")
    df = pl.read_parquet(unified_path)
    total_shipments = len(df)
    print(f"  {total_shipments:,} shipments loaded")

    # Load aggregated dataset for baseline comparison
    agg_path = COMBINED_DATASETS / "shipments_aggregated.parquet"
    df_agg = pl.read_parquet(agg_path)
    baseline_cost = df_agg["cost_current_carrier_total"].sum()

    print("\n" + "-" * 70)
    print("BASELINE: Current Carrier Mix")
    print("-" * 70)
    print(f"  Total cost: ${baseline_cost:,.2f}")
    print(f"  Shipments:  {total_shipments:,}")
    print(f"  Avg cost:   ${baseline_cost/total_shipments:.2f}")

    # Calculate FedEx cost components
    print("\n" + "-" * 70)
    print("FedEx Cost Component Breakdown (Before Earned Discount)")
    print("-" * 70)

    # Base transportation charges (undiscounted rate)
    base_rate_total = df["fedex_cost_base_rate"].sum()
    performance_pricing_total = df["fedex_cost_performance_pricing"].sum()
    grace_discount_total = df["fedex_cost_grace_discount"].sum()
    current_earned_discount = df["fedex_cost_earned_discount"].sum()

    # Surcharges
    ahs_total = df["fedex_cost_ahs"].sum()
    ahs_weight_total = df["fedex_cost_ahs_weight"].sum()
    oversize_total = df["fedex_cost_oversize"].sum()
    das_total = df["fedex_cost_das"].sum()
    residential_total = df["fedex_cost_residential"].sum()
    dem_base_total = df["fedex_cost_dem_base"].sum()
    dem_ahs_total = df["fedex_cost_dem_ahs"].sum()
    dem_oversize_total = df["fedex_cost_dem_oversize"].sum()
    fuel_total = df["fedex_cost_fuel"].sum()

    fedex_total = df["fedex_cost_total"].sum()

    print(f"\n  Base Rate Components:")
    print(f"    Undiscounted base rate:   ${base_rate_total:>12,.2f}")
    print(f"    Performance pricing:      ${performance_pricing_total:>12,.2f}")
    print(f"    Current earned discount:  ${current_earned_discount:>12,.2f}")
    print(f"    Grace discount:           ${grace_discount_total:>12,.2f}")

    print(f"\n  Surcharges:")
    print(f"    Additional Handling (dim):${ahs_total:>12,.2f}")
    print(f"    Additional Handling (wt): ${ahs_weight_total:>12,.2f}")
    print(f"    Oversize:                 ${oversize_total:>12,.2f}")
    print(f"    DAS:                      ${das_total:>12,.2f}")
    print(f"    Residential:              ${residential_total:>12,.2f}")
    print(f"    Demand (base):            ${dem_base_total:>12,.2f}")
    print(f"    Demand (AHS):             ${dem_ahs_total:>12,.2f}")
    print(f"    Demand (oversize):        ${dem_oversize_total:>12,.2f}")
    print(f"    Fuel:                     ${fuel_total:>12,.2f}")

    total_surcharges = (ahs_total + ahs_weight_total + oversize_total + das_total +
                        residential_total + dem_base_total + dem_ahs_total +
                        dem_oversize_total + fuel_total)

    print(f"\n  Summary:")
    print(f"    Total surcharges:         ${total_surcharges:>12,.2f}")
    print(f"    Total (calculated):       ${fedex_total:>12,.2f}")

    # Calculate transportation charges for earned discount tier determination
    # Transportation charges = base rate (undiscounted) - this is what FedEx uses to determine tier
    transportation_charges = base_rate_total

    print("\n" + "-" * 70)
    print("Earned Discount Tier Calculation")
    print("-" * 70)
    print(f"\n  Transportation charges (undiscounted base rate): ${transportation_charges:,.2f}")

    tier_desc, discount_pct = get_earned_discount_tier(transportation_charges)

    print(f"\n  Tier achieved: {tier_desc}")
    print(f"  Earned discount: {discount_pct*100:.1f}%")

    # Show all tiers for context
    print(f"\n  Earned Discount Tier Table (Ground/Home Delivery):")
    print(f"    {'Annual Transportation Charges':<30} {'Discount':>10}")
    print(f"    {'-'*30} {'-'*10}")
    for min_val, max_val, disc in EARNED_DISCOUNT_TIERS:
        if max_val == float('inf'):
            tier = f"$24.5M+"
        elif min_val == 0:
            tier = f"< ${max_val/1_000_000:.1f}M"
        else:
            tier = f"${min_val/1_000_000:.1f}M - ${max_val/1_000_000:.1f}M"

        marker = " <-- YOU ARE HERE" if tier == tier_desc else ""
        print(f"    {tier:<30} {disc*100:>9.1f}%{marker}")

    # Calculate new earned discount amount
    # Note: Earned discount applies to transportation charges (base rates), not surcharges
    # For simplicity, we apply it to the base rate total
    earned_discount_amount = transportation_charges * discount_pct

    # Calculate total cost after earned discount
    # Remove any existing earned discount and apply the new one
    fedex_total_before_new_discount = fedex_total - current_earned_discount
    fedex_total_with_earned_discount = fedex_total_before_new_discount - earned_discount_amount

    print("\n" + "-" * 70)
    print("Total Cost Calculation")
    print("-" * 70)
    print(f"\n  FedEx cost (with current 0% earned discount): ${fedex_total:>14,.2f}")
    print(f"  Less: Current earned discount (0%):           ${current_earned_discount:>14,.2f}")
    print(f"  Cost before new earned discount:              ${fedex_total_before_new_discount:>14,.2f}")
    print(f"  Less: New earned discount ({discount_pct*100:.1f}%):           ${-earned_discount_amount:>14,.2f}")
    print(f"  ---------------------------------------------------------------")
    print(f"  TOTAL COST WITH EARNED DISCOUNT:              ${fedex_total_with_earned_discount:>14,.2f}")

    print("\n" + "-" * 70)
    print("Comparison to Baseline (Current Carrier Mix)")
    print("-" * 70)

    diff_vs_baseline = fedex_total_with_earned_discount - baseline_cost
    diff_pct = (diff_vs_baseline / baseline_cost) * 100

    diff_before_discount = fedex_total - baseline_cost
    diff_before_discount_pct = (diff_before_discount / baseline_cost) * 100

    print(f"\n  Current carrier mix baseline:    ${baseline_cost:>14,.2f}")
    print(f"  100% FedEx (before earned disc): ${fedex_total:>14,.2f}  ({diff_before_discount_pct:+.1f}%)")
    print(f"  100% FedEx (after earned disc):  ${fedex_total_with_earned_discount:>14,.2f}  ({diff_pct:+.1f}%)")
    print(f"\n  Savings from earned discount:    ${earned_discount_amount:>14,.2f}")
    print(f"  Net difference vs baseline:      ${diff_vs_baseline:>14,.2f}  ({diff_pct:+.1f}%)")

    # Breakdown by weight bracket
    print("\n" + "-" * 70)
    print("Cost Breakdown by Weight Bracket")
    print("-" * 70)

    df_weight = (
        df
        .with_columns(
            pl.col("weight_lbs").ceil().cast(pl.Int32).alias("weight_bracket")
        )
        .group_by("weight_bracket")
        .agg([
            pl.len().alias("shipment_count"),
            pl.col("fedex_cost_total").sum().alias("fedex_total"),
            pl.col("fedex_cost_base_rate").sum().alias("base_rate_total"),
        ])
        .sort("weight_bracket")
        .with_columns([
            (pl.col("base_rate_total") * discount_pct).alias("earned_discount"),
        ])
        .with_columns([
            (pl.col("fedex_total") - pl.col("earned_discount")).alias("fedex_with_discount"),
        ])
    )

    print(f"\n  {'Weight':<10} {'Shipments':>12} {'FedEx Total':>14} {'After Discount':>16}")
    print(f"  {'-'*10} {'-'*12} {'-'*14} {'-'*16}")

    # Show top weight brackets
    top_brackets = df_weight.sort("fedex_total", descending=True).head(15)
    for row in top_brackets.iter_rows(named=True):
        wt = f"{row['weight_bracket']} lb"
        print(f"  {wt:<10} {row['shipment_count']:>12,} ${row['fedex_total']:>13,.2f} ${row['fedex_with_discount']:>15,.2f}")

    # Breakdown by zone
    print("\n" + "-" * 70)
    print("Cost Breakdown by Zone")
    print("-" * 70)

    df_zone = (
        df
        .group_by("fedex_shipping_zone")
        .agg([
            pl.len().alias("shipment_count"),
            pl.col("fedex_cost_total").sum().alias("fedex_total"),
            pl.col("fedex_cost_base_rate").sum().alias("base_rate_total"),
        ])
        .sort("fedex_shipping_zone")
        .with_columns([
            (pl.col("base_rate_total") * discount_pct).alias("earned_discount"),
        ])
        .with_columns([
            (pl.col("fedex_total") - pl.col("earned_discount")).alias("fedex_with_discount"),
        ])
    )

    print(f"\n  {'Zone':<10} {'Shipments':>12} {'FedEx Total':>14} {'After Discount':>16}")
    print(f"  {'-'*10} {'-'*12} {'-'*14} {'-'*16}")

    for row in df_zone.iter_rows(named=True):
        zone = row['fedex_shipping_zone']
        print(f"  {zone:<10} {row['shipment_count']:>12,} ${row['fedex_total']:>13,.2f} ${row['fedex_with_discount']:>15,.2f}")

    # What-if analysis: Show potential savings at each tier
    print("\n" + "-" * 70)
    print("What-If Analysis: Impact of Different Earned Discount Tiers")
    print("-" * 70)
    print(f"\n  If we could reach different tiers, here's the impact:")
    print(f"\n  {'Tier':<25} {'Discount':>10} {'Savings':>15} {'Total Cost':>15} {'vs Baseline':>12}")
    print(f"  {'-'*25} {'-'*10} {'-'*15} {'-'*15} {'-'*12}")

    for min_val, max_val, disc in EARNED_DISCOUNT_TIERS:
        if max_val == float('inf'):
            tier = f"$24.5M+"
        elif min_val == 0:
            tier = f"< ${max_val/1_000_000:.1f}M"
        else:
            tier = f"${min_val/1_000_000:.1f}M - ${max_val/1_000_000:.1f}M"

        potential_savings = transportation_charges * disc
        potential_total = fedex_total - potential_savings
        potential_diff = potential_total - baseline_cost
        potential_diff_pct = (potential_diff / baseline_cost) * 100

        marker = " <--" if tier == tier_desc else ""
        print(f"  {tier:<25} {disc*100:>9.1f}% ${potential_savings:>14,.2f} ${potential_total:>14,.2f} {potential_diff_pct:>+11.1f}%{marker}")

    # Gap to next tier
    if transportation_charges < 4_500_000:
        gap_to_next = 4_500_000 - transportation_charges
        next_tier_savings = 4_500_000 * 0.16
        print(f"\n  Gap to $4.5M tier: ${gap_to_next:,.2f}")
        print(f"  At $4.5M, would save: ${next_tier_savings:,.2f} (16% of $4.5M)")

    # Key findings
    print("\n" + "=" * 70)
    print("KEY FINDINGS")
    print("=" * 70)

    print(f"""
  1. Transportation charges of ${transportation_charges/1_000_000:.2f}M qualify for the
     "{tier_desc}" earned discount tier ({discount_pct*100:.1f}% discount).

  2. The earned discount saves ${earned_discount_amount:,.2f} annually.

  3. Even with the {discount_pct*100:.1f}% earned discount, 100% FedEx costs
     ${abs(diff_vs_baseline):,.2f} {'more' if diff_vs_baseline > 0 else 'less'} than the current carrier mix
     ({abs(diff_pct):.1f}% {'increase' if diff_vs_baseline > 0 else 'decrease'}).

  4. Without the earned discount (current 0% tier), FedEx would cost
     ${abs(diff_before_discount):,.2f} {'more' if diff_before_discount > 0 else 'less'} than baseline ({abs(diff_before_discount_pct):.1f}% {'increase' if diff_before_discount > 0 else 'decrease'}).

  5. We are ${4_500_000 - transportation_charges:,.2f} short of the $4.5M threshold
     needed to qualify for the 16% earned discount tier.
""")

    # Export results
    results = {
        "baseline_cost": baseline_cost,
        "total_shipments": total_shipments,
        "transportation_charges": transportation_charges,
        "earned_discount_tier": tier_desc,
        "earned_discount_pct": discount_pct,
        "earned_discount_amount": earned_discount_amount,
        "fedex_total_before_earned_discount": fedex_total,
        "fedex_total_with_earned_discount": fedex_total_with_earned_discount,
        "diff_vs_baseline": diff_vs_baseline,
        "diff_vs_baseline_pct": diff_pct,
        "total_surcharges": total_surcharges,
        "base_rate_total": base_rate_total,
    }

    # Save detailed results
    results_df = pl.DataFrame([results])
    results_df.write_parquet(RESULTS_DIR / "scenario_3_results.parquet")

    # Save weight breakdown
    df_weight.write_parquet(RESULTS_DIR / "cost_by_weight_bracket.parquet")

    # Save zone breakdown
    df_zone.write_parquet(RESULTS_DIR / "cost_by_zone.parquet")

    print(f"\nResults saved to: {RESULTS_DIR}")
    print("  - scenario_3_results.parquet")
    print("  - cost_by_weight_bracket.parquet")
    print("  - cost_by_zone.parquet")

    print("\n" + "=" * 70)
    print("Done.")
    print("=" * 70)

    return results


if __name__ == "__main__":
    results = main()
