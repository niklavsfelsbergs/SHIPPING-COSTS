"""
FedEx Shipping Cost Calculator

DataFrame in, DataFrame out. The input can come from any source (PCS database,
CSV, manual creation) as long as it contains the required columns. The output
is the same DataFrame with calculation columns and costs appended.

REQUIRED INPUT COLUMNS
----------------------
    ship_date           - Date for demand period checks
    production_site     - Origin facility (determines zone)
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
        - surcharge_* flags
        - cost_base_rate (undiscounted list price)
        - cost_performance_pricing (PP discount, negative)
        - cost_earned_discount (earned discount, negative, currently 0)
        - cost_grace_discount (grace discount, negative, currently 0)
        - cost_subtotal (base + discounts + surcharges)
        - cost_fuel, cost_total
        - calculator_version

USAGE
-----
    from carriers.fedex.calculate_costs import calculate_costs
    result = calculate_costs(df)
"""

import polars as pl

from .data import (
    load_zones,
    load_das_zones,
    DIM_FACTOR,
    FUEL_RATE,
    SERVICE_MAPPING,
)
from .data.reference import (
    load_undiscounted_rates,
    load_performance_pricing,
    load_earned_discount,
    load_grace_discount,
)
from .surcharges import ALL, BASE, DEPENDENT, get_exclusivity_group, get_unique_exclusivity_groups
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
    zones: pl.DataFrame | None = None,
    das_zones: pl.DataFrame | None = None
) -> pl.DataFrame:
    """
    Supplement shipment data with zone and weight calculations.

    Args:
        df: Raw shipment DataFrame
        zones: Zone mapping DataFrame (loaded if not provided)
        das_zones: DAS zone mapping DataFrame (loaded if not provided)

    Returns:
        DataFrame with added columns:
            - rate_service (Home Delivery or Ground Economy)
            - cubic_in, longest_side_in, second_longest_in, length_plus_girth
            - shipping_zone
            - das_zone (DAS tier or null)
            - dim_weight_lbs, uses_dim_weight, billable_weight_lbs
    """
    if zones is None:
        zones = load_zones()
    if das_zones is None:
        das_zones = load_das_zones()

    df = _add_service_type(df)
    df = _add_calculated_dimensions(df)
    df = _lookup_zones(df, zones)
    df = _lookup_das_zones(df, das_zones)
    df = _add_billable_weight(df)

    return df


def _add_service_type(df: pl.DataFrame) -> pl.DataFrame:
    """
    Add rate_service column based on PCS service code (pcs_shipping_provider).

    Maps PCS extkey to either 'Home Delivery' or 'Ground Economy'.
    Unknown service codes default to 'Home Delivery'.
    """
    # Build when/then chain for service mapping
    expr = pl.lit("Home Delivery")  # Default
    for code, service in SERVICE_MAPPING.items():
        expr = (
            pl.when(pl.col("pcs_shipping_provider") == code)
            .then(pl.lit(service))
            .otherwise(expr)
        )

    return df.with_columns(expr.alias("rate_service"))


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
    Add zone data to shipments based on shipping ZIP code and origin.

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

    # Ensure zones zip_code is also normalized
    zones = zones.with_columns(
        pl.col("zip_code")
        .cast(pl.Utf8)
        .str.zfill(5)
        .alias("zip_code")
    )

    zones_subset = zones.select(["zip_code", "state", "phx_zone", "cmh_zone"])

    # State-level fallback (mode zone per state)
    state_zones = (
        zones
        .group_by("state")
        .agg([
            pl.col("phx_zone").mode().first().alias("_state_phx_zone"),
            pl.col("cmh_zone").mode().first().alias("_state_cmh_zone"),
        ])
    )

    # Join on ZIP code
    df = df.join(zones_subset, left_on="_zip_normalized", right_on="zip_code", how="left")

    # Join state fallback
    df = df.join(state_zones, left_on="shipping_region", right_on="state", how="left")

    # Coalesce: ZIP zone -> state zone -> default zone 5
    df = df.with_columns([
        pl.coalesce(["phx_zone", "_state_phx_zone", pl.lit(5)]).alias("_phx_zone_final"),
        pl.coalesce(["cmh_zone", "_state_cmh_zone", pl.lit(5)]).alias("_cmh_zone_final"),
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
        "_state_phx_zone", "_state_cmh_zone",
        "_phx_zone_final", "_cmh_zone_final",
        "state",
    ])

    return df


def _lookup_das_zones(df: pl.DataFrame, das_zones: pl.DataFrame) -> pl.DataFrame:
    """
    Add DAS zone to shipments based on shipping ZIP code and service type.

    DAS zones are destination-only (not origin-dependent).
    The das_zones.csv has separate columns for Home Delivery and SmartPost
    since some ZIPs have different DAS tiers by service.

    Args:
        df: DataFrame with shipping_zip_code and rate_service columns
        das_zones: DAS zone mapping with zip_code, das_type_hd, das_type_sp

    Returns:
        DataFrame with das_zone column added (DAS tier or null)
    """
    # Normalize ZIP code to 5 digits
    df = df.with_columns(
        pl.col("shipping_zip_code")
        .cast(pl.Utf8)
        .str.slice(0, 5)
        .str.zfill(5)
        .alias("_das_zip")
    )

    # Ensure das_zones zip_code is normalized
    das_zones = das_zones.with_columns(
        pl.col("zip_code")
        .cast(pl.Utf8)
        .str.zfill(5)
        .alias("zip_code")
    )

    # Join to get DAS zone data
    df = df.join(
        das_zones,
        left_on="_das_zip",
        right_on="zip_code",
        how="left"
    )

    # Select the appropriate DAS type based on service
    df = df.with_columns(
        pl.when(pl.col("rate_service") == "Home Delivery")
        .then(pl.col("das_type_hd"))
        .otherwise(pl.col("das_type_sp"))
        .alias("das_zone")
    )

    # Drop intermediate columns
    df = df.drop(["_das_zip", "das_type_hd", "das_type_sp"])

    return df


def _add_billable_weight(df: pl.DataFrame) -> pl.DataFrame:
    """
    Calculate dimensional weight and billable weight.

    FedEx uses dimensional weight factor of 139 for Ground.
    Billable weight is the greater of actual weight and dimensional weight.
    """
    # Calculate dimensional weight
    df = df.with_columns(
        (pl.col("cubic_in") / DIM_FACTOR).alias("dim_weight_lbs")
    )

    # Billable weight is always max(actual, dimensional) - no threshold
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

    # cost() may return float or pl.Expr (for conditional costs)
    cost_value = surcharge.cost()
    cost_expr = cost_value if isinstance(cost_value, pl.Expr) else pl.lit(cost_value)

    df = df.with_columns(surcharge.conditions().alias(flag_col))
    df = df.with_columns(
        pl.when(pl.col(flag_col))
        .then(cost_expr)
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

        # cost() may return float or pl.Expr (for conditional costs)
        cost_value = surcharge.cost()
        cost_expr = cost_value if isinstance(cost_value, pl.Expr) else pl.lit(cost_value)

        # Applies only if: conditions met AND no higher priority already matched
        applies = surcharge.conditions() & ~exclusion_mask

        df = df.with_columns(applies.alias(flag_col))
        df = df.with_columns(
            pl.when(pl.col(flag_col))
            .then(cost_expr)
            .otherwise(pl.lit(0.0))
            .alias(cost_col)
        )

        # Update exclusion mask: if this one matched, exclude the rest
        exclusion_mask = exclusion_mask | pl.col(flag_col)

    return df


def _apply_min_billable_weights(df: pl.DataFrame) -> pl.DataFrame:
    """
    Apply minimum billable weights from triggered surcharges.

    Some surcharges enforce minimum billable weights when triggered.
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
    """
    Look up base shipping rate and discount components by service, zone, and weight.

    Uses separate rate tables for Home Delivery and SmartPost (Ground Economy).
    Outputs four cost components:
        - cost_base_rate: Undiscounted list price
        - cost_performance_pricing: Performance pricing discount (negative)
        - cost_earned_discount: Earned discount (negative, currently 0)
        - cost_grace_discount: Grace discount (negative, currently 0)

    ZONE FALLBACK LOGIC
    -------------------
    - Null/missing zone → zone 5 (mid-range default)
    - Letter zones (A, H, M, P) → zone 9 (Hawaii rate)
    - Unknown numeric zones → zone 5
    """
    # Load rate tables for both services
    hd_undiscounted = load_undiscounted_rates("Home Delivery")
    hd_performance = load_performance_pricing("Home Delivery")
    hd_earned = load_earned_discount("Home Delivery")
    hd_grace = load_grace_discount("Home Delivery")

    sp_undiscounted = load_undiscounted_rates("SmartPost")
    sp_performance = load_performance_pricing("SmartPost")
    sp_earned = load_earned_discount("SmartPost")
    sp_grace = load_grace_discount("SmartPost")

    # Add service column to rate tables
    for rates_df in [hd_undiscounted, hd_performance, hd_earned, hd_grace]:
        rates_df = rates_df.with_columns(pl.lit("Home Delivery").alias("service"))
    for rates_df in [sp_undiscounted, sp_performance, sp_earned, sp_grace]:
        rates_df = rates_df.with_columns(pl.lit("Ground Economy").alias("service"))

    # Cap weights at max for each service (150 for HD, 71 for SmartPost)
    df = df.with_columns(
        pl.when(pl.col("rate_service") == "Home Delivery")
        .then(pl.col("billable_weight_lbs").clip(0, 150))
        .otherwise(pl.col("billable_weight_lbs").clip(0, 71))
        .alias("_capped_weight")
    )

    # Ceiling weight to integer for lookup (1 lb minimum)
    df = df.with_columns(
        pl.col("_capped_weight").ceil().clip(1, None).cast(pl.Int64).alias("_weight_bracket")
    )

    # Zone fallback logic:
    # - Null → zone 5
    # - Letter zones (A, H, M, P) → zone 9
    # - Valid zones (2-9, 17) → use as-is
    # - Unknown → zone 5
    valid_zones = [2, 3, 4, 5, 6, 7, 8, 9, 17]
    letter_zones = ["A", "H", "M", "P"]

    df = df.with_columns(
        pl.when(pl.col("shipping_zone").is_null())
        .then(pl.lit(5))
        .when(pl.col("shipping_zone").cast(pl.Utf8).is_in(letter_zones))
        .then(pl.lit(9))
        .when(pl.col("shipping_zone").cast(pl.Int64, strict=False).is_in(valid_zones))
        .then(pl.col("shipping_zone").cast(pl.Int64, strict=False))
        .otherwise(pl.lit(5))
        .alias("_rate_zone")
    )

    # Combine rate tables by service
    hd_undiscounted_svc = hd_undiscounted.with_columns(pl.lit("Home Delivery").alias("service"))
    sp_undiscounted_svc = sp_undiscounted.with_columns(pl.lit("Ground Economy").alias("service"))
    all_undiscounted = pl.concat([hd_undiscounted_svc, sp_undiscounted_svc])

    hd_performance_svc = hd_performance.with_columns(pl.lit("Home Delivery").alias("service"))
    sp_performance_svc = sp_performance.with_columns(pl.lit("Ground Economy").alias("service"))
    all_performance = pl.concat([hd_performance_svc, sp_performance_svc])

    hd_earned_svc = hd_earned.with_columns(pl.lit("Home Delivery").alias("service"))
    sp_earned_svc = sp_earned.with_columns(pl.lit("Ground Economy").alias("service"))
    all_earned = pl.concat([hd_earned_svc, sp_earned_svc])

    hd_grace_svc = hd_grace.with_columns(pl.lit("Home Delivery").alias("service"))
    sp_grace_svc = sp_grace.with_columns(pl.lit("Ground Economy").alias("service"))
    all_grace = pl.concat([hd_grace_svc, sp_grace_svc])

    # Join to get undiscounted rate
    df = df.join(
        all_undiscounted,
        left_on=["rate_service", "_weight_bracket", "_rate_zone"],
        right_on=["service", "weight_lbs", "zone"],
        how="left"
    ).rename({"rate": "cost_base_rate"})

    # Join to get performance pricing discount
    df = df.join(
        all_performance,
        left_on=["rate_service", "_weight_bracket", "_rate_zone"],
        right_on=["service", "weight_lbs", "zone"],
        how="left"
    ).rename({"rate": "cost_performance_pricing"})

    # Join to get earned discount
    df = df.join(
        all_earned,
        left_on=["rate_service", "_weight_bracket", "_rate_zone"],
        right_on=["service", "weight_lbs", "zone"],
        how="left"
    ).rename({"rate": "cost_earned_discount"})

    # Join to get grace discount
    df = df.join(
        all_grace,
        left_on=["rate_service", "_weight_bracket", "_rate_zone"],
        right_on=["service", "weight_lbs", "zone"],
        how="left"
    ).rename({"rate": "cost_grace_discount"})

    # Clean up intermediate columns
    df = df.drop(["_capped_weight", "_weight_bracket", "_rate_zone"])

    return df


def _calculate_subtotal(df: pl.DataFrame) -> pl.DataFrame:
    """Calculate cost_subtotal as sum of base rate, discounts, and surcharges.

    cost_subtotal = cost_base_rate + cost_performance_pricing + cost_earned_discount
                    + cost_grace_discount + surcharges

    Note: Discounts (PP, earned, grace) are stored as negative values.
    """
    # Rate components (base + discounts)
    rate_cols = [
        "cost_base_rate",
        "cost_performance_pricing",
        "cost_earned_discount",
        "cost_grace_discount",
    ]
    # Add surcharge costs
    surcharge_cols = [f"cost_{s.name.lower()}" for s in ALL]
    # Combine and filter to only existing columns
    all_cost_cols = rate_cols + surcharge_cols
    existing_cols = [c for c in all_cost_cols if c in df.columns]
    return df.with_columns(pl.sum_horizontal(existing_cols).round(2).alias("cost_subtotal"))


def _apply_fuel(df: pl.DataFrame) -> pl.DataFrame:
    """Apply fuel surcharge as percentage of (base + surcharges).

    Fuel is calculated on base charge + surcharges, NOT including discounts.
    Rate configured in data/reference/fuel.py.
    """
    # Fuel is calculated on base + surcharges (excluding discounts)
    # cost_base_rate is positive, surcharges are positive
    # Discounts (performance_pricing, earned, grace) are NOT included
    surcharge_cols = [f"cost_{s.name.lower()}" for s in ALL]
    existing_surcharge_cols = [c for c in surcharge_cols if c in df.columns]

    fuel_base_cols = ["cost_base_rate"] + existing_surcharge_cols
    existing_fuel_base_cols = [c for c in fuel_base_cols if c in df.columns]

    return df.with_columns(
        (pl.sum_horizontal(existing_fuel_base_cols) * pl.lit(FUEL_RATE)).round(2).alias("cost_fuel")
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
