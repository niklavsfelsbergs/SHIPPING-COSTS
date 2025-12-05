"""
Supplement Shipments

Enriches shipment data with calculated dimensions, zone lookups, and billable weight.
"""

import polars as pl

from .load_inputs import load_zones
from ..data.billable_weight import DIM_FACTOR, DIM_THRESHOLD, THRESHOLD_FIELD, FACTOR_FIELD


def supplement_shipments(
    df: pl.DataFrame,
    zones: pl.DataFrame | None = None
) -> pl.DataFrame:
    """
    Supplement shipment data with zone and weight calculations.

    Args:
        df: Raw shipment DataFrame from load_pcs_shipments
        zones: Zone mapping DataFrame (loaded if not provided)

    Returns:
        DataFrame with added columns:
            - cubic_in: Cubic inches (L x W x H)
            - longest_side_in: Longest dimension
            - second_longest_in: Second longest dimension
            - length_plus_girth: Longest + 2*(sum of other two)
            - shipping_zone: Zone based on ZIP and production site (2-8)
            - das_zone: DAS classification (DAS, EDAS, or NO)
            - dim_weight_lbs: Dimensional weight
            - uses_dim_weight: Whether dim weight applies
            - billable_weight_lbs: Max of actual and dim weight
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

    Uses three-tier fallback:
    1. Exact ZIP code match
    2. State-level mode (most common zone for the state)
    3. Default zone 5
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
