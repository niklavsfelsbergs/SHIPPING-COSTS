"""
Fuel Surcharge

Updated weekly from ontrac.com/surcharges.
Last updated: 2025-12-05
"""

LIST_RATE = 0.195             # 19.5%
DISCOUNT = 0.35               # 35% contract discount
RATE = LIST_RATE * (1 - DISCOUNT)

APPLICATION = "LAST"          # Applied to subtotal after all other surcharges
