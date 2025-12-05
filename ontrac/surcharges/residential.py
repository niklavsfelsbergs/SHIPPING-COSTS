"""
Residential Surcharge (RES)

Allocated surcharge applied to all shipments at historical rate.
Cannot predict per-shipment if delivery is residential or commercial.
"""

import polars as pl
from .base import Surcharge


class RES(Surcharge):
    """
    Residential Surcharge (Allocated)

    Applied to ~95% of shipments based on historical data.
    Contract: 90% discount
    """

    name = "RES"
    list_price = 6.10
    discount = 0.90
    allocation_type = "allocated"
    allocation_rate = 0.95

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.lit(True)  # Always applies (allocated)
