"""
PFS Nonstandard Volume Surcharge

Applies to PFS packages exceeding 2 cubic feet (3,456 cubic inches).

Cost: $21.00
"""

import polars as pl
from shared.surcharges import Surcharge


class PFS_NONSTANDARD_VOLUME(Surcharge):
    """PFS Nonstandard Volume - exceeds 2 cubic feet."""

    name = "PFS_NSV"
    list_price = 21.00
    discount = 0.00

    exclusivity_group = None
    priority = None

    CUBIC_IN = 3456

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("cubic_in") > cls.CUBIC_IN
