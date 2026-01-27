"""
Demand Surcharge (Base)

Seasonal surcharge applied to Home Delivery packages during peak period.
Ground Economy (SmartPost) is exempt.

Two pricing tiers:
- Phase 1 (Oct 27 - Nov 23): $0.40
- Phase 2 (Nov 24 - Jan 18): $0.65

Note: This surcharge applies to ALL Home Delivery packages in the demand period,
not just those with other surcharges. It's a base demand charge.
"""

import polars as pl
from shared.surcharges import Surcharge, in_period


class DEM_Base(Surcharge):
    """Demand Surcharge - base seasonal surcharge for Home Delivery."""

    name = "DEM_Base"

    # -------------------------------------------------------------------------
    # PRICING
    # -------------------------------------------------------------------------
    # Dummy values - actual cost is calculated in cost() method
    list_price = 0.40
    discount = 0.0

    # Phase 1 and Phase 2 prices
    PHASE_1_PRICE = 0.40  # Oct 27 - Nov 23
    PHASE_2_PRICE = 0.65  # Nov 24 - Jan 18

    # -------------------------------------------------------------------------
    # PERIOD
    # -------------------------------------------------------------------------
    # Note: Period starts Oct 27, not Sep 29 like other demand surcharges
    period_start = (10, 27)  # Oct 27
    period_end = (1, 18)     # Jan 18

    # Phase 2 boundaries (peak of peak)
    PHASE_2_START = (11, 24)  # Nov 24
    PHASE_2_END = (1, 18)     # Jan 18

    @classmethod
    def conditions(cls) -> pl.Expr:
        """
        Triggers for Home Delivery packages within demand period.

        Ground Economy (SmartPost) is exempt.
        """
        is_home_delivery = pl.col("rate_service") == "Home Delivery"
        in_demand_period = in_period(cls.period_start, cls.period_end)
        return is_home_delivery & in_demand_period

    @classmethod
    def cost(cls) -> pl.Expr:
        """
        Return surcharge cost based on phase.

        Phase 1 (Oct 27 - Nov 23): $0.40
        Phase 2 (Nov 24 - Jan 18): $0.65
        """
        in_phase_2 = in_period(cls.PHASE_2_START, cls.PHASE_2_END)

        return (
            pl.when(in_phase_2)
            .then(pl.lit(cls.PHASE_2_PRICE))
            .otherwise(pl.lit(cls.PHASE_1_PRICE))
        )
