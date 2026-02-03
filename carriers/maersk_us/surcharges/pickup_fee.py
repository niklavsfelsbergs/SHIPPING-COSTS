"""
Pickup Fee Surcharge (PICKUP)

Applies to all packages at $0.04 per billable pound.
"""

import polars as pl
from shared.surcharges import Surcharge


class PICKUP(Surcharge):
    """Pickup Fee - $0.04 per billable pound."""

    # Identity
    name = "PICKUP"

    # Pricing (per-lb rate, not flat)
    list_price = 0.04  # Per lb
    discount = 0.00

    # Not exclusive - always applies
    exclusivity_group = None
    priority = None

    @classmethod
    def conditions(cls) -> pl.Expr:
        """Always applies to all packages."""
        return pl.lit(True)

    @classmethod
    def cost(cls) -> pl.Expr:
        """Cost is per billable pound, rounded up to nearest whole lb."""
        return pl.col("billable_weight_lbs").ceil() * cls.list_price
