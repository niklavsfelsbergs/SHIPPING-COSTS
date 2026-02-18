"""
P2P US2 Shipping Cost Calculator

Dual-service calculator outputting BOTH PFA and PFS costs per shipment.
Service selection happens at the group level in the upload script, not here.

REQUIRED INPUT COLUMNS
----------------------
    ship_date           - Date for rate lookups
    production_site     - Origin site
    shipping_zip_code   - Destination ZIP (5-digit)
    shipping_region     - State name (fallback for zone lookup)
    length_in           - Package length in inches
    width_in            - Package width in inches
    height_in           - Package height in inches
    weight_lbs          - Actual weight in pounds

OUTPUT COLUMNS ADDED
--------------------
    supplement_shipments() adds:
        - cubic_in, longest_side_in, second_longest_in, shortest_side_in
        - shipping_zone, is_remote, zone_covered
        - pfa_dim_weight_lbs, pfa_uses_dim_weight, pfa_billable_weight_lbs
        - pfs_dim_weight_lbs, pfs_uses_dim_weight, pfs_billable_weight_lbs

    calculate_pfa() adds:
        - surcharge_pfa_oversize, cost_pfa_oversize
        - surcharge_pfa_oversize_volume, cost_pfa_oversize_volume
        - pfa_cost_base, pfa_cost_subtotal, pfa_cost_total

    calculate_pfs() adds:
        - surcharge_pfs_nsl, cost_pfs_nsl
        - surcharge_pfs_nsv, cost_pfs_nsv
        - pfs_cost_base, pfs_cost_subtotal, pfs_cost_total

USAGE
-----
    from carriers.p2p_us2.calculate_costs import calculate_costs
    result = calculate_costs(df)
"""

import polars as pl

from .version import VERSION
from .data import (
    load_pfa_rates,
    load_pfs_rates,
    load_zones,
    PFA_DIM_FACTOR,
    PFA_DIM_THRESHOLD,
    PFA_DIM_WEIGHT_THRESHOLD,
    PFS_DIM_FACTOR,
    PFS_DIM_THRESHOLD,
)
from .surcharges import PFA_ALL, PFS_ALL
from .surcharges.peak import peak_season_condition, peak_surcharge_amount


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def calculate_costs(
    df: pl.DataFrame,
    zones: pl.DataFrame | None = None
) -> pl.DataFrame:
    """
    Calculate PFA and PFS shipping costs for a shipment DataFrame.

    Outputs both pfa_cost_total and pfs_cost_total per shipment.
    Null values indicate the shipment is ineligible for that service.

    Args:
        df: Raw shipment DataFrame with required columns
        zones: Zone mapping DataFrame (loaded from zones.csv if not provided)

    Returns:
        DataFrame with supplemented data and both PFA + PFS costs
    """
    df = supplement_shipments(df, zones)
    df = calculate_pfa(df)
    df = calculate_pfs(df)
    df = _stamp_version(df)
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

    Adds dimensions, zones (with is_remote), and billable weights for both services.
    """
    if zones is None:
        zones = load_zones()

    df = _add_calculated_dimensions(df)
    df = _lookup_zones(df, zones)
    df = _add_billable_weight(df)

    return df


def _add_calculated_dimensions(df: pl.DataFrame) -> pl.DataFrame:
    """Add calculated dimensional columns including shortest_side_in for PFA oversize."""
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

        # Shortest dimension (rounded to 1 decimal) — needed for PFA oversize check
        pl.min_horizontal("length_in", "width_in", "height_in")
        .round(1)
        .alias("shortest_side_in"),
    ])


def _lookup_zones(df: pl.DataFrame, zones: pl.DataFrame) -> pl.DataFrame:
    """
    Add zone data to shipments based on 5-digit ZIP.

    P2P US2 uses 5-digit ZIP for zone lookup. Preserves is_remote flag.

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
    df = df.with_columns([
        pl.coalesce([pl.col("zone"), pl.lit(mode_zone), pl.lit(5)])
        .alias("shipping_zone"),
        pl.coalesce([pl.col("is_remote"), pl.lit(False)])
        .alias("is_remote"),
    ])

    # Drop intermediate columns
    df = df.drop(["_zip_5digit", "zone"])

    return df


def _add_billable_weight(df: pl.DataFrame) -> pl.DataFrame:
    """
    Calculate billable weight for both PFA and PFS services.

    PFA: DIM factor 166, applies when cubic_in > 1728 AND weight_lbs > 1.
    PFS: DIM factor 166, applies when cubic_in > 1728.
    """
    df = df.with_columns([
        # PFA DIM weight (only when above threshold AND weight > 1 lb)
        pl.when(
            (pl.col("cubic_in") > PFA_DIM_THRESHOLD) &
            (pl.col("weight_lbs") > PFA_DIM_WEIGHT_THRESHOLD)
        )
        .then(pl.col("cubic_in") / PFA_DIM_FACTOR)
        .otherwise(pl.lit(0.0))
        .alias("pfa_dim_weight_lbs"),

        # PFS DIM weight (when above threshold)
        pl.when(pl.col("cubic_in") > PFS_DIM_THRESHOLD)
        .then(pl.col("cubic_in") / PFS_DIM_FACTOR)
        .otherwise(pl.lit(0.0))
        .alias("pfs_dim_weight_lbs"),
    ])

    df = df.with_columns([
        # PFA billable weight
        (pl.col("pfa_dim_weight_lbs") > pl.col("weight_lbs")).alias("pfa_uses_dim_weight"),
        pl.max_horizontal("weight_lbs", "pfa_dim_weight_lbs").alias("pfa_billable_weight_lbs"),

        # PFS billable weight
        (pl.col("pfs_dim_weight_lbs") > pl.col("weight_lbs")).alias("pfs_uses_dim_weight"),
        pl.max_horizontal("weight_lbs", "pfs_dim_weight_lbs").alias("pfs_billable_weight_lbs"),
    ])

    return df


# =============================================================================
# CALCULATE PFA
# =============================================================================

PFA_MAX_WEIGHT = 30
PFA_MAX_ZONE = 8


def calculate_pfa(df: pl.DataFrame) -> pl.DataFrame:
    """
    Calculate PFA costs. Null where ineligible (zone > 8 or weight > 30 lbs).
    """
    # Apply PFA surcharges
    for s in PFA_ALL:
        df = _apply_surcharge(df, s, prefix="pfa")

    # Rate lookup
    df = _lookup_rate(df, load_pfa_rates(), "pfa")

    # Peak surcharge
    df = df.with_columns(
        pl.when(peak_season_condition())
        .then(peak_surcharge_amount("pfa_billable_weight_lbs", "shipping_zone"))
        .otherwise(pl.lit(0.0))
        .alias("pfa_cost_peak")
    )

    # Calculate subtotal
    cost_cols = ["pfa_cost_base", "pfa_cost_peak"] + [f"cost_{s.name.lower()}" for s in PFA_ALL]
    df = df.with_columns(
        pl.sum_horizontal(cost_cols).alias("pfa_cost_subtotal")
    )

    # Total = subtotal (no fuel)
    df = df.with_columns(
        pl.col("pfa_cost_subtotal").alias("pfa_cost_total")
    )

    # Null out ineligible: zone > 8 OR billable weight > 30
    pfa_ineligible = (
        (pl.col("shipping_zone") > PFA_MAX_ZONE) |
        (pl.col("pfa_billable_weight_lbs") > PFA_MAX_WEIGHT)
    )
    pfa_cost_cols = [
        "pfa_cost_base", "pfa_cost_peak", "pfa_cost_subtotal", "pfa_cost_total",
    ] + [f"cost_{s.name.lower()}" for s in PFA_ALL]

    df = df.with_columns([
        pl.when(pfa_ineligible)
        .then(pl.lit(None))
        .otherwise(pl.col(c))
        .alias(c)
        for c in pfa_cost_cols
    ])

    return df


# =============================================================================
# CALCULATE PFS
# =============================================================================

PFS_MAX_WEIGHT = 70
PFS_MAX_ZONE = 9


def calculate_pfs(df: pl.DataFrame) -> pl.DataFrame:
    """
    Calculate PFS costs. Null where ineligible (weight > 70 lbs).
    """
    # Apply PFS surcharges
    for s in PFS_ALL:
        df = _apply_surcharge(df, s, prefix="pfs")

    # Rate lookup
    df = _lookup_rate(df, load_pfs_rates(), "pfs")

    # Peak surcharge
    df = df.with_columns(
        pl.when(peak_season_condition())
        .then(peak_surcharge_amount("pfs_billable_weight_lbs", "shipping_zone"))
        .otherwise(pl.lit(0.0))
        .alias("pfs_cost_peak")
    )

    # Calculate subtotal
    cost_cols = ["pfs_cost_base", "pfs_cost_peak"] + [f"cost_{s.name.lower()}" for s in PFS_ALL]
    df = df.with_columns(
        pl.sum_horizontal(cost_cols).alias("pfs_cost_subtotal")
    )

    # Total = subtotal (no fuel)
    df = df.with_columns(
        pl.col("pfs_cost_subtotal").alias("pfs_cost_total")
    )

    # Null out ineligible: billable weight > 70
    pfs_ineligible = pl.col("pfs_billable_weight_lbs") > PFS_MAX_WEIGHT
    pfs_cost_cols = [
        "pfs_cost_base", "pfs_cost_peak", "pfs_cost_subtotal", "pfs_cost_total",
    ] + [f"cost_{s.name.lower()}" for s in PFS_ALL]

    df = df.with_columns([
        pl.when(pfs_ineligible)
        .then(pl.lit(None))
        .otherwise(pl.col(c))
        .alias(c)
        for c in pfs_cost_cols
    ])

    return df


# =============================================================================
# SHARED HELPERS
# =============================================================================

def _apply_surcharge(df: pl.DataFrame, surcharge, prefix: str) -> pl.DataFrame:
    """Apply a single surcharge (no competition — all standalone)."""
    flag_col = f"surcharge_{surcharge.name.lower()}"
    cost_col = f"cost_{surcharge.name.lower()}"

    df = df.with_columns(surcharge.conditions().alias(flag_col))

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


def _lookup_rate(
    df: pl.DataFrame,
    rates: pl.DataFrame,
    prefix: str,
) -> pl.DataFrame:
    """
    Look up base rate by zone and weight bracket for a service.

    Preserves all rows — missing rates result in null (not error).
    This handles PFA zone 9 and out-of-range weights gracefully.
    """
    weight_col = f"{prefix}_billable_weight_lbs"
    cost_col = f"{prefix}_cost_base"

    df = df.with_columns(pl.col("shipping_zone").cast(pl.Int64))
    df = df.with_row_index("_row_id")

    # Find matching rate for each shipment via join + filter
    matched = (
        df
        .select(["_row_id", "shipping_zone", weight_col])
        .join(rates, left_on="shipping_zone", right_on="zone", how="left")
        .filter(
            (pl.col(weight_col) > pl.col("weight_lbs_lower")) &
            (pl.col(weight_col) <= pl.col("weight_lbs_upper"))
        )
        .select(["_row_id", "rate"])
        .rename({"rate": cost_col})
    )

    # Left join matched rates back to preserve all original rows
    df = df.join(matched, on="_row_id", how="left")
    df = df.drop("_row_id")

    return df


def _stamp_version(df: pl.DataFrame) -> pl.DataFrame:
    """Stamp calculator version on output."""
    return df.with_columns(pl.lit(VERSION).alias("calculator_version"))


__all__ = [
    "calculate_costs",
    "supplement_shipments",
    "calculate_pfa",
    "calculate_pfs",
]
