"""
Surcharges Package

Exports all surcharge classes and processing order groups.

Processing Order:
    1. INDEPENDENT_UNGROUPED  - no dependency, no priority group
    2. INDEPENDENT_GROUPED    - no dependency, has priority group (mutual exclusivity)
    3. DEPENDENT_UNGROUPED    - has dependency, no priority group
    4. DEPENDENT_GROUPED      - has dependency, has priority group (mutual exclusivity)
"""

from .base import Surcharge
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
# PROCESSING ORDER GROUPS
# =============================================================================

# Group 1: No dependency, no priority group
INDEPENDENT_UNGROUPED = [
    s for s in ALL
    if s.depends_on is None and s.priority_group is None
]
# OnTrac: [RES]

# Group 2: No dependency, has priority group
INDEPENDENT_GROUPED = [
    s for s in ALL
    if s.depends_on is None and s.priority_group is not None
]
# OnTrac: [OML, LPS, AHS, DAS, EDAS]

# Group 3: Has dependency, no priority group
DEPENDENT_UNGROUPED = [
    s for s in ALL
    if s.depends_on is not None and s.priority_group is None
]
# OnTrac: [DEM_RES, DEM_AHS, DEM_LPS, DEM_OML]

# Group 4: Has dependency, has priority group
DEPENDENT_GROUPED = [
    s for s in ALL
    if s.depends_on is not None and s.priority_group is not None
]
# OnTrac: []


# =============================================================================
# HELPERS
# =============================================================================

def get_by_priority_group(group: str) -> list[type[Surcharge]]:
    """Get surcharges in a priority group, sorted by priority (lowest number first)."""
    return sorted(
        [s for s in ALL if s.priority_group == group],
        key=lambda s: s.priority
    )


def get_unique_priority_groups(surcharges: list) -> list[str]:
    """Get unique priority group names from a list of surcharges."""
    groups = set(s.priority_group for s in surcharges if s.priority_group is not None)
    return list(groups)
