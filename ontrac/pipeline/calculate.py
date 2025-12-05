"""
Calculate Shipping Costs

Main orchestrator that applies surcharges and calculates costs.
"""

import polars as pl

from ..surcharges import (
    ALL,
    INDEPENDENT_UNGROUPED,
    INDEPENDENT_GROUPED,
    DEPENDENT_UNGROUPED,
    DEPENDENT_GROUPED,
    get_by_priority_group,
    get_unique_priority_groups,
)
from .load_inputs import load_rates
from ..data.fuel import RATE as FUEL_RATE
from ..version import VERSION


def calculate(df: pl.DataFrame) -> pl.DataFrame:
    """
    Calculate shipping costs for supplemented shipments.

    Args:
        df: Supplemented shipment DataFrame from supplement_shipments

    Returns:
        DataFrame with surcharge costs

    Processing order:
        1. INDEPENDENT_UNGROUPED  - no dependency, no priority group (e.g., RES)
        2. INDEPENDENT_GROUPED    - no dependency, has priority group (e.g., OML/LPS/AHS, EDAS/DAS)
        3. DEPENDENT_UNGROUPED    - has dependency, no priority group (e.g., DEM_*)
        4. DEPENDENT_GROUPED      - has dependency, has priority group (none currently)
    """
    # Step 1: Apply independent surcharges (no dependencies)
    df = _apply_surcharges_ungrouped(df, INDEPENDENT_UNGROUPED)
    df = _apply_surcharges_grouped(df, INDEPENDENT_GROUPED)

    # Step 2: Apply dependent surcharges (reference base surcharge flags)
    df = _apply_surcharges_ungrouped(df, DEPENDENT_UNGROUPED)
    df = _apply_surcharges_grouped(df, DEPENDENT_GROUPED)

    # Step 3: Adjust billable weight based on min_billable_weight
    df = _apply_min_billable_weights(df)

    # Step 4: Look up base rate
    df = _lookup_base_rate(df)

    # Step 5: Calculate costs
    df = _calculate_subtotal(df)
    df = _apply_fuel(df)
    df = _calculate_total(df)

    # Step 6: Stamp version
    df = _stamp_version(df)

    return df


def _apply_single_surcharge(df: pl.DataFrame, surcharge) -> pl.DataFrame:
    """
    Apply a single surcharge without mutual exclusivity.

    Adds flag and cost columns for the surcharge.
    """
    flag_col = f"surcharge_{surcharge.name.lower()}"
    cost_col = f"cost_{surcharge.name.lower()}"

    # Add flag column first
    df = df.with_columns(surcharge.conditions().alias(flag_col))

    # Add cost column referencing the flag
    df = df.with_columns(
        pl.when(pl.col(flag_col))
        .then(pl.lit(surcharge.cost()))
        .otherwise(pl.lit(0.0))
        .alias(cost_col)
    )

    return df


def _apply_surcharges_ungrouped(df: pl.DataFrame, surcharges: list) -> pl.DataFrame:
    """
    Apply surcharges without mutual exclusivity.

    Each surcharge is evaluated independently.
    """
    for surcharge in surcharges:
        df = _apply_single_surcharge(df, surcharge)
    return df


def _apply_surcharges_grouped(df: pl.DataFrame, surcharges: list) -> pl.DataFrame:
    """
    Apply surcharges with mutual exclusivity within priority groups.

    Within each priority group, only the highest priority surcharge applies.
    Surcharges are processed in priority order (lowest number = highest priority).
    """
    for group_name in get_unique_priority_groups(surcharges):
        group = get_by_priority_group(group_name)
        exclusion_mask = pl.lit(False)

        for surcharge in group:
            flag_col = f"surcharge_{surcharge.name.lower()}"
            cost_col = f"cost_{surcharge.name.lower()}"

            # Applies only if condition is true AND no higher priority already matched
            applies = surcharge.conditions() & ~exclusion_mask

            df = df.with_columns(applies.alias(flag_col))
            df = df.with_columns(
                pl.when(pl.col(flag_col))
                .then(pl.lit(surcharge.cost()))
                .otherwise(pl.lit(0.0))
                .alias(cost_col)
            )

            # Update exclusion mask for next iteration
            exclusion_mask = exclusion_mask | pl.col(flag_col)

    return df


def _apply_min_billable_weights(df: pl.DataFrame) -> pl.DataFrame:
    """
    Apply minimum billable weights from triggered surcharges.

    Surcharges like OML, LPS, AHS have minimum billable weights.
    When triggered, billable_weight_lbs is raised to at least the minimum.
    """
    surcharges_with_min = [s for s in ALL if s.min_billable_weight is not None]

    if not surcharges_with_min:
        return df

    # Sort by min_billable_weight descending (highest first)
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


def _lookup_base_rate(df: pl.DataFrame) -> pl.DataFrame:
    """
    Look up base rate by joining on zone and weight bracket.

    Raises:
        ValueError: If any shipments have no matching rate bracket.
    """
    input_count = len(df)
    rates = load_rates()

    # Ensure shipping_zone is Int64 for join
    df = df.with_columns(pl.col("shipping_zone").cast(pl.Int64))

    # Add row index to preserve order after join
    df = df.with_row_index("_row_id")

    # Join on zone and filter by weight bracket
    df = (
        df
        .join(rates, left_on="shipping_zone", right_on="zone", how="left")
        .filter(
            (pl.col("billable_weight_lbs") > pl.col("weight_lbs_lower")) &
            (pl.col("billable_weight_lbs") <= pl.col("weight_lbs_upper"))
        )
        .rename({"rate": "cost_base"})
    )

    # Check for missing rates
    output_count = len(df)
    if output_count < input_count:
        missing_count = input_count - output_count
        raise ValueError(
            f"{missing_count} shipment(s) have no matching rate bracket. "
            f"Check shipping_zone and billable_weight_lbs values."
        )

    # Clean up and restore order
    df = df.drop(["weight_lbs_lower", "weight_lbs_upper"])
    df = df.sort("_row_id").drop("_row_id")

    return df


def _calculate_subtotal(df: pl.DataFrame) -> pl.DataFrame:
    """
    Calculate cost_subtotal as sum of base rate and all surcharge costs.
    """
    cost_cols = ["cost_base"] + [f"cost_{s.name.lower()}" for s in ALL]

    return df.with_columns(
        pl.sum_horizontal(cost_cols).alias("cost_subtotal")
    )


def _apply_fuel(df: pl.DataFrame) -> pl.DataFrame:
    """
    Apply fuel surcharge as percentage of subtotal.
    """
    return df.with_columns(
        (pl.col("cost_subtotal") * pl.lit(FUEL_RATE)).alias("cost_fuel")
    )


def _calculate_total(df: pl.DataFrame) -> pl.DataFrame:
    """
    Calculate cost_total as subtotal plus fuel.
    """
    return df.with_columns(
        (pl.col("cost_subtotal") + pl.col("cost_fuel")).alias("cost_total")
    )


def _stamp_version(df: pl.DataFrame) -> pl.DataFrame:
    """
    Stamp calculator version on output.
    """
    return df.with_columns(
        pl.lit(VERSION).alias("calculator_version")
    )
