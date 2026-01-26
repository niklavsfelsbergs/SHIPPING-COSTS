# FedEx Shipping Cost Calculator

Calculates expected shipping costs for FedEx carrier shipments, uploads them to Redshift, and compares against actual invoice costs.

**Status:** In development

---

## Quick Reference

| Task | Command |
|------|---------|
| Calculate single shipment | `python -m carriers.fedex.scripts.calculator` |
| Upload expected costs | `python -m carriers.fedex.scripts.upload_expected --incremental` |
| Upload actual costs | `python -m carriers.fedex.scripts.upload_actuals --incremental` |
| Compare expected vs actual | `python -m carriers.fedex.scripts.compare_expected_to_actuals` |
| Run tests | `pytest carriers/fedex/tests/` |

---

## Implementation Status

### Completed
- [x] Directory structure
- [x] Basic calculate_costs.py skeleton
- [x] Data loader structure
- [x] Script skeletons

### TODO
- [ ] Zone lookup implementation
- [ ] Base rate table
- [ ] Fuel surcharge configuration
- [ ] Surcharge implementations:
  - [ ] Additional Handling (AHS)
  - [ ] Oversize
  - [ ] Residential Delivery
  - [ ] Delivery Area Surcharge (DAS)
  - [ ] Peak/Demand surcharges
- [ ] Invoice data extraction (upload_actuals)
- [ ] Comparison report generation
- [ ] Full test coverage

---

## Scripts

### 1. Calculator (Interactive)

Calculate expected cost for a single shipment.

```bash
python -m carriers.fedex.scripts.calculator
```

### 2. Upload Expected Costs

Calculates expected shipping costs from PCS shipment data and uploads to the database.

```bash
# Incremental: from latest date in DB (recommended for daily use)
python -m carriers.fedex.scripts.upload_expected --incremental

# Full: recalculate everything from 2025-01-01
python -m carriers.fedex.scripts.upload_expected --full

# Last N days only
python -m carriers.fedex.scripts.upload_expected --days 7

# Preview without making changes
python -m carriers.fedex.scripts.upload_expected --incremental --dry-run
```

**Output table:** `shipping_costs.expected_shipping_costs_fedex`

### 3. Upload Actual Costs

Pulls actual costs from FedEx invoices and uploads to the database.

```bash
# Incremental: only orders without actuals
python -m carriers.fedex.scripts.upload_actuals --incremental

# Full: delete all and repull from invoices
python -m carriers.fedex.scripts.upload_actuals --full

# Last N days
python -m carriers.fedex.scripts.upload_actuals --days 7
```

**Output table:** `shipping_costs.actual_shipping_costs_fedex`

### 4. Compare Expected to Actual

Generates HTML comparison reports between expected and actual costs.

```bash
# All available data
python -m carriers.fedex.scripts.compare_expected_to_actuals

# Specific date range
python -m carriers.fedex.scripts.compare_expected_to_actuals --date_from 2025-01-01 --date_to 2025-01-31

# Specific invoice
python -m carriers.fedex.scripts.compare_expected_to_actuals --invoice ABC123
```

---

## Configuration

### Reference Data Location

```
carriers/fedex/data/reference/
├── zones.csv           # ZIP → Zone mappings
├── base_rates.csv      # Zone × Weight → Rate
├── billable_weight.py  # DIM_FACTOR = 139
├── fuel.py             # Weekly fuel surcharge rate
└── contracts/current/  # Contract PDFs
```

### Key Configuration Values

| Setting | Value | Source |
|---------|-------|--------|
| DIM Factor | 139 | FedEx Service Guide |
| DIM Threshold | 0 (always applies) | FedEx Service Guide |
| Fuel Surcharge | TBD | fedex.com weekly |

---

## Surcharges

### Planned Surcharges

| Surcharge | Description | Trigger |
|-----------|-------------|---------|
| AHS | Additional Handling | Weight/dimension thresholds |
| Oversize | Oversize Package | Length + girth > limit |
| RES | Residential Delivery | Residential address |
| DAS | Delivery Area | Remote ZIP codes |
| Peak | Demand/Peak | Seasonal periods |

### Surcharge Implementation Pattern

```python
from shared.surcharges import Surcharge
import polars as pl

class AHS(Surcharge):
    name = "AHS"
    list_price = 0.00  # TODO: Get from contract
    discount = 0.00    # TODO: Get from contract

    @classmethod
    def conditions(cls) -> pl.Expr:
        return (
            (pl.col("weight_lbs") > 50) |  # TODO: Verify threshold
            (pl.col("longest_side_in") > 48)  # TODO: Verify threshold
        )
```

---

## Database Tables

### Expected Costs Table
`shipping_costs.expected_shipping_costs_fedex`

TODO: Define schema

### Actual Costs Table
`shipping_costs.actual_shipping_costs_fedex`

TODO: Define schema

---

## Testing

```bash
# Run all FedEx tests
pytest carriers/fedex/tests/ -v

# Run specific test file
pytest carriers/fedex/tests/test_calculate_costs.py -v

# Run with coverage
pytest carriers/fedex/tests/ --cov=carriers.fedex
```

---

## Development Notes

### FedEx-Specific Considerations

1. **Dimensional Weight**: FedEx Ground uses a DIM factor of 139 (vs OnTrac's 166)

2. **Zone Structure**: FedEx zones are origin-destination based, similar to OnTrac

3. **Fuel Surcharge**: FedEx publishes weekly fuel surcharge rates based on national diesel prices

4. **Invoice Format**: Need to determine how FedEx invoice data is available and structured

### Next Steps

1. Obtain FedEx contract documents
2. Extract zone tables from contract
3. Extract base rate tables
4. Identify surcharge structure and thresholds
5. Set up invoice data extraction
6. Implement and validate surcharges one by one
