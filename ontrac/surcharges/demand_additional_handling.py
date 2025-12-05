"""
Demand Additional Handling Surcharge (DEM_AHS)

Applied during peak season when AHS also applies.
"""

import polars as pl
from .base import Surcharge


class DEM_AHS(Surcharge):
    """
    Demand Additional Handling Surcharge

    Applied during dimensional demand period when AHS triggers.
    Contract: 50% discount (Second Amendment)
    Period: Sept 27 - Jan 16 (year-agnostic)
    """

    name = "DEM_AHS"
    list_price = 11.00
    discount = 0.50
    allocation_type = "deterministic"

    period_start = (9, 27)   # Sept 27
    period_end = (1, 16)     # Jan 16
    depends_on = "AHS"

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("surcharge_ahs") & cls._period_expr()
