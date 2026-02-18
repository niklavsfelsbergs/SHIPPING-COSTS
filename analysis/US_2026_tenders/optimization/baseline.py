"""
Shared helpers for computing the Scenario 1 baseline consistently.
"""

from pathlib import Path

import polars as pl

from analysis.US_2026_tenders.optimization.fedex_adjustment import adjust_fedex_costs, BAKED_EARNED


PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
COMBINED_DATASETS = PROJECT_ROOT / "analysis" / "US_2026_tenders" / "combined_datasets"

# DHL estimated cost per shipment (no calculator available)
DHL_ESTIMATED_COST = 6.00


def apply_s1_adjustments(df: pl.DataFrame, target_earned: float = 0.16) -> pl.DataFrame:
    """Apply the Scenario 1 baseline adjustments to a unified shipment DataFrame."""
    # Adjust FedEx costs to target earned discount tier
    if target_earned != BAKED_EARNED:
        df = adjust_fedex_costs(df, target_earned=target_earned)

    # Apply DHL flat estimate
    df = df.with_columns(
        pl.when(pl.col("pcs_shipping_provider").str.contains("DHL"))
        .then(pl.lit(DHL_ESTIMATED_COST))
        .otherwise(pl.col("cost_current_carrier"))
        .alias("cost_current_carrier")
    )

    # Impute OnTrac null costs (if any remain)
    ontrac_null_count = df.filter(
        (pl.col("pcs_shipping_provider") == "ONTRAC") &
        (pl.col("cost_current_carrier").is_null())
    ).height

    if ontrac_null_count > 0:
        ontrac_avg_by_pkg = df.filter(
            (pl.col("pcs_shipping_provider") == "ONTRAC") &
            (pl.col("cost_current_carrier").is_not_null())
        ).group_by("packagetype").agg(
            pl.col("cost_current_carrier").mean().alias("_ontrac_avg_cost")
        )

        df = df.join(ontrac_avg_by_pkg, on="packagetype", how="left")
        df = df.with_columns(
            pl.when(
                (pl.col("pcs_shipping_provider") == "ONTRAC") &
                (pl.col("cost_current_carrier").is_null())
            )
            .then(pl.col("_ontrac_avg_cost"))
            .otherwise(pl.col("cost_current_carrier"))
            .alias("cost_current_carrier")
        ).drop("_ontrac_avg_cost")

    return df


def compute_s1_baseline(target_earned: float = 0.16) -> float:
    """Compute the Scenario 1 baseline cost using unified shipments."""
    df = pl.read_parquet(COMBINED_DATASETS / "shipments_unified.parquet")
    df = apply_s1_adjustments(df, target_earned=target_earned)
    return float(df["cost_current_carrier"].sum())
