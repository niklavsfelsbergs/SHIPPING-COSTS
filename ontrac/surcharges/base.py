"""
Surcharge Base Class

Re-exports from shared.surcharges for OnTrac surcharges.
"""

from shared.surcharges import Surcharge, in_period

__all__ = [
    "Surcharge",
    "in_period",
]
