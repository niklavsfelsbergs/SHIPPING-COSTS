"""
Delivery Area Surcharge (DAS)

Applies to deliveries in designated delivery areas.
"""

import polars as pl
from .base import Surcharge


class DAS(Surcharge):
    """
    Delivery Area Surcharge

    Triggers when delivery ZIP is in a DAS zone.
    Contract: 60% discount
    """

    name = "DAS"
    list_price = 6.15
    discount = 0.60
    allocation_type = "deterministic"

    priority_group = "delivery"
    priority = 2

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("das_zone") == "DAS"
