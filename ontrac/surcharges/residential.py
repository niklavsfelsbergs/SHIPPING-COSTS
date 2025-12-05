"""
Residential Surcharge (RES)

Allocated surcharge - cannot predict per-shipment if residential or commercial.
Cost spread across all shipments at historical rate.
"""

from .base import Surcharge


class RES(Surcharge):
    """Residential - allocated at 95% based on historical residential rate."""

    # Identity
    name = "RES"

    # Pricing (90% discount, allocated at 95%)
    list_price = 6.10
    discount = 0.90
    is_allocated = True
    allocation_rate = 0.95

    # Uses default conditions() -> pl.lit(True)
