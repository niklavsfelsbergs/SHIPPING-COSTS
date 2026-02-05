"""
USPS Shipping Cost Calculator

DataFrame in, DataFrame out. The input can come from any source (PCS database,
CSV, manual creation) as long as it contains the required columns. The output
is the same DataFrame with calculation columns and costs appended.

REQUIRED INPUT COLUMNS
----------------------
    ship_date           - Date for rate lookups
    production_site     - Origin site (determines zone)
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
        - shipping_zone, rate_zone (asterisk stripped for lookup)
        - dim_weight_lbs, uses_dim_weight, billable_weight_lbs

    calculate() adds:
        - surcharge_* flags (nsl1, nsl2, nsv, peak)
        - cost_* amounts (base, nsl1, nsl2, nsv, peak, subtotal, total)
        - calculator_version

USAGE
-----
    from carriers.usps.calculate_costs import calculate_costs
    result = calculate_costs(df)
"""

import polars as pl

from .version import VERSION
from .data import (
    load_rates,
    load_zones,
    load_oversize_rates,
    DIM_FACTOR,
    DIM_THRESHOLD,
    THRESHOLD_FIELD,
    FACTOR_FIELD,
    OVERSIZE_GIRTH_THRESHOLD,
)
from .surcharges import (
    ALL,
    BASE,
    DEPENDENT,
    get_exclusivity_group,
    get_unique_exclusivity_groups,
    peak_season_condition,
    peak_surcharge_amount,
)


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
            - shipping_zone, rate_zone
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
    Add zone data to shipments based on 3-digit ZIP prefix.

    ORIGIN-DEPENDENT ZONES
    ----------------------
    The same destination ZIP has different zones depending on origin.
    zones.csv contains phx_zone and cmh_zone columns - we select based
    on the production_site field (Phoenix or Columbus).

    ASTERISK ZONES
    --------------
    Some zones have asterisk variants (1*, 2*, 3*) indicating local delivery.
    We store shipping_zone with the asterisk for reference, and rate_zone
    with the asterisk stripped for rate table lookup.

    THREE-TIER FALLBACK
    -------------------
    1. Exact 3-digit ZIP prefix match from zones.csv
    2. State-level mode (most common zone for that state)
    3. Default zone 5 (mid-range, minimizes worst-case pricing error)
    """
    # Extract 3-digit ZIP prefix
    df = df.with_columns(
        pl.col("shipping_zip_code")
        .cast(pl.Utf8)
        .str.slice(0, 3)
        .str.zfill(3)
        .alias("_zip_prefix")
    )

    zones_subset = zones.select(["zip_prefix", "phx_zone", "cmh_zone"])

    # State-level fallback (mode zone per state) - strip asterisks for mode calc
    state_zones = (
        zones
        .with_columns([
            pl.col("phx_zone").str.replace(r"\*", "").alias("_phx_base"),
            pl.col("cmh_zone").str.replace(r"\*", "").alias("_cmh_base"),
        ])
        .filter(
            (pl.col("_phx_base") != "") | (pl.col("_cmh_base") != "")
        )
    )

    # For state mode, we need to derive state from ZIP prefix
    # Since we don't have explicit state mapping, use zone mode across all valid entries
    # For simplicity, just calculate overall mode for fallback
    phx_mode = (
        state_zones
        .filter(pl.col("_phx_base") != "")
        .select(pl.col("_phx_base").mode().first())
        .item()
    )
    cmh_mode = (
        state_zones
        .filter(pl.col("_cmh_base") != "")
        .select(pl.col("_cmh_base").mode().first())
        .item()
    )

    # Join on ZIP prefix
    df = df.join(zones_subset, left_on="_zip_prefix", right_on="zip_prefix", how="left")

    # Select zone based on production site, coalesce with fallback
    df = df.with_columns([
        pl.when(pl.col("production_site") == "Phoenix")
        .then(pl.coalesce([pl.col("phx_zone"), pl.lit(phx_mode), pl.lit("5")]))
        .when(pl.col("production_site") == "Columbus")
        .then(pl.coalesce([pl.col("cmh_zone"), pl.lit(cmh_mode), pl.lit("5")]))
        .otherwise(pl.lit("5"))
        .alias("shipping_zone")
    ])

    # Create rate_zone by stripping asterisk
    df = df.with_columns(
        pl.col("shipping_zone")
        .str.replace(r"\*", "")
        .cast(pl.Int64)
        .alias("rate_zone")
    )

    # Drop intermediate columns
    df = df.drop(["_zip_prefix", "phx_zone", "cmh_zone"])

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
        3. Peak surcharge       - date-based seasonal surcharge
    """
    # Phase 1: Apply base surcharges (don't reference other surcharge flags)
    df = _apply_surcharges(df, BASE)

    # Phase 2: Apply dependent surcharges (reference flags from phase 1)
    # Note: USPS has no dependent surcharges currently
    df = _apply_surcharges(df, DEPENDENT)

    # Phase 3: Look up base shipping rate
    df = _lookup_base_rate(df)

    # Phase 3b: Apply oversize rate override (replaces base rate if girth > 108")
    df = _apply_oversize_rate(df)

    # Phase 4: Apply peak season surcharge (requires billable_weight_lbs and rate_zone)
    df = _apply_peak_surcharge(df)

    # Phase 5: Calculate costs (no fuel for USPS)
    df = _calculate_subtotal(df)
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


def _lookup_base_rate(df: pl.DataFrame) -> pl.DataFrame:
    """Look up base shipping rate by zone and weight bracket."""
    input_count = len(df)
    rates = load_rates()

    df = df.with_row_index("_row_id")

    df = (
        df
        .join(rates, left_on="rate_zone", right_on="zone", how="left")
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
            f"Check rate_zone and billable_weight_lbs values. "
            f"USPS Ground Advantage max weight is 20 lbs."
        )

    df = df.drop(["weight_lbs_lower", "weight_lbs_upper"])
    df = df.sort("_row_id").drop("_row_id")

    return df


def _apply_oversize_rate(df: pl.DataFrame) -> pl.DataFrame:
    """
    Apply oversize rate for packages exceeding girth threshold.

    When length + girth > 108", the normal weight-based rate is replaced
    with a flat zone-based oversize rate.

    Adds column:
        - surcharge_oversize: Boolean flag if oversize rate applies
    Modifies column:
        - cost_base: Replaced with oversize_rate when surcharge_oversize is True
    """
    oversize_rates = load_oversize_rates()

    # Add oversize flag
    df = df.with_columns(
        (pl.col("length_plus_girth") > OVERSIZE_GIRTH_THRESHOLD).alias("surcharge_oversize")
    )

    # Join oversize rates by zone
    # For now using latest rates (could filter by ship_date if needed)
    latest_rates = (
        oversize_rates
        .sort("date_from", descending=True)
        .group_by("zone")
        .first()
        .select(["zone", "oversize_rate"])
    )

    df = df.join(latest_rates, left_on="rate_zone", right_on="zone", how="left")

    # Replace cost_base with oversize_rate when applicable
    df = df.with_columns(
        pl.when(pl.col("surcharge_oversize"))
        .then(pl.col("oversize_rate"))
        .otherwise(pl.col("cost_base"))
        .alias("cost_base")
    )

    # Drop the temporary oversize_rate column
    df = df.drop("oversize_rate")

    return df


def _apply_peak_surcharge(df: pl.DataFrame) -> pl.DataFrame:
    """
    Apply peak season surcharge based on ship date, weight tier, and zone.

    Peak surcharge applies during defined peak periods (typically Oct-Jan).
    Amount varies by weight tier (0-3, 4-10, 11-25, 26-70 lbs) and
    zone grouping (1-4 vs 5-9).

    Adds columns:
        - surcharge_peak: Boolean flag if peak surcharge applies
        - cost_peak: Peak surcharge amount (0.0 if not in peak season)
    """
    # Determine if in peak season
    df = df.with_columns(
        peak_season_condition().alias("surcharge_peak")
    )

    # Calculate peak surcharge amount (only if in peak season)
    df = df.with_columns(
        pl.when(pl.col("surcharge_peak"))
        .then(peak_surcharge_amount())
        .otherwise(pl.lit(0.0))
        .alias("cost_peak")
    )

    return df


def _calculate_subtotal(df: pl.DataFrame) -> pl.DataFrame:
    """Calculate cost_subtotal as sum of base rate, surcharges, and peak surcharge."""
    cost_cols = ["cost_base"] + [f"cost_{s.name.lower()}" for s in ALL] + ["cost_peak"]
    return df.with_columns(pl.sum_horizontal(cost_cols).alias("cost_subtotal"))


def _calculate_total(df: pl.DataFrame) -> pl.DataFrame:
    """Calculate cost_total (same as subtotal for USPS - no fuel surcharge)."""
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
