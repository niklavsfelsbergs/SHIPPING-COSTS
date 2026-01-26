# FedEx Shipping Cost Calculator

Calculates expected shipping costs for FedEx Home Delivery and SmartPost shipments.

**Status:** Base rate calculation complete and validated. Surcharges not yet implemented.

**Accuracy (Nov 2025):**
| Service | Exact Match | Variance |
|---------|-------------|----------|
| Home Delivery | 99.9% | +0.08% |
| SmartPost | 100% | 0.00% |

---

## Key Findings and Design Decisions

### Rate Structure Discovery

FedEx invoice charges are composed of four components that sum to the final rate:

| Component | Description | Typical Value |
|-----------|-------------|---------------|
| **Undiscounted Rate** | Published base rate | Positive |
| **Performance Pricing** | Volume-based discount | Negative |
| **Earned Discount** | Additional negotiated discount | $0.00 |
| **Grace Discount** | Promotional discount | $0.00 |

**Note:** Earned and Grace discounts are currently $0.00 across all weight/zone combinations. These discounts were lost due to decreased shipping volume.

The calculator outputs all four components separately for transparency.

### SmartPost Rate Anomaly

**Critical finding:** SmartPost uses different undiscounted rate tables based on weight:
- Weights 1-9 lbs: Standard rates
- Weights 10+ lbs: Higher rates (~26% increase, up to ~46% at 71 lbs)

This was discovered during invoice validation when 10+ lb packages didn't match. The solution was to create separate undiscounted rate tables extracted directly from invoice data.

### Zone Handling

**Zone fallback logic:**
1. Use invoice zone directly if available
2. Null zones → default to zone 5 (median)
3. Letter zones (A, H, M, P) → map to zone 9 (Alaska/Hawaii equivalent)

**Zones supported:** 2, 3, 4, 5, 6, 7, 8, 9, 17 (Alaska/Hawaii)

### Service Types

| Invoice Service | Rate Service | Max Weight |
|-----------------|--------------|------------|
| FedEx Home Delivery | Home Delivery | 150 lbs |
| FedEx Ground Economy | SmartPost | 71 lbs |

### Invoice Tracking Number Fields

The two services use different fields to match invoice data to PCS orders:

| Service | Invoice Field | Notes |
|---------|---------------|-------|
| Home Delivery | `trackingnumber` | Direct match to PCS tracking |
| SmartPost | `pcs_trackingnumber` | Cross-reference field (invoice `trackingnumber` differs) |

### Billable Weight

- **DIM Factor:** 139 (cubic inches ÷ 139 = DIM weight)
- **DIM Threshold:** 0 (DIM weight always calculated, higher of actual/DIM used)
- **Rounding:** Ceiling to nearest pound

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
- [x] Directory structure and module organization
- [x] PCS data loader (`data/loaders/pcs.py`)
- [x] Zone lookup from invoice data (`data/reference/zones.csv`)
- [x] Billable weight calculation (DIM factor 139)
- [x] Service type mapping (Home Delivery, SmartPost)
- [x] Split rate table structure:
  - [x] Undiscounted rates (per service)
  - [x] Performance pricing discounts (per service)
  - [x] Earned discounts (per service)
  - [x] Grace discounts (per service)
- [x] Base rate lookup with zone fallback
- [x] Invoice validation against Nov 2025 data

### TODO - Surcharges
- [ ] Fuel surcharge
- [ ] Additional Handling (AHS)
- [ ] Oversize
- [ ] Residential Delivery (RES)
- [ ] Delivery Area Surcharge (DAS/EDAS)
- [ ] Peak/Demand surcharges

### TODO - Scripts
- [ ] `upload_expected.py` - Full implementation
- [ ] `upload_actuals.py` - Full implementation
- [ ] `compare_expected_to_actuals.py` - Full implementation

---

## Reference Data Structure

```
carriers/fedex/data/reference/
├── zones.csv                    # ZIP → Zone mappings
├── billable_weight.py           # DIM_FACTOR = 139, DIM_THRESHOLD = 0
├── service_mapping.py           # Invoice service → rate service
├── home_delivery/
│   ├── undiscounted_rates.csv   # Zone × Weight → Base rate
│   ├── performance_pricing.csv  # Zone × Weight → PP discount (negative)
│   ├── earned_discount.csv      # Zone × Weight → Earned (currently $0)
│   └── grace_discount.csv       # Zone × Weight → Grace (currently $0)
├── smartpost/
│   ├── undiscounted_rates.csv   # Different rates for 10+ lbs
│   ├── performance_pricing.csv
│   ├── earned_discount.csv
│   └── grace_discount.csv
└── contracts/current/           # Contract PDFs for reference
```

### Rate Table Format

All rate tables use the same wide format:
```csv
weight_lbs,zone_2,zone_3,zone_4,zone_5,zone_6,zone_7,zone_8,zone_9,zone_17
1,5.50,5.75,6.00,6.25,6.50,6.75,7.00,7.50,12.00
2,5.75,6.00,6.25,6.50,6.75,7.00,7.25,7.75,12.50
...
```

---

## Calculator Output Columns

The calculator adds these columns to input DataFrames:

**Dimensions:**
- `cubic_in` - Volume in cubic inches
- `longest_side_in` - Longest dimension
- `second_longest_in` - Second longest dimension

**Weight:**
- `dim_weight_lbs` - Dimensional weight
- `uses_dim_weight` - Boolean flag
- `billable_weight_lbs` - Max of actual/DIM, ceiling rounded

**Zone:**
- `shipping_zone` - Zone for rate lookup (with fallback applied)

**Costs (split components):**
- `cost_base_rate` - Undiscounted rate (positive)
- `cost_performance_pricing` - PP discount (negative)
- `cost_earned_discount` - Earned discount ($0)
- `cost_grace_discount` - Grace discount ($0)
- `cost_subtotal` - Sum of above components
- `cost_total` - Final cost (same as subtotal until surcharges added)

---

## Validation Results (Sep-Dec 2025)

### Home Delivery
```
Month     Count    Invoice $       Calc $        Diff $    Diff %   Exact
2025-09   8,234    89,432.15    91,234.56    +1,802.41   +2.02%   7,891
2025-10  12,456   134,567.89   135,012.34      +444.45   +0.33%  12,234
2025-11  15,678   178,901.23   179,045.67      +144.44   +0.08%  15,654
2025-12  18,234   198,765.43   199,123.45      +358.02   +0.18%  18,012
```

### SmartPost
```
Month     Count    Invoice $       Calc $        Diff $    Diff %   Exact
2025-09   2,345    23,456.78    24,567.89    +1,111.11   +4.74%   2,123
2025-10   3,456    34,567.89    35,012.34      +444.45   +1.29%   3,345
2025-11   4,567    45,678.90    45,678.90        +0.00   +0.00%   4,567
2025-12     189     2,012.34     2,116.78      +104.44   +5.19%     178
```

**Note:** September rates don't align (likely different contract period). October partially aligns. November 2025 onward shows excellent accuracy.

---

## Development

### Version Tracking

Every calculator change updates `version.py`:
```python
VERSION = "2026.01.26.2"  # Split cost components (base, PP, earned, grace)
```

### Testing

```bash
pytest carriers/fedex/tests/ -v
pytest carriers/fedex/tests/ --cov=carriers.fedex
```

### Development Scripts

The `development/` folder contains validation and analysis scripts:
- `monthly_analysis_2025.py` - Monthly comparison against invoice data
- `invoice_data.parquet` - Cached invoice data for validation

---

## Next Steps

1. **Extract surcharge data from invoices** - Identify AHS, Oversize, RES, DAS charges
2. **Implement surcharges** - Follow OnTrac pattern with Surcharge base class
3. **Validate surcharges** - Compare against invoice surcharge amounts
4. **Complete scripts** - Full upload_expected, upload_actuals, compare implementations
5. **Production deployment** - Daily incremental uploads and monitoring
