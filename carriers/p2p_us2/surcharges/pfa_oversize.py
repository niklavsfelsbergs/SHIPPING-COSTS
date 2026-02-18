"""
PFA Oversize Surcharge

Applies to PFA packages exceeding 21"×17"×14" in any orientation.
Checks longest > 21" OR second_longest > 17" OR shortest > 14".

Cost: $9.00
"""

import polars as pl
from shared.surcharges import Surcharge


class PFA_OVERSIZE(Surcharge):
    """PFA Oversize - exceeds 21"×17"×14" box dimensions."""

    name = "PFA_OVERSIZE"
    list_price = 9.00
    discount = 0.00

    exclusivity_group = None
    priority = None

    LONGEST_IN = 21
    SECOND_LONGEST_IN = 17
    SHORTEST_IN = 14

    @classmethod
    def conditions(cls) -> pl.Expr:
        return (
            (pl.col("longest_side_in") > cls.LONGEST_IN) |
            (pl.col("second_longest_in") > cls.SECOND_LONGEST_IN) |
            (pl.col("shortest_side_in") > cls.SHORTEST_IN)
        )
