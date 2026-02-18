"""
P2P US2 Data

Reference data and loaders for rates, zones, and configuration.

Structure:
    - reference/: Static reference data (zones, rates, config)
    - loaders/: Dynamic data loaders (PCS database)
"""

import polars as pl
from pathlib import Path

from .reference.billable_weight import (
    PFA_DIM_FACTOR,
    PFA_DIM_THRESHOLD,
    PFA_DIM_WEIGHT_THRESHOLD,
    PFS_DIM_FACTOR,
    PFS_DIM_THRESHOLD,
)

from .loaders import (
    load_pcs_shipments_all_us,
    DEFAULT_COUNTRY,
    DEFAULT_START_DATE,
)


REFERENCE_DIR = Path(__file__).parent / "reference"


def load_pfa_rates() -> pl.DataFrame:
    """
    Load PFA base rates in long format, ready for joining.

    Returns:
        DataFrame with columns:
            - weight_lbs_lower: Lower bound of weight bracket (exclusive)
            - weight_lbs_upper: Upper bound of weight bracket (inclusive)
            - zone: Shipping zone (1-8)
            - rate: Base rate for this zone/weight combination
    """
    return pl.read_csv(REFERENCE_DIR / "base_rates_pfa.csv")


def load_pfs_rates() -> pl.DataFrame:
    """
    Load PFS base rates in long format, ready for joining.

    Returns:
        DataFrame with columns:
            - weight_lbs_lower: Lower bound of weight bracket (exclusive)
            - weight_lbs_upper: Upper bound of weight bracket (inclusive)
            - zone: Shipping zone (1-9)
            - rate: Base rate for this zone/weight combination
    """
    return pl.read_csv(REFERENCE_DIR / "base_rates_pfs.csv")


def load_zones() -> pl.DataFrame:
    """
    Load zone mappings from CSV.

    P2P US2 uses 5-digit ZIP for zone lookup.
    Includes is_remote flag for remote delivery areas.

    Returns:
        DataFrame with columns: zip, zone, is_remote
    """
    return pl.read_csv(
        REFERENCE_DIR / "zones.csv",
        schema_overrides={
            "zip": pl.Utf8,
            "zone": pl.Int64,
            "is_remote": pl.Boolean,
        }
    )


__all__ = [
    "load_pfa_rates",
    "load_pfs_rates",
    "load_zones",
    "REFERENCE_DIR",
    "load_pcs_shipments_all_us",
    "DEFAULT_COUNTRY",
    "DEFAULT_START_DATE",
    "PFA_DIM_FACTOR",
    "PFA_DIM_THRESHOLD",
    "PFA_DIM_WEIGHT_THRESHOLD",
    "PFS_DIM_FACTOR",
    "PFS_DIM_THRESHOLD",
]
