"""
Delivery Area Surcharge (DAS)

Applies to deliveries in designated delivery areas.
"""

import polars as pl
from .base import Surcharge


class DAS(Surcharge):
    """Delivery Area - delivery ZIP is in a DAS zone."""

    # Identity
    name = "DAS"

    # Pricing (60% discount)
    list_price = 6.15
    discount = 0.60

    # Exclusivity (delivery: EDAS > DAS)
    exclusivity_group = "delivery"
    priority = 2

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("das_zone") == "DAS"
