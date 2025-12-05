"""
Extended Delivery Area Surcharge (EDAS)

Applies to deliveries in extended (remote) delivery areas.
"""

import polars as pl
from .base import Surcharge


class EDAS(Surcharge):
    """
    Extended Delivery Area Surcharge

    Triggers when delivery ZIP is in an EDAS zone.
    Contract: 60% discount
    """

    name = "EDAS"
    list_price = 8.30
    discount = 0.60
    allocation_type = "deterministic"

    priority_group = "delivery"
    priority = 1  # Higher priority than DAS (more specific)

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("das_zone") == "EDAS"
