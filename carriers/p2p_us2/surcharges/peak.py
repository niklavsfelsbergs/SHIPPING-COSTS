"""
Peak Season Surcharge for P2P US2

P2P uses the same peak surcharge schedule as USPS Ground Advantage.
Surcharge amounts vary by weight tier and zone grouping.

Standalone copy — no cross-carrier imports.
"""

from datetime import date
from typing import NamedTuple

import polars as pl


# =============================================================================
# PEAK PERIODS
# =============================================================================

class PeakPeriod(NamedTuple):
    start: date
    end: date
    name: str


PEAK_PERIODS = [
    PeakPeriod(date(2025, 10, 5), date(2026, 1, 18), "2025-2026 Holiday"),
    PeakPeriod(date(2026, 10, 5), date(2027, 1, 18), "2026-2027 Holiday"),
]


# =============================================================================
# PEAK RATES BY TIER
# =============================================================================

# (weight_upper_bound, zone_upper_bound): surcharge_amount
# Zone groups: 1-4 and 5-9
PEAK_RATES = {
    (3, 4): 0.30,    # Zones 1-4, 0-3 lbs
    (3, 9): 0.35,    # Zones 5-9, 0-3 lbs
    (10, 4): 0.45,   # Zones 1-4, 4-10 lbs
    (10, 9): 0.75,   # Zones 5-9, 4-10 lbs
    (25, 4): 0.75,   # Zones 1-4, 11-25 lbs
    (25, 9): 1.25,   # Zones 5-9, 11-25 lbs
    (70, 4): 2.25,   # Zones 1-4, 26-70 lbs
    (70, 9): 5.50,   # Zones 5-9, 26-70 lbs
}


# =============================================================================
# POLARS EXPRESSIONS
# =============================================================================

def peak_season_condition() -> pl.Expr:
    """Returns True if ship_date falls within any peak season period."""
    conditions = []
    for period in PEAK_PERIODS:
        conditions.append(
            (pl.col("ship_date") >= period.start) &
            (pl.col("ship_date") <= period.end)
        )
    if not conditions:
        return pl.lit(False)
    result = conditions[0]
    for cond in conditions[1:]:
        result = result | cond
    return result


def peak_surcharge_amount(weight_col: str, zone_col: str) -> pl.Expr:
    """
    Polars expression for peak surcharge by weight tier and zone group.

    Args:
        weight_col: Column name for billable weight (e.g. "pfa_billable_weight_lbs")
        zone_col: Column name for zone (e.g. "shipping_zone")
    """
    return (
        pl.when(pl.col(weight_col) <= 3)
        .then(
            pl.when(pl.col(zone_col) <= 4)
            .then(pl.lit(PEAK_RATES[(3, 4)]))
            .otherwise(pl.lit(PEAK_RATES[(3, 9)]))
        )
        .when(pl.col(weight_col) <= 10)
        .then(
            pl.when(pl.col(zone_col) <= 4)
            .then(pl.lit(PEAK_RATES[(10, 4)]))
            .otherwise(pl.lit(PEAK_RATES[(10, 9)]))
        )
        .when(pl.col(weight_col) <= 25)
        .then(
            pl.when(pl.col(zone_col) <= 4)
            .then(pl.lit(PEAK_RATES[(25, 4)]))
            .otherwise(pl.lit(PEAK_RATES[(25, 9)]))
        )
        .otherwise(
            pl.when(pl.col(zone_col) <= 4)
            .then(pl.lit(PEAK_RATES[(70, 4)]))
            .otherwise(pl.lit(PEAK_RATES[(70, 9)]))
        )
    )
