"""
USPS Shipping Cost Calculator

DataFrame in, DataFrame out. The input can come from any source (PCS database,
CSV, manual creation) as long as it contains the required columns. The output
is the same DataFrame with calculation columns and costs appended.

REQUIRED INPUT COLUMNS
----------------------
    ship_date           - Date for rate lookups
    production_site     - Origin site (determines zone)
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
        - cost_* amounts (base, surcharges, subtotal, total)
        - calculator_version

USAGE
-----
    from carriers.usps.calculate_costs import calculate_costs
    result = calculate_costs(df)
"""

import polars as pl

from .version import VERSION

# TODO: Import data loaders once implemented
# from .data import (
#     load_rates,
#     load_zones,
#     DIM_FACTOR,
#     DIM_THRESHOLD,
#     THRESHOLD_FIELD,
#     FACTOR_FIELD,
# )

# TODO: Import surcharges once implemented
# from .surcharges import ALL, BASE, DEPENDENT


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
    zones: pl.DataFrame | None = None
) -> pl.DataFrame:
    """
    Supplement shipment data with zone and weight calculations.

    Args:
        df: Raw shipment DataFrame
        zones: Zone mapping DataFrame (loaded if not provided)

    Returns:
        DataFrame with added columns:
            - cubic_in, longest_side_in, second_longest_in, length_plus_girth
            - shipping_zone
            - dim_weight_lbs, uses_dim_weight, billable_weight_lbs
    """
    # TODO: Implement zone lookup and billable weight calculation
    raise NotImplementedError("supplement_shipments not yet implemented for USPS")


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
    """
    # TODO: Implement cost calculation
    raise NotImplementedError("calculate not yet implemented for USPS")


def _stamp_version(df: pl.DataFrame) -> pl.DataFrame:
    """Stamp calculator version on output."""
    return df.with_columns(pl.lit(VERSION).alias("calculator_version"))


__all__ = [
    "calculate_costs",
    "supplement_shipments",
    "calculate",
]
