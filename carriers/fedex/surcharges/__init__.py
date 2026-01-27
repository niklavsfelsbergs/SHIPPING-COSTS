"""
FedEx Surcharges Package

Exports all surcharge classes and processing groups.

Processing Order:
    1. BASE      - surcharges that don't reference other surcharge flags
    2. DEPENDENT - surcharges that reference other surcharge flags (via depends_on)

Within each phase, surcharges with the same exclusivity_group compete -
only the highest priority (lowest number) wins.

Common FedEx surcharges to implement:
- Additional Handling (AHS) - weight/dimensions exceed thresholds
- Oversize (OS) - length + girth exceeds limits
- Residential Delivery (RES) - delivery to residential addresses
- Delivery Area Surcharge (DAS) - remote/extended areas
- Peak/Demand surcharges - seasonal surcharges

Usage:
    from carriers.fedex.surcharges import ALL, BASE, DEPENDENT
"""

from shared.surcharges import Surcharge, in_period
from .das import DAS
from .residential import Residential
from .additional_handling import AHS
from .additional_handling_weight import AHS_Weight
from .oversize import Oversize
from .demand_ahs import DEM_AHS
from .demand_base import DEM_Base
from .demand_oversize import DEM_Oversize


# All surcharges - add classes here as they are implemented
# Note: Order matters for exclusivity groups - Oversize > AHS_Weight > AHS
ALL: list[type[Surcharge]] = [
    DAS, Residential, Oversize, AHS_Weight, AHS,
    DEM_Base, DEM_AHS, DEM_Oversize
]


# =============================================================================
# PROCESSING GROUPS
# =============================================================================
#
# Surcharges are processed in two phases because demand surcharges (DEM_*)
# depend on base surcharge flags. For example, DEM_AHS only applies when
# surcharge_ahs=True AND ship_date is in demand period.
#
# Phase 1 creates the flags, Phase 2 references them via depends_on.

# Phase 1: Base surcharges (don't reference other surcharge flags)
BASE = [s for s in ALL if s.depends_on is None]

# Phase 2: Dependent surcharges (reference flags from phase 1)
DEPENDENT = [s for s in ALL if s.depends_on is not None]


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
    if not ALL:
        return  # Skip validation if no surcharges defined yet

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
    "AHS",
    "AHS_Weight",
    "DAS",
    "DEM_AHS",
    "DEM_Base",
    "DEM_Oversize",
    "Oversize",
    "Residential",
    # Lists
    "ALL",
    "BASE",
    "DEPENDENT",
    # Helpers
    "get_exclusivity_group",
    "get_unique_exclusivity_groups",
]
