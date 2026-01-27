---
description: Compare FedEx calculated costs to invoice actuals
---

Run the FedEx comparison script to compare calculator output against invoice actuals.

## Command

```bash
python carriers/fedex/development/run_comparison.py
```

## What It Does

1. Loads invoice data from `carriers/fedex/development/invoice_data.parquet` (Sep-Dec 2025)
2. Loads PCS shipments with extended date range (+/- 1 month to catch all matches)
3. Runs PCS data through `calculate_costs()`
4. Joins on tracking number (HD uses `trackingnumber`, SmartPost uses `pcs_trackingnumber`)
5. Prints monthly comparison for each cost position

## Cost Positions Compared

| Position | Calculator Columns | Invoice charge_description |
|----------|-------------------|---------------------------|
| Base (after discounts) | `cost_base_rate + cost_performance_pricing + cost_earned_discount + cost_grace_discount` | `Base Charge` + `Performance Pricing` + `Earned Discount` + `Grace Discount` |
| DAS | `cost_das` | Any containing `DAS` or `Delivery Area Surcharge` |
| Residential | `cost_residential` | `Residential` |

## Expected Output

```
FedEx Cost Comparison (Sep 2025 - Dec 2025)
==========================================

Base (after discounts):
Month      |   Expected |     Actual | Variance $ | Variance %
----------|-----------|-----------|------------|------------
2025-09    | $   64,864 | $   50,150 | +$   14,714 | +    29.34%
2025-10    | $   45,529 | $   42,381 | +$    3,148 | +     7.43%
...
----------|-----------|-----------|------------|------------
TOTAL      | $  302,560 | $  279,063 | +$   23,497 | +     8.42%

DAS:
Month      |   Expected |     Actual | Variance $ | Variance %
----------|-----------|-----------|------------|------------
2025-09    | $    6,986 | $    7,150 | $     -164 |     -2.29%
...
----------|-----------|-----------|------------|------------
TOTAL      | $   44,896 | $   45,354 | $     -458 |     -1.01%

Residential:
Month      |   Expected |     Actual | Variance $ | Variance %
----------|-----------|-----------|------------|------------
2025-09    | $    9,241 | $    9,241 | +$        0 | +     0.00%
...
----------|-----------|-----------|------------|------------
TOTAL      | $   32,230 | $   32,234 | $       -4 |     -0.01%

(Base = cost_base_rate + cost_performance_pricing + cost_earned_discount + cost_grace_discount)
```

## Notes

- **Positive variance** = calculator overestimates (expected > actual)
- **Negative variance** = calculator underestimates (actual > expected)
