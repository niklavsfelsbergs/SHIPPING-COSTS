"""
Peak Season Surcharge Configuration

USPS applies temporary peak season surcharges during the holiday shipping period.
Surcharge amounts vary by weight tier and zone grouping.

Reference: https://about.usps.com/newsroom/national-releases/2025/0808-usps-announces-temporary-price-change-for-2025-holiday-shipping-season.htm
"""

from datetime import date
from typing import NamedTuple

import polars as pl


# =============================================================================
# PEAK PERIODS
# =============================================================================

class PeakPeriod(NamedTuple):
    """A peak season period with start and end dates."""
    start: date
    end: date
    name: str


# Define peak periods (add new seasons here)
PEAK_PERIODS = [
    PeakPeriod(date(2025, 10, 5), date(2026, 1, 18), "2025-2026 Holiday"),
    PeakPeriod(date(2026, 10, 5), date(2027, 1, 18), "2026-2027 Holiday"),
]


# =============================================================================
# PEAK RATES BY TIER
# =============================================================================

# Weight tier boundaries (in lbs)
# Tier 1: 0 < weight <= 3
# Tier 2: 3 < weight <= 10
# Tier 3: 10 < weight <= 25
# Tier 4: 25 < weight <= 70 (not applicable for Ground Advantage, max 20 lbs)

PEAK_RATES = {
    # (weight_upper_bound, zone_upper_bound): surcharge_amount
    # Zone groups: 1-4 and 5-9

    # Tier 1: 0-3 lbs
    (3, 4): 0.30,   # Zones 1-4, 0-3 lbs
    (3, 9): 0.35,   # Zones 5-9, 0-3 lbs

    # Tier 2: 4-10 lbs (actually >3 to <=10)
    (10, 4): 0.45,  # Zones 1-4, 4-10 lbs
    (10, 9): 0.75,  # Zones 5-9, 4-10 lbs

    # Tier 3: 11-25 lbs (actually >10 to <=25)
    (25, 4): 0.75,  # Zones 1-4, 11-25 lbs
    (25, 9): 1.25,  # Zones 5-9, 11-25 lbs

    # Tier 4: 26-70 lbs (not used for Ground Advantage)
    (70, 4): 2.25,  # Zones 1-4, 26-70 lbs
    (70, 9): 5.50,  # Zones 5-9, 26-70 lbs
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_peak_season(ship_date: date) -> bool:
    """Check if a date falls within any peak season period."""
    for period in PEAK_PERIODS:
        if period.start <= ship_date <= period.end:
            return True
    return False


def get_peak_surcharge(weight_lbs: float, zone: int) -> float:
    """
    Get peak surcharge amount for a given weight and zone.

    Args:
        weight_lbs: Billable weight in pounds
        zone: Shipping zone (1-9)

    Returns:
        Peak surcharge amount in dollars
    """
    # Determine weight tier upper bound
    if weight_lbs <= 3:
        weight_tier = 3
    elif weight_lbs <= 10:
        weight_tier = 10
    elif weight_lbs <= 25:
        weight_tier = 25
    else:
        weight_tier = 70

    # Determine zone group upper bound (1-4 or 5-9)
    zone_group = 4 if zone <= 4 else 9

    return PEAK_RATES.get((weight_tier, zone_group), 0.0)


def peak_season_condition() -> pl.Expr:
    """
    Polars expression that returns True if ship_date is in peak season.
    """
    conditions = []
    for period in PEAK_PERIODS:
        condition = (
            (pl.col("ship_date") >= period.start) &
            (pl.col("ship_date") <= period.end)
        )
        conditions.append(condition)

    if not conditions:
        return pl.lit(False)

    # Combine with OR
    result = conditions[0]
    for cond in conditions[1:]:
        result = result | cond

    return result


def peak_surcharge_amount() -> pl.Expr:
    """
    Polars expression that calculates peak surcharge amount based on weight and zone.

    Returns 0.0 if not in peak season.
    """
    # Build nested when/then for weight tiers and zone groups
    return (
        pl.when(pl.col("billable_weight_lbs") <= 3)
        .then(
            pl.when(pl.col("rate_zone") <= 4)
            .then(pl.lit(PEAK_RATES[(3, 4)]))
            .otherwise(pl.lit(PEAK_RATES[(3, 9)]))
        )
        .when(pl.col("billable_weight_lbs") <= 10)
        .then(
            pl.when(pl.col("rate_zone") <= 4)
            .then(pl.lit(PEAK_RATES[(10, 4)]))
            .otherwise(pl.lit(PEAK_RATES[(10, 9)]))
        )
        .when(pl.col("billable_weight_lbs") <= 25)
        .then(
            pl.when(pl.col("rate_zone") <= 4)
            .then(pl.lit(PEAK_RATES[(25, 4)]))
            .otherwise(pl.lit(PEAK_RATES[(25, 9)]))
        )
        .otherwise(
            pl.when(pl.col("rate_zone") <= 4)
            .then(pl.lit(PEAK_RATES[(70, 4)]))
            .otherwise(pl.lit(PEAK_RATES[(70, 9)]))
        )
    )


__all__ = [
    "PEAK_PERIODS",
    "PEAK_RATES",
    "PeakPeriod",
    "is_peak_season",
    "get_peak_surcharge",
    "peak_season_condition",
    "peak_surcharge_amount",
]
