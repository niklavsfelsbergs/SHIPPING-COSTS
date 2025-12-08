"""
OnTrac Shipping Cost Calculator

DataFrame in, DataFrame out. The input can come from any source (PCS database,
CSV, manual creation) as long as it contains the required columns. The output
is the same DataFrame with calculation columns and costs appended.

REQUIRED INPUT COLUMNS
----------------------
    ship_date           - Date for demand period checks
    production_site     - "Phoenix" or "Columbus" (determines zone)
    shipping_zip_code   - Destination ZIP (5-digit)
    shipping_region     - State name (fallback for zone lookup)
    length_in           - Package length in inches
    width_in            - Package width in inches
    height_in           - Package height in inches
    weight_lbs          - Actual weight in pounds

OUTPUT COLUMNS ADDED
--------------------
    supplement_shipments() adds:
        - cubic_in, longest_side_in, second_longest_in, length_plus_girth
        - shipping_zone, das_zone
        - dim_weight_lbs, uses_dim_weight, billable_weight_lbs

    calculate() adds:
        - surcharge_* flags (oml, lps, ahs, das, edas, res, dem_*)
        - cost_* amounts (base, oml, lps, ahs, das, edas, res, dem_*, subtotal, fuel, total)
        - calculator_version

USAGE
-----
    from ontrac.calculate_costs import calculate_costs
    result = calculate_costs(df)
"""

import polars as pl

from .data import (
    load_rates,
    load_zones,
    FUEL_RATE,
    DIM_FACTOR,
    DIM_THRESHOLD,
    THRESHOLD_FIELD,
    FACTOR_FIELD,
)
from .surcharges import (
    ALL,
    BASE,
    DEPENDENT,
    get_exclusivity_group,
    get_unique_exclusivity_groups,
)
from .version import VERSION


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def calculate_costs(
    df: pl.DataFrame,
    zones: pl.DataFrame | None = None
) -> pl.DataFrame:
    """
    Calculate shipping costs for a shipment DataFrame.

    This is the main entry point. Takes raw shipment data and returns
    the same DataFrame with all calculation columns and costs appended.

    Args:
        df: Raw shipment DataFrame with required columns (see module docstring)
        zones: Zone mapping DataFrame (loaded from zones.csv if not provided)

    Returns:
        DataFrame with supplemented data, surcharge flags, and costs
    """
    df = supplement_shipments(df, zones)
    df = calculate(df)
    return df


# =============================================================================
# SUPPLEMENT SHIPMENTS
# =============================================================================

def supplement_shipments(
    df: pl.DataFrame,
    zones: pl.DataFrame | None = None
) -> pl.DataFrame:
    """
    Supplement shipment data with zone and weight calculations.

    Args:
        df: Raw shipment DataFrame
        zones: Zone mapping DataFrame (loaded if not provided)

    Returns:
        DataFrame with added columns:
            - cubic_in, longest_side_in, second_longest_in, length_plus_girth
            - shipping_zone, das_zone
            - dim_weight_lbs, uses_dim_weight, billable_weight_lbs
    """
    if zones is None:
        zones = load_zones()

    df = _add_calculated_dimensions(df)
    df = _lookup_zones(df, zones)
    df = _add_billable_weight(df)

    return df


def _add_calculated_dimensions(df: pl.DataFrame) -> pl.DataFrame:
    """Add calculated dimensional columns."""
    return df.with_columns([
        # Cubic inches
        (pl.col("length_in") * pl.col("width_in") * pl.col("height_in"))
        .alias("cubic_in"),

        # Longest dimension
        pl.max_horizontal("length_in", "width_in", "height_in")
        .alias("longest_side_in"),

        # Second longest dimension
        pl.concat_list(["length_in", "width_in", "height_in"])
        .list.sort(descending=True)
        .list.get(1)
        .alias("second_longest_in"),

        # Length + Girth (longest + 2 * sum of other two)
        (
            pl.max_horizontal("length_in", "width_in", "height_in") +
            2 * (
                pl.col("length_in") + pl.col("width_in") + pl.col("height_in") -
                pl.max_horizontal("length_in", "width_in", "height_in")
            )
        ).alias("length_plus_girth"),
    ])


def _lookup_zones(df: pl.DataFrame, zones: pl.DataFrame) -> pl.DataFrame:
    """
    Add zone data to shipments based on shipping ZIP code.

    ORIGIN-DEPENDENT ZONES
    ----------------------
    The same destination ZIP has different zones depending on origin.
    zones.csv contains phx_zone and cmh_zone columns - we select based
    on the production_site field (Phoenix or Columbus).

    THREE-TIER FALLBACK
    -------------------
    1. Exact ZIP code match from zones.csv
    2. State-level mode (most common zone for that state)
    3. Default zone 5 (mid-range, minimizes worst-case pricing error)
    """
    # Normalize ZIP code to 5 digits with leading zeros
    df = df.with_columns(
        pl.col("shipping_zip_code")
        .cast(pl.Utf8)
        .str.slice(0, 5)
        .str.zfill(5)
        .alias("_zip_normalized")
    )

    zones_subset = zones.select(["zip_code", "das", "shipping_state", "phx_zone", "cmh_zone"])

    # State-level fallback (mode zone per state)
    state_zones = (
        zones
        .group_by("shipping_state")
        .agg([
            pl.col("phx_zone").mode().first().alias("_state_phx_zone"),
            pl.col("cmh_zone").mode().first().alias("_state_cmh_zone"),
            pl.lit("NO").alias("_state_das"),
        ])
    )

    # Join on ZIP code
    df = df.join(zones_subset, left_on="_zip_normalized", right_on="zip_code", how="left")

    # Join state fallback
    df = df.join(state_zones, left_on="shipping_region", right_on="shipping_state", how="left")

    # Coalesce: ZIP zone -> state zone -> default zone 5
    df = df.with_columns([
        pl.coalesce(["phx_zone", "_state_phx_zone", pl.lit(5)]).alias("_phx_zone_final"),
        pl.coalesce(["cmh_zone", "_state_cmh_zone", pl.lit(5)]).alias("_cmh_zone_final"),
        pl.coalesce(["das", "_state_das"]).alias("das_zone"),
    ])

    # Select zone based on production site
    df = df.with_columns(
        pl.when(pl.col("production_site") == "Phoenix")
        .then(pl.col("_phx_zone_final"))
        .when(pl.col("production_site") == "Columbus")
        .then(pl.col("_cmh_zone_final"))
        .otherwise(pl.lit(5))
        .alias("shipping_zone")
    )

    # Drop intermediate columns
    df = df.drop([
        "_zip_normalized",
        "phx_zone", "cmh_zone",
        "_state_phx_zone", "_state_cmh_zone", "_state_das",
        "_phx_zone_final", "_cmh_zone_final",
        "shipping_state",
    ])

    return df


def _add_billable_weight(df: pl.DataFrame) -> pl.DataFrame:
    """
    Calculate dimensional weight and billable weight.

    Billable weight is the greater of actual weight and dimensional weight,
    but only when the threshold field exceeds DIM_THRESHOLD.
    """
    # Calculate dimensional weight
    df = df.with_columns(
        (pl.col(FACTOR_FIELD) / DIM_FACTOR).alias("dim_weight_lbs")
    )

    # Determine if dim weight applies and calculate billable weight
    df = df.with_columns([
        pl.when(pl.col(THRESHOLD_FIELD) > DIM_THRESHOLD)
        .then(pl.col("dim_weight_lbs") > pl.col("weight_lbs"))
        .otherwise(False)
        .alias("uses_dim_weight"),

        pl.when(pl.col(THRESHOLD_FIELD) > DIM_THRESHOLD)
        .then(pl.max_horizontal("weight_lbs", "dim_weight_lbs"))
        .otherwise(pl.col("weight_lbs"))
        .alias("billable_weight_lbs"),
    ])

    return df


# =============================================================================
# CALCULATE COSTS
# =============================================================================

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


def _apply_min_billable_weights(df: pl.DataFrame) -> pl.DataFrame:
    """
    Apply minimum billable weights from triggered surcharges.

    Surcharges like OML, LPS, AHS enforce minimum billable weights.
    """
    surcharges_with_min = [s for s in ALL if s.min_billable_weight is not None]

    if not surcharges_with_min:
        return df

    # Sort by min_billable_weight descending (highest minimum first)
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
    """Look up base shipping rate by zone and weight bracket."""
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


__all__ = [
    "calculate_costs",
    "supplement_shipments",
    "calculate",
]
