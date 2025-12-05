"""
Surcharge Base Class

All surcharges inherit from this class.
"""

from abc import ABC, abstractmethod
import polars as pl


class Surcharge(ABC):
    """
    Base class for all surcharges.

    Required:
        name: Short code (e.g., "AHS", "DEM_RES")
        list_price: Published rate before discount
        discount: Decimal (0.70 = 70% off)
        allocation_type: "deterministic" or "allocated"

    Optional:
        priority_group: For mutually exclusive surcharges ("dimensional", "delivery")
        priority: Order within priority_group (1 = highest)
        min_billable_weight: Minimum billable weight when surcharge applies
        period_start: (month, day) tuple for demand period start
        period_end: (month, day) tuple for demand period end
        allocation_rate: Required if allocation_type="allocated" (e.g., 0.95)
        depends_on: Name of surcharge this depends on (e.g., "AHS" for DEM_AHS)
    """

    # Required
    name: str
    list_price: float
    discount: float
    allocation_type: str

    # Optional
    priority_group: str | None = None
    priority: int | None = None
    min_billable_weight: int | None = None
    period_start: tuple[int, int] | None = None  # (month, day)
    period_end: tuple[int, int] | None = None    # (month, day)
    allocation_rate: float | None = None
    depends_on: str | None = None

    @classmethod
    def cost(cls) -> float:
        """Final cost after discount, accounting for allocation type."""
        base_cost = cls.list_price * (1 - cls.discount)

        if cls.allocation_type == "allocated":
            return base_cost * cls.allocation_rate

        return base_cost

    @classmethod
    def _period_expr(cls) -> pl.Expr:
        """Polars expression for period check using period_start/period_end.

        Uses month*100+day for comparison (Jan 1 = 101, Sept 27 = 927, Dec 31 = 1231).
        Note: Must cast to Int32 to avoid Int8 overflow when multiplying month by 100.
        """
        start_md = cls.period_start[0] * 100 + cls.period_start[1]
        end_md = cls.period_end[0] * 100 + cls.period_end[1]
        ship_md = pl.col("pcs_created").dt.month().cast(pl.Int32) * 100 + pl.col("pcs_created").dt.day().cast(pl.Int32)

        if start_md <= end_md:
            # Normal range (e.g., Mar 1 to Jun 30)
            return (ship_md >= start_md) & (ship_md <= end_md)
        else:
            # Crosses year boundary (e.g., Sept 27 to Jan 16)
            return (ship_md >= start_md) | (ship_md <= end_md)

    @classmethod
    @abstractmethod
    def conditions(cls) -> pl.Expr:
        """Polars expression for when this surcharge triggers."""
        pass
