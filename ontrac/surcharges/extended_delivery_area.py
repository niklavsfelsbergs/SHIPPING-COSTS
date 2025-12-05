"""
Extended Delivery Area Surcharge (EDAS)

Applies to deliveries in extended (remote) delivery areas.
"""

import polars as pl
from .base import Surcharge


class EDAS(Surcharge):
    """Extended Delivery Area - delivery ZIP is in a remote EDAS zone."""

    # Identity
    name = "EDAS"

    # Pricing (60% discount)
    list_price = 8.30
    discount = 0.60

    # Grouping (delivery: EDAS > DAS)
    priority_group = "delivery"
    priority = 1

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("das_zone") == "EDAS"
