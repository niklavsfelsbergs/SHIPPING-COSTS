"""
Column Schema Definitions

Documents all columns at each pipeline stage and provides validation utilities.
"""

from ..surcharges import ALL as ALL_SURCHARGES


# =============================================================================
# REQUIRED INPUT COLUMNS (must be present from any loader)
# =============================================================================

REQUIRED_INPUT_COLS = [
    "pcs_created",          # Ship date (for demand period checks)
    "production_site",      # "Phoenix" or "Columbus" (for zone lookup)
    "shipping_zip_code",    # Destination ZIP code (for zone lookup)
    "shipping_region",      # Destination state/region (for zone fallback)
    "length_in",            # Package length (inches)
    "width_in",             # Package width (inches)
    "height_in",            # Package height (inches)
    "weight_lbs",           # Package weight (pounds)
]

# =============================================================================
# PCS-SPECIFIC COLUMNS (additional columns from PCS loader)
# =============================================================================

PCS_COLS = [
    "pcs_ordernumber",      # PCS order number
    "pcs_orderid",          # PCS order ID
    "trackingnumber",       # Carrier tracking number
    "shop_ordernumber",     # Shop reference number
    "shipping_country",     # Destination country name
]


# =============================================================================
# SUPPLEMENT COLUMNS (added by supplement_shipments)
# =============================================================================

SUPPLEMENT_COLS = [
    # Calculated dimensions
    "cubic_in",             # L x W x H (cubic inches)
    "longest_side_in",      # Longest dimension
    "second_longest_in",    # Second longest dimension
    "length_plus_girth",    # Longest + 2*(sum of other two)

    # Zone lookup
    "shipping_zone",        # Shipping zone (2-8) based on ZIP and production site
    "das_zone",             # DAS classification: "DAS", "EDAS", or "NO"

    # Billable weight
    "dim_weight_lbs",       # Dimensional weight (cubic_in / DIM_FACTOR)
    "uses_dim_weight",      # True if dim weight > actual weight and threshold met
    "billable_weight_lbs",  # Max of actual and dim weight (may be adjusted by surcharges)
]


# =============================================================================
# SURCHARGE COLUMNS (added by calculate - surcharge application)
# =============================================================================

def _surcharge_flag_cols() -> list[str]:
    """Flag columns indicating if surcharge applies."""
    return [f"surcharge_{s.name.lower()}" for s in ALL_SURCHARGES]


def _surcharge_cost_cols() -> list[str]:
    """Cost columns for each surcharge."""
    return [f"cost_{s.name.lower()}" for s in ALL_SURCHARGES]


SURCHARGE_FLAG_COLS = _surcharge_flag_cols()
# surcharge_oml, surcharge_lps, surcharge_ahs, surcharge_das, surcharge_edas,
# surcharge_res, surcharge_dem_res, surcharge_dem_ahs, surcharge_dem_lps, surcharge_dem_oml

SURCHARGE_COST_COLS = _surcharge_cost_cols()
# cost_oml, cost_lps, cost_ahs, cost_das, cost_edas,
# cost_res, cost_dem_res, cost_dem_ahs, cost_dem_lps, cost_dem_oml


# =============================================================================
# COST COLUMNS (added by calculate - cost calculation)
# =============================================================================

COST_COLS = [
    "cost_base",            # Base shipping rate (from rate table)
    "cost_subtotal",        # Base + all surcharges
    "cost_fuel",            # Fuel surcharge (percentage of subtotal)
    "cost_total",           # Final total (subtotal + fuel)
]


# =============================================================================
# METADATA COLUMNS
# =============================================================================

METADATA_COLS = [
    "calculator_version",   # Version stamp from ontrac/version.py
]


# =============================================================================
# COLUMN SETS
# =============================================================================

# All columns after supplement_shipments (with required inputs)
AFTER_SUPPLEMENT = REQUIRED_INPUT_COLS + SUPPLEMENT_COLS

# All columns after calculate (with required inputs)
AFTER_CALCULATE = (
    REQUIRED_INPUT_COLS +
    SUPPLEMENT_COLS +
    SURCHARGE_FLAG_COLS +
    SURCHARGE_COST_COLS +
    COST_COLS +
    METADATA_COLS
)
