"""
Demand Large Package Surcharge (DEM_LPS)

Seasonal surcharge applied when LPS triggers during peak period.
"""

import polars as pl
from .base import Surcharge, in_period


class DEM_LPS(Surcharge):
    """Demand Large Package - seasonal surcharge when LPS applies."""

    # Identity
    name = "DEM_LPS"

    # Pricing (50% discount per Second Amendment)
    list_price = 105.00
    discount = 0.50

    # Dependencies
    depends_on = "LPS"
    period_start = (9, 27)   # Sept 27
    period_end = (1, 16)     # Jan 16

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("surcharge_lps") & in_period(cls.period_start, cls.period_end)
