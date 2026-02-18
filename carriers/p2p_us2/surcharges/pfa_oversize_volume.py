"""
PFA Oversize Volume Surcharge

Applies to PFA packages exceeding 2 cubic feet (3,456 cubic inches).

Cost: $16.00
"""

import polars as pl
from shared.surcharges import Surcharge


class PFA_OVERSIZE_VOLUME(Surcharge):
    """PFA Oversize Volume - exceeds 2 cubic feet."""

    name = "PFA_OVERSIZE_VOLUME"
    list_price = 16.00
    discount = 0.00

    exclusivity_group = None
    priority = None

    CUBIC_IN = 3456

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("cubic_in") > cls.CUBIC_IN
