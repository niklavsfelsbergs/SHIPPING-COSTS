"""FedEx data loaders and reference configuration."""

from carriers.fedex.data.loaders import load_pcs_shipments
from carriers.fedex.data.reference import (
    load_zones,
    load_base_rates_home_delivery,
    load_base_rates_ground_economy,
    DIM_FACTOR,
    DIM_THRESHOLD,
)
from carriers.fedex.data.reference.discounts import (
    HOME_DELIVERY_DISCOUNT,
    GROUND_ECONOMY_DISCOUNT,
)
from carriers.fedex.data.reference.service_mapping import (
    SERVICE_MAPPING,
    get_rate_service,
)

__all__ = [
    "load_pcs_shipments",
    "load_zones",
    "load_base_rates_home_delivery",
    "load_base_rates_ground_economy",
    "DIM_FACTOR",
    "DIM_THRESHOLD",
    "HOME_DELIVERY_DISCOUNT",
    "GROUND_ECONOMY_DISCOUNT",
    "SERVICE_MAPPING",
    "get_rate_service",
]
