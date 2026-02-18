"""
P2P US2 Surcharges Package

Two service types, each with their own surcharges:
    - PFA: pfa_oversize, pfa_oversize_volume
    - PFS: pfs_nonstandard_length, pfs_nonstandard_volume

No mutual exclusivity, no dependencies.
"""

from shared.surcharges import Surcharge

from .pfa_oversize import PFA_OVERSIZE
from .pfa_oversize_volume import PFA_OVERSIZE_VOLUME
from .pfs_nonstandard_length import PFS_NONSTANDARD_LENGTH
from .pfs_nonstandard_volume import PFS_NONSTANDARD_VOLUME


# PFA surcharges (applied only in PFA cost calculation)
PFA_ALL = [PFA_OVERSIZE, PFA_OVERSIZE_VOLUME]

# PFS surcharges (applied only in PFS cost calculation)
PFS_ALL = [PFS_NONSTANDARD_LENGTH, PFS_NONSTANDARD_VOLUME]


__all__ = [
    "Surcharge",
    "PFA_OVERSIZE",
    "PFA_OVERSIZE_VOLUME",
    "PFS_NONSTANDARD_LENGTH",
    "PFS_NONSTANDARD_VOLUME",
    "PFA_ALL",
    "PFS_ALL",
]
