"""
FedEx Billable Weight Configuration

TODO: Get actual DIM factor and threshold from FedEx contract.

Reference: FedEx contract documents
"""

# Dimensional weight divisor (cubic inches per pound)
# TODO: Get from contract - common values are 139 (standard) or negotiated
DIM_FACTOR = 139  # PLACEHOLDER - verify with contract

# Dimensional weight threshold
# TODO: Get from contract - some contracts have minimum cubic size
DIM_THRESHOLD = 0  # PLACEHOLDER - verify with contract
