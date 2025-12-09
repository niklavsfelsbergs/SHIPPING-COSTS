"""
Residential Surcharge (RES)

ALLOCATED SURCHARGE PATTERN
---------------------------
Unlike deterministic surcharges (AHS, LPS, OML) which trigger on specific
measurable conditions, RES cannot be predicted per-shipment because we don't
know if a destination is residential or commercial.

OnTrac charges RES on ~95% of our shipments historically. Rather than guess
which specific shipments will be charged, we allocate the expected cost
across ALL shipments:

    cost = list_price * (1 - discount) * allocation_rate

This spreads the RES cost evenly, so total expected RES matches total actual
RES across the portfolio, even though individual shipments may differ.

The conditions() method returns True for all shipments (inherited default).
"""

from shared.surcharges import Surcharge


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
