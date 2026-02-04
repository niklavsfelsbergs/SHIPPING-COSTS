# Carrier Optimization Guide

This guide documents the approach for finding the optimal carrier setup for US shipments using 2026 tender rates.

---

## 1. Objective

Analyze shipping costs across carriers and find the optimal routing strategy considering:
- Cost per shipment by carrier
- Volume commitments (USPS, OnTrac)
- Volume-based discounts (FedEx Earned Discount)
- Geographic constraints (handled via penalty costs)

### Current vs Future Carriers

| Carrier   | Status          | Notes                                      |
|-----------|-----------------|------------------------------------------- |
| OnTrac    | Currently used  | Included in current mix optimization       |
| USPS      | Currently used  | Included in current mix optimization       |
| FedEx     | Currently used  | Included in current mix optimization       |
| P2P US    | **Not used**    | Future scenario assessment only            |
| Maersk US | **Not used**    | Future scenario assessment only            |

---

## 2. Data Foundation

### 2.1 Source Data

Each carrier has a parquet file with ALL US shipments calculated as if shipped with that carrier:

| File                           | Description                     | Status           |
|--------------------------------|---------------------------------|------------------|
| `ontrac_all_us_*.parquet`      | All shipments with OnTrac costs | Currently used   |
| `usps_all_us_*.parquet`        | All shipments with USPS costs   | Currently used   |
| `fedex_all_us_*.parquet`       | All shipments with FedEx costs  | Currently used   |
| `p2p_us_all_us_*.parquet`      | All shipments with P2P costs    | Future assessment|
| `maersk_us_all_us_*.parquet`   | All shipments with Maersk costs | Future assessment|

**Note:** Files currently contain 2025 calculations. Will be updated with 2026 rates before final analysis.

### 2.2 Shipment-Level Dataset

**Script:** `build_shipment_dataset.py`

Join all carrier files on shipment ID to create unified view:

```
shipment_id | packagetype | zip | weight | pcs_shippingprovider | cost_ontrac | cost_usps | cost_fedex | cost_p2p | cost_maersk | cost_current_carrier
```

- `pcs_shippingprovider`: The carrier actually used for this shipment
- `cost_current_carrier`: The **expected/calculated** cost from the carrier file matching `pcs_shippingprovider`

**Logic for `cost_current_carrier`:**
```
if pcs_shippingprovider == 'ONTRAC':
    cost_current_carrier = cost_total from ontrac parquet
elif pcs_shippingprovider == 'USPS':
    cost_current_carrier = cost_total from usps parquet
elif pcs_shippingprovider contains 'FX':
    cost_current_carrier = cost_total from fedex parquet
...
```

**`pcs_shippingprovider` value mapping:**

| Carrier   | `pcs_shippingprovider` values                                  |
|-----------|----------------------------------------------------------------|
| OnTrac    | `ONTRAC`                                                       |
| USPS      | `USPS`                                                         |
| FedEx     | Contains `FX` (e.g., `FXEHD`, `FXSP`, etc.) - exact values TBD |
| P2P       | N/A - not currently used                                       |
| Maersk    | N/A - not currently used                                       |

**Note:** This is NOT invoice/actual cost. All costs are calculated/expected costs from the respective carrier calculators.

**Output:** `shipments_unified.parquet`

### 2.3 Aggregated Dataset

**Script:** `build_aggregated_dataset.py`

Group by: `(packagetype, zip_code, weight_bracket_1lb)`

Columns per group:
- `shipment_count`
- Per carrier: `cost_{carrier}_total`, `cost_{carrier}_avg`
- `cost_current_carrier_total`, `cost_current_carrier_avg`

**Output:** `shipments_aggregated.parquet`

---

## 3. Scenarios

### Scenario 1: Current Carrier Mix

**Question:** What is the total expected cost with current carrier routing using 2026 rates?

**Carriers:** OnTrac, USPS, FedEx (current carriers only)

**Approach:** Sum `cost_current_carrier` across all shipments (calculated costs, not invoice actuals).

---

### Scenario 2: 100% Maersk *(Future Assessment)*

**Question:** What would it cost if all volume went to Maersk? What are the main cost drivers?

**Note:** Maersk US is not currently used. This is a hypothetical scenario to assess potential future partnership.

**Approach:**
1. Sum `cost_maersk` across all shipments
2. Analyze cost drivers:
   - Distribution by zone
   - Distribution by weight (especially around 30 lb rate jump)
   - Surcharge breakdown (NSL1, NSL2, NSD, PICKUP)
   - Identify expensive shipment segments

---

### Scenario 3: 100% FedEx

**Question:** What would it cost if all volume went to FedEx? What Earned Discount tier would we achieve?

**Approach:**
1. Calculate total transportation charges (base rates)
2. Determine Earned Discount tier (see Section 4)
3. Apply Earned Discount to all shipments
4. Analyze cost drivers

**TODO:** Clarify in FedEx meeting how Earned Discount interacts with Performance Pricing.

---

### Scenario 4: Constrained Optimization (OnTrac/FedEx/USPS)

**Question:** What is the optimal carrier mix considering volume commitments?

**Constraints (annual):**

| Carrier   | Minimum Volume      | Calculation                        |
|-----------|---------------------|------------------------------------|
| USPS      | 375,000 shipments   | 93,750/quarter × 4 (rolling avg)   |
| OnTrac    | 279,080 shipments   | 5,365/week × 52                    |
| FedEx     | No minimum          | But Earned Discount tiers apply    |

**Approach: Greedy + Adjustment**

```
Step 1: Initial Assignment
    For each (packagetype, zip, weight_bracket) group:
        Assign to cheapest carrier among {OnTrac, FedEx, USPS}

Step 2: Check Constraints
    Calculate total volume per carrier
    Identify violated constraints (USPS < 375K or OnTrac < 279K)

Step 3: Adjust for Constraints
    While constraints violated:
        Find groups where shifting to underutilized carrier has lowest cost penalty
        Cost penalty = (cost_target - cost_current) × shipment_count
        Shift lowest-penalty groups until constraint met

Step 4: Recalculate FedEx Earned Discount
    Based on final FedEx volume, determine tier
    Apply Earned Discount to FedEx shipments
    Recalculate total cost
```

---

### Scenario 5: Optimal with P2P *(Future Assessment)*

**Question:** Does adding P2P improve the optimal mix?

**Note:** P2P US is not currently used. This assesses whether adding P2P to the carrier mix would reduce costs.

Same as Scenario 4, but include P2P as fourth carrier option.

**P2P specifics:**
- No volume commitments
- Geographic constraints handled via penalty costs (makes non-serviceable routes expensive)
- No service level considerations

---

## 4. FedEx Earned Discount Tiers

From FedEx Agreement #491103984-115-04 (Proposed 2026).

### Ground / Home Delivery (Single Piece)

| Annual Transportation Charges   | Earned Discount |
|---------------------------------|-----------------|
| < $4.5M                         | 0%              |
| $4.5M - $6.5M                   | 16%             |
| $6.5M - $9.5M                   | 18%             |
| $9.5M - $12.5M                  | 19%             |
| $12.5M - $15.5M                 | 20%             |
| $15.5M - $24.5M                 | 20.5%           |
| $24.5M+                         | 21%             |

### Ground Economy

| Annual Transportation Charges   | By Pound | By Ounce |
|---------------------------------|----------|----------|
| < $4.5M                         | 0%       | 0%       |
| $4.5M - $6.5M                   | 4%       | 0.5%     |
| $6.5M - $9.5M                   | 4.5%     | 1%       |
| $9.5M - $12.5M                  | 5%       | 2%       |
| $12.5M - $15.5M                 | 5.5%     | 3%       |
| $15.5M - $24.5M                 | 5.75%    | 3.5%     |
| $24.5M+                         | 6%       | 4%       |

**Key details:**
- Based on 52-week rolling average
- Applies to Transportation Charges only (base rates, not surcharges)
- Does NOT apply to special zones (9, 14, 17, 22, 23, 25, 92, 96) except Ground Economy
- Currently at 0% tier due to reduced volume

**Implementation note:** Apply Earned Discount on top of existing base + performance pricing. Performance pricing is currently $0 in our calculations.

---

## 5. Optimization Parameters

### Grouping Dimensions

Optimize by:
- `packagetype`
- `zip_code` (5-digit)
- `weight_bracket` (1 lb increments)

### Time Period

Use annual totals for simplicity (not rolling averages).

### Geographic Constraints

Handled via penalty costs built into carrier calculations:
- OnTrac: Non-serviceable areas have high penalty cost
- P2P: Non-serviceable areas have high penalty cost

This makes non-serviceable routes automatically non-optimal.

---

## 6. File Structure

```
analysis/US_2026_tenders/
│
├── carrier_datasets/                         # Base parquet files (one per carrier)
│   ├── ontrac_all_us_*.parquet
│   ├── usps_all_us_*.parquet
│   ├── fedex_all_us_*.parquet
│   ├── p2p_us_all_us_*.parquet
│   └── maersk_us_all_us_*.parquet
│
├── combined_datasets/                        # Joined/aggregated datasets
│   ├── shipments_unified.parquet             # Shipment-level with all carrier costs
│   └── shipments_aggregated.parquet          # Aggregated by (packagetype, zip, weight)
│
├── scripts/                                  # Data preparation scripts
│   ├── copy_carrier_datasets.py              # Copy parquets from carriers/*/scripts/output/
│   ├── build_shipment_dataset.py             # Join carrier files → shipments_unified
│   └── build_aggregated_dataset.py           # Aggregate → shipments_aggregated
│
├── optimization/                             # Scenario analysis & optimization
│   ├── scenario_1_current_mix.py
│   ├── scenario_2_maersk_100.py
│   ├── scenario_3_fedex_100.py
│   ├── scenario_4_constrained_optimization.py
│   └── scenario_5_with_p2p.py
│
└── docs/                                     # Documentation
    ├── optimization_guide.md                 # This file
    ├── optimization_guide_supplement.md      # Working notes
    ├── FedEx_agreement.md                    # FedEx contract details
    └── fedex_questions.md                    # Questions for FedEx meeting
```

---

## 7. Implementation Order

| Done | Step | Script                                        | Description                                        |
|------|------|-----------------------------------------------|----------------------------------------------------|
| [x]  | 0    | `scripts/copy_carrier_datasets.py`            | Copy parquets from carriers/ to carrier_datasets/  |
| [x]  | 1    | `scripts/build_shipment_dataset.py`           | Join carrier files, add `cost_current_carrier`     |
| [x]  | 2    | `scripts/build_aggregated_dataset.py`         | Group by (packagetype, zip, weight), calc totals   |
| [ ]  | 3    | `optimization/scenario_1_current_mix.py`      | Baseline cost with current carrier routing         |
| [ ]  | 4    | `optimization/scenario_2_maersk_100.py`       | 100% Maersk cost + driver analysis                 |
| [ ]  | 5    | `optimization/scenario_3_fedex_100.py`        | 100% FedEx cost + Earned Discount tier             |
| [ ]  | 6    | `optimization/scenario_4_constrained.py`      | Optimal mix with USPS/OnTrac minimums              |
| [ ]  | 7    | `optimization/scenario_5_with_p2p.py`         | Check if P2P improves the mix                      |

**Repeatability:** All scripts should be re-runnable when 2026 rate calculations are updated.

---

## 8. Open Questions / TODOs

### FedEx Meeting

- [ ] How exactly does Earned Discount interact with Performance Pricing?
- [ ] Is Earned Discount applied to base rate before or after Performance Pricing?
- [ ] Confirm 52-week rolling calculation methodology

### Data Validation

| Task                                              | Status  |
|---------------------------------------------------|---------|
| Verify parquet files have consistent shipment IDs | Pending |
| Document `pcs_shippingprovider` value mapping     | Partial |
| - `ONTRAC` → OnTrac                               | Done    |
| - `USPS` → USPS                                   | Done    |
| - Contains `FX` → FedEx (verify variants)         | Pending |
| - P2P / Maersk                                    | N/A (not currently used) |
| Check for shipments missing from carrier files    | Pending |

### Rate Updates

- [ ] Update all carrier calculations with 2026 rates before final analysis
- [ ] Document which rate version is used in each parquet file

---

*Last updated: February 2026*
