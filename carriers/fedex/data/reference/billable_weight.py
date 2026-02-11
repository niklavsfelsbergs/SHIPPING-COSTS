"""
FedEx Billable Weight Configuration

FedEx Ground uses simple billable weight logic:
    billable_weight = max(actual_weight, dimensional_weight)

No threshold - dimensional weight is always considered.

Dim factors vary by service:
    - Home Delivery: 250
    - Ground Economy (SmartPost): 225

Reference: FedEx Service Guide, verified against invoice data (Dec 2025)
"""

# Dimensional weight divisors (cubic inches per pound)
# Different services use different divisors based on invoice analysis
DIM_FACTOR_HOME_DELIVERY = 250   # Ground / Home Delivery
DIM_FACTOR_GROUND_ECONOMY = 225  # Ground Economy

# Legacy single factor (kept for backwards compatibility)
DIM_FACTOR = 250
