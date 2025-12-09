---
description: Review contracts and OnTrac website to verify config is up-to-date
---

Review the OnTrac contract documents and official surcharges website to determine if the calculator configuration needs updating.

## Steps

### 1. Review Current Config

Read all configuration files:

**Surcharges** (`carriers/ontrac/surcharges/*.py`):
- `additional_handling.py` - AHS: list_price, discount, thresholds
- `large_package.py` - LPS: list_price, discount, thresholds
- `over_maximum_limits.py` - OML: list_price, discount, thresholds
- `residential.py` - RES: list_price, discount, allocation_rate
- `delivery_area.py` - DAS: list_price, discount
- `extended_delivery_area.py` - EDAS: list_price, discount
- `demand_*.py` - DEM_*: list_price, discount, period_start, period_end

**Data** (`carriers/ontrac/data/reference/`):
- `fuel.py` - LIST_RATE, DISCOUNT
- `billable_weight.py` - DIM_FACTOR, DIM_THRESHOLD

**Version** (`carriers/ontrac/version.py`):
- VERSION - last update date

### 2. Review Contract Documents

Read the PDFs in `carriers/ontrac/data/reference/contracts/current/`:
- Main contract and any supplements/amendments
- Extract: negotiated discounts, DIM factor, special terms

### 3. Fetch OnTrac Official Rates

Fetch the latest information from: https://www.ontrac.com/surchargesandrates/

Extract:
- Surcharge list prices (OML, LPS, AHS, DAS, EDAS, RES)
- Surcharge thresholds (weight, dimensions, cubic size)
- Current fuel surcharge rate
- Demand surcharge amounts and period dates

### 4. Compare and Analyze

Create a comparison table for each category:

**Surcharge Costs**
| Surcharge | Config | Website | Contract Discount | Calculated | Status |
|-----------|--------|---------|-------------------|------------|--------|

**Thresholds** (AHS, LPS, OML)
| Threshold | Config | Website | Status |
|-----------|--------|---------|--------|

**Fuel Rate**
| Item | Config | Website | Status |
|------|--------|---------|--------|

**Demand Periods**
| Surcharge | Config Period | Website Period | Status |
|-----------|---------------|----------------|--------|

**DIM Settings**
| Setting | Config | Contract | Status |
|---------|--------|----------|--------|

### 5. Generate Report

Summarize findings:
- **Matches**: Values aligned with contract/website
- **Discrepancies**: Values needing update, with:
  - Current value in config
  - Expected value from source
  - Source (contract/website)
  - File to update

### 6. Suggest Updates (if needed)

If discrepancies found, for EACH change provide:

1. **What to change**: File path and specific edit
2. **Source citation** (so human can verify):
   - For contracts: Document name, page number, section/exhibit (e.g., "Third Amendment, page 2, Restated Exhibit C")
   - For website: Exact section name and quote the relevant text (e.g., "Demand Surcharges section: 'October 25, 2025 to January 16, 2026'")
3. **Current vs Expected**: Show the before/after values clearly

Also remind:
- Update `carriers/ontrac/version.py` with new VERSION date
- Commit with descriptive message referencing contract/website change

### 7. Human Approval Required

**IMPORTANT**: Do not make any config changes without explicit approval. Present:
- All proposed changes
- Impact on calculations
- Files to be modified

Ask: "Would you like me to apply these updates?"
