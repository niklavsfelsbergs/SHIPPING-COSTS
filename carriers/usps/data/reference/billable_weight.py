"""
Billable Weight Configuration

USPS Ground Advantage dimensional weight rules from contract.
"""

# Contract specifies DIM divisor of 200 (not standard 166)
DIM_FACTOR = 200              # Cubic inches per pound (contract rate)
DIM_THRESHOLD = 1728          # Min value to apply dimensional weight (1 cubic foot)

# Fields used in calculation
THRESHOLD_FIELD = "cubic_in"  # Compare this field against DIM_THRESHOLD
FACTOR_FIELD = "cubic_in"     # Divide this field by DIM_FACTOR for dim weight
