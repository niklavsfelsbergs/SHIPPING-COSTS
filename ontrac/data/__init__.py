"""
OnTrac Data

Reference data and loaders for rates, zones, and configuration.

Structure:
    - reference/: Static reference data (zones, rates, config)
    - loaders/: Dynamic data loaders (PCS database)
"""

import polars as pl
from pathlib import Path

from .reference.billable_weight import DIM_FACTOR, DIM_THRESHOLD, THRESHOLD_FIELD, FACTOR_FIELD
from .reference.fuel import LIST_RATE, DISCOUNT, RATE, APPLICATION

# Re-export loaders for convenience
from .loaders import (
    load_pcs_shipments,
    DEFAULT_CARRIER,
    DEFAULT_PRODUCTION_SITES,
    DEFAULT_START_DATE,
)


REFERENCE_DIR = Path(__file__).parent / "reference"


def load_rates() -> pl.DataFrame:
    """
    Load base rates in long format, ready for joining.

    Transforms wide CSV format (zone_2, zone_3, ...) to long format.

    Returns:
        DataFrame with columns:
            - weight_lbs_lower: Lower bound of weight bracket (exclusive)
            - weight_lbs_upper: Upper bound of weight bracket (inclusive)
            - zone: Shipping zone (2-8)
            - rate: Base rate for this zone/weight combination
    """
    rates = pl.read_csv(REFERENCE_DIR / "base_rates.csv")
    zone_cols = [c for c in rates.columns if c.startswith("zone_")]

    return (
        rates
        .unpivot(
            index=["weight_lbs_lower", "weight_lbs_upper"],
            on=zone_cols,
            variable_name="_zone_col",
            value_name="rate"
        )
        .with_columns(
            pl.col("_zone_col").str.replace("zone_", "").cast(pl.Int64).alias("zone")
        )
        .drop("_zone_col")
    )


def load_zones() -> pl.DataFrame:
    """
    Load zone mappings from CSV.

    Returns:
        DataFrame with columns: zip_code, shipping_state, phx_zone, cmh_zone, das
    """
    return pl.read_csv(
        REFERENCE_DIR / "zones.csv",
        schema_overrides={"zip_code": pl.Utf8}  # Keep zip codes as strings (leading zeros)
    )


# Re-export fuel rate for convenience
FUEL_RATE = RATE

__all__ = [
    # Reference data loaders
    "load_rates",
    "load_zones",
    "REFERENCE_DIR",
    # PCS data loaders
    "load_pcs_shipments",
    "DEFAULT_CARRIER",
    "DEFAULT_PRODUCTION_SITES",
    "DEFAULT_START_DATE",
    # Billable weight config
    "DIM_FACTOR",
    "DIM_THRESHOLD",
    "THRESHOLD_FIELD",
    "FACTOR_FIELD",
    # Fuel config
    "LIST_RATE",
    "DISCOUNT",
    "RATE",
    "FUEL_RATE",
    "APPLICATION",
]
