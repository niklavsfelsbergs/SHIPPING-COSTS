"""
FedEx Fuel Surcharge Configuration

FedEx publishes weekly fuel surcharge rates based on the
U.S. Energy Information Administration's weekly national
average diesel fuel price.

The fuel surcharge is applied as a percentage of the
transportation charges (base rate + surcharges, excluding discounts).

Update frequency: Weekly (check every Monday)
Source: https://www.fedex.com/en-us/shipping/fuel-surcharge.html
Last updated: 2026-01-27
"""

LIST_RATE = 0.10              # ~10% average for Sep-Dec 2025
DISCOUNT = 0.0                # No contractual fuel discount
RATE = LIST_RATE * (1 - DISCOUNT)

APPLICATION = "BASE_PLUS_SURCHARGES"  # Excludes performance pricing discounts
