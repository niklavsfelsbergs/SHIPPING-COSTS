"""
Surcharges Package

Exports all surcharge classes and processing groups.

Processing Order:
    1. BASE      - surcharges that don't reference other surcharge flags
    2. DEPENDENT - surcharges that reference other surcharge flags (via depends_on)

Within each phase, surcharges with the same exclusivity_group compete -
only the highest priority (lowest number) wins.
"""

from .base import Surcharge, in_period
from .over_maximum_limits import OML
from .large_package import LPS
from .additional_handling import AHS
from .delivery_area import DAS
from .extended_delivery_area import EDAS
from .residential import RES
from .demand_residential import DEM_RES
from .demand_additional_handling import DEM_AHS
from .demand_large_package import DEM_LPS
from .demand_over_maximum_limits import DEM_OML


# All surcharges
ALL = [OML, LPS, AHS, DAS, EDAS, RES, DEM_RES, DEM_AHS, DEM_LPS, DEM_OML]


# =============================================================================
# PROCESSING GROUPS
# =============================================================================

# Phase 1: Base surcharges (don't reference other surcharge flags)
BASE = [s for s in ALL if s.depends_on is None]
# OnTrac: [OML, LPS, AHS, DAS, EDAS, RES]

# Phase 2: Dependent surcharges (reference flags from phase 1)
DEPENDENT = [s for s in ALL if s.depends_on is not None]
# OnTrac: [DEM_RES, DEM_AHS, DEM_LPS, DEM_OML]


# =============================================================================
# HELPERS
# =============================================================================

def get_exclusivity_group(group: str) -> list[type[Surcharge]]:
    """Get surcharges in an exclusivity group, sorted by priority (lowest first)."""
    return sorted(
        [s for s in ALL if s.exclusivity_group == group],
        key=lambda s: s.priority
    )


def get_unique_exclusivity_groups(surcharges: list) -> set[str]:
    """Get unique exclusivity group names from a list of surcharges."""
    return {s.exclusivity_group for s in surcharges if s.exclusivity_group is not None}


# =============================================================================
# VALIDATION
# =============================================================================

def validate_surcharges() -> None:
    """
    Validate surcharge configuration integrity.

    Raises ValueError if any configuration issues are found.
    Called at import time to fail fast on configuration errors.
    """
    names = {s.name for s in ALL}
    errors = []

    for s in ALL:
        # Check dependency references a valid surcharge
        if s.depends_on is not None and s.depends_on not in names:
            errors.append(f"{s.name}: depends_on '{s.depends_on}' not found in ALL")

        # Check allocated surcharges have allocation_rate
        if s.is_allocated and s.allocation_rate is None:
            errors.append(f"{s.name}: is_allocated=True requires allocation_rate")

        # Check non-allocated surcharges don't have allocation_rate
        if not s.is_allocated and s.allocation_rate is not None:
            errors.append(f"{s.name}: is_allocated=False should not have allocation_rate")

        # Check exclusivity_group surcharges have priority defined
        if s.exclusivity_group is not None and s.priority is None:
            errors.append(f"{s.name}: exclusivity_group '{s.exclusivity_group}' requires priority")

        # Check demand surcharges have both period_start and period_end
        if (s.period_start is None) != (s.period_end is None):
            errors.append(f"{s.name}: must have both period_start and period_end, or neither")

    if errors:
        raise ValueError("Surcharge configuration errors:\n  " + "\n  ".join(errors))


# Run validation at import time
validate_surcharges()

__all__ = [
    # Base
    "Surcharge",
    "in_period",
    # Surcharge classes
    "OML",
    "LPS",
    "AHS",
    "DAS",
    "EDAS",
    "RES",
    "DEM_RES",
    "DEM_AHS",
    "DEM_LPS",
    "DEM_OML",
    # Lists
    "ALL",
    "BASE",
    "DEPENDENT",
    # Helpers
    "get_exclusivity_group",
    "get_unique_exclusivity_groups",
]
