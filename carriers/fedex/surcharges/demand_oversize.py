"""
Demand Oversize Surcharge (DEM_Oversize)

Seasonal surcharge applied when Oversize triggers during peak period.

Two pricing tiers:
- Phase 1 (Sep 29 - Nov 23): $45.00
- Phase 2 (Nov 24 - Jan 18): $54.25

Triggers when:
- surcharge_oversize is True
- ship_date is within demand period
"""

import polars as pl
from shared.surcharges import Surcharge, in_period


class DEM_Oversize(Surcharge):
    """Demand Oversize - seasonal surcharge when Oversize applies."""

    name = "DEM_Oversize"

    # -------------------------------------------------------------------------
    # PRICING
    # -------------------------------------------------------------------------
    # Dummy values - actual cost is calculated in cost() method
    list_price = 45.00
    discount = 0.0

    # Phase 1 and Phase 2 prices
    PHASE_1_PRICE = 45.00  # Sep 29 - Nov 23
    PHASE_2_PRICE = 54.25  # Nov 24 - Jan 18

    # -------------------------------------------------------------------------
    # DEPENDENCIES
    # -------------------------------------------------------------------------
    depends_on = "Oversize"
    period_start = (9, 29)   # Sep 29
    period_end = (1, 18)     # Jan 18

    # Phase 2 boundaries (peak of peak)
    PHASE_2_START = (11, 24)  # Nov 24
    PHASE_2_END = (1, 18)     # Jan 18

    @classmethod
    def conditions(cls) -> pl.Expr:
        """Triggers when Oversize flag is set and within demand period."""
        return pl.col("surcharge_oversize") & in_period(cls.period_start, cls.period_end)

    @classmethod
    def cost(cls) -> pl.Expr:
        """
        Return surcharge cost based on phase.

        Phase 1 (Sep 29 - Nov 23): $45.00
        Phase 2 (Nov 24 - Jan 18): $54.25
        """
        in_phase_2 = in_period(cls.PHASE_2_START, cls.PHASE_2_END)

        return (
            pl.when(in_phase_2)
            .then(pl.lit(cls.PHASE_2_PRICE))
            .otherwise(pl.lit(cls.PHASE_1_PRICE))
        )
