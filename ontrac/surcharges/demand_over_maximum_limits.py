"""
Demand Over Maximum Limits Surcharge (DEM_OML)

Seasonal surcharge applied when OML triggers during peak period.
"""

import polars as pl
from .base import Surcharge, in_period


class DEM_OML(Surcharge):
    """Demand Over Maximum Limits - seasonal surcharge when OML applies."""

    # Identity
    name = "DEM_OML"

    # Pricing (50% discount per Second Amendment)
    list_price = 550.00
    discount = 0.50

    # Dependencies
    depends_on = "OML"
    period_start = (9, 27)   # Sept 27
    period_end = (1, 16)     # Jan 16

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("surcharge_oml") & in_period(cls.period_start, cls.period_end)
