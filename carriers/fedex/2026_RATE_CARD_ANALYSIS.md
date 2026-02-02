# FedEx Rate Card 2026 - Structure Analysis

**File:** `carriers/fedex/temp_files/FedEx Rate Card 2026.xlsx`
**Analyzed:** 2026-02-02
**Effective Date:** November 4, 2025
**Customer:** Picanova Inc.

---

## Executive Summary

The 2026 FedEx Rate Card contains NET rates (after discounts applied) in a single Excel sheet with multiple service sections. This differs from the current reference file structure which stores undiscounted rates and applies discounts as separate components.

**Key Differences from Current Implementation:**
1. **Discount Structure:** 2026 rates show net prices (post-discount), current files store list prices + separate discount files
2. **Additional Zones:** 2026 includes many zones not in current system (14, 22, 23, 25, 92, 96 for Ground/HD; 10, 26, 99 for Economy)
3. **Consolidated Format:** Single Excel file vs. separate CSV files per service and discount type

---

## Document Structure

### Overall Format
- **Single Sheet:** "Report"
- **Total Rows:** 1,941
- **Services Included:**
  - FedEx Express services (Priority Overnight, Standard Overnight, 2Day, etc.)
  - FedEx Ground Domestic Single Piece
  - FedEx Home Delivery Domestic Single Piece
  - FedEx Ground Economy (SmartPost replacement)

### Header Information (Rows 1-35)
```
Customer: Picanova Inc.
Effective Date: 04 November 2025
Created On: 14 January 2026
Country ID: 488838028
Account Status: 'Delete' status (rates may not apply unless reactivated)
```

**Important Disclaimer (Row 11):**
> "Net rates are not legally binding... In the event of a conflict between any net rates and any actual invoiced amount, the actual invoiced amount shall always prevail."

---

## Rate Sections

### 1. Ground Domestic Single Piece (Row 1109-1270)

**Discount:** 18% (labeled as "SYSTEMATIC Earned Discount ED Program 1: 0.18")
**Net Rate Calculation:** `net_rate = list_rate × (1 - 0.18) = list_rate × 0.82`

**Billing Types:** Inbound, Outbound, Recipient Billing, Third Party
**Currency:** USD

#### Zone Structure
```
Standard Zones: 2, 3, 4, 5, 6, 7, 8, 9
Additional Zones: 14, 17, 22, 23, 25, 92, 96
```

**Current Implementation Uses:** Zones 2-9, 17 only
**Not Yet Implemented:** Zones 14, 22, 23, 25, 92, 96

#### Sample Net Rates (18% discount applied)
| Weight | Zone 2 | Zone 3 | Zone 4 | Zone 5 | Zone 6 | Zone 7 | Zone 8 | Zone 9 | Zone 17 |
|--------|--------|--------|--------|--------|--------|--------|--------|--------|---------|
| 1 lb   | $6.13  | $6.13  | $6.13  | $6.13  | $6.13  | $6.13  | $6.13  | $39.38 | $39.38  |
| 10 lbs | $6.13  | $6.28  | $6.86  | $7.56  | $7.80  | $8.79  | $9.71  | $57.67 | $44.07  |
| 20 lbs | $6.56  | $7.37  | $7.55  | $9.28  | $10.81 | $13.18 | $14.68 | $87.44 | $66.82  |
| 30 lbs | $6.13  | $6.99  | $7.70  | $9.22  | $11.51 | $13.40 | $15.78 | $115.57| $88.32  |
| 70 lbs | $6.34  | $11.54 | $12.98 | $15.86 | $20.21 | $24.15 | $27.62 | $199.69| $153.34 |

#### Undiscounted (List) Rates Calculation
To match current file format, reverse the discount: `list_rate = net_rate / 0.82`

| Weight | Zone 2 | Zone 3 | Zone 4 | Zone 5 | Zone 6 | Zone 7 | Zone 8 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| 1 lb   | $7.48  | $7.48  | $7.48  | $7.48  | $7.48  | $7.48  | $7.48  |
| 10 lbs | $7.48  | $7.66  | $8.37  | $9.22  | $9.51  | $10.72 | $11.84 |
| 20 lbs | $8.00  | $8.99  | $9.21  | $11.32 | $13.18 | $16.07 | $17.90 |
| 30 lbs | $7.48  | $8.52  | $9.39  | $11.24 | $14.04 | $16.34 | $19.24 |

**Comparison to 2025 Rates:**
- 10 lb, Zone 5: 2025=$19.39, 2026=$9.22 (calculated list=$11.24)
- This appears to be a significant rate decrease OR the 2025 files contain different rate structures

---

### 2. Home Delivery Domestic Single Piece (Row 1279-1440)

**Discount:** 18% (same as Ground)
**Billing Types:** Outbound, Third Party only
**Currency:** USD

#### Zone Structure
```
Identical to Ground Domestic: 2, 3, 4, 5, 6, 7, 8, 9, 14, 17, 22, 23, 25, 92, 96
```

#### Rate Data
**IDENTICAL** to Ground Domestic Single Piece rates. Every rate matches exactly.

**Implications:**
- Home Delivery and Ground now use same base rates
- Service differentiation likely comes from surcharges (Residential, DAS)
- Current implementation has separate undiscounted_rates.csv files for each service

---

### 3. FedEx Ground Economy (by Pound) - Row 1820-1902

**Service Note:** This is the successor to "SmartPost"
**Discount:** 4.5% (labeled as "0.045")
**Billing Type:** Outbound only
**Currency:** USD

#### Zone Structure
```
Standard Zones: 2, 3, 4, 5, 6, 7, 8, 9, 10
Additional Zones: 17, 26, 99
```

**Current Implementation Uses:** Zones 2-9, 17
**Not Yet Implemented:** Zones 10, 26, 99

#### Sample Net Rates (4.5% discount applied)
| Weight | Zone 2 | Zone 3 | Zone 4 | Zone 5 | Zone 6 | Zone 7 | Zone 8 | Zone 9 | Zone 17 |
|--------|--------|--------|--------|--------|--------|--------|--------|--------|---------|
| 1 lb   | $6.87  | $6.87  | $6.87  | $6.87  | $6.87  | $6.87  | $6.87  | $20.22 | $20.22  |
| 10 lbs | $8.07  | $8.67  | $9.50  | $10.47 | $10.81 | $12.01 | $13.40 | $25.66 | $25.66  |
| 20 lbs | $9.96  | $11.21 | $11.45 | $14.09 | $16.41 | $19.97 | $22.24 | $44.97 | $44.97  |
| 30 lbs | $11.96 | $14.28 | $15.57 | $18.66 | $23.29 | $27.06 | $31.87 | $64.91 | $64.91  |
| 70 lbs | $16.94 | $24.92 | $29.30 | $35.46 | $45.68 | $52.25 | $60.84 | $124.77| $124.77 |

**Max Weight:** 70 lbs (per row 1889)

#### Zone 99 Rates
Zone 99 appears to be a special long-distance or remote zone:
- 1 lb: $20.22
- 10 lbs: $25.66
- 30 lbs: $64.91
- 70 lbs: $124.77

Rates identical to Zone 9/17 for lighter weights, suggesting possible Alaska/Hawaii/remote designation.

---

### 4. FedEx Ground Economy (by Ounce) - Row 1911-1941

**Discount:** 4.5%
**Billing Type:** Outbound only
**Weight Range:** Sub-pound shipments (measured in ounces)

**Zone Structure:** Same as by-pound (2-10, 17, 26, 99)

**Sample Rates:**
| Weight | Zone 2 | Zone 3 | Zone 4 | Zone 5 | Zone 6 | Zone 7 | Zone 8 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| 4 oz   | $6.87  | $6.87  | $6.87  | $6.87  | $6.87  | $6.87  | $6.87  |
| 8 oz   | $6.87  | $6.87  | $6.87  | $6.87  | $6.87  | $6.87  | $6.87  |
| 12 oz  | $6.87  | $6.87  | $6.87  | $6.87  | $6.87  | $6.87  | $6.87  |
| 16 oz  | $6.87  | $6.87  | $6.87  | $6.87  | $6.87  | $6.87  | $6.87  |

All sub-pound shipments have flat rate of $6.87 across zones 2-8.

---

## Comparison to Current Implementation

### Current File Structure
```
carriers/fedex/data/reference/
├── home_delivery/
│   ├── undiscounted_rates.csv       # List prices (before discount)
│   ├── performance_pricing.csv      # Discount amounts (negative values)
│   ├── earned_discount.csv          # Currently $0.00
│   └── grace_discount.csv           # Currently $0.00
└── smartpost/
    └── (same structure)
```

### 2026 Rate Card Structure
- Single Excel file with net rates (post-discount)
- Multiple services in one sheet
- Discount percentage noted but not applied as separate line item

### Zone Coverage Gap

**Current Implementation:**
- Ground/Home Delivery: Zones 2-9, 17
- SmartPost: Zones 2-9, 17

**2026 Rate Card:**
- Ground/Home Delivery: Zones 2-9, 14, 17, 22, 23, 25, 92, 96
- Ground Economy: Zones 2-10, 17, 26, 99

**Missing Zones:** 10, 14, 22, 23, 25, 26, 92, 96, 99

### Rate Comparison Issues

Direct comparison shows apparent 50%+ rate decreases, which suggests:
1. **Different discount structures** - 2025 files may include different discounts in "undiscounted_rates.csv"
2. **Contract differences** - 2025 data may be from different contract terms
3. **Rate basis mismatch** - Need to verify what the 2025 "undiscounted" rates actually represent

**Example (10 lbs, Zone 5):**
- Current HD undiscounted_rates.csv: $19.39
- 2026 net rate: $9.22
- 2026 calculated list rate (÷0.82): $11.24
- Difference: $19.39 → $11.24 = -42% (seems incorrect)

**Recommendation:** Verify 2025 rate file sourcing before finalizing comparison.

---

## Surcharge Information

### Noted in Document
Row 21: "Net rates are calculated based on applicable transportation discounts and do not include: surcharges, ancillary / other charges, duties and taxes, or special handling fees."

**Surcharges NOT included in rate card:**
- Fuel surcharge
- Residential Delivery (RES)
- Delivery Area Surcharge (DAS/EDAS)
- Additional Handling (AHS)
- Oversize
- Peak/Demand surcharges

These must be sourced from:
1. Contract documents
2. Invoice data analysis
3. FedEx Rate/Rules Tariff

---

## Special Notes

### Zone 14
Appears throughout Ground/Home Delivery but not documented. Rates are very low (e.g., 1 lb = $8.96, 30 lbs = $9.10), suggesting possible:
- Local/same-city delivery
- Special contract zone
- Consolidation center delivery

### Zones 22, 23, 25
Similar to zone 14, these show consistent rate patterns but no documentation of geographic coverage.

### Zones 92, 96
High-number zones suggest possible:
- Extended delivery areas
- Special handling zones
- Non-contiguous territories

### Zone 99 (Ground Economy only)
Appears to be remote/maximum distance zone with rates matching Zone 17 (Alaska/Hawaii).

---

## Implementation Recommendations

### 1. Immediate Actions
- [ ] Extract 2026 net rates from Excel to CSV format
- [ ] Calculate undiscounted list rates (÷ by discount factor)
- [ ] Verify 2025 rate file sourcing and structure
- [ ] Document what the 2025 "undiscounted_rates.csv" actually contains

### 2. Rate File Updates
```
New structure to create:
carriers/fedex/data/reference/2026/
├── ground/
│   └── net_rates.csv                # Direct from rate card
├── home_delivery/
│   └── net_rates.csv                # Same as ground (identical)
└── ground_economy/
    ├── net_rates_by_pound.csv
    └── net_rates_by_ounce.csv
```

### 3. Zone Expansion
- [ ] Identify geographic coverage for new zones (14, 22, 23, 25, 92, 96)
- [ ] Update zones.csv with new zone mappings
- [ ] Determine if new zones are used in actual shipments
- [ ] Document zone definitions in README

### 4. Discount Structure Decision
**Option A:** Keep current structure (undiscounted + discount files)
- Convert 2026 net rates to list rates
- Calculate new performance_pricing discount amounts
- Maintains compatibility with existing calculator

**Option B:** Switch to net rate structure
- Store 2026 net rates directly
- Remove discount file complexity
- Requires calculator refactor

**Recommendation:** Option A for consistency, unless surcharge analysis reveals simpler approach.

### 5. Rate Validation
- [ ] Compare sample shipments against actual 2026 invoices (when available)
- [ ] Validate zone assignments match invoice data
- [ ] Confirm surcharge amounts haven't changed
- [ ] Test with November 2025 - January 2026 actual shipments

### 6. Calculator Updates
- [ ] Update version.py to "2026.02.XX"
- [ ] Add support for new zones if needed
- [ ] Update rate file loading logic
- [ ] Test against historical data with new rates

---

## Questions for Clarification

1. **What do the 2025 "undiscounted_rates.csv" files actually contain?**
   - True list prices?
   - Net prices with different discount applied?
   - Contract-specific rates?

2. **Are zones 14, 22, 23, 25, 92, 96 actively used in shipments?**
   - Check PCS database for actual zone assignments
   - Review invoice data for these zone codes

3. **What is the effective date hierarchy?**
   - Rate card says "Effective 04 November 2025"
   - But created "14 January 2026"
   - When should these rates start being used?

4. **Account status warning:**
   - Rate card notes account in 'Delete' status
   - Are these rates actually active/valid?
   - Need confirmation from FedEx rep

5. **Ground vs Home Delivery separation:**
   - If rates are identical, why maintain separate services?
   - Is differentiation purely surcharge-based?
   - Should calculator combine them?

---

## File Extraction Script Needed

```python
# Script to extract rate tables from Excel to CSV format
# Should create:
# - ground_net_rates_2026.csv
# - home_delivery_net_rates_2026.csv (identical to ground)
# - ground_economy_by_pound_net_rates_2026.csv
# - ground_economy_by_ounce_net_rates_2026.csv
#
# Each with columns: weight_lbs, zone_2, zone_3, ..., zone_99
```

---

## Next Steps

1. **Clarify 2025 rate file structure** - Understand what current files represent
2. **Extract 2026 rates to CSV** - Convert Excel data to calculator-compatible format
3. **Map new zones** - Identify geographic coverage of zones 10, 14, 22, 23, 25, 26, 92, 96, 99
4. **Validate against actuals** - Test with Nov 2025 - Jan 2026 invoice data
5. **Update calculator** - Implement 2026 rates with proper effective date logic
6. **Document changes** - Update README with 2026 rate structure details

---

**Analysis Date:** 2026-02-02
**Analyst:** Claude Code
**Status:** Initial structure analysis complete, pending clarifications and validation
