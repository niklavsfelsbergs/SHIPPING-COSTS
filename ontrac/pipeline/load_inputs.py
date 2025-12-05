"""
Load Input Data

Loads reference data files (rates, zones) for the pipeline.
"""

import polars as pl
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data"


def load_rates() -> pl.DataFrame:
    """
    Load base rates from CSV.

    Returns:
        DataFrame with columns: weight_lbs_lower, weight_lbs_upper, zone_2..zone_8
    """
    return pl.read_csv(DATA_DIR / "base_rates.csv")


def load_zones() -> pl.DataFrame:
    """
    Load zone mappings from CSV.

    Returns:
        DataFrame with columns: zip_code, shipping_state, phx_zone, cmh_zone, das
    """
    return pl.read_csv(
        DATA_DIR / "zones.csv",
        dtypes={"zip_code": pl.Utf8}  # Keep zip codes as strings (leading zeros)
    )
