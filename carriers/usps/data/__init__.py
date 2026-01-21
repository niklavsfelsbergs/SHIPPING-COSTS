"""
USPS Data

Reference data and loaders for rates, zones, and configuration.

Structure:
    - reference/: Static reference data (zones, rates, config)
    - loaders/: Dynamic data loaders (PCS database)
"""

import polars as pl
from pathlib import Path

# TODO: Uncomment once reference files are created
# from .reference.billable_weight import DIM_FACTOR, DIM_THRESHOLD, THRESHOLD_FIELD, FACTOR_FIELD

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

    Returns:
        DataFrame with columns:
            - weight_lbs_lower: Lower bound of weight bracket (exclusive)
            - weight_lbs_upper: Upper bound of weight bracket (inclusive)
            - zone: Shipping zone
            - rate: Base rate for this zone/weight combination
    """
    # TODO: Implement once base_rates.csv is created
    raise NotImplementedError("load_rates not yet implemented for USPS")


def load_zones() -> pl.DataFrame:
    """
    Load zone mappings from CSV.

    Returns:
        DataFrame with zone mapping columns
    """
    # TODO: Implement once zones.csv is created
    raise NotImplementedError("load_zones not yet implemented for USPS")


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
]
