"""
USPS Data

Reference data and loaders for rates, zones, and configuration.

Structure:
    - reference/: Static reference data (zones, rates, config)
    - loaders/: Dynamic data loaders (PCS database)
"""

import polars as pl
from pathlib import Path

from .reference.billable_weight import (
    DIM_FACTOR,
    DIM_THRESHOLD,
    THRESHOLD_FIELD,
    FACTOR_FIELD,
    OVERSIZE_GIRTH_THRESHOLD,
)

# Re-export loaders for convenience
from .loaders import (
    load_pcs_shipments,
    load_pcs_shipments_all_us,
    DEFAULT_CARRIER,
    DEFAULT_PRODUCTION_SITES,
    DEFAULT_START_DATE,
)


REFERENCE_DIR = Path(__file__).parent / "reference"


def load_rates() -> pl.DataFrame:
    """
    Load base rates in long format, ready for joining.

    Transforms wide CSV format (zone_1, zone_2, ...) to long format.

    Returns:
        DataFrame with columns:
            - weight_lbs_lower: Lower bound of weight bracket (exclusive)
            - weight_lbs_upper: Upper bound of weight bracket (inclusive)
            - zone: Shipping zone (1-8)
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

    USPS uses 3-digit ZIP prefix for zone lookup (unlike OnTrac's 5-digit).
    Zones may have asterisk variants (1*, 2*, 3*) for local delivery.

    Returns:
        DataFrame with columns: zip_prefix, phx_zone, cmh_zone
    """
    return pl.read_csv(
        REFERENCE_DIR / "zones.csv",
        schema_overrides={
            "zip_prefix": pl.Utf8,  # Keep prefixes as strings (leading zeros)
            "phx_zone": pl.Utf8,    # Zone can have asterisks (1*, 2*, 3*)
            "cmh_zone": pl.Utf8,    # Zone can have asterisks (1*, 2*, 3*)
        }
    )


def load_oversize_rates() -> pl.DataFrame:
    """
    Load oversize rates by zone.

    Oversize rates apply when length + girth > 108 inches.
    These flat rates replace the normal weight-based base rate.

    Returns:
        DataFrame with columns:
            - date_from: Effective date for rates
            - zone: Shipping zone (1-9)
            - oversize_rate: Flat rate for oversize packages
    """
    return pl.read_csv(
        REFERENCE_DIR / "oversize_rates.csv",
        schema_overrides={
            "date_from": pl.Date,
            "zone": pl.Int64,
            "oversize_rate": pl.Float64,
        }
    )


__all__ = [
    # Reference data loaders
    "load_rates",
    "load_zones",
    "load_oversize_rates",
    "REFERENCE_DIR",
    # PCS data loaders
    "load_pcs_shipments",
    "load_pcs_shipments_all_us",
    "DEFAULT_CARRIER",
    "DEFAULT_PRODUCTION_SITES",
    "DEFAULT_START_DATE",
    # Billable weight config
    "DIM_FACTOR",
    "DIM_THRESHOLD",
    "THRESHOLD_FIELD",
    "FACTOR_FIELD",
    "OVERSIZE_GIRTH_THRESHOLD",
]
