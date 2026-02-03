"""
Billable Weight Configuration

Maersk US uses DIM weight with factor 166 and no threshold -
always compares actual vs dimensional weight and uses the higher.
"""

DIM_FACTOR = 166
DIM_THRESHOLD = 0  # No threshold - always compare actual vs DIM
THRESHOLD_FIELD = "cubic_in"
FACTOR_FIELD = "cubic_in"
