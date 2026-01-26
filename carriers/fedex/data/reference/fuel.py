"""
FedEx Fuel Surcharge Configuration

FedEx publishes weekly fuel surcharge rates based on the
U.S. Energy Information Administration's weekly national
average diesel fuel price.

The fuel surcharge is applied as a percentage of the
transportation charges (base rate + most surcharges).

Update frequency: Weekly (check every Monday)
Source: https://www.fedex.com/en-us/shipping/fuel-surcharge.html
"""

# Current fuel surcharge rate (as percentage, e.g., 0.12 = 12%)
# TODO: Update with actual contracted fuel surcharge rate
LIST_RATE = 0.12  # Placeholder - check FedEx fuel surcharge page

# Contractual fuel discount (if applicable)
DISCOUNT = 0.0

# Net fuel rate after discount
RATE = LIST_RATE * (1 - DISCOUNT)
