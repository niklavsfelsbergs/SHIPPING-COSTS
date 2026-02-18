"""
FedEx Earned Discount Adjustment

Adjusts FedEx costs to reflect a target earned discount tier, given that rate tables
have 18% earned discount baked in.

The FedEx discount structure is additive — both PP and earned are percentages
of the true undiscounted rate:

    baked_rate = undiscounted × (1 - PP - BAKED_EARNED) = undiscounted × 0.37
    target_rate = undiscounted × (1 - PP - target_earned)
    multiplier = (1 - PP - target_earned) / (1 - PP - BAKED_EARNED)

Examples:
    target_earned=0.00 → multiplier = 0.55/0.37 = 1.4865 (lose all earned discount)
    target_earned=0.16 → multiplier = 0.39/0.37 = 1.0541 (16% tier instead of 18%)
    target_earned=0.18 → multiplier = 1.0 (no change, verification mode)

Fuel (14%) is applied on base rate only, so per-shipment adjustment:

    delta = fedex_cost_base_rate × (multiplier - 1) × (1 + FUEL_RATE)
    new_fedex_cost_total = old_total + delta
"""

import polars as pl
from pathlib import Path

# Discount parameters
PP_DISCOUNT = 0.45       # Performance pricing (flat percentage)
BAKED_EARNED = 0.18      # Earned discount baked into rate tables
FUEL_RATE = 0.14         # From carriers/fedex/data/reference/fuel.py

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
COMBINED_DATASETS = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "combined_datasets"


def adjust_fedex_costs(df: pl.DataFrame, target_earned: float) -> pl.DataFrame:
    """Adjust FedEx costs on a shipment-level DataFrame to reflect a target earned discount.

    Args:
        df: Shipment-level DataFrame with fedex_cost_base_rate, fedex_cost_total,
            fedex_hd_cost_total, fedex_sp_cost_total, fedex_service_selected,
            cost_current_carrier, pcs_shipping_provider columns.
        target_earned: The target earned discount percentage (e.g., 0.16 for 16% tier,
            0.0 to remove all earned discount).

    Returns:
        DataFrame with adjusted FedEx costs. If target_earned == BAKED_EARNED (0.18),
        no adjustment is made.
    """
    baked_factor = 1 - PP_DISCOUNT - BAKED_EARNED   # 0.37
    target_factor = 1 - PP_DISCOUNT - target_earned  # e.g., 0.39 for 16%, 0.55 for 0%
    multiplier = target_factor / baked_factor

    print(f"\n    FedEx earned discount adjustment:")
    print(f"      Baked earned:   {BAKED_EARNED:.0%}")
    print(f"      Target earned:  {target_earned:.0%}")
    print(f"      Multiplier:     {multiplier:.4f}")

    if abs(multiplier - 1.0) < 1e-6:
        print(f"      No adjustment needed (target matches baked rate)")
        return df

    # Snapshot original FedEx totals
    old_fedex_total = float(df["fedex_cost_total"].sum())

    # Per-shipment adjustment: delta = base_rate × (multiplier - 1) × (1 + fuel_rate)
    delta_expr = pl.col("fedex_cost_base_rate") * (multiplier - 1) * (1 + FUEL_RATE)

    df = df.with_columns([
        (pl.col("fedex_cost_total") + delta_expr).alias("fedex_cost_total"),
        (pl.col("fedex_hd_cost_total") + delta_expr).alias("fedex_hd_cost_total"),
        (pl.col("fedex_sp_cost_total") + delta_expr).alias("fedex_sp_cost_total"),
    ])

    # Re-select service: SP if cheaper and weight <= 70, else HD
    df = df.with_columns(
        pl.when(
            (pl.col("fedex_sp_cost_total") < pl.col("fedex_hd_cost_total")) &
            (pl.col("weight_lbs") <= 70)
        )
        .then(pl.col("fedex_sp_cost_total"))
        .otherwise(pl.col("fedex_hd_cost_total"))
        .alias("fedex_cost_total")
    )

    # Re-select service type label
    df = df.with_columns(
        pl.when(
            (pl.col("fedex_sp_cost_total") < pl.col("fedex_hd_cost_total")) &
            (pl.col("weight_lbs") <= 70)
        )
        .then(pl.lit("FXSP"))
        .otherwise(pl.lit("FXEHD"))
        .alias("fedex_service_selected")
    )

    # Update cost_current_carrier for FedEx shipments
    df = df.with_columns(
        pl.when(pl.col("pcs_shipping_provider").str.contains("FX"))
        .then(pl.col("fedex_cost_total"))
        .otherwise(pl.col("cost_current_carrier"))
        .alias("cost_current_carrier")
    )

    # Print summary
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
