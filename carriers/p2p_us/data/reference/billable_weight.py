"""
Billable Weight Configuration

P2P US uses DIM weight with factor 250 and no threshold -
always compares actual vs dimensional weight and uses the higher.
"""

DIM_FACTOR = 250
DIM_THRESHOLD = 0  # No threshold - always compare actual vs DIM
THRESHOLD_FIELD = "cubic_in"
FACTOR_FIELD = "cubic_in"
