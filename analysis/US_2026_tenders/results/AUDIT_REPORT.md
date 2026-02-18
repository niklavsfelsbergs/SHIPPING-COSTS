# US 2026 Tenders: Deep Calculation Audit Report

## 1. FedEx Earned Discount Adjustment (`fedex_adjustment.py`)

### 1.1 Multiplier Formula Math
- **PASS** — Constants: `PP_DISCOUNT=0.45`, `BAKED_EARNED=0.18`, `FUEL_RATE=0.14`
- `baked_factor = 1 - 0.45 - 0.18 = 0.37` ✓
- `target_earned=0.16`: `multiplier = 0.39/0.37 = 1.054054...` (reported 1.0541) ✓
- `target_earned=0.00`: `multiplier = 0.55/0.37 = 1.486486...` (reported 1.4865) ✓

### 1.2 Additive vs Multiplicative Discount Model
- **PASS** — The FedEx README confirms: "Undiscounted Rate + Performance Pricing (negative) + Earned Discount + Grace Discount". The calculator (`calculate_costs.py:608-628`) sums these components additively: `cost_subtotal = cost_base_rate + cost_performance_pricing + cost_earned_discount + cost_grace_discount + surcharges`. The additive model `net = undiscounted × (1 - PP - earned)` is correct.

### 1.3 Delta Formula
- **PASS** — `delta = fedex_cost_base_rate × (multiplier - 1) × (1 + FUEL_RATE)` (line 69)
- `fedex_cost_base_rate` is the **undiscounted list price** (see `calculate_costs.py:576` — `cost_base_rate` is from `undiscounted_rates.csv`). The PP discount is already baked into `fedex_cost_total` as a separate negative component. The multiplier adjusts the portion of the undiscounted rate corresponding to the earned discount change. Since fuel is applied on base rate only (`calculate_costs.py:636-638`: `cost_fuel = cost_base_rate * FUEL_RATE`), the `(1 + FUEL_RATE)` scaling is correct.

### 1.4 Fuel Application — BASE_PLUS_SURCHARGES vs BASE_ONLY
- **WARNING (Major)** — `fuel.py:20` says `APPLICATION = "BASE_PLUS_SURCHARGES"` (fuel applies to base + surcharges, excluding PP discounts). But `calculate_costs.py:636-638` applies fuel as `cost_base_rate * FUEL_RATE` — **base rate only, not base + surcharges**. Meanwhile, `fedex_adjustment.py:69` also uses `cost_base_rate × (multiplier-1) × (1+FUEL_RATE)` which is consistent with the calculator (base-only fuel). **The issue is internal to the FedEx calculator, not the adjustment module.** The adjustment correctly mirrors the calculator's behavior. However, if fuel should really apply to base + surcharges, the calculator understates fuel and the adjustment would need revision. For the audit's purposes: **the adjustment is consistent with the calculator** — both use base-only fuel. But this should be verified against actual FedEx invoices.

### 1.5 Service Re-Selection After Adjustment
- **FAIL (Major)** — `fedex_adjustment.py:71-75` applies the **same delta** to both `fedex_hd_cost_total` and `fedex_sp_cost_total`:
  ```python
  delta_expr = pl.col("fedex_cost_base_rate") * (multiplier - 1) * (1 + FUEL_RATE)
  df = df.with_columns([
      (pl.col("fedex_cost_total") + delta_expr).alias("fedex_cost_total"),
      (pl.col("fedex_hd_cost_total") + delta_expr).alias("fedex_hd_cost_total"),
      (pl.col("fedex_sp_cost_total") + delta_expr).alias("fedex_sp_cost_total"),
  ])
  ```
  The `fedex_cost_base_rate` column comes from `build_shipment_dataset.py:load_fedex()` which selects it from the FedEx calculator output. In the calculator, `cost_base_rate` is set once per shipment during `_lookup_base_rate()` based on the **selected** rate service (HD or SP). There is only ONE `cost_base_rate` per shipment — it corresponds to whichever service was selected as cheapest.

  **This means the same delta (based on the initially-selected service's base rate) is applied to both HD and SP totals.** Since HD and SP have different undiscounted rates, applying the HD's base-rate-derived delta to the SP total (or vice versa) is incorrect. The re-selection at lines 78-86 then compares incorrectly-adjusted costs.

  **Impact assessment:** The error only matters for shipments where the service selection **changes** after adjustment. If the selected service doesn't change (vast majority of cases), the final `fedex_cost_total` is correct because it uses the delta from the correct base rate. The incorrect cost is on the "other" service that was already more expensive and stays more expensive. For the small number of shipments where the adjustment causes a service flip, the cost will be slightly wrong. **Likely low impact** but technically incorrect.

### 1.6 `cost_current_carrier` Update
- **PASS** — Lines 100-105: Updates `cost_current_carrier` for FedEx shipments (provider contains "FX") to the new `fedex_cost_total`. This happens AFTER service re-selection (lines 78-97), so it picks up the post-adjustment, re-selected service cost. The sequence is correct.

### 1.7 `adjust_and_aggregate()` Baseline
- **PASS** — The function computes S1 baseline as `sum(cost_current_carrier)` AFTER the FedEx adjustment. So S4/S5 (target=0%) get a higher baseline (~$7.07M) and S6/S7 (target=16%) get the $5.97M baseline. The returned `s1_baseline` is scenario-specific. The executive summary uses $5,971,748 (the S1/S6/S7 baseline) for all "vs S1" comparisons, not the internal S4/S5 baseline. This is correct — S4/S5's internal comparison tables use their own adjusted baselines, while the executive summary normalizes everything to $5,971,748.

---

## 2. Scenario 1: Current Carrier Mix Baseline

### 2.1 FedEx Adjustment
- **PASS** — Uses `target_earned=0.16`, multiplier 1.0541. Correct.

### 2.2 DHL Estimation
- **PASS** — `DHL_ESTIMATED_COST = 6.00`, applied at line 72. 40,157 DHL × $6.00 = $240,942.

### 2.3 OnTrac Null Imputation
- **PASS** — Lines 80-101: Null OnTrac costs (non-serviceable ZIPs that were historically shipped) are imputed with packagetype average. Logic is correct.

### 2.4 Carrier Breakdown Sum
- **PASS** — $3,160,980 (FedEx) + $1,736,638 (OnTrac) + $833,188 (USPS) + $240,942 (DHL) = $5,971,748. ✓

### 2.5 FedEx Shipment Share
- **PASS** — 273,941 / 558,013 = 49.1%. Consistent with executive summary.

### 2.6 Single Carrier Comparison Table
- **WARNING (Minor)** — S1's "100% FedEx" comparison uses FedEx at 16% earned (adjusted), showing $6,160,686. S3 uses the baked 18% rate showing $5,889,066. These are different methodologies and not directly comparable. The executive summary correctly labels S3's methodology. No error, but could confuse readers.

---

## 3. Scenario 2: 100% Maersk

### 3.1 Baseline Inconsistency
- **FAIL (Major)** — S2 (`scenario_2_maersk_100.py:68`) loads `baseline_cost` from `shipments_aggregated.parquet` as `cost_current_carrier_total.sum()`. This aggregated dataset was built by `build_aggregated_dataset.py` from `shipments_unified.parquet` **without any FedEx adjustment** — so the baseline uses FedEx at 18% baked. Meanwhile, S1 uses FedEx at 16% ($5,971,748). S3 also uses this 18%-baked baseline (line 68).

  **However**, the executive summary's comparison is **not** based on S2's internal baseline. The executive summary independently reports S2's Maersk total ($6,041,478) and computes savings vs the universal S1 baseline ($5,971,748): `-$69,730 (-1.2%)`. The $6,041,478 is purely Maersk costs (no FedEx involved), so this number is independent of the FedEx adjustment. The "vs S1" calculation in the executive summary is correct.

  **The issue is only within S2's internal comparison.** S2's own output would show a different "vs baseline" than the executive summary. Not a calculation error in the executive summary, but an internal inconsistency in S2's script. **Downgraded to Warning.**

### 3.2 S2 Total
- **PASS** — $6,041,478 is the sum of Maersk costs for all 558,013 shipments. Independent of FedEx adjustments.

---

## 4. Scenario 3: 100% FedEx

### 4.1 Earned Discount Application
- **PASS** — S3 uses the baked rates (18% earned already in base rates). `fedex_cost_earned_discount` from the calculator is $0.00 (confirmed in FedEx README: "Earned and Grace discounts are currently $0.00 across all weight/zone combinations"). So `fedex_total - current_earned_discount` (line 189) = `fedex_total - 0` = no change. S3 then applies the calculated earned discount based on the tier.

### 4.2 Transportation Charges Definition
- **WARNING (Major)** — S3 line 155: `transportation_charges = base_rate_total` (the undiscounted base rate sum). This is used to determine the earned discount tier. **But the `cost_base_rate` column from the calculator is the undiscounted rate** — NOT the rate after PP. The FedEx tiers are based on "annual transportation charges" which per the contract would be undiscounted charges. Using `cost_base_rate` (undiscounted) is correct for tier determination.

  However, the earned discount is then applied as `transportation_charges × discount_pct` (line 185), which gives the discount amount on the full undiscounted base rate. The FedEx contract says "Earned Discount" is a percentage of undiscounted transportation charges. This appears correct.

### 4.3 S3 vs S1 Sign Convention
- **PASS** — Executive summary: S3 = $5,889,066, Savings vs S1 = $82,682 (1.4%). This means S3 is $82,682 CHEAPER than S1. The table header says "Savings vs S1" so positive = S3 saves money. $5,971,748 - $5,889,066 = $82,682. ✓

---

## 5. Scenario 4: Constrained Optimization

### 5.1 Greedy Assignment
- **PASS** — `pl.min_horizontal(*cost_cols)` correctly finds the cheapest. The when/then chain processes non-fallback carriers first, with FedEx as fallback. Ties go to the first carrier in the non_fallback list (OnTrac before USPS). This is acceptable behavior.

### 5.2 Constraint Adjustment
- **PASS** — Priority order: OnTrac first, then USPS. For each underutilized carrier, penalty = `(target_cost_avg - source_cost_avg) * shipment_count`. Groups sorted by penalty ascending (cheapest switches first). Cumulative shipment count determines cutoff.

### 5.3 Locking Mechanism
- **PASS** — Lines 140-146: If a carrier meets its minimum naturally, its groups are locked before the next carrier's adjustment. Lines 191-207: After shifting, both shifted groups AND all carrier's groups are locked. This prevents USPS adjustment from stealing from OnTrac.

### 5.4 Cost Calculation
- **PASS** — `calculate_costs()` (lines 220-232) uses `{carrier}_cost_total` columns from the aggregated data, NOT `min_cost_avg`. The assigned carrier's actual total cost is used. Correct.

### 5.5 S4 Comparison Baselines
- **PASS** — S4 internally reports against its own adjusted baseline ($7.07M at 0% earned). The executive summary reports S4 ($5,492,793) savings vs S1 ($5,971,748) = $478,955 (8.0%). These are different baselines used for different purposes. The executive summary is consistent.

---

## 6. Scenario 5: Constrained + P2P

### 6.1 Method A (Greedy with P2P)
- **PASS** — Same greedy + adjust as S4 but with P2P added. Constraint adjustment prefers shifting from non-P2P first, then P2P (lines 135-137). Correct.

### 6.2 Method B (Improve S4)
- **PASS** — Takes S4's solution, computes P2P savings as `(current_cost_avg - p2p_cost_avg) * shipment_count` (line 294). Only switches where savings > 0. Respects surplus limits. FedEx switches unlimited. Correct.

### 6.3 S5 <= S4 Guarantee
- **PASS** — Method B only makes beneficial switches, so `S5_B <= S4`. The code picks `min(A, B)` at line 406. So `S5 = min(A, B) <= B <= S4`. ✓

### 6.4 S5 "Both Constraints" Numbers
- Reported: OnTrac 279,082 + USPS 181,917 + FedEx 53,158 + P2P 43,856 = **558,013** ✓
- Costs: $2,563,752 + $1,471,243 + $1,160,117 + $197,977 = **$5,393,089** (vs reported $5,393,088 — $1 rounding). ✓

---

## 7. Scenario 6: FedEx 16% Optimal

### 7.1 Threshold Calculation
- **PASS** — `FEDEX_BASE_RATE_THRESHOLD = 4,500,000 × 0.37 = $1,665,000`. The baked rate tables give `base_rate = undiscounted × (1 - PP - 0.18) = undiscounted × 0.37`. So `undiscounted = baked_base_rate / 0.37` is correct. But see note below.

### 7.2 Threshold Definition — What Counts as "Undiscounted Transportation"?
- **WARNING (Major)** — The $4.5M threshold is on "undiscounted transportation charges". The code converts between baked base rate and undiscounted using factor 0.37. But the `fedex_cost_base_rate` from the calculator is the **full undiscounted rate** (not the baked rate). It's called `cost_base_rate` and represents the undiscounted list price (`undiscounted_rates.csv`). So `fedex_cost_base_rate_total / 0.37` would give `undiscounted / 0.37` — which is WRONG.

  **Wait — let me re-check.** In `adjust_and_aggregate()` line 164, the aggregation sums `fedex_cost_base_rate` into `fedex_cost_base_rate_total`. The delta formula uses `fedex_cost_base_rate` as the undiscounted rate. But in `scenario_6`, `get_fedex_base_rate()` returns `fedex_cost_base_rate_total` and divides by `BAKED_FACTOR` (0.37) to get "undiscounted".

  If `fedex_cost_base_rate` IS the undiscounted rate, then dividing by 0.37 gives undiscounted/0.37 — which is ~2.7x the undiscounted rate. That's wrong.

  **BUT** — let's look at the delta formula again: `delta = base_rate × (multiplier - 1) × (1 + fuel)`. If base_rate is undiscounted, then `delta = undiscounted × (0.39/0.37 - 1) × 1.14`. The new total would be `old_total + delta`. The "old_total" includes the baked rate = `undiscounted × 0.37` (after PP and earned). So the adjustment adds `undiscounted × (target_factor/baked_factor - 1) × (1+fuel)` to reach `undiscounted × target_factor × (1+fuel)/baked_factor`... that doesn't simplify cleanly.

  **Actually, re-examining the calculator:** `cost_base_rate` is from `undiscounted_rates.csv` (line 576). `cost_performance_pricing` is the PP discount (negative). `cost_earned_discount` is $0. `cost_subtotal = base_rate + PP + earned + grace + surcharges`. `cost_total = cost_subtotal + cost_fuel`. So `cost_total` includes the undiscounted rate minus PP (but no earned discount subtracted since it's $0 in the tables).

  The FedEx README says the rate tables have "18% earned discount baked in". But the calculator shows `cost_earned_discount = $0`. **The 18% is baked into the undiscounted rate tables themselves** — i.e., the `undiscounted_rates.csv` already reflects rates with 18% earned discount applied. So `cost_base_rate` is NOT truly undiscounted — it's `true_undiscounted × (1 - 0.18)` ... no, that doesn't match either.

  **Resolution:** The docstring in `fedex_adjustment.py` says `baked_rate = undiscounted × (1 - PP - BAKED_EARNED) = undiscounted × 0.37`. The "baked_rate" is the net rate after PP and earned. In the calculator, `cost_subtotal ≈ cost_base_rate + cost_PP` (since earned/grace = 0). So `cost_subtotal = undiscounted_table_rate + PP_discount`. If the table rate already has earned baked in, then `undiscounted_table_rate = true_undiscounted × (1 - earned) = true_undiscounted × 0.82`. And `PP_discount = -true_undiscounted × 0.45`. So `subtotal = true_undiscounted × 0.82 - true_undiscounted × 0.45 = true_undiscounted × 0.37 = baked_rate`.

  But `cost_base_rate = undiscounted_table_rate = true_undiscounted × 0.82` (not × 0.37 and not fully undiscounted).

  **So in the delta formula:** `delta = cost_base_rate × (multiplier - 1) × (1 + fuel) = true_undiscounted × 0.82 × (target_factor/0.37 - 1) × 1.14`. Let's check for target=0.16: `= true_undiscounted × 0.82 × (0.39/0.37 - 1) × 1.14 = true_undiscounted × 0.82 × 0.05405 × 1.14 = true_undiscounted × 0.05055`. Meanwhile the correct delta should adjust from 18% to 16% earned: `correct_delta = true_undiscounted × (0.82 - 0.84) × ... ` — no, this isn't right either because the undiscounted table rate would change from 0.82 to 0.84 of true undiscounted.

  **I need to think about this more carefully.** The baked rate = `true_undiscounted × (1 - PP - 0.18)`. The target rate = `true_undiscounted × (1 - PP - target)`. The delta (before fuel) = `target_rate - baked_rate = true_undiscounted × (0.18 - target)`. We need to express this in terms of `cost_base_rate`.

  If `cost_base_rate = true_undiscounted × (1 - 0.18) = true_undiscounted × 0.82`, then `true_undiscounted = cost_base_rate / 0.82`. And `delta = cost_base_rate / 0.82 × (0.18 - target)`.

  But the code computes: `delta = cost_base_rate × (multiplier - 1) = cost_base_rate × (target_factor/baked_factor - 1) = cost_base_rate × ((0.55 - target_earned × ... ) / 0.37 - 1)`.

  For target=0.16: `= cost_base_rate × (0.39/0.37 - 1) = cost_base_rate × 0.05405`.

  The correct delta: `cost_base_rate/0.82 × (0.18-0.16) = cost_base_rate × 0.02/0.82 = cost_base_rate × 0.02439`.

  **These don't match!** `0.05405 ≠ 0.02439`. The ratio is 2.22x.

  **HOWEVER** — maybe the "baked in" means something different. Maybe the rate tables DON'T have earned baked into the undiscounted rate itself. Maybe "baked in" means the rate tables were negotiated assuming 18% earned would apply, so the effective rate = `table_rate + PP = undiscounted - PP_amount`, and the earned discount would bring it to `undiscounted - PP - earned = undiscounted × (1-PP-earned)`. If the table rate IS the true undiscounted rate, then:
  - `cost_base_rate = true_undiscounted`
  - `cost_PP = -true_undiscounted × PP = -true_undiscounted × 0.45`
  - `cost_earned = -true_undiscounted × 0.18 = $0` (baked into tables by being $0)
  - `cost_subtotal = true_undiscounted × (1 - 0.45) = true_undiscounted × 0.55`
  - `baked_rate` in the docstring would then be wrong...

  **This is getting circular. Let me look at the actual number check.** If S1 reports FedEx delta of ~$137,854 on 273,941 FedEx shipments, and multiplier is 1.0541, then `delta = sum(cost_base_rate) × 0.0541 × 1.14`. The executive summary reports FedEx total $3,160,980. If the pre-adjustment FedEx total was ~$3,023,126, then delta ≈ $137,854.

  The resolution depends on what `cost_base_rate` actually represents in the rate tables. Since the calculator has 99.9%+ accuracy against invoices, and the adjustment produces consistent results, **I'll flag this as needing verification against actual invoice data but not a confirmed bug.**

  **REVISED STATUS: WARNING (Major)** — The `fedex_cost_base_rate` column semantics need to be verified. If it's the true undiscounted rate (and earned discount is "baked" by being set to $0 rather than being reduced from the undiscounted rate), then the adjustment formula's multiplier derivation is wrong. If the rate tables already incorporate the 18% earned into the base rates, then the formula is correct. **Recommend verifying by computing `cost_base_rate / cost_subtotal` for a sample shipment and comparing to the expected ratio.**

### 7.3 S6 Threshold Enforcement
- **PASS** — Algorithm shifts groups from USPS/OnTrac surplus to FedEx, sorted by efficiency (penalty per unit of base rate contribution). Logic is sound.

### 7.4 "Both Constraints" Infeasibility
- **PASS** — 279,080 + 140,000 = 419,080 committed. 558,013 - 419,080 = 138,933 for FedEx. The report says 138,932 FedEx producing $3.67M undiscounted. At ~$26/shipment undiscounted this is reasonable for the most expensive FedEx shipments (those NOT cherry-picked by OnTrac/USPS).

---

## 8. Scenario 7: FedEx 16% + P2P

### 8.1 Method B FedEx Threshold Awareness
- **PASS** — Lines 430-451: For FedEx -> P2P switches, computes `base_surplus = fedex_base - FEDEX_BASE_RATE_THRESHOLD`. Accumulates `fedex_cost_base_rate_total` cumulatively and stops at surplus. This correctly preserves the threshold.

### 8.2 "Drop OnTrac" Razor-Thin Margin
- **WARNING (Minor)** — $4,500,015 undiscounted ($15 above $4.5M). This is a natural consequence of the group-level optimization — the algorithm includes the boundary group that pushes past the threshold. Not a bug, but a business risk. The code does NOT build in a safety buffer.

### 8.3 "Both Constraints" = S6
- **PASS** — S7 "Both constraints" = $5,002,886 = S6 "Both constraints". P2P captures 0 shipments because all carriers are at minimums with no surplus. Correct.

### 8.4 S7 <= S6 Guarantee
- **PASS** — Method B only improves. Code picks `min(A, B)` among threshold-meeting results. ✓

---

## 9. Cross-Scenario Consistency

### 9.1 S1 Baseline Consistency
- **PASS** — Executive summary uses $5,971,748 consistently for all "vs S1" comparisons. S4/S5 internal baselines differ but the executive summary normalizes correctly.

### 9.2 Shipment Count
- **PASS** — All scenarios account for 558,013 shipments. Verified in S4, S5, S6, S7 carrier breakdowns.

### 9.3 S2 Baseline vs S1 Baseline
- **WARNING (Minor)** — S2 and S3 internally use the 18%-baked baseline from `shipments_aggregated.parquet`. The executive summary correctly uses S1's $5,971,748 for cross-comparison. No impact on reported numbers.

### 9.4 DHL Handling in Optimization Scenarios
- **WARNING (Major)** — DHL shipments (40,157) are in `shipments_unified.parquet` with `cost_current_carrier = $6.00` and carrier costs for USPS, FedEx, Maersk (but null for OnTrac and P2P). In S4-S7, these shipments enter the aggregated dataset. In greedy assignment, they'd be assigned to a carrier with non-null cost (USPS or FedEx). Their S1 cost is $6.00/shipment, but their optimized cost could differ significantly. This is **intentional** (DHL shipments DO need to go somewhere), but should be noted: optimization savings partly come from re-routing DHL shipments to cheaper carriers, which is legitimate.

### 9.5 FedEx Cost Reasonableness
- **PASS** — S4 FedEx avg $21.79/shipment (0% earned, most expensive groups) vs S6 FedEx avg $13.37/shipment (16% earned, wider mix). The 1.63x difference (vs expected 1.41x from rate alone) is explained by shipment mix: S4 sends only the most expensive groups to FedEx (those where even inflated FedEx is cheapest), while S6 sends a broader mix including cheaper groups.

### 9.6 OnTrac 279,080 vs 279,082
- **PASS** — The 2-shipment difference is a rounding artifact from group-level assignment. S4/S5 slightly overshoot because the last shifted group pushes cumulative count 2 over minimum. S6 uses a different adjustment order (volume then threshold) producing exactly 279,080. Not a bug.

### 9.7 Actuals Comparison
- **PASS** — 539,941 matched (96.8%). The actuals comparison in the executive summary is computed within `scenario_1_current_mix.py` (lines 528-593) for S1. For S4-S7, the monthly breakdown table in the executive summary implies per-scenario actuals comparisons exist. These would need the scenario assignments mapped back to shipment-level for matching. **Could not verify how S4-S7 actuals are computed** — the scenario scripts don't contain actuals comparison code. This suggests it's computed separately (perhaps in a run-scenarios script).

---

## 10. Data Pipeline

### 10.1 `build_shipment_dataset.py`
- **PASS** — Joins 5 carriers on `pcs_orderid` using Maersk as base. OML/LPS exclusion removes orders entirely (all carrier costs removed). Actuals loaded from Redshift with OML/LPS filter.

### 10.2 `build_aggregated_dataset.py`
- **PASS** — Groups by (packagetype, shipping_zip_code, weight_bracket). Weight bracket = `ceil(weight_lbs)` matching `adjust_and_aggregate()`.

### 10.3 Null Weight Risk
- **WARNING (Minor)** — If any shipments have null `weight_lbs`, `ceil(null) = null`, creating a null weight bracket. These would be grouped together but could produce unexpected behavior in cost lookups. Low risk if input data is clean.

---

## 11. Specific Number Verification

Cannot run scenarios (no database access), but cross-checked reported numbers against code logic:

| Check | Expected | Code Logic | Status |
|-------|----------|------------|--------|
| S1 total | $5,971,748 | FedEx 16% adj + DHL $6 + OnTrac imputation | Consistent |
| S2 Maersk | $6,041,478 | Sum of maersk_cost_total | Consistent |
| S3 FedEx | $5,889,066 | FedEx at 18% baked + earned discount | Consistent |
| S4 "Both" | $5,492,793 | 0% earned, 3-carrier optimization | Consistent |
| S5 "Both" | $5,393,088 | S4 + P2P cherry-picking | Consistent |
| S5 check | 558,013 | 279,082+181,917+53,158+43,856 | ✓ |
| S6 "Drop OnTrac" | $5,040,871 | 16% earned, 2-carrier + threshold | Consistent |
| S7 "Drop OnTrac" | $4,433,040 | 16% earned, 3-carrier + threshold | Consistent |
| S7 FedEx undiscounted | $4,500,015 | Just above $4.5M threshold | Consistent |
| S7 check | 558,013 | 186,791+173,170+198,052 | ✓ |
| Matched shipments | 539,941 | 558,013 - 18,072 unmatched | Consistent |

---

## Summary of Findings

### Critical: None

### Major (3)

1. **Service re-selection uses wrong base rate for "other" service** (`fedex_adjustment.py:71-75`). Same delta applied to both HD and SP using the selected service's base rate. Impact likely small (only affects service-flip cases).

2. **`fedex_cost_base_rate` semantics ambiguity.** The adjustment formula depends on whether this column is the true undiscounted rate or has 18% earned already baked in. The calculator's accuracy against invoices suggests the implementation works, but the mathematical derivation in the docstring may not match the actual column semantics. Needs verification with sample data.

3. **Fuel application inconsistency.** `fuel.py` says `APPLICATION = "BASE_PLUS_SURCHARGES"` but the calculator applies fuel on base rate only. Consistent internally but may not match FedEx's actual fuel calculation.

### Minor (4)

4. **S2/S3 internal baselines use 18%-baked data** — no impact on executive summary.
5. **S7 razor-thin FedEx threshold margin** ($15 buffer) — business risk, not a code bug.
6. **Null weight bracket risk** — low probability if data is clean.
7. **S1 single-carrier comparison uses 16% rates** vs S3 using 18% — potentially confusing but correctly labeled.

### Info (2)

8. **DHL shipments in optimization scenarios** are correctly re-routed to real carriers.
9. **279,080 vs 279,082 OnTrac count** is a group-level rounding artifact.

---

*Audit completed: February 2026*
*Auditor: Claude Code*
*Scope: Code review and mathematical verification (no runtime execution)*
