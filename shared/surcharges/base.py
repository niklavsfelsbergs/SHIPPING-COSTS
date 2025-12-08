"""
Surcharge Base Class

Shared base class for all carrier surcharges.
"""

from abc import ABC
import polars as pl


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def in_period(
    start: tuple[int, int],
    end: tuple[int, int],
    date_col: str = "ship_date"
) -> pl.Expr:
    """
    Check if date falls within a (month, day) period.

    Handles year boundary crossings (e.g., Sept 27 to Jan 16).

    Args:
        start: (month, day) tuple for period start
        end: (month, day) tuple for period end
        date_col: Column name containing the date

    Returns:
        Polars expression evaluating to True if date is in period
    """
    start_md = start[0] * 100 + start[1]
    end_md = end[0] * 100 + end[1]
    ship_md = (
        pl.col(date_col).dt.month().cast(pl.Int32) * 100 +
        pl.col(date_col).dt.day().cast(pl.Int32)
    )

    if start_md <= end_md:
        # Normal range (e.g., Mar 1 to Jun 30)
        return (ship_md >= start_md) & (ship_md <= end_md)
    else:
        # Crosses year boundary (e.g., Sept 27 to Jan 16)
        return (ship_md >= start_md) | (ship_md <= end_md)


# =============================================================================
# BASE CLASS
# =============================================================================

class Surcharge(ABC):
    """
    Base class for all surcharges.

    Attributes:
        IDENTITY
            name            - Short code (e.g., "AHS", "DEM_RES")

        PRICING
            list_price      - Published rate before discount
            discount        - Decimal discount (0.70 = 70% off)
            is_allocated    - True if cost is spread across all shipments
            allocation_rate - Rate for allocated surcharges (e.g., 0.95)

        EXCLUSIVITY (for mutually exclusive surcharges)
            exclusivity_group - Group name (e.g., "dimensional", "delivery")
            priority          - Rank within group (1 = highest, wins ties)

        DEPENDENCIES
            depends_on      - Name of surcharge this depends on (e.g., "AHS")
            period_start    - (month, day) tuple for seasonal start
            period_end      - (month, day) tuple for seasonal end

        SIDE EFFECTS
            min_billable_weight - Minimum billable weight when triggered
    """

    # -------------------------------------------------------------------------
    # IDENTITY
    # -------------------------------------------------------------------------
    name: str

    # -------------------------------------------------------------------------
    # PRICING
    # -------------------------------------------------------------------------
    list_price: float
    discount: float
    is_allocated: bool = False
    allocation_rate: float | None = None

    # -------------------------------------------------------------------------
    # EXCLUSIVITY
    # -------------------------------------------------------------------------
    exclusivity_group: str | None = None
    priority: int | None = None

    # -------------------------------------------------------------------------
    # DEPENDENCIES
    # -------------------------------------------------------------------------
    depends_on: str | None = None
    period_start: tuple[int, int] | None = None
    period_end: tuple[int, int] | None = None

    # -------------------------------------------------------------------------
    # SIDE EFFECTS
    # -------------------------------------------------------------------------
    min_billable_weight: int | None = None

    # -------------------------------------------------------------------------
    # METHODS
    # -------------------------------------------------------------------------

    @classmethod
    def net_price(cls) -> float:
        """Price after discount, before allocation."""
        return cls.list_price * (1 - cls.discount)

    @classmethod
    def cost(cls) -> float:
        """Cost per shipment (net_price * allocation_rate if allocated)."""
        if cls.is_allocated:
            return cls.net_price() * cls.allocation_rate
        return cls.net_price()

    @classmethod
    def conditions(cls) -> pl.Expr:
        """
        Polars expression for when this surcharge triggers.

        Default returns True (for allocated surcharges).
        Override for deterministic surcharges with specific conditions.
        """
        return pl.lit(True)
