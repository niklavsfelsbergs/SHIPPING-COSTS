"""FedEx data loaders and reference configuration."""

from carriers.fedex.data.loaders import load_pcs_shipments
from carriers.fedex.data.reference import (
    load_zones,
    load_das_zones,
    load_undiscounted_rates,
    load_performance_pricing,
    load_earned_discount,
    load_grace_discount,
    DIM_FACTOR,
    DIM_THRESHOLD,
)
from carriers.fedex.data.reference.service_mapping import (
    SERVICE_MAPPING,
    get_rate_service,
)

__all__ = [
    "load_pcs_shipments",
    "load_zones",
    "load_das_zones",
    "load_undiscounted_rates",
    "load_performance_pricing",
    "load_earned_discount",
    "load_grace_discount",
    "DIM_FACTOR",
    "DIM_THRESHOLD",
    "SERVICE_MAPPING",
    "get_rate_service",
]
