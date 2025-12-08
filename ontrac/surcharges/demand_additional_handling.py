"""
Demand Additional Handling Surcharge (DEM_AHS)

Seasonal surcharge applied when AHS triggers during peak period.
"""

import polars as pl
from shared.surcharges import Surcharge, in_period


class DEM_AHS(Surcharge):
    """Demand Additional Handling - seasonal surcharge when AHS applies."""

    # Identity
    name = "DEM_AHS"

    # Pricing (50% discount per Second Amendment)
    list_price = 11.00
    discount = 0.50

    # Dependencies
    depends_on = "AHS"
    period_start = (9, 27)   # Sept 27
    period_end = (1, 16)     # Jan 16

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("surcharge_ahs") & in_period(cls.period_start, cls.period_end)
