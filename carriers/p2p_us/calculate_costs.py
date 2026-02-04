"""
P2P US Shipping Cost Calculator

DataFrame in, DataFrame out. The input can come from any source (PCS database,
CSV, manual creation) as long as it contains the required columns. The output
is the same DataFrame with calculation columns and costs appended.

REQUIRED INPUT COLUMNS
----------------------
    ship_date           - Date for rate lookups
    production_site     - Origin site (Columbus)
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
        - shipping_zone
        - dim_weight_lbs, uses_dim_weight, billable_weight_lbs

    calculate() adds:
        - surcharge_* flags (ahs, oversize)
        - cost_* amounts (base, ahs, oversize, subtotal, total)
        - calculator_version

USAGE
-----
    from carriers.p2p_us.calculate_costs import calculate_costs
    result = calculate_costs(df)
"""

import polars as pl

from .version import VERSION
from .data import (
    load_rates,
    load_zones,
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
from .surcharges.additional_handling import AHS


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
            - shipping_zone
            - dim_weight_lbs, uses_dim_weight, billable_weight_lbs
    """
    if zones is None:
        zones = load_zones()

    df = _add_calculated_dimensions(df)
    df = _lookup_zones(df, zones)
    df = _add_billable_weight(df)

    return df


def _add_calculated_dimensions(df: pl.DataFrame) -> pl.DataFrame:
    """Add calculated dimensional columns.

    Note: Dimensions are rounded to 1 decimal place to avoid floating point
    precision issues when comparing against surcharge thresholds.
    """
    return df.with_columns([
        # Cubic inches (rounded to whole number)
        (pl.col("length_in") * pl.col("width_in") * pl.col("height_in"))
        .round(0)
        .alias("cubic_in"),

        # Longest dimension (rounded to 1 decimal)
        pl.max_horizontal("length_in", "width_in", "height_in")
        .round(1)
        .alias("longest_side_in"),

        # Second longest dimension (rounded to 1 decimal)
        pl.concat_list(["length_in", "width_in", "height_in"])
        .list.sort(descending=True)
        .list.get(1)
        .round(1)
        .alias("second_longest_in"),

        # Length + Girth (longest + 2 * sum of other two, rounded to 1 decimal)
        (
            pl.max_horizontal("length_in", "width_in", "height_in") +
            2 * (
                pl.col("length_in") + pl.col("width_in") + pl.col("height_in") -
                pl.max_horizontal("length_in", "width_in", "height_in")
            )
        ).round(1).alias("length_plus_girth"),
    ])


def _lookup_zones(df: pl.DataFrame, zones: pl.DataFrame) -> pl.DataFrame:
    """
    Add zone data to shipments based on 5-digit ZIP.

    P2P US uses 5-digit ZIP for zone lookup.

    THREE-TIER FALLBACK
    -------------------
    1. Exact 5-digit ZIP match from zones.csv
    2. Mode zone across all entries (most common zone)
    3. Default zone 5 (mid-range, minimizes worst-case pricing error)
    """
    # Normalize ZIP to 5-digit string
    df = df.with_columns(
        pl.col("shipping_zip_code")
        .cast(pl.Utf8)
        .str.slice(0, 5)
        .str.zfill(5)
        .alias("_zip_5digit")
    )

    # Calculate mode zone for fallback
    mode_zone = (
        zones
        .select(pl.col("zone").mode().first())
        .item()
    )

    # Join on 5-digit ZIP
    df = df.join(zones, left_on="_zip_5digit", right_on="zip", how="left")

    # Flag whether ZIP was found in zones file (for coverage tracking)
    df = df.with_columns(
        pl.col("zone").is_not_null().alias("zone_covered")
    )

    # Apply fallback: use mode zone if no match, then default to 5
    df = df.with_columns(
        pl.coalesce([pl.col("zone"), pl.lit(mode_zone), pl.lit(5)])
        .alias("shipping_zone")
    )

    # Drop intermediate columns
    df = df.drop(["_zip_5digit", "zone"])

    return df


def _add_billable_weight(df: pl.DataFrame) -> pl.DataFrame:
    """
    Calculate dimensional weight and billable weight.

    P2P US always compares actual vs dimensional weight (no threshold).
    Billable weight is the greater of the two.
    """
    # Calculate dimensional weight
    df = df.with_columns(
        (pl.col(FACTOR_FIELD) / DIM_FACTOR).alias("dim_weight_lbs")
    )

    # Always compare actual vs dim weight (threshold is 0)
    df = df.with_columns([
        (pl.col("dim_weight_lbs") > pl.col("weight_lbs")).alias("uses_dim_weight"),
        pl.max_horizontal("weight_lbs", "dim_weight_lbs").alias("billable_weight_lbs"),
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
        1. Check AHS dimensional conditions (for min billable weight)
        2. Apply min billable weight BEFORE rate lookup
        3. BASE surcharges      - apply surcharge flags and costs
        4. DEPENDENT surcharges - reference flags from phase 1 (via depends_on)
        5. Rate lookup          - base shipping rate by zone and weight
        6. Totals               - sum up all costs
    """
    # Phase 1: Check AHS dimensional conditions and apply min billable weight
    # This must happen BEFORE rate lookup
    df = _apply_ahs_min_billable_weight(df)

    # Phase 2: Apply base surcharges (don't reference other surcharge flags)
    df = _apply_surcharges(df, BASE)

    # Phase 3: Apply dependent surcharges (reference flags from phase 1)
    # Note: P2P US has no dependent surcharges currently
    df = _apply_surcharges(df, DEPENDENT)

    # Phase 4: Look up base shipping rate
    df = _lookup_base_rate(df)

    # Phase 5: Calculate totals (no fuel for P2P US)
    df = _calculate_subtotal(df)
    df = _calculate_total(df)

    # Phase 6: Stamp version
    df = _stamp_version(df)

    return df


def _apply_ahs_min_billable_weight(df: pl.DataFrame) -> pl.DataFrame:
    """
    Apply AHS minimum billable weight side effect for dimensional conditions.

    When AHS triggers due to dimensional conditions (longest >48", second >30",
    or L+G >105"), enforce 30 lb minimum billable weight BEFORE rate lookup.
    """
    # Check if AHS dimensional conditions are met
    # (not the weight condition - that doesn't trigger the minimum)
    dimensional_trigger = AHS.dimensional_conditions()

    df = df.with_columns(
        pl.when(dimensional_trigger)
        .then(pl.max_horizontal("billable_weight_lbs", pl.lit(AHS.min_billable_weight)))
        .otherwise(pl.col("billable_weight_lbs"))
        .alias("billable_weight_lbs")
    )

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

    # Handle both fixed cost and expression-based cost
    cost_expr = surcharge.cost()
    if isinstance(cost_expr, pl.Expr):
        df = df.with_columns(
            pl.when(pl.col(flag_col))
            .then(cost_expr)
            .otherwise(pl.lit(0.0))
            .alias(cost_col)
        )
    else:
        df = df.with_columns(
            pl.when(pl.col(flag_col))
            .then(pl.lit(cost_expr))
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

        # Handle both fixed cost and expression-based cost
        cost_expr = surcharge.cost()
        if isinstance(cost_expr, pl.Expr):
            df = df.with_columns(
                pl.when(pl.col(flag_col))
                .then(cost_expr)
                .otherwise(pl.lit(0.0))
                .alias(cost_col)
            )
        else:
            df = df.with_columns(
                pl.when(pl.col(flag_col))
                .then(pl.lit(cost_expr))
                .otherwise(pl.lit(0.0))
                .alias(cost_col)
            )

        # Update exclusion mask: if this one matched, exclude the rest
        exclusion_mask = exclusion_mask | pl.col(flag_col)

    return df


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
            f"Check shipping_zone and billable_weight_lbs values. "
            f"P2P US max weight is 50 lbs."
        )

    df = df.drop(["weight_lbs_lower", "weight_lbs_upper"])
    df = df.sort("_row_id").drop("_row_id")

    return df


def _calculate_subtotal(df: pl.DataFrame) -> pl.DataFrame:
    """Calculate cost_subtotal as sum of base rate and surcharges."""
    cost_cols = ["cost_base"] + [f"cost_{s.name.lower()}" for s in ALL]
    return df.with_columns(pl.sum_horizontal(cost_cols).alias("cost_subtotal"))


def _calculate_total(df: pl.DataFrame) -> pl.DataFrame:
    """Calculate cost_total (same as subtotal for P2P US - no fuel surcharge)."""
    return df.with_columns(
        pl.col("cost_subtotal").alias("cost_total")
    )


def _stamp_version(df: pl.DataFrame) -> pl.DataFrame:
    """Stamp calculator version on output."""
    return df.with_columns(pl.lit(VERSION).alias("calculator_version"))


__all__ = [
    "calculate_costs",
    "supplement_shipments",
    "calculate",
]
