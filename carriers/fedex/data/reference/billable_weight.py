"""
FedEx Billable Weight Configuration

FedEx Ground uses simple billable weight logic:
    billable_weight = max(actual_weight, dimensional_weight)

No threshold - dimensional weight is always considered.

Reference: FedEx Service Guide, verified against invoice data
"""

# Dimensional weight divisor (cubic inches per pound)
# FedEx Ground standard is 139
DIM_FACTOR = 139
