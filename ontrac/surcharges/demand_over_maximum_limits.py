"""
Demand Over Maximum Limits Surcharge (DEM_OML)

Applied during peak season when OML also applies.
"""

import polars as pl
from .base import Surcharge


class DEM_OML(Surcharge):
    """
    Demand Over Maximum Limits Surcharge

    Applied during dimensional demand period when OML triggers.
    Contract: 50% discount (Second Amendment)
    Period: Sept 27 - Jan 16 (year-agnostic)
    """

    name = "DEM_OML"
    list_price = 550.00
    discount = 0.50
    allocation_type = "deterministic"

    period_start = (9, 27)   # Sept 27
    period_end = (1, 16)     # Jan 16
    depends_on = "OML"

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("surcharge_oml") & cls._period_expr()
