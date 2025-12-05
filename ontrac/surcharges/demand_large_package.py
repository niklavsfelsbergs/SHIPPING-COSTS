"""
Demand Large Package Surcharge (DEM_LPS)

Applied during peak season when LPS also applies.
"""

import polars as pl
from .base import Surcharge


class DEM_LPS(Surcharge):
    """
    Demand Large Package Surcharge

    Applied during dimensional demand period when LPS triggers.
    Contract: 50% discount (Second Amendment)
    Period: Sept 27 - Jan 16 (year-agnostic)
    """

    name = "DEM_LPS"
    list_price = 105.00
    discount = 0.50
    allocation_type = "deterministic"

    period_start = (9, 27)   # Sept 27
    period_end = (1, 16)     # Jan 16
    depends_on = "LPS"

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("surcharge_lps") & cls._period_expr()
