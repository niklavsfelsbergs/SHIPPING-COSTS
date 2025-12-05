"""
Billable Weight Configuration

Contract: DIM Factor 250 (standard OnTrac is 139)
Last updated: 2025-12-05
"""

DIM_FACTOR = 250              # Cubic inches per pound
DIM_THRESHOLD = 1728          # Min value to apply dimensional weight

# Fields used in calculation
THRESHOLD_FIELD = "cubic_in"  # Compare this field against DIM_THRESHOLD
FACTOR_FIELD = "cubic_in"     # Divide this field by DIM_FACTOR for dim weight
