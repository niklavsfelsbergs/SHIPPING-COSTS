"""
Fuel Surcharge

Updated weekly from ontrac.com/surcharges.
Last updated: 2026-01-21
"""

LIST_RATE = 0.1875            # 18.75%
DISCOUNT = 0.35               # 35% contract discount
RATE = LIST_RATE * (1 - DISCOUNT)

APPLICATION = "LAST"          # Applied to subtotal after all other surcharges
