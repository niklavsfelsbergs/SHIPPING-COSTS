# Investigation Complete - FedEx Calculator Update to 2026 Rates

**Investigation Date:** February 2, 2026
**Current Version:** 2026.01.27.8
**Status:** Comprehensive investigation complete, ready for implementation planning

---

## PART 1: HOW THE CURRENT CALCULATOR WAS BUILT

### Method: Reverse Engineering from Invoice Data

The FedEx calculator was built by analyzing actual invoice data to discover the rate structure, rather than starting from published rate cards. This was a smart approach that led to several critical discoveries:

#### Key Discovery #1: 4-Component Rate Structure
FedEx invoices break down charges into:
1. **Undiscounted Rate** (positive) - Published list price
2. **Performance Pricing** (negative) - Volume discount
3. **Earned Discount** (negative) - Currently $0.00
4. **Grace Discount** (negative) - Currently $0.00

These four components sum to the final base charge on invoices.

#### Key Discovery #2: SmartPost Weight Cliff
SmartPost (now Ground Economy) uses **different rate tables** based on weight:
- 1-9 lbs: Standard rates
- 10+ lbs: ~26-46% higher rates

This creates a cost "cliff" at 10 lbs that was only discovered through invoice analysis.

#### Key Discovery #3: Origin-Dependent Zones
The same destination ZIP has different zones depending on origin (Phoenix vs Columbus), requiring origin-aware zone lookups.

**Documentation:** The reverse-engineering process is documented in:
- `carriers/fedex/README.md` - Implementation details
- `carriers/fedex/RATE_INCREASE_ANALYSIS.md` - January 2026 rate increase analysis
- Analysis scripts: `analyze_rate_increase.py`, `investigate_base_rates.py`, `final_rate_increase_report.py`

---

## PART 2: CURRENT IMPLEMENTATION STATUS

**Version:** 2026.01.27.8 (includes 10% fuel surcharge)

**Accuracy (November 2025 validation):**
- Home Delivery: 99.9% exact match, +0.08% variance
- SmartPost: 100% exact match, 0.00% variance

### ✅ FULLY IMPLEMENTED:
- Two-stage calculator (supplement → calculate)
- Zone lookup with 3-tier fallback (ZIP → state mode → default zone 5)
- DIM weight calculation (HD: 250 divisor, GE: 139 divisor)
- Service mapping (HD vs Ground Economy)
- Base rate lookup (4-component structure)
- 8 surcharges implemented:
  - **Base:** DAS, Residential, Oversize, AHS-Weight, AHS, DEM_Base
  - **Dependent:** DEM_AHS, DEM_Oversize
- Fuel surcharge: 10% (verified Jan 27, 2026)
- Upload/compare scripts
- Full Streamlit dashboard (4 pages)

### Current Rate Files:
```
carriers/fedex/data/reference/
├── home_delivery/
│   ├── undiscounted_rates.csv    # List prices
│   ├── performance_pricing.csv   # Volume discounts (negative)
│   ├── earned_discount.csv       # $0.00
│   └── grace_discount.csv        # $0.00
└── smartpost/
    └── (same structure)
```

**Zones Supported:** 2, 3, 4, 5, 6, 7, 8, 9, 17 (Alaska/Hawaii)

---

## PART 3: 2026 RATE CARD ANALYSIS

**File Location:** `fedex/temp_files/FedEx Rate Card 2026.xlsx`

**Effective Date:** November 4, 2025 (but document created Jan 14, 2026)

### VERY CLEAR FINDINGS:

#### 1. Rate Format Difference
- The 2026 rate card contains **NET rates** (after discounts applied)
- Ground/Home Delivery: 18% discount already applied (net = list × 0.82)
- Ground Economy: 4.5% discount already applied (net = list × 0.955)
- Your current implementation stores undiscounted list prices + separate discount files
- **Action required:** Reverse-engineer list prices from net rates (÷ 0.82 or ÷ 0.955)

#### 2. Ground and Home Delivery Are Identical
- Both services show **exactly the same** base rates
- Differentiation comes purely from surcharges (Residential applies only to HD)
- This is a significant finding - you may be able to consolidate rate tables

#### 3. New Zones Introduced
- **Ground/Home Delivery:** Added zones 14, 22, 23, 25, 92, 96 (7 new zones)
- **Ground Economy:** Added zones 10, 26, 99 (3 new zones)
- Zone 14 shows very low rates (possible local/same-city delivery)
- Zones 92, 96, 99 are high-numbered (likely extended/remote areas)

#### 4. Rate Increase Confirmed
The `RATE_INCREASE_ANALYSIS.md` document confirms:
- January 1, 2026 rate increase: ~5.93% average
- 138 of 140 rate cards increased (98.6%)
- 100% were increases (zero decreases)
- Range: 4.49% to 6.71%

#### 5. Sub-Pound Ground Economy Pricing
- Ground Economy by ounce: flat $6.87 for all weights/zones 2-8
- Separate from by-pound pricing

### NOT SO CLEAR:

#### 1. Rate File Sourcing Discrepancy ⚠️ CRITICAL
When I compare your current 2025 files to the 2026 rate card, I see apparent 42-50% decreases, which seems wrong:
- Current HD undiscounted_rates.csv (10 lbs, Zone 5): $19.39
- 2026 net rate: $7.56
- 2026 calculated list rate (÷0.82): $9.22

**Questions:**
- What do your current "undiscounted_rates.csv" files actually contain?
- Are they true list prices or do they have different discounts baked in?
- Were they extracted from a different contract period?

#### 2. New Zone Geographic Coverage
- No documentation of what ZIP codes map to zones 10, 14, 22, 23, 25, 26, 92, 96, 99
- Need to check actual shipment data or zone files to understand coverage

#### 3. Effective Date Confusion
- Rate card says "Effective 04 November 2025"
- But created "14 January 2026"
- Analysis shows rate increase on January 1, 2026
- **When should these rates actually be used?**

#### 4. Account Status Warning
- Rate card notes account status: 'Delete'
- Are these rates actually valid/active?
- Need confirmation from FedEx rep

#### 5. Surcharge Prices for 2026
The rate card explicitly excludes surcharges. Your current surcharge prices are:
- Residential: $2.08
- AHS: $8.60
- Oversize: ~$115 (tiered)
- DAS: Tiered ($2.17 to $43.00)

**Not clear if these prices changed for 2026.** You'd need to:
- Check 2026 contract documents
- Analyze Jan 2026 invoice surcharge amounts
- Check FedEx published tariffs

---

## PART 4: PLAN TO UPDATE TO 2026 RATES

### IMMEDIATE PRIORITIES (MUST DO):

#### 1. Clarify 2025 Rate File Sourcing ⚠️ CRITICAL
- Investigate what your current `undiscounted_rates.csv` files represent
- Compare them to Nov-Dec 2025 invoice data
- Understand why there's a 42% difference vs 2026 rates
- This will determine the correct approach for conversion

#### 2. Extract 2026 Rates from Excel
- Create Python script to parse the Excel file
- Extract rate tables for:
  - Ground Domestic (rows 1109-1270)
  - Home Delivery (rows 1279-1440) - identical to Ground
  - Ground Economy by pound (rows 1820-1902)
  - Ground Economy by ounce (rows 1911-1941)
- Convert to CSV format matching your current structure

#### 3. Convert Net Rates to List Prices
Two options:
- **Option A (Recommended):** Keep current structure
  - Calculate list prices: `list_rate = net_rate / (1 - discount)`
  - Ground/HD: `list_rate = net_rate / 0.82`
  - Ground Economy: `list_rate = net_rate / 0.955`
  - Recalculate performance_pricing discounts
  - Maintains compatibility with existing calculator

- **Option B:** Switch to net rate structure
  - Store net rates directly
  - Simplify calculator to use net rates
  - Requires refactoring but eliminates discount complexity

### SECONDARY PRIORITIES (SHOULD DO):

#### 4. Handle New Zones
- Check if zones 10, 14, 22, 23, 25, 26, 92, 96, 99 appear in actual shipment data
- If yes: Update `zones.csv` with mappings (may need to analyze invoice zone assignments)
- If no: Document but don't implement (fallback to zone 5 will handle)
- Update zone fallback logic if needed

#### 5. Validate Surcharge Prices
- Review 2026 contract documents for surcharge prices
- Analyze Jan 2026 invoices to see actual surcharge amounts
- Update surcharge files if prices changed:
  - `carriers/fedex/surcharges/residential.py`
  - `carriers/fedex/surcharges/additional_handling.py`
  - `carriers/fedex/surcharges/oversize.py`
  - `carriers/fedex/surcharges/das.py`

#### 6. Test Against Actual Data
- Run calculator with 2026 rates against Nov 2025 - Jan 2026 invoices
- Check accuracy metrics (should maintain 99%+ match rate)
- Identify any discrepancies
- Adjust if needed

#### 7. Update Version and Documentation
- Update `version.py` to "2026.02.XX"
- Document rate structure changes in README
- Note effective date and rate increase percentage
- Update CLAUDE.md if needed

### NICE TO HAVE (OPTIONAL):

#### 8. Consolidate Ground and Home Delivery
- Since rates are identical, consider single rate table
- Differentiate at calculator level based on service type
- Reduces maintenance burden

#### 9. Document Zone Definitions
- Research FedEx zone maps for new zones
- Document geographic coverage
- Add to README

---

## PART 5: WHAT I'M VERY CONFIDENT ABOUT

1. ✅ Your current calculator is **production-ready** and **highly accurate** (99.9%/100%)
2. ✅ The reverse-engineering approach was **excellent** - it discovered the SmartPost weight cliff and 4-component structure
3. ✅ The 2026 rate card contains **net rates** after 18% (Ground/HD) or 4.5% (GE) discounts
4. ✅ Ground and Home Delivery now use **identical base rates**
5. ✅ There was a **confirmed 5.93% average rate increase** on January 1, 2026
6. ✅ The calculator structure is **well-designed** and follows the same pattern as OnTrac/USPS
7. ✅ All surcharges are implemented correctly based on invoice analysis

---

## PART 6: WHAT I'M UNCERTAIN ABOUT

1. ❓ **Why are your 2025 undiscounted rates 42% higher than 2026 calculated list rates?**
   - Need to understand what your current files represent
   - Critical for determining correct conversion approach

2. ❓ **When should 2026 rates be effective?**
   - Rate card says Nov 4, 2025
   - Analysis shows Jan 1, 2026 increase
   - Need to reconcile these dates

3. ❓ **Are the new zones (10, 14, 22, 23, 25, 26, 92, 96, 99) actually used?**
   - Can check actual shipment data to confirm
   - May not need to implement if not used

4. ❓ **Did surcharge prices change for 2026?**
   - Rate card doesn't include surcharges
   - Need contract docs or invoice analysis to verify

5. ❓ **Is the account actually active?**
   - Rate card shows 'Delete' status
   - May just be a draft or outdated document

---

## RECOMMENDED NEXT STEPS

### Step 1: Investigate your current 2025 rate files
```bash
# Compare current rates to Nov-Dec 2025 actual invoices
python -m carriers.fedex.scripts.compare_expected_to_actuals --date_from 2025-11-01 --date_to 2025-12-31
```

### Step 2: Extract 2026 rates from Excel
(Can create Python script to automate this)

### Step 3: Convert net rates to list prices and update rate files

### Step 4: Test against Jan 2026 actual data

### Step 5: Deploy and monitor

---

## AVAILABLE ACTIONS

Would you like me to:
1. Write the Excel extraction script?
2. Investigate the 2025 rate file discrepancy further?
3. Check actual shipment data for new zone usage?
4. Analyze Jan 2026 invoices for surcharge changes?

---

## RELATED DOCUMENTATION

- `carriers/fedex/README.md` - Current implementation details
- `carriers/fedex/RATE_INCREASE_ANALYSIS.md` - January 2026 rate increase analysis
- `carriers/fedex/2026_RATE_CARD_ANALYSIS.md` - Detailed 2026 rate card structure
- `carriers/fedex/version.py` - Current version tracker
- `fedex/temp_files/` - 2026 rate card and supporting documents

---

**Report Generated By:** Claude Code
**Date:** February 2, 2026
