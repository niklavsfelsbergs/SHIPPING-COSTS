"""
Billable Weight Configuration

Contract: DIM Factor 250 (standard OnTrac is 139)
Last updated: 2025-12-05

HOW DIM WEIGHT WORKS
--------------------
Billable weight = max(actual_weight, dim_weight) when package exceeds threshold.

The calculation uses two configurable fields:
- THRESHOLD_FIELD: If this value > DIM_THRESHOLD, we consider DIM weight
- FACTOR_FIELD: dim_weight = FACTOR_FIELD / DIM_FACTOR

Current config uses cubic_in for both:
- If cubic_in > 1728 (1 cubic foot), check if DIM weight applies
- dim_weight = cubic_in / 250

These are separate fields because some carriers use different dimensions
for the threshold check vs the weight calculation.
"""

DIM_FACTOR = 250              # Cubic inches per pound
DIM_THRESHOLD = 1728          # Min value to apply dimensional weight

# Fields used in calculation (see docstring for explanation)
THRESHOLD_FIELD = "cubic_in"  # Compare this field against DIM_THRESHOLD
FACTOR_FIELD = "cubic_in"     # Divide this field by DIM_FACTOR for dim weight
