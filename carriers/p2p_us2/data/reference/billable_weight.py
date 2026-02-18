"""
Billable Weight Configuration

P2P US2 uses DIM factor 166 for both PFA and PFS.

PFA: DIM applies when cubic_in > 1728 (1 cu ft) AND weight_lbs > 1.
PFS: DIM applies when cubic_in > 1728 (1 cu ft).
"""

# PFA: DIM factor 166, threshold 1728 cu in (1 cu ft), only when weight > 1 lb
PFA_DIM_FACTOR = 166
PFA_DIM_THRESHOLD = 1728  # cubic inches (1 cu ft)
PFA_DIM_WEIGHT_THRESHOLD = 1.0  # DIM only applies when weight > 1 lb

# PFS: DIM factor 166, threshold 1728 cu in (1 cu ft)
PFS_DIM_FACTOR = 166
PFS_DIM_THRESHOLD = 1728  # cubic inches (1 cu ft)
