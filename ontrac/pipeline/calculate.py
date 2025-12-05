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
    """
    # Step 1: Apply INDEPENDENT_UNGROUPED surcharges
    df = _apply_independent_ungrouped(df)

    # Step 2: Apply INDEPENDENT_GROUPED surcharges (with mutual exclusivity)
    df = _apply_independent_grouped(df)

    # Step 3: Apply DEPENDENT_UNGROUPED surcharges (reference base surcharge flags)
    df = _apply_dependent_ungrouped(df)

    # Step 4: Apply DEPENDENT_GROUPED surcharges (with mutual exclusivity)
    df = _apply_dependent_grouped(df)

    # Step 5: Adjust billable weight based on min_billable_weight
    df = _adjust_billable_weight(df)

    # Step 6: Look up base rate
    df = _lookup_base_rate(df)

    # Step 7: Calculate subtotal
    df = _calculate_subtotal(df)

    # Step 8: Apply fuel surcharge
    df = _apply_fuel(df)

    # Step 9: Calculate total
    df = _calculate_total(df)

    # Step 10: Stamp version
    df = _stamp_version(df)

    return df


def _apply_independent_ungrouped(df: pl.DataFrame) -> pl.DataFrame:
    """
    Apply surcharges with no dependency and no priority group.

    These can be applied directly - no mutual exclusivity logic needed.
    OnTrac: [RES]
    """
    for surcharge in INDEPENDENT_UNGROUPED:
        flag_col = f"surcharge_{surcharge.name.lower()}"
        cost_col = f"cost_{surcharge.name.lower()}"

        df = df.with_columns([
            surcharge.conditions().alias(flag_col),
            pl.when(surcharge.conditions())
            .then(pl.lit(surcharge.cost()))
            .otherwise(pl.lit(0.0))
            .alias(cost_col)
        ])

    return df


def _apply_independent_grouped(df: pl.DataFrame) -> pl.DataFrame:
    """
    Apply surcharges with priority groups (mutual exclusivity).

    Within each priority group, only the highest priority surcharge applies.
    OnTrac groups: "dimensional" [OML, LPS, AHS], "delivery" [EDAS, DAS]
    """
    for group_name in get_unique_priority_groups(INDEPENDENT_GROUPED):
        # Get surcharges in this group, sorted by priority
        surcharges = get_by_priority_group(group_name)

        # Build exclusion mask as we go
        exclusion_mask = pl.lit(False)

        for surcharge in surcharges:
            flag_col = f"surcharge_{surcharge.name.lower()}"
            cost_col = f"cost_{surcharge.name.lower()}"

            # Applies only if condition is true AND no higher priority already matched
            applies = surcharge.conditions() & ~exclusion_mask

            df = df.with_columns([
                applies.alias(flag_col),
                pl.when(applies)
                .then(pl.lit(surcharge.cost()))
                .otherwise(pl.lit(0.0))
                .alias(cost_col)
            ])

            # Update exclusion mask using the flag column
            exclusion_mask = exclusion_mask | pl.col(flag_col)

    return df


def _apply_dependent_ungrouped(df: pl.DataFrame) -> pl.DataFrame:
    """
    Apply surcharges that depend on base surcharges (no priority group).

    These reference base surcharge flags in their conditions().
    OnTrac: [DEM_RES, DEM_AHS, DEM_LPS, DEM_OML]
    """
    for surcharge in DEPENDENT_UNGROUPED:
        flag_col = f"surcharge_{surcharge.name.lower()}"
        cost_col = f"cost_{surcharge.name.lower()}"

        df = df.with_columns([
            surcharge.conditions().alias(flag_col),
            pl.when(surcharge.conditions())
            .then(pl.lit(surcharge.cost()))
            .otherwise(pl.lit(0.0))
            .alias(cost_col)
        ])

    return df


def _apply_dependent_grouped(df: pl.DataFrame) -> pl.DataFrame:
    """
    Apply surcharges that depend on base surcharges (with priority group).

    These reference base surcharge flags and have mutual exclusivity.
    OnTrac: [] (none)
    """
    for group_name in get_unique_priority_groups(DEPENDENT_GROUPED):
        # Get surcharges in this group, sorted by priority
        surcharges = get_by_priority_group(group_name)

        # Build exclusion mask as we go
        exclusion_mask = pl.lit(False)

        for surcharge in surcharges:
            flag_col = f"surcharge_{surcharge.name.lower()}"
            cost_col = f"cost_{surcharge.name.lower()}"

            # Applies only if condition is true AND no higher priority already matched
            applies = surcharge.conditions() & ~exclusion_mask

            df = df.with_columns([
                applies.alias(flag_col),
                pl.when(applies)
                .then(pl.lit(surcharge.cost()))
                .otherwise(pl.lit(0.0))
                .alias(cost_col)
            ])

            # Update exclusion mask using the flag column
            exclusion_mask = exclusion_mask | pl.col(flag_col)

    return df


def _adjust_billable_weight(df: pl.DataFrame) -> pl.DataFrame:
    """
    Adjust billable weight based on min_billable_weight from triggered surcharges.

    Surcharges like OML, LPS, AHS have minimum billable weights that apply
    when the surcharge is triggered.
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
    Look up base rate from rate table by zone and billable weight.

    Unpivots rate table from wide format (zone_2, zone_3, ...) to long format,
    then joins on shipping_zone and filters by weight bracket.
    """
    rates = load_rates()

    # Unpivot rates table: zone_2, zone_3, ... -> zone, base_rate
    zone_cols = [c for c in rates.columns if c.startswith("zone_")]

    rates_long = (
        rates
        .unpivot(
            index=["weight_lbs_lower", "weight_lbs_upper"],
            on=zone_cols,
            variable_name="_zone_col",
            value_name="cost_base"
        )
        .with_columns(
            pl.col("_zone_col").str.replace("zone_", "").cast(pl.Int64).alias("_zone")
        )
        .drop("_zone_col")
    )

    # Ensure shipping_zone is Int64 for join
    df = df.with_columns(pl.col("shipping_zone").cast(pl.Int64))

    # Add row index to preserve order after join
    df = df.with_row_index("_row_id")

    # Join on zone and filter by weight bracket
    df = (
        df
        .join(rates_long, left_on="shipping_zone", right_on="_zone", how="left")
        .filter(
            (pl.col("billable_weight_lbs") > pl.col("weight_lbs_lower")) &
            (pl.col("billable_weight_lbs") <= pl.col("weight_lbs_upper"))
        )
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
