"""
Demand Residential Surcharge (DEM_RES)

Allocated surcharge applied during residential demand period.
"""

import polars as pl
from .base import Surcharge


class DEM_RES(Surcharge):
    """
    Demand Residential Surcharge (Allocated)

    Applied during residential demand period at 95% rate.
    Contract: 50% discount (Second Amendment)
    Period: Oct 25 - Jan 16 (year-agnostic)
    """

    name = "DEM_RES"
    list_price = 1.00
    discount = 0.50
    allocation_type = "allocated"
    allocation_rate = 0.95

    period_start = (10, 25)  # Oct 25
    period_end = (1, 16)     # Jan 16
    depends_on = "RES"

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("surcharge_res") & cls._period_expr()
