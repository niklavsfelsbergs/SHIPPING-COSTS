"""
P2P US Data

Reference data and loaders for rates, zones, and configuration.

Structure:
    - reference/: Static reference data (zones, rates, config)
    - loaders/: Dynamic data loaders (PCS database)
"""

import polars as pl
from pathlib import Path

from .reference.billable_weight import DIM_FACTOR, DIM_THRESHOLD, THRESHOLD_FIELD, FACTOR_FIELD

# Re-export loaders for convenience
from .loaders import (
    load_pcs_shipments,
    DEFAULT_CARRIER,
    DEFAULT_PRODUCTION_SITES,
    DEFAULT_COUNTRY,
    DEFAULT_START_DATE,
)


REFERENCE_DIR = Path(__file__).parent / "reference"


def load_rates() -> pl.DataFrame:
    """
    Load base rates in long format, ready for joining.

    Returns:
        DataFrame with columns:
            - weight_lbs_lower: Lower bound of weight bracket (exclusive)
            - weight_lbs_upper: Upper bound of weight bracket (inclusive)
            - zone: Shipping zone (1-8)
            - rate: Base rate for this zone/weight combination
    """
    return pl.read_csv(REFERENCE_DIR / "base_rates.csv")


def load_zones() -> pl.DataFrame:
    """
    Load zone mappings from CSV.

    P2P US uses 5-digit ZIP for zone lookup.

    Returns:
        DataFrame with columns: zip, zone
    """
    return pl.read_csv(
        REFERENCE_DIR / "zones.csv",
        schema_overrides={
            "zip": pl.Utf8,  # Keep ZIPs as strings (leading zeros)
            "zone": pl.Int64,
        }
    )


__all__ = [
    # Reference data loaders
    "load_rates",
    "load_zones",
    "REFERENCE_DIR",
    # PCS data loaders
    "load_pcs_shipments",
    "DEFAULT_CARRIER",
    "DEFAULT_PRODUCTION_SITES",
    "DEFAULT_COUNTRY",
    "DEFAULT_START_DATE",
    # Billable weight config
    "DIM_FACTOR",
    "DIM_THRESHOLD",
    "THRESHOLD_FIELD",
    "FACTOR_FIELD",
]
