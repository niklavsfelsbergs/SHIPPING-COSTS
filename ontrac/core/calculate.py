"""
Calculate Shipping Costs

Main orchestrator that applies surcharges and calculates costs.
"""

import polars as pl

from ..surcharges import (
    ALL,
    BASE,
    DEPENDENT,
    get_exclusivity_group,
    get_unique_exclusivity_groups,
)
from .inputs import load_rates, FUEL_RATE
from ..version import VERSION


def calculate(df: pl.DataFrame) -> pl.DataFrame:
    """
    Calculate shipping costs for supplemented shipments.

    Args:
        df: Supplemented shipment DataFrame from supplement_shipments

    Returns:
        DataFrame with surcharge flags, costs, and totals

    Processing order:
        1. BASE surcharges      - don't reference other surcharge flags
        2. DEPENDENT surcharges - reference flags from phase 1 (via depends_on)

    Within each phase, surcharges with the same exclusivity_group compete.
    Only the highest priority (lowest number) wins.
    """
    # Phase 1: Apply base surcharges (don't reference other surcharge flags)
    df = _apply_surcharges(df, BASE)

    # Phase 2: Apply dependent surcharges (reference flags from phase 1)
    df = _apply_surcharges(df, DEPENDENT)

    # Phase 3: Adjust billable weights based on triggered surcharges
    df = _apply_min_billable_weights(df)

    # Phase 4: Look up base shipping rate
    df = _lookup_base_rate(df)

    # Phase 5: Calculate costs
    df = _calculate_subtotal(df)
    df = _apply_fuel(df)
    df = _calculate_total(df)

    # Phase 6: Stamp version
    df = _stamp_version(df)

    return df


# =============================================================================
# SURCHARGE APPLICATION
# =============================================================================

def _apply_surcharges(df: pl.DataFrame, surcharges: list) -> pl.DataFrame:
    """
    Apply surcharges, handling mutual exclusivity within exclusivity groups.

    Surcharges with the same exclusivity_group compete - only highest priority wins.
    Surcharges without exclusivity_group are applied independently.
    """
    # Separate standalone vs exclusive surcharges
    standalone = [s for s in surcharges if s.exclusivity_group is None]
    exclusive = [s for s in surcharges if s.exclusivity_group is not None]

    # Apply standalone surcharges (no competition)
    for s in standalone:
        df = _apply_single_surcharge(df, s)

    # Apply exclusive surcharges by group
    for group_name in get_unique_exclusivity_groups(exclusive):
        df = _apply_exclusive_group(df, group_name)

    return df


def _apply_single_surcharge(df: pl.DataFrame, surcharge) -> pl.DataFrame:
    """Apply a single surcharge without competition."""
    flag_col = f"surcharge_{surcharge.name.lower()}"
    cost_col = f"cost_{surcharge.name.lower()}"

    df = df.with_columns(surcharge.conditions().alias(flag_col))
    df = df.with_columns(
        pl.when(pl.col(flag_col))
        .then(pl.lit(surcharge.cost()))
        .otherwise(pl.lit(0.0))
        .alias(cost_col)
    )

    return df


def _apply_exclusive_group(df: pl.DataFrame, group_name: str) -> pl.DataFrame:
    """
    Apply mutually exclusive surcharges within a group.

    Only the highest priority surcharge (lowest number) that matches wins.
    Once one matches, the rest are excluded.
    """
    group = get_exclusivity_group(group_name)
    exclusion_mask = pl.lit(False)

    for surcharge in group:
        flag_col = f"surcharge_{surcharge.name.lower()}"
        cost_col = f"cost_{surcharge.name.lower()}"

        # Applies only if: conditions met AND no higher priority already matched
        applies = surcharge.conditions() & ~exclusion_mask

        df = df.with_columns(applies.alias(flag_col))
        df = df.with_columns(
            pl.when(pl.col(flag_col))
            .then(pl.lit(surcharge.cost()))
            .otherwise(pl.lit(0.0))
            .alias(cost_col)
        )

        # Update exclusion mask: if this one matched, exclude the rest
        exclusion_mask = exclusion_mask | pl.col(flag_col)

    return df


# =============================================================================
# BILLABLE WEIGHT ADJUSTMENT
# =============================================================================

def _apply_min_billable_weights(df: pl.DataFrame) -> pl.DataFrame:
    """
    Apply minimum billable weights from triggered surcharges.

    Surcharges like OML, LPS, AHS enforce minimum billable weights.
    When triggered, billable_weight_lbs is raised to at least the minimum.
    """
    surcharges_with_min = [s for s in ALL if s.min_billable_weight is not None]

    if not surcharges_with_min:
        return df

    # Sort by min_billable_weight descending (highest minimum first)
    # This ensures the highest applicable minimum wins
    surcharges_with_min.sort(key=lambda s: s.min_billable_weight, reverse=True)

    # Build chained when/then expression
    expr = pl.col("billable_weight_lbs")
    for surcharge in surcharges_with_min:
        flag_col = f"surcharge_{surcharge.name.lower()}"
        expr = (
            pl.when(pl.col(flag_col))
            .then(pl.max_horizontal("billable_weight_lbs", pl.lit(surcharge.min_billable_weight)))
            .otherwise(expr)
        )

    return df.with_columns(expr.alias("billable_weight_lbs"))


# =============================================================================
# RATE LOOKUP
# =============================================================================

def _lookup_base_rate(df: pl.DataFrame) -> pl.DataFrame:
    """
    Look up base shipping rate by zone and weight bracket.

    Raises:
        ValueError: If any shipments have no matching rate bracket.
    """
    input_count = len(df)
    rates = load_rates()

    df = df.with_columns(pl.col("shipping_zone").cast(pl.Int64))
    df = df.with_row_index("_row_id")

    df = (
        df
        .join(rates, left_on="shipping_zone", right_on="zone", how="left")
        .filter(
            (pl.col("billable_weight_lbs") > pl.col("weight_lbs_lower")) &
            (pl.col("billable_weight_lbs") <= pl.col("weight_lbs_upper"))
        )
        .rename({"rate": "cost_base"})
    )

    output_count = len(df)
    if output_count < input_count:
        missing_count = input_count - output_count
        raise ValueError(
            f"{missing_count} shipment(s) have no matching rate bracket. "
            f"Check shipping_zone and billable_weight_lbs values."
        )

    df = df.drop(["weight_lbs_lower", "weight_lbs_upper"])
    df = df.sort("_row_id").drop("_row_id")

    return df


# =============================================================================
# COST CALCULATION
# =============================================================================

def _calculate_subtotal(df: pl.DataFrame) -> pl.DataFrame:
    """Calculate cost_subtotal as sum of base rate and all surcharge costs."""
    cost_cols = ["cost_base"] + [f"cost_{s.name.lower()}" for s in ALL]
    return df.with_columns(pl.sum_horizontal(cost_cols).alias("cost_subtotal"))


def _apply_fuel(df: pl.DataFrame) -> pl.DataFrame:
    """Apply fuel surcharge as percentage of subtotal."""
    return df.with_columns(
        (pl.col("cost_subtotal") * pl.lit(FUEL_RATE)).alias("cost_fuel")
    )


def _calculate_total(df: pl.DataFrame) -> pl.DataFrame:
    """Calculate cost_total as subtotal plus fuel."""
    return df.with_columns(
        (pl.col("cost_subtotal") + pl.col("cost_fuel")).alias("cost_total")
    )


def _stamp_version(df: pl.DataFrame) -> pl.DataFrame:
    """Stamp calculator version on output."""
    return df.with_columns(pl.lit(VERSION).alias("calculator_version"))
