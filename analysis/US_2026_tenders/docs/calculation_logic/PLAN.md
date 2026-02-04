# Plan: Create Calculation Logic Documentation for US Carriers

Create a calculation logic documentation file for each of the 4 remaining US carriers, following the same structure as `usps.md`.

---

## Template Structure

Each file should follow this structure:

```
# {Carrier Name} - Calculation Logic

**Service:** {Service name}
**Max Weight:** {Weight limit}
**Calculator Version:** {From version.py}

---

## Executive Summary
{Business-friendly explanation of the calculation in plain language with costs in parentheses}

---

## 1. Input Requirements
{Table of required input columns}

## 2. Calculation Pipeline
{Visual flow diagram of the stages}

## 3. Dimensional Calculations
{How cubic_in, longest_side_in, etc. are calculated, including rounding rules}

## 4. Zone Lookup
{How zones are determined - ZIP matching, origin-dependent, fallback logic}

## 5. Billable Weight
{DIM factor, DIM threshold, calculation logic with examples}

## 6. Surcharges
{Each surcharge with: condition, cost, exclusivity, examples}
{Include demand/peak surcharges if applicable}

## 7. Base Rate Lookup
{Rate table structure, weight brackets, zone columns}

## 8. Fuel Surcharge (if applicable)
{Rate, what it's applied to, discount if any}

## 9. Total Cost Calculation
{Formula + complete worked example}

## 10. Output Columns
{All output columns with types and descriptions}

## 11. Data Sources
{File paths for all reference data}

## 12. Key Constraints
{Important limits, rules, and gotchas}
```

---

## Carrier-Specific Instructions

### 1. OnTrac (`ontrac.md`)

**Directory:** `carriers/ontrac/`

**Key aspects to document:**
- Service: OnTrac Ground
- Zone lookup: 5-digit ZIP (not 3-digit like USPS)
- DAS zones: OnTrac has its own DAS zone system
- DIM factor: 250 (different from USPS 200)
- Surcharges (many more than USPS):
  - OML (Overmax Length)
  - LPS (Large Package Surcharge)
  - AHS (Additional Handling Surcharge)
  - DAS/EDAS (Delivery Area Surcharge)
  - RES (Residential)
  - Demand surcharges (DEM_AHS, DEM_RES, etc.)
- Exclusivity groups and priorities
- Minimum billable weights (some surcharges enforce minimums)
- Fuel surcharge: Yes, percentage-based
- Borderline allocation logic (if any)
- Peak/demand periods with exact dates

**Read these files:**
- `carriers/ontrac/calculate_costs.py`
- `carriers/ontrac/README.md`
- `carriers/ontrac/surcharges/*.py`
- `carriers/ontrac/data/reference/` (zones, rates, fuel, billable_weight)

---

### 2. FedEx (`fedex.md`)

**Directory:** `carriers/fedex/`

**Key aspects to document:**
- Services: Home Delivery AND Ground Economy (SmartPost) - document both
- 4-part rate structure: Undiscounted Rate + Performance Pricing + Earned Discount + Grace Discount
- Different rate tables for each service
- SmartPost 10+ lb anomaly (different rates for weights 10+ lbs)
- DIM factors: 250 (Home Delivery), 225 (Ground Economy)
- Zone handling: letter zones (A, H, M, P) map to zone 9
- Surcharges: DAS, Residential, Oversize, AHS, Demand surcharges
- Fuel surcharge: Yes, percentage-based
- Note: Earned and Grace discounts currently $0 (document this)

**Read these files:**
- `carriers/fedex/calculate_costs.py`
- `carriers/fedex/README.md`
- `carriers/fedex/surcharges/*.py`
- `carriers/fedex/data/reference/` (all rate files, zones, fuel, billable_weight)

---

### 3. P2P US (`p2p_us.md`)

**Directory:** `carriers/p2p_us/`

**Key aspects to document:**
- Service: P2P US (likely a consolidator/regional carrier)
- Explore the calculator to understand:
  - Zone lookup method
  - DIM factor and threshold
  - Rate table structure
  - Surcharges (if any)
  - Fuel surcharge (if any)
- This may be simpler or more complex than others - document what exists

**Read these files:**
- `carriers/p2p_us/calculate_costs.py`
- `carriers/p2p_us/README.md` (if exists)
- `carriers/p2p_us/surcharges/` (if exists)
- `carriers/p2p_us/data/reference/`

---

### 4. Maersk US (`maersk_us.md`)

**Directory:** `carriers/maersk_us/`

**Key aspects to document:**
- Service: Maersk US (likely freight/logistics)
- Early development status - document what exists
- Explore the calculator to understand:
  - Zone lookup method
  - DIM factor and threshold
  - Rate table structure
  - Surcharges (if any)
  - Fuel surcharge (if any)
- May be incomplete - document current state and note any TODOs

**Read these files:**
- `carriers/maersk_us/calculate_costs.py`
- `carriers/maersk_us/README.md` (if exists)
- `carriers/maersk_us/surcharges/` (if exists)
- `carriers/maersk_us/data/reference/`

---

## Quality Checklist

For each documentation file, ensure:

- [ ] Executive summary explains calculation in business language
- [ ] All costs have dollar amounts in parentheses
- [ ] All thresholds specify `>` vs `>=` explicitly
- [ ] All surcharges have exact conditions documented
- [ ] Exclusivity groups and priorities are explained
- [ ] Complete worked example with real numbers
- [ ] All data source file paths are listed
- [ ] Tables are properly aligned with spacing
- [ ] Version number from version.py is included

---

## Output Location

All files should be created in:
```
analysis/US_2026_tenders/docs/calculation_logic/
├── PLAN.md (this file)
├── usps.md (already complete)
├── ontrac.md
├── fedex.md
├── p2p_us.md
└── maersk_us.md
```

---

## Agent Prompts

### OnTrac Agent Prompt:
```
Create calculation logic documentation for OnTrac carrier.

1. Read carriers/ontrac/calculate_costs.py, README.md, surcharges/*.py, and data/reference/ files
2. Document EVERY aspect of the calculation with exact thresholds and costs
3. Follow the template structure in analysis/US_2026_tenders/docs/calculation_logic/PLAN.md
4. Use analysis/US_2026_tenders/docs/calculation_logic/usps.md as a formatting reference
5. Write the output to analysis/US_2026_tenders/docs/calculation_logic/ontrac.md
6. Ensure all tables are properly aligned with spacing
```

### FedEx Agent Prompt:
```
Create calculation logic documentation for FedEx carrier.

1. Read carriers/fedex/calculate_costs.py, README.md, surcharges/*.py, and data/reference/ files
2. Document EVERY aspect of the calculation with exact thresholds and costs
3. Document BOTH Home Delivery and Ground Economy services
4. Follow the template structure in analysis/US_2026_tenders/docs/calculation_logic/PLAN.md
5. Use analysis/US_2026_tenders/docs/calculation_logic/usps.md as a formatting reference
6. Write the output to analysis/US_2026_tenders/docs/calculation_logic/fedex.md
7. Ensure all tables are properly aligned with spacing
```

### P2P US Agent Prompt:
```
Create calculation logic documentation for P2P US carrier.

1. Read carriers/p2p_us/calculate_costs.py, README.md (if exists), surcharges/ (if exists), and data/reference/ files
2. Document EVERY aspect of the calculation with exact thresholds and costs
3. Follow the template structure in analysis/US_2026_tenders/docs/calculation_logic/PLAN.md
4. Use analysis/US_2026_tenders/docs/calculation_logic/usps.md as a formatting reference
5. Write the output to analysis/US_2026_tenders/docs/calculation_logic/p2p_us.md
6. Ensure all tables are properly aligned with spacing
```

### Maersk US Agent Prompt:
```
Create calculation logic documentation for Maersk US carrier.

1. Read carriers/maersk_us/calculate_costs.py, README.md (if exists), surcharges/ (if exists), and data/reference/ files
2. Document EVERY aspect of the calculation with exact thresholds and costs
3. Follow the template structure in analysis/US_2026_tenders/docs/calculation_logic/PLAN.md
4. Use analysis/US_2026_tenders/docs/calculation_logic/usps.md as a formatting reference
5. Write the output to analysis/US_2026_tenders/docs/calculation_logic/maersk_us.md
6. Ensure all tables are properly aligned with spacing
7. Note any incomplete/TODO items if the carrier is still in development
```
