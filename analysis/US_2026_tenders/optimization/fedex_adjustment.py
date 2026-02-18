"""
FedEx Earned Discount Adjustment

Adjusts FedEx costs to reflect a target earned discount tier, given that rate tables
have earned discount baked in.

HD and SmartPost have different baked earned discounts:
    HD:  baked_earned = 18%, baked_factor = 1 - 0.45 - 0.18 = 0.37
    SP:  baked_earned = 4.5%, baked_factor = 1 - 0.45 - 0.045 = 0.505

The FedEx discount structure is additive — both PP and earned are percentages
of the true undiscounted rate:

    baked_rate = undiscounted × (1 - PP - BAKED_EARNED)
    target_rate = undiscounted × (1 - PP - target_earned)
    multiplier = (1 - PP - target_earned) / (1 - PP - BAKED_EARNED)

Examples (HD):
    target_earned=0.00 → multiplier = 0.55/0.37 = 1.4865 (lose all earned discount)
    target_earned=0.16 → multiplier = 0.39/0.37 = 1.0541 (16% tier instead of 18%)
    target_earned=0.18 → multiplier = 1.0 (no change, verification mode)

Examples (SP):
    target_earned=0.00 → multiplier = 0.55/0.505 = 1.0891 (lose all earned discount)
    target_earned=0.04 → multiplier = 0.51/0.505 = 1.0099 (4% tier instead of 4.5%)
    target_earned=0.045 → multiplier = 1.0 (no change, verification mode)

Fuel (14%) is applied on base rate only, so per-shipment adjustment:

    delta = fedex_cost_base_rate × (multiplier - 1) × (1 + FUEL_RATE)
    new_fedex_cost_total = old_total + delta
"""

import polars as pl
from pathlib import Path

# Discount parameters
PP_DISCOUNT = 0.45           # Performance pricing (flat percentage)
BAKED_EARNED_HD = 0.18       # Earned discount baked into HD rate tables
BAKED_EARNED_SP = 0.045      # Earned discount baked into SmartPost rate tables
BAKED_EARNED = BAKED_EARNED_HD  # Backward compat (used by other scenarios)
FUEL_RATE = 0.14             # From carriers/fedex/data/reference/fuel.py

# Baked factors: what fraction of undiscounted rate the baked rate represents
BAKED_FACTOR_HD = 1 - PP_DISCOUNT - BAKED_EARNED_HD   # 0.37
BAKED_FACTOR_SP = 1 - PP_DISCOUNT - BAKED_EARNED_SP   # 0.505


def compute_undiscounted(hd_base: float, sp_base: float) -> float:
    """Compute FedEx undiscounted spend from HD and SP base rates (baked rates)."""
    return hd_base / BAKED_FACTOR_HD + sp_base / BAKED_FACTOR_SP

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
COMBINED_DATASETS = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "combined_datasets"


def _derive_sp_target(target_earned_hd: float) -> float:
    """Derive SP earned discount target from HD target using proportional mapping.

    HD and SP earned discount tiers are proportional:
        HD 18% (baked) → SP 4.5% (baked)
        HD 16% (first tier) → SP 4%
        HD 0% (no earned) → SP 0%
    """
    if BAKED_EARNED_HD == 0:
        return 0.0
    return target_earned_hd * (BAKED_EARNED_SP / BAKED_EARNED_HD)


def adjust_fedex_costs(
    df: pl.DataFrame,
    target_earned: float,
    target_earned_sp: float | None = None,
) -> pl.DataFrame:
    """Adjust FedEx costs on a shipment-level DataFrame to reflect a target earned discount.

    HD and SP are always adjusted independently using their respective baked earned
    discounts (HD=18%, SP=4.5%).

    Args:
        df: Shipment-level DataFrame with fedex_cost_base_rate, fedex_cost_total,
            fedex_service_selected, cost_current_carrier, pcs_shipping_provider.
        target_earned: The target HD earned discount percentage (e.g., 0.16 for 16% tier).
        target_earned_sp: Optional SP earned discount target (e.g., 0.04).
            When None, auto-derived proportionally from target_earned.

    Returns:
        DataFrame with adjusted FedEx costs.
    """
    target_hd = target_earned
    target_sp = target_earned_sp if target_earned_sp is not None else _derive_sp_target(target_hd)

    multiplier_hd = (1 - PP_DISCOUNT - target_hd) / BAKED_FACTOR_HD
    multiplier_sp = (1 - PP_DISCOUNT - target_sp) / BAKED_FACTOR_SP

    print(f"\n    FedEx earned discount adjustment:")
    print(f"      HD: baked {BAKED_EARNED_HD:.1%} -> target {target_hd:.1%}, multiplier {multiplier_hd:.4f}")
    print(f"      SP: baked {BAKED_EARNED_SP:.1%} -> target {target_sp:.1%}, multiplier {multiplier_sp:.4f}")

    if abs(multiplier_hd - 1.0) < 1e-6 and abs(multiplier_sp - 1.0) < 1e-6:
        print(f"      No adjustment needed (targets match baked rates)")
        return df

    old_fedex_total = float(df["fedex_cost_total"].sum())

    # Service-conditional delta
    is_sp = pl.col("fedex_service_selected") == "FXSP"
    delta_expr = (
        pl.when(is_sp)
        .then(pl.col("fedex_cost_base_rate") * (multiplier_sp - 1) * (1 + FUEL_RATE))
        .otherwise(pl.col("fedex_cost_base_rate") * (multiplier_hd - 1) * (1 + FUEL_RATE))
    )

    df = df.with_columns(
        (pl.col("fedex_cost_total") + delta_expr).alias("fedex_cost_total"),
    )

    # Update cost_current_carrier for FedEx shipments
    df = df.with_columns(
        pl.when(pl.col("pcs_shipping_provider").str.contains("FX"))
        .then(pl.col("fedex_cost_total"))
        .otherwise(pl.col("cost_current_carrier"))
        .alias("cost_current_carrier")
    )

    new_fedex_total = float(df["fedex_cost_total"].sum())
    print(f"\n    FedEx cost impact:")
    print(f"      Old total:  ${old_fedex_total:,.2f}")
    print(f"      New total:  ${new_fedex_total:,.2f}")
    print(f"      Delta:      ${new_fedex_total - old_fedex_total:+,.2f} ({(new_fedex_total/old_fedex_total - 1)*100:+.1f}%)")

    return df


def adjust_and_aggregate(target_earned: float = 0.0) -> tuple[pl.DataFrame, float]:
    """Load shipment data, adjust FedEx costs, and return aggregated data.

    Args:
        target_earned: The target earned discount percentage (default 0.0 = no earned
            discount). Used by S4/S5 where FedEx volume drops below $4.5M threshold.

    Returns:
        Tuple of (aggregated DataFrame, adjusted S1 baseline cost).
    """
    # Load shipment-level data
    input_path = COMBINED_DATASETS / "shipments_unified.parquet"
    print(f"    Loading: {input_path.name}")
    df = pl.read_parquet(input_path)
    print(f"    {df.shape[0]:,} shipments loaded")

    # Adjust FedEx costs
    df = adjust_fedex_costs(df, target_earned)

    # Compute adjusted S1 baseline (sum of cost_current_carrier)
    s1_baseline = float(df["cost_current_carrier"].sum())
    print(f"\n    Adjusted S1 baseline: ${s1_baseline:,.2f}")

    # Add weight bracket
    df = df.with_columns(
        pl.col("weight_lbs").ceil().cast(pl.Int32).alias("weight_bracket")
    )

    # Aggregate — replicate build_aggregated_dataset.py logic
    group_cols = ["packagetype", "shipping_zip_code", "weight_bracket"]

    agg_exprs = [
        pl.len().alias("shipment_count"),

        # Current carrier costs
        pl.col("cost_current_carrier").sum().alias("cost_current_carrier_total"),
        pl.col("cost_current_carrier").mean().alias("cost_current_carrier_avg"),

        # OnTrac
        pl.col("ontrac_cost_total").sum().alias("ontrac_cost_total"),
        pl.col("ontrac_cost_total").mean().alias("ontrac_cost_avg"),

        # USPS
        pl.col("usps_cost_total").sum().alias("usps_cost_total"),
        pl.col("usps_cost_total").mean().alias("usps_cost_avg"),

        # FedEx base rate (unadjusted, for threshold calculations)
        pl.col("fedex_cost_base_rate").sum().alias("fedex_cost_base_rate_total"),

        # FedEx HD vs SP base rate split (for undiscounted spend with split baked factors)
        (pl.when(pl.col("fedex_service_selected") == "FXEHD")
         .then(pl.col("fedex_cost_base_rate")).otherwise(0.0)
        ).sum().alias("fedex_hd_base_rate_total"),
        (pl.when(pl.col("fedex_service_selected") == "FXSP")
         .then(pl.col("fedex_cost_base_rate")).otherwise(0.0)
        ).sum().alias("fedex_sp_base_rate_total"),

        # FedEx (best of HD vs SP)
        pl.col("fedex_cost_total").sum().alias("fedex_cost_total"),
        pl.col("fedex_cost_total").mean().alias("fedex_cost_avg"),

        # FedEx HD vs SP breakdown
        pl.col("fedex_hd_cost_total").sum().alias("fedex_hd_cost_total"),
        pl.col("fedex_hd_cost_total").mean().alias("fedex_hd_cost_avg"),
        pl.col("fedex_sp_cost_total").sum().alias("fedex_sp_cost_total"),
        pl.col("fedex_sp_cost_total").mean().alias("fedex_sp_cost_avg"),
        (pl.col("fedex_service_selected") == "FXSP").sum().alias("fedex_sp_shipment_count"),
        (pl.col("fedex_service_selected") == "FXEHD").sum().alias("fedex_hd_shipment_count"),

        # P2P
        pl.col("p2p_cost_total").sum().alias("p2p_cost_total"),
        pl.col("p2p_cost_total").mean().alias("p2p_cost_avg"),

        # Maersk
        pl.col("maersk_cost_total").sum().alias("maersk_cost_total"),
        pl.col("maersk_cost_total").mean().alias("maersk_cost_avg"),
    ]

    df_agg = df.group_by(group_cols).agg(agg_exprs).sort(group_cols)

    print(f"\n    Aggregated: {df_agg.shape[0]:,} groups, {int(df_agg['shipment_count'].sum()):,} shipments")

    return df_agg, s1_baseline
