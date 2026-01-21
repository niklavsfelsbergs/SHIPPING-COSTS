# USPS Calculator Implementation Plan

Comprehensive step-by-step guide to implementing the USPS expected cost calculator.

---

## Phase 1: Research & Discovery

### 1.1 Gather Contract Documents
- [x] Obtain current USPS contract/agreement from procurement
- [x] Identify contract effective date and term
- [x] Save all documents to `data/reference/contracts/current/`

**Documents obtained:**
- `USPS_Contract_2025.pdf` - Main SSC contract
- `USPS Ground Advantage Rate Card.pdf` - Tier 1 pricing
- `USPS_zones.xlsx` - Zone charts for PHX and CMH

### 1.2 Understand USPS Pricing Structure
- [x] Identify which USPS service(s) we use:
  - [ ] Priority Mail - **NOT USED**
  - [ ] Priority Mail Express - **NOT USED**
  - [x] Ground Advantage (formerly Parcel Select Ground) - **USED**
  - [ ] Media Mail - **NOT USED**
- [x] Determine if we use Commercial Base or Commercial Plus pricing
  - **Commercial Plus (SSC Contract)**
- [ ] Identify if we use USPS directly or through a consolidator (e.g., Pitney Bowes, Stamps.com)
  - **TBD**

### 1.3 Document Rate Structure
- [x] How are base rates determined?
  - [ ] By weight only?
  - [x] By weight and zone? - **YES**
  - [ ] By weight, zone, and dimensions?
  - [ ] Flat rate options?
- [x] What is the zone system? **Zones 1-9 (with asterisk variants 1*, 2*, 3* for local)**
- [x] How is origin zone determined? **By production site ZIP (PHX or CMH)**
- [x] Are there different rate tables for different services? **Only using Ground Advantage**

### 1.4 Document Dimensional Weight Rules
- [x] What is the DIM divisor? **200** (not standard 166, per contract)
- [x] At what size threshold does DIM weight apply? **1 cubic foot (1728 cubic inches)**
- [x] Is DIM weight used for all services or only some? **Applies to Ground Advantage**

### 1.5 Identify All Surcharges & Fees
Document each surcharge with:
- Name and code
- List price
- Any negotiated discount
- Trigger conditions
- Whether it's deterministic or allocated

Common USPS surcharges to investigate:
- [x] Fuel surcharge (if any) - **None identified in contract**
- [ ] Delivery Area Surcharge / Nonstandard Delivery Area - **TBD**
- [x] Oversize / Nonmachinable surcharge - **See Nonstandard Length fees below**
- [ ] Signature confirmation fees - **TBD (likely allocated)**
- [ ] Address correction fees - **TBD (likely allocated)**
- [ ] Return/redirect fees - **TBD (likely allocated)**
- [ ] Peak/demand season surcharges - **TBD**
- [ ] Residential vs commercial (if differentiated) - **TBD**

**Identified from contract:**
| Surcharge | Trigger | Price |
|-----------|---------|-------|
| Nonstandard Length (NSL1) | Length > 22" | $4.00 |
| Nonstandard Length (NSL2) | Length > 30" | $15.00 |
| Nonstandard Volume (NSV) | > 2 cubic feet | Price TBD |

### 1.6 Identify Special Rules
- [x] Weight limits (max weight per service) - **20 lbs**
- [ ] Size limits (max dimensions per service) - **TBD**
- [ ] Combined length + girth limits - **TBD**
- [x] Any volume-based tier pricing? **Yes - Tier 1 (50K-200K units/quarter) vs Tier 2 (200K+)**
- [ ] Any minimum charges? - **TBD**

**Excluded ZIP prefixes from contract:**
003, 006, 007, 008, 009, 96, 97 (likely military/territories)

---

## Phase 2: Data Collection & Validation

### 2.1 Obtain Rate Card
- [x] Get official rate card from contract or USPS website
  - **File:** `USPS Ground Advantage Rate Card.pdf`
- [ ] Verify rates match what we're being invoiced
- [ ] Note effective dates for rate changes

### 2.2 Obtain Zone Chart
- [x] Get zone chart for each origin ZIP (production site)
- [x] Phoenix origin ZIP: **850-863 area** (Zone 1*-3* local)
- [x] Columbus origin ZIP: **430-459 area** (Zone 1*-3* local)
- [x] **Zone data saved to:** `data/reference/zones.csv`

### 2.3 Pull Sample Invoice Data
- [ ] Export 1-2 months of USPS invoices
- [ ] Identify all charge types appearing on invoices
- [ ] Map invoice line items to our surcharge model
- [ ] Note any charges we didn't anticipate

### 2.4 Pull Sample PCS Data
- [x] Verify PCS has USPS shipments with carrier extkey
- [x] Check what the extkey value is: **`USPS`**
- [ ] Verify required columns are available:
  - [ ] ship_date
  - [ ] production_site
  - [ ] shipping_zip_code
  - [ ] shipping_region (state)
  - [ ] length_in, width_in, height_in
  - [ ] weight_lbs
- [ ] Identify any USPS-specific columns needed

**Database table:** `poc_staging.usps`

---

## Phase 3: Reference Data Setup

### 3.1 Create Base Rates CSV
Location: `data/reference/base_rates.csv`

```csv
weight_lbs_lower,weight_lbs_upper,zone_1,zone_2,zone_3,zone_4,zone_5,zone_6,zone_7,zone_8,zone_9
0,1,X.XX,X.XX,X.XX,X.XX,X.XX,X.XX,X.XX,X.XX,X.XX
1,2,X.XX,X.XX,X.XX,X.XX,X.XX,X.XX,X.XX,X.XX,X.XX
...
```

- [x] Determine weight brackets: **1-20 lbs in 1 lb increments**
- [x] Determine zones: **1-9** (including local asterisk zones 1*, 2*, 3*)
- [ ] Enter rates from rate card (**Tier 1 rates from PDF**)
- [ ] Verify a few rates manually against invoices

**Note:** Asterisk zones (1*, 2*, 3*) are local zones with discounted rates.
Need to determine if they use same rates as regular zones or have separate pricing.

### 3.2 Create Zones CSV
Location: `data/reference/zones.csv`

```csv
zip_prefix,phx_zone,cmh_zone
005,8,4
006,8,7
...
```

- [x] **COMPLETED** - Created from `USPS_zones.xlsx`
- [x] Uses 3-digit ZIP prefixes (not full 5-digit)
- [x] Includes zones for both PHX and CMH origins
- [ ] Determine if DAS/remote area flags needed

**File created:** `data/reference/zones.csv` (1000 rows)

### 3.3 Configure Billable Weight
Location: `data/reference/billable_weight.py`

- [x] Set `DIM_FACTOR` = **200** (contract rate, not standard 166)
- [x] Set `DIM_THRESHOLD` = **1728** (1 cubic foot)
- [x] Verified against contract terms

**File updated:** `data/reference/billable_weight.py`

### 3.4 Configure Fuel Surcharge (if applicable)
Location: `data/reference/fuel.py`

- [x] Determine if USPS has a fuel surcharge: **No fuel surcharge identified in contract**
- [ ] This file may not be needed for USPS

---

## Phase 4: Surcharge Implementation

For each surcharge, create a file in `surcharges/`:

### 4.1 Template for Each Surcharge
```python
"""
[Surcharge Name] ([CODE])

[Description of when this surcharge applies]
"""

import polars as pl
from shared.surcharges import Surcharge


class CODE(Surcharge):
    """[Description]"""

    # Identity
    name = "CODE"

    # Pricing
    list_price = X.XX
    discount = 0.XX  # Contract discount

    # Exclusivity (if competes with other surcharges)
    # exclusivity_group = "group_name"
    # priority = 1

    # Side effects (if triggers minimum billable weight)
    # min_billable_weight = XX

    @classmethod
    def conditions(cls) -> pl.Expr:
        return (
            # Polars expression for when surcharge applies
            pl.lit(False)  # Replace with actual conditions
        )
```

### 4.2 Surcharges to Implement
Based on Phase 1 research, create each surcharge file:

**Confirmed from contract:**
- [ ] `surcharges/nonstandard_length_22.py` - NSL1: Length > 22", $4.00
- [ ] `surcharges/nonstandard_length_30.py` - NSL2: Length > 30", $15.00
- [ ] `surcharges/nonstandard_volume.py` - NSV: > 2 cubic feet, price TBD

**To investigate from invoices:**
- [ ] `surcharges/_____________.py` (additional surcharges TBD)

### 4.3 Update Surcharges Registry
Update `surcharges/__init__.py`:
- [ ] Import all surcharge classes
- [ ] Add to `ALL` list
- [ ] Verify validation passes on import

---

## Phase 5: Calculator Implementation

### 5.1 Update Data Package
File: `data/__init__.py`

- [ ] Uncomment/implement `load_rates()`
- [ ] Uncomment/implement `load_zones()`
- [ ] Export all config values

### 5.2 Implement supplement_shipments()
File: `calculate_costs.py`

- [ ] `_add_calculated_dimensions()` - cubic_in, longest_side, etc.
- [ ] `_lookup_zones()` - zone lookup with fallback logic
- [ ] `_add_billable_weight()` - DIM weight calculation

### 5.3 Implement calculate()
File: `calculate_costs.py`

- [ ] `_apply_surcharges()` - apply BASE then DEPENDENT surcharges
- [ ] `_apply_exclusive_group()` - handle mutually exclusive surcharges
- [ ] `_apply_min_billable_weights()` - enforce minimums from surcharges
- [ ] `_lookup_base_rate()` - join to rate table
- [ ] `_calculate_subtotal()` - sum base + surcharges
- [ ] `_apply_fuel()` - if applicable
- [ ] `_calculate_total()` - final total
- [ ] `_stamp_version()` - add version stamp

### 5.4 Test Basic Calculation
- [ ] Create simple test shipment
- [ ] Run through calculator
- [ ] Verify output columns exist
- [ ] Verify a known shipment matches expected cost

---

## Phase 6: Testing

### 6.1 Unit Tests
File: `tests/test_calculate_costs.py`

Implement tests for:
- [ ] `TestSupplementShipments`
  - [ ] Cubic inch calculation
  - [ ] Longest side calculation
  - [ ] Zone lookup (each origin)
  - [ ] DIM weight calculation
  - [ ] Billable weight selection

- [ ] `TestSurchargeFlags`
  - [ ] Each surcharge trigger condition
  - [ ] Mutual exclusivity (if any)
  - [ ] Allocated surcharges

- [ ] `TestCostCalculations`
  - [ ] Base rate lookup
  - [ ] Surcharge costs
  - [ ] Subtotal calculation
  - [ ] Fuel calculation (if applicable)
  - [ ] Total calculation

- [ ] `TestVersionStamp`
  - [ ] Version is stamped on output

### 6.2 Run Tests
```bash
pytest carriers/usps/tests/ -v
```

- [ ] All tests pass
- [ ] No skipped tests remain

---

## Phase 7: Scripts Implementation

### 7.1 Interactive Calculator
File: `scripts/calculator.py`

- [ ] Prompt for shipment details
- [ ] Display calculated cost breakdown
- [ ] Show which surcharges triggered

### 7.2 Upload Expected
File: `scripts/upload_expected.py`

- [ ] Implement `--full` mode (recalculate all from start date)
- [ ] Implement `--incremental` mode (from last DB date)
- [ ] Implement `--days N` mode
- [ ] Implement `--dry-run` mode
- [ ] Create target table in Redshift if needed
- [ ] Test upload with small batch

### 7.3 Compare Expected to Actuals
File: `scripts/compare_expected_to_actuals.py`

- [ ] Load expected costs from DB
- [ ] Load actual costs from invoice table
- [ ] Join on shipment ID
- [ ] Calculate differences
- [ ] Generate summary report
- [ ] Flag significant variances

---

## Phase 8: Validation & Calibration

### 8.1 Historical Validation
- [ ] Calculate expected costs for 1+ months of historical shipments
- [ ] Compare to actual invoice totals
- [ ] Target: within 2-3% of actual

### 8.2 Investigate Variances
For significant variances:
- [ ] Pull sample mismatched shipments
- [ ] Compare line-by-line with invoice
- [ ] Identify root cause:
  - [ ] Missing surcharge?
  - [ ] Wrong rate?
  - [ ] Wrong zone?
  - [ ] Weight/dimension discrepancy?

### 8.3 Calibrate
- [ ] Adjust any misconfigured rates/surcharges
- [ ] Re-run validation
- [ ] Document any known limitations

### 8.4 Document Allocation Rates
For non-deterministic surcharges:
- [ ] Calculate historical application rate
- [ ] Set `allocation_rate` in surcharge class
- [ ] Document basis for rate

---

## Phase 9: Documentation & Handoff

### 9.1 Update README
- [ ] Document all configuration files
- [ ] Document all surcharges implemented
- [ ] Add troubleshooting section

### 9.2 Create Maintenance Guide
File: `maintenance/README.md`

Document procedures for:
- [ ] Updating base rates (annual/periodic)
- [ ] Updating zones (if needed)
- [ ] Updating surcharge prices
- [ ] Updating fuel rate (if applicable)
- [ ] Adding new surcharges

### 9.3 Version Control
- [ ] Commit all files
- [ ] Tag release version

---

## Checklist Summary

### Phase 1: Research & Discovery
- [x] Contract documents gathered
- [x] Pricing structure understood
- [ ] All surcharges identified (partial - need invoice data)
- [x] Special rules documented

### Phase 2: Data Collection
- [x] Rate card obtained
- [x] Zone charts obtained
- [ ] Sample data validated

### Phase 3: Reference Data
- [ ] `base_rates.csv` created (need to extract from PDF)
- [x] `zones.csv` created
- [x] `billable_weight.py` configured
- [x] `fuel.py` configured (not needed - no fuel surcharge)

### Phase 4: Surcharges
- [ ] All surcharge classes created
- [ ] Surcharge registry updated
- [ ] Validation passes

### Phase 5: Calculator
- [ ] `supplement_shipments()` implemented
- [ ] `calculate()` implemented
- [ ] Basic calculation works

### Phase 6: Testing
- [ ] All unit tests written
- [ ] All tests pass

### Phase 7: Scripts
- [ ] Calculator script works
- [ ] Upload script works
- [ ] Comparison script works

### Phase 8: Validation
- [ ] Historical validation < 3% variance
- [ ] Variances investigated
- [ ] Allocation rates calibrated

### Phase 9: Documentation
- [ ] README complete
- [ ] Maintenance guide complete
- [ ] Code committed

---

## Notes

_Use this section to capture decisions, assumptions, and open questions during implementation._

### Decisions Made
- Use Ground Advantage only (not Priority Mail)
- DIM factor is 200 (contract rate, not USPS standard 166)
- Zone lookup uses 3-digit ZIP prefixes

### Assumptions
- Tier 1 pricing applies (50K-200K units/quarter)
- Asterisk zones (1*, 2*, 3*) use same rates as regular zones (need to verify)
- No fuel surcharge for USPS Ground Advantage

### Open Questions
- Do asterisk zones have different pricing than regular numbered zones?
- What is the Nonstandard Volume (NSV) fee amount?
- Are there any DAS (Delivery Area Surcharge) equivalents?
- What surcharges appear on actual invoices that aren't in the contract?
- Is there peak/demand season pricing?

### Known Limitations
- Excluded ZIP prefixes (003, 006-009, 96, 97) - likely military/territories
- Max weight: 20 lbs per package
- Zone 9 only applies to ZIP 969 (Guam)
