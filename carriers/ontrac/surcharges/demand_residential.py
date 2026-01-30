"""
Demand Residential Surcharge (DEM_RES)

Seasonal allocated surcharge applied during residential demand period.
"""

import polars as pl
from shared.surcharges import Surcharge, in_period


class DEM_RES(Surcharge):
    """Demand Residential - seasonal surcharge during peak period (allocated)."""

    # Identity
    name = "DEM_RES"

    # Pricing (50% discount per Second Amendment, allocated at 95%)
    list_price = 1.00
    discount = 0.50
    is_allocated = True
    allocation_rate = 0.95

    # Dependencies
    depends_on = "RES"
    period_start = (10, 25)  # Oct 25
    period_end = (1, 16)     # Jan 16

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("surcharge_res") & in_period(
            cls.period_start, cls.period_end, billing_lag_days=5
        )
