"""
Billable Weight Configuration

Maersk US dimensional weight rules:
- If cubic inches <= 1728: use actual scale weight
- If cubic inches > 1728: use max(actual weight, dimensional weight)

DIM factor is 166 (industry standard).
"""

DIM_FACTOR = 166
DIM_THRESHOLD = 1728  # 1 cubic foot - threshold for DIM weight comparison
THRESHOLD_FIELD = "cubic_in"
FACTOR_FIELD = "cubic_in"
