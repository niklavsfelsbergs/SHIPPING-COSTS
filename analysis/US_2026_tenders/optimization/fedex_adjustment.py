"""
FedEx Earned Discount Adjustment

When S4/S5 optimization reduces FedEx spend below $4.5M, the 18% earned discount
is lost. This module adjusts FedEx costs to reflect 0% earned discount.

The FedEx discount structure is additive — both PP and earned are percentages
of the true undiscounted rate:

    current_rate = undiscounted × (1 - PP - earned) = undiscounted × 0.37
    rate_without_earned = undiscounted × (1 - PP) = undiscounted × 0.55
    multiplier = 0.55 / 0.37 ≈ 1.4865

Fuel (14%) is applied on base rate only, so per-shipment adjustment:

    delta = fedex_cost_base_rate × (multiplier - 1) × (1 + FUEL_RATE)
    new_fedex_cost_total = old_total + delta
"""

import polars as pl
from pathlib import Path

# Discount parameters
PP_DISCOUNT = 0.45       # Performance pricing (flat percentage)
EARNED_DISCOUNT = 0.18   # Earned discount being removed
FUEL_RATE = 0.14         # From carriers/fedex/data/reference/fuel.py

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
COMBINED_DATASETS = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "combined_datasets"


def adjust_and_aggregate(earned_discount: float = EARNED_DISCOUNT) -> tuple[pl.DataFrame, float]:
    """Adjust FedEx costs for earned discount removal and return aggregated data.

    Args:
        earned_discount: The earned discount percentage to remove (default 0.18).
            Pass 0.0 for no adjustment (verification mode).

    Returns:
        Tuple of (aggregated DataFrame, adjusted S1 baseline cost).
        The aggregated DataFrame has the same schema as shipments_aggregated.parquet.
    """
    # Load shipment-level data
    input_path = COMBINED_DATASETS / "shipments_unified.parquet"
    print(f"    Loading: {input_path.name}")
    df = pl.read_parquet(input_path)
    print(f"    {df.shape[0]:,} shipments loaded")

    # Compute multiplier
    current_factor = 1 - PP_DISCOUNT - earned_discount   # 0.37 with defaults
    adjusted_factor = 1 - PP_DISCOUNT                     # 0.55
    multiplier = adjusted_factor / current_factor         # 1.4865 with defaults
    print(f"\n    FedEx adjustment:")
    print(f"      PP discount:      {PP_DISCOUNT:.0%}")
    print(f"      Earned discount:  {earned_discount:.0%} (being removed)")
    print(f"      Current factor:   {current_factor:.4f}")
    print(f"      Adjusted factor:  {adjusted_factor:.4f}")
    print(f"      Multiplier:       {multiplier:.4f}")

    # Snapshot original FedEx totals
    old_fedex_total = float(df["fedex_cost_total"].sum())
    old_fedex_hd_total = float(df["fedex_hd_cost_total"].sum())
    old_fedex_sp_total = float(df["fedex_sp_cost_total"].sum())

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
