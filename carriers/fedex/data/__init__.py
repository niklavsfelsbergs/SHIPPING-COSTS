"""
FedEx Data

Reference data and loaders for rates, zones, and configuration.

Structure:
    - reference/: Static reference data (zones, rates, config)
    - loaders/: Dynamic data loaders (PCS database)
"""

from .loaders import load_pcs_shipments
from .reference import (
    load_zones,
    load_das_zones,
    load_undiscounted_rates,
    load_performance_pricing,
    load_earned_discount,
    load_grace_discount,
    DIM_FACTOR,
    DIM_FACTOR_HOME_DELIVERY,
    DIM_FACTOR_GROUND_ECONOMY,
    FUEL_RATE,
)
from .reference.service_mapping import (
    SERVICE_MAPPING,
    get_rate_service,
)

__all__ = [
    # PCS data loaders
    "load_pcs_shipments",
    # Reference data loaders
    "load_zones",
    "load_das_zones",
    "load_undiscounted_rates",
    "load_performance_pricing",
    "load_earned_discount",
    "load_grace_discount",
    # Billable weight config
    "DIM_FACTOR",
    "DIM_FACTOR_HOME_DELIVERY",
    "DIM_FACTOR_GROUND_ECONOMY",
    # Fuel config
    "FUEL_RATE",
    # Service mapping
    "SERVICE_MAPPING",
    "get_rate_service",
]
