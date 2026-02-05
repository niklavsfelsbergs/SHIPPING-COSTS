"""
Fuel Surcharge

Updated weekly from ontrac.com/surcharges.
Last updated: 2026-02-05
"""

LIST_RATE = 0.1925            # 19.25%
DISCOUNT = 0.35               # 35% contract discount
RATE = LIST_RATE * (1 - DISCOUNT)

APPLICATION = "LAST"          # Applied to subtotal after all other surcharges
