"""
FedEx Reference Data

Static reference data for rates, zones, and configuration.
"""

from pathlib import Path

import polars as pl

from .billable_weight import DIM_FACTOR
from .fuel import RATE as FUEL_RATE

REFERENCE_DIR = Path(__file__).parent


def load_zones() -> pl.DataFrame:
    """Load zone mappings from zones.csv."""
    return pl.read_csv(REFERENCE_DIR / "zones.csv")


def load_das_zones() -> pl.DataFrame:
    """Load DAS zone mappings from das_zones.csv."""
    return pl.read_csv(REFERENCE_DIR / "das_zones.csv")


# =============================================================================
# RATE TABLE LOADERS (for calculator)
# =============================================================================

def _load_rate_table(service: str, table_name: str) -> pl.DataFrame:
    """Load a rate table and convert to long format for lookups."""
    service_dir = "home_delivery" if service == "Home Delivery" else "smartpost"
    df = pl.read_csv(REFERENCE_DIR / service_dir / f"{table_name}.csv")

    # Convert from wide to long format
    zone_cols = [c for c in df.columns if c.startswith("zone_")]
    df_long = df.unpivot(
        index="weight_lbs",
        on=zone_cols,
        variable_name="zone_col",
        value_name="rate"
    ).with_columns(
        pl.col("zone_col").str.replace("zone_", "").cast(pl.Int64).alias("zone")
    ).select(["weight_lbs", "zone", "rate"])

    return df_long


def load_undiscounted_rates(service: str) -> pl.DataFrame:
    """Load undiscounted rates for a service."""
    return _load_rate_table(service, "undiscounted_rates")


def load_performance_pricing(service: str) -> pl.DataFrame:
    """Load performance pricing discounts for a service."""
    return _load_rate_table(service, "performance_pricing")


def load_earned_discount(service: str) -> pl.DataFrame:
    """Load earned discounts for a service."""
    return _load_rate_table(service, "earned_discount")


def load_grace_discount(service: str) -> pl.DataFrame:
    """Load grace discounts for a service."""
    return _load_rate_table(service, "grace_discount")


__all__ = [
    "load_zones",
    "load_das_zones",
    "load_undiscounted_rates",
    "load_performance_pricing",
    "load_earned_discount",
    "load_grace_discount",
    "DIM_FACTOR",
    "FUEL_RATE",
]
