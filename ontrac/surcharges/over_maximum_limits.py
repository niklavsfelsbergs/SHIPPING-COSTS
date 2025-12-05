"""
Over Maximum Limits (OML) Surcharge

Penalty surcharge for packages exceeding maximum size/weight limits.
No discount - full list price applies.
"""

import polars as pl
from .base import Surcharge


class OML(Surcharge):
    """
    Over Maximum Limits Surcharge

    Triggers when package exceeds weight, length, or length+girth limits.
    This is a penalty surcharge with no discount.
    """

    name = "OML"
    list_price = 1300.00
    discount = 0.00
    allocation_type = "deterministic"

    priority_group = "dimensional"
    priority = 1

    min_billable_weight = 150  # OnTrac: 150, Contract: 150

    # Thresholds
    weight_threshold = 150
    longest_threshold = 108
    length_plus_girth_threshold = 165

    @classmethod
    def conditions(cls) -> pl.Expr:
        return (
            (pl.col("weight_lbs").round(0) > cls.weight_threshold) |
            (pl.col("longest_side_in").round(0) > cls.longest_threshold) |
            (pl.col("length_plus_girth").round(0) > cls.length_plus_girth_threshold)
        )
