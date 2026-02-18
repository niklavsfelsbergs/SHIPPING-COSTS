# US 2026 Tenders: Deep Calculation Audit Prompt

You are auditing a shipping cost optimization analysis. Your job is to deeply verify that every calculation across 7 scenarios is mathematically correct, internally consistent, and that the summary documents accurately reflect what the code produces. Be skeptical. Assume there are bugs until you prove otherwise.

## Context

This analysis evaluates 558,013 US shipments (2025 volumes) across 5 carriers (OnTrac, USPS, FedEx, P2P, Maersk) using 2026 rate cards. It produces 7 scenarios to find the optimal carrier routing strategy. The key output is the executive summary recommending S7 "Drop OnTrac" at $4,433,040 (25.8% savings vs baseline).

The analysis lives in `analysis/US_2026_tenders/`. Carrier cost calculators live in `carriers/{name}/`. The shared FedEx adjustment module is the most critical piece of shared logic.

## What to Audit

### 1. FedEx Earned Discount Adjustment (CRITICAL)

**File:** `analysis/US_2026_tenders/optimization/fedex_adjustment.py`

This is the single most important module. It adjusts FedEx costs from the 18% earned discount baked into rate tables to a target earned discount tier. Every scenario except S2 and S3 depends on it.

**Verify the math:**
- Constants: `PP_DISCOUNT = 0.45`, `BAKED_EARNED = 0.18`, `FUEL_RATE = 0.14`
- `baked_factor = 1 - 0.45 - 0.18 = 0.37` (the fraction of undiscounted rate that the baked rate represents)
- `target_factor = 1 - 0.45 - target_earned`
- `multiplier = target_factor / baked_factor`
- For `target_earned=0.16`: multiplier = 0.39/0.37 = 1.054054... (reported as 1.0541)
- For `target_earned=0.00`: multiplier = 0.55/0.37 = 1.486486... (reported as 1.4865)
- **Question:** Is the multiplier formula correct? The FedEx discount structure claims PP and earned are both percentages of undiscounted rate. So: `baked_rate = undiscounted * (1 - PP - baked_earned)`. To get `target_rate = undiscounted * (1 - PP - target_earned)`, the ratio `target_rate / baked_rate = (1 - PP - target_earned) / (1 - PP - baked_earned)`. Verify this is the right model for how FedEx discounts compound.

**Verify the delta formula:**
- `delta = fedex_cost_base_rate * (multiplier - 1) * (1 + FUEL_RATE)`
- Fuel (14%) is applied to base rate only. So the adjustment must also scale by (1 + fuel).
- **Question:** Is `fedex_cost_base_rate` the right column to apply the multiplier to? The base rate in the calculator output represents `undiscounted * (1 - PP - 0.18)` = the baked discounted base rate. The delta formula adjusts this to the target tier. Verify that surcharges are NOT being adjusted (they shouldn't be — only the base transportation component). Read `carriers/fedex/calculate_costs.py` to confirm what `fedex_cost_base_rate` represents.

**Verify service re-selection:**
- After adjusting costs, the code re-selects between Home Delivery and SmartPost (cheaper wins, SmartPost only for weight <= 70 lbs).
- **Question:** The delta is applied identically to both `fedex_hd_cost_total` and `fedex_sp_cost_total` using the same `fedex_cost_base_rate`. But HD and SP have different base rates. Is there a single `fedex_cost_base_rate` column, or are there separate HD/SP base rates? If the base rate column is for the selected service only, applying the same delta to both services is WRONG. Read the FedEx calculator to verify the column definitions.

**Verify `cost_current_carrier` update:**
- Line 100-105: For FedEx shipments (provider contains "FX"), `cost_current_carrier` is updated to the new `fedex_cost_total`.
- **Question:** Does this correctly handle the case where a FedEx shipment was originally FXEHD but after adjustment FXSP becomes cheaper (or vice versa)? The service re-selection happens first (lines 78-97), then `cost_current_carrier` is updated. Trace through the full sequence.

**Verify `adjust_and_aggregate()`:**
- Loads `shipments_unified.parquet`, adjusts FedEx, computes S1 baseline as `sum(cost_current_carrier)`, aggregates by (packagetype, zip, weight_bracket).
- **Question:** The S1 baseline is computed AFTER the FedEx adjustment. For S4/S5 (target_earned=0.0), this means the S1 baseline includes FedEx at 0% earned. For S6/S7 (target_earned=0.16), the baseline includes FedEx at 16%. These are DIFFERENT baselines for different scenarios. Is this handled correctly in the comparison tables? The executive summary uses $5,971,748 as the universal baseline, but S4/S5 internally use a different (higher) baseline. Verify that the reported "vs S1" savings percentages use the correct denominator.

### 2. Scenario 1: Current Carrier Mix Baseline

**File:** `analysis/US_2026_tenders/optimization/scenario_1_current_mix.py`

**Verify:**
- FedEx adjustment uses `target_earned=0.16`. The resulting multiplier should be 1.0541.
- DHL shipments are estimated at $6.00/shipment flat. 40,157 DHL shipments = $240,942 DHL cost.
- OnTrac null cost imputation: shipments to "non-serviceable" ZIPs are imputed with packagetype average cost.
- Total shipments = 558,013. Total cost should be $5,971,748.12.
- **Cross-check:** The carrier breakdown (FedEx: $3,160,980, OnTrac: $1,736,638, USPS: $833,188, DHL: $240,942) should sum to the total.
- **Cross-check:** The executive summary says FedEx is 49.1% of shipments (273,941). Verify this matches the code output.
- The "Comparison: 100% Single Carrier" table uses FedEx costs at 16% earned (adjusted). But in S3, FedEx 100% uses the baked 18% rate. The numbers should differ: S1 reports FedEx 100% at $6,160,686 (at 16%), while S3 reports $5,889,066 (at 18% with earned discount applied differently). Verify these are consistent with the different discount methodologies.

### 3. Scenario 2: 100% Maersk

**File:** `analysis/US_2026_tenders/optimization/scenario_2_maersk_100.py`

**Verify:**
- S2 does NOT use `fedex_adjustment.py`. It loads data directly from `shipments_aggregated.parquet` and `shipments_unified.parquet`.
- **Critical question:** The aggregated dataset was built by `build_aggregated_dataset.py` from `shipments_unified.parquet`. At that point, FedEx costs had the 18% earned discount baked in (no adjustment). So the `cost_current_carrier_total` in the aggregated dataset uses FedEx at 18%, NOT 16%. But S1 reports the baseline at 16% ($5,971,748). S2 compares Maersk to `cost_current_carrier_total` in the aggregated data, which is at 18%. **This means S2's "vs current" comparison uses a different baseline than S1.** Check if the executive summary comparison table uses consistent baselines.
- S2 reports $6,041,478. The executive summary says S2 is -1.2% vs S1 ($5,971,748). But if S2 internally compares to 18%-baseline, the internal comparison is different. Verify whether the $6,041,478 figure is the correct Maersk total regardless of baseline issues.

### 4. Scenario 3: 100% FedEx

**File:** `analysis/US_2026_tenders/optimization/scenario_3_fedex_100.py`

**Verify:**
- S3 does NOT use `fedex_adjustment.py`. It loads data directly.
- The earned discount is applied DIFFERENTLY than in other scenarios: S3 takes the total FedEx cost (at baked 18%), removes the current earned discount column, then applies the earned discount as `transportation_charges * discount_pct` where `transportation_charges = base_rate_total` (undiscounted base rate).
- **Critical question:** The `fedex_cost_earned_discount` column should already be zero if the rate tables bake in 18% earned by reducing the base rate. But S3 subtracts it (line 189: `fedex_total - current_earned_discount`). If the earned discount is baked in (i.e., already reflected in lower base rates), then `current_earned_discount` should be $0, and this subtraction is a no-op. Verify by checking what `fedex_cost_earned_discount` contains — read `carriers/fedex/calculate_costs.py`.
- S3 reports $5,889,066 in the executive summary. But the S3 summary.md (not yet read) should have the full calculation. The earned discount tier for 100% FedEx should be 18% (baked) since transportation charges would be in the $6.5-9.5M range.
- **Question:** The executive summary says S3 is +1.4% vs S1. That's $5,889,066 vs $5,971,748 = -$82,682, which is -1.4%, meaning FedEx is CHEAPER. But +1.4% in the table means MORE expensive. Check the sign convention — the table says "Savings vs S1" = $82,682 and % = 1.4%, which reads as S3 saves $82,682. Verify this.

### 5. Scenario 4: Constrained Optimization (FedEx 0% Earned)

**File:** `analysis/US_2026_tenders/optimization/scenario_4_constrained.py`

**Verify the optimization algorithm:**

a) **Greedy assignment correctness:**
   - Uses `pl.min_horizontal(*cost_cols)` to find the cheapest carrier per group.
   - Then builds a when/then chain to assign carrier name.
   - **Question:** If two carriers have exactly the same cost (tie), which one wins? The when/then chain evaluates top-to-bottom, so the first carrier in `non_fallback` list wins. For S4, `available = ["ONTRAC", "USPS", "FEDEX"]` and `fallback = "FEDEX"`, so `non_fallback = ["ONTRAC", "USPS"]`. Ties between OnTrac and USPS go to OnTrac. Ties involving FedEx go to whichever non-fallback carrier matches first. Is this the intended behavior?

b) **Constraint adjustment correctness:**
   - Priority order: OnTrac first, then USPS.
   - For each underutilized carrier, shift lowest-cost-penalty groups from other carriers.
   - Penalty = `(target_cost_avg - source_cost_avg) * shipment_count`.
   - **Question:** The penalty is computed per-group using average costs. But total costs are computed later using `{carrier}_cost_total` columns. Is the penalty based on avg cost consistent with the actual cost impact based on total cost? Only if `cost_total = cost_avg * shipment_count`, which should be true if the aggregation was done correctly.

c) **Locking mechanism:**
   - After shifting groups to OnTrac, those groups are locked so they can't be taken by the USPS adjustment.
   - Groups already assigned to OnTrac naturally are also locked.
   - **Question:** Are groups that were naturally assigned to USPS by the greedy step also locked before the USPS adjustment? Look at the code — when `shortfall <= 0` for a carrier, it locks that carrier's groups. This means if OnTrac is satisfied naturally, its groups get locked. Then USPS's adjustment can't take from OnTrac. But what if OnTrac needed adjustment? After OnTrac's adjustment completes, OnTrac's groups are locked (line 202-207). Then USPS can still take from FedEx. Verify this logic chain.

d) **Cost calculation after assignment:**
   - `calculate_costs()` uses `{carrier}_cost_total` columns, NOT the greedy `min_cost_avg`.
   - **Question:** For groups that were shifted during constraint adjustment, does the cost come from the target carrier's cost_total? Yes — the assigned_carrier is updated, and cost is looked up by the assigned carrier's cost_total column. Verify there's no mismatch.

e) **S4 comparison table:**
   - Reports "Current Mix (adjusted)" as $7,074,583. This is the S1 baseline with FedEx at 0% earned.
   - But also reports "Both constraints" savings "vs S1 Baseline" as $478,955 (8.0%), implying S1 = $5,971,748.
   - **These are different baselines.** The internal comparison table uses the 0%-adjusted baseline ($7.07M), but the executive summary uses the 16% baseline ($5.97M). Verify that both are correctly computed and that the reported savings percentages in the executive summary use $5,971,748 consistently.

### 6. Scenario 5: Constrained + P2P (FedEx 0% Earned)

**File:** `analysis/US_2026_tenders/optimization/scenario_5_with_p2p.py`

**Verify the dual-method approach:**

a) **Method A (greedy with P2P):**
   - Same greedy + adjust as S4 but with P2P added to available carriers.
   - **Question:** With P2P added, the greedy step may assign many groups to P2P. Then constraint adjustment must shift FROM P2P to OnTrac/USPS. The code handles this with "prefer non-P2P sources first, then P2P" ordering. Verify this works correctly — if the greedy over-assigns to P2P, the penalty to shift P2P->OnTrac could be high.

b) **Method B (improve S4 with P2P):**
   - Takes S4's solution and switches groups to P2P where `p2p_cost_avg < current_cost_avg`.
   - Respects surplus limits (can't take OnTrac below 279,080 or USPS below 140,000).
   - FedEx switches are unlimited (no FedEx minimum in S4/S5).
   - **Question:** Method B computes P2P savings as `(current_cost_avg - p2p_cost_avg) * shipment_count`. But the actual cost difference should be `current_cost_total_for_group - p2p_cost_total_for_group`. If `cost_avg * shipment_count == cost_total`, this is equivalent. Verify.

c) **S5 <= S4 guarantee:**
   - Method B guarantees this because it only makes beneficial switches.
   - Method A does NOT guarantee this (it's a fresh optimization that might get stuck in worse local optima).
   - The code picks `min(Method A, Method B)`, so the guarantee holds.
   - **Verify:** Check that the reported numbers confirm S5 <= S4 for all 4 variants.

d) **S5 "Both constraints" result:**
   - Reports $5,393,088 (Method B).
   - OnTrac: 279,082 (same as S4 — Method B doesn't touch OnTrac because it's at minimum with zero surplus).
   - USPS: 181,917 (reduced from S4's 224,183 by P2P switches).
   - P2P: 43,856 shipments, $197,977 total ($4.51/shipment avg).
   - FedEx: 53,158 (reduced from S4's 54,748).
   - **Verify:** 279,082 + 181,917 + 53,158 + 43,856 = 558,013. Costs: $2,563,752 + $1,471,243 + $1,160,117 + $197,977 = $5,393,089 (rounding).

### 7. Scenario 6: Constrained Optimization (FedEx 16% Earned)

**File:** `analysis/US_2026_tenders/optimization/scenario_6_fedex_16pct.py`

**Verify the FedEx threshold constraint:**

a) **Threshold calculation:**
   - `FEDEX_UNDISCOUNTED_THRESHOLD = 4,500,000`
   - `BAKED_FACTOR = 0.37`
   - `FEDEX_BASE_RATE_THRESHOLD = 4,500,000 * 0.37 = $1,665,000`
   - **Question:** The threshold is on "true undiscounted transportation" ($4.5M), but the code enforces it on `fedex_cost_base_rate_total` which is the BAKED (discounted) base rate. The relationship `undiscounted = baked_base_rate / BAKED_FACTOR` is correct IF `baked_base_rate = undiscounted * BAKED_FACTOR`. Verify: do the baked rate tables give `base_rate = undiscounted * (1 - PP - 0.18) = undiscounted * 0.37`? Read `carriers/fedex/calculate_costs.py` to confirm.

b) **Threshold enforcement algorithm:**
   - After volume constraints, shifts groups from USPS/OnTrac surplus to FedEx.
   - Sorted by "efficiency" (penalty per unit of threshold contribution).
   - **Question:** The shift penalty is `fedex_cost_total - {source}_cost_total`, but the contribution is `fedex_cost_base_rate_total`. These are different measures. A group might have high penalty but low base rate contribution (e.g., high surcharges). Verify the efficiency metric makes sense.

c) **"Both constraints" infeasibility:**
   - Reports $3.67M undiscounted FedEx spend, $830K short of $4.5M.
   - OnTrac at 279,080 + USPS at 140,001 = 419,081, leaving 138,932 for FedEx.
   - **Verify:** Does 138,932 FedEx shipments producing $3.67M undiscounted make sense? That's ~$26.42/shipment undiscounted, which seems high. Cross-check against S3 where 558,013 FedEx shipments produce X undiscounted.

d) **"Drop OnTrac" feasibility:**
   - Reports FedEx at $5.66M undiscounted (MET).
   - USPS: 328,764 shipments, FedEx: 229,249 shipments.
   - **Verify:** 328,764 + 229,249 = 558,013.

### 8. Scenario 7: Constrained + P2P (FedEx 16% Earned)

**File:** `analysis/US_2026_tenders/optimization/scenario_7_with_p2p.py`

**Verify:**

a) **Method B FedEx threshold awareness:**
   - When switching FedEx -> P2P in Method B, the code checks `fedex_base_rate_surplus = current_base_rate - FEDEX_BASE_RATE_THRESHOLD`.
   - Only switches FedEx groups whose cumulative base rate reduction stays within the surplus.
   - **Question:** Does this correctly preserve the threshold? After FedEx -> P2P switches, the remaining FedEx base rate should be >= $1,665,000. Verify the logic in `method_b_improve_s6()`.

b) **"Drop OnTrac" result ($4,433,040):**
   - USPS: 186,791, FedEx: 173,170, P2P: 198,052. Sum = 558,013.
   - FedEx undiscounted: $4,500,015 (just $15 above threshold).
   - **Question:** This razor-thin margin is suspicious. Is the optimizer perfectly calibrated, or is there an off-by-one / rounding issue? Examine how the threshold cutoff works — does it include or exclude the boundary group?

c) **"Both constraints" result ($5,002,886):**
   - Identical to S6 "Both constraints". P2P captures 0 shipments.
   - **Verify:** This makes sense because OnTrac is at minimum (no surplus to release to P2P), USPS is at minimum (no surplus), and FedEx is BELOW threshold (can't release to P2P). So P2P has no available groups to take. The code should show Method B switches = 0.

d) **S7 <= S6 guarantee:**
   - "Both constraints": S7 = $5,002,886, S6 = $5,002,886. Equal (0 improvement). OK.
   - "Drop OnTrac": S7 = $4,433,040, S6 = $5,040,871. S7 < S6. OK.
   - Verify all 4 variants.

### 9. Cross-Scenario Consistency Checks

**These are the most important checks. Numbers across scenarios must be consistent.**

a) **S1 baseline consistency:**
   - S1 reports $5,971,748 as the baseline.
   - S4/S5 internally use a DIFFERENT baseline (FedEx at 0% earned, ~$7.07M).
   - S6/S7 internally use the SAME baseline as S1 (FedEx at 16%, $5,971,748).
   - The executive summary reports all savings "vs S1" using $5,971,748.
   - **Verify:** For S4 "Both constraints" ($5,492,793), the savings is $5,971,748 - $5,492,793 = $478,955 (8.0%). But S4's INTERNAL comparison says savings vs adjusted baseline ($7.07M) is $1,581,789 (22.4%). The executive summary should use the $478,955 figure. Confirm.

b) **Shipment count consistency:**
   - Every scenario should account for exactly 558,013 shipments.
   - S1: 558,013 (including 40,157 DHL)
   - S4/S5/S6/S7: 558,013 (no DHL — optimization scenarios exclude DHL?)
   - **Question:** S4-S7 use `shipments_unified.parquet` which includes DHL shipments. But DHL has no carrier column in the optimization (only OnTrac, USPS, FedEx, P2P, Maersk). What happens to the 40,157 DHL shipments in optimization scenarios? They should have null costs for OnTrac and FedEx but valid costs for USPS and Maersk. The greedy assignment should assign them to a valid carrier. Verify DHL shipments are not lost or double-counted.

c) **Cost column consistency across scenarios:**
   - S2 uses `cost_current_carrier_total` from the AGGREGATED dataset (18% FedEx baked).
   - S1 uses `cost_current_carrier` from the UNIFIED dataset (adjusted to 16%).
   - S4 uses `cost_current_carrier` from UNIFIED (adjusted to 0%).
   - **Are these the same column?** In S1, `adjust_fedex_costs` modifies `cost_current_carrier`. In S4, `adjust_and_aggregate` also modifies it. But S2 loads the aggregated dataset independently, so it gets the pre-adjustment values. Verify that S2's baseline comparison uses consistent numbers.

d) **FedEx cost totals across scenarios:**
   - S1: FedEx total = $3,160,980 (at 16% earned, 273,941 shipments)
   - S3: FedEx total = $5,889,066 (at 18% earned, 558,013 shipments) — but this applies earned discount differently
   - S4 "Both constraints": FedEx total = $1,192,804 (at 0% earned, 54,748 shipments)
   - S6 "Both constraints": FedEx total = $1,856,932 (at 16% earned, 138,932 shipments)
   - **Reasonableness check:** S4 FedEx at 0% with 55K shipments = $21.79/avg. S6 FedEx at 16% with 139K shipments = $13.37/avg. The 0% rate should be 1.4865/1.0541 = 1.41x the 16% rate. $21.79 / $13.37 = 1.63x. This doesn't match. Why? Because the shipment MIX is different (S4 sends only the most expensive shipments to FedEx while S6 sends more). Verify this explanation is correct.

e) **2025 actuals comparison:**
   - The executive summary reports 539,941 matched shipments (96.8%).
   - 558,013 - 539,941 = 18,072 unmatched (3.2%).
   - S1 matched total: $5,731,467 (at 16% earned, for matched shipments only).
   - S7 matched total: $4,254,429.
   - **Question:** How are scenario assignments mapped to matched-only shipments? S4-S7 use aggregated data. The actuals comparison in the executive summary must disaggregate back to shipment-level to match against 2025 actuals. Verify how this is done — is there separate code that computes the actuals comparison, or is it computed within the scenario scripts?

f) **OnTrac constraint: 279,080 vs 279,082:**
   - S4 reports OnTrac at exactly 279,082 (2 over minimum).
   - S5 reports OnTrac at 279,082 (same — Method B doesn't change OnTrac).
   - S6 reports OnTrac at 279,080 (exactly at minimum).
   - **Why the 2-shipment difference?** In S4, the constraint adjustment shifts groups in bulk (whole groups). The cumulative shipment count may slightly overshoot. S6 uses a different adjustment algorithm order (volume first, then threshold). Verify this is just a rounding artifact from group-level assignment, not a bug.

### 10. Data Pipeline Verification

**Files:** `analysis/US_2026_tenders/scripts/`

a) **`build_shipment_dataset.py`:**
   - Joins 5 carrier parquet files on `pcs_orderid`.
   - Uses Maersk as base (most complete).
   - Loads 2025 actuals from Redshift.
   - Excludes 197 OnTrac OML/LPS outlier shipments.
   - **Question:** Are the 197 excluded shipments removed from ALL carrier cost columns (not just OnTrac)? If a shipment is excluded, it should be removed entirely, affecting shipment counts for all scenarios.

b) **`build_aggregated_dataset.py`:**
   - Groups by (packagetype, shipping_zip_code, weight_bracket).
   - Weight bracket = `ceil(weight_lbs)`.
   - **Question:** Is this the SAME weight bracket definition used in `adjust_and_aggregate()`? Check line 142 of `fedex_adjustment.py`: `pl.col("weight_lbs").ceil().cast(pl.Int32)`. This matches. Good.
   - **Question:** Are there any shipments with null weight that would create a null weight_bracket, potentially losing them in the group_by?

c) **Carrier calculator invocation:**
   - `run_all_carriers.py` runs 5 carrier calculators.
   - Each calculator is run via `carriers.{name}.scripts.upload_expected_all_us`.
   - **Assumption check:** These scripts produce parquet files that are then copied to `carrier_datasets/`. The costs in these parquets are "expected" costs using 2026 rate cards. Are these the same rate cards used in production? Verify the rate card dates/versions are 2026.

### 11. Specific Numbers to Verify

Run the scenario scripts and compare output to the reported numbers. For each, verify:

| Check | Expected | Source |
|-------|----------|--------|
| S1 total | $5,971,748.12 | scenario_1 output |
| S1 FedEx adjustment delta | ~$137,854 | S1 summary (1.0541x on FedEx base rates) |
| S2 Maersk total | $6,041,478.28 | scenario_2 output |
| S3 FedEx total (at 18%) | $5,889,066 | scenario_3 output |
| S4 "Both" total | $5,492,793.43 | scenario_4 output |
| S4 "Drop OnTrac" total | $5,857,270 | scenario_4 output |
| S5 "Both" total | $5,393,087.95 | scenario_5 output |
| S5 "Drop OnTrac" total | $4,931,056 | scenario_5 output |
| S6 "Both" total | $5,002,886 | scenario_6 output |
| S6 "Drop OnTrac" total | $5,040,871 | scenario_6 output |
| S7 "Both" total | $5,002,886 | scenario_7 output |
| S7 "Drop OnTrac" total | $4,433,040 | scenario_7 output |
| S7 FedEx undiscounted | $4,500,015 | scenario_7 output |
| Total shipments (all scenarios) | 558,013 | all scenarios |
| Matched shipments for actuals | 539,941 | executive_summary.md |

### 12. Logical Consistency Questions

These are higher-level questions about whether the analysis makes business sense:

a) **Is the FedEx earned discount model correct?** The analysis assumes PP (45%) and earned discount are both flat percentages of undiscounted rate, applied additively: `net_rate = undiscounted * (1 - PP - earned)`. Verify this against `carriers/fedex/README.md` and the FedEx rate structure documentation. If FedEx discounts are multiplicative instead (e.g., `undiscounted * (1 - PP) * (1 - earned)`), the entire adjustment formula is wrong.

b) **Is the FedEx threshold correctly defined?** The $4.5M threshold is on "undiscounted transportation charges". But what exactly counts? Just base rates? Or base rates + surcharges? The code uses `fedex_cost_base_rate` to compute undiscounted spend (`base_rate / 0.37`). Verify this is the correct definition by reading the FedEx contract terms in `carriers/fedex/README.md` or `carriers/fedex/data/reference/`.

c) **Should surcharges be adjusted?** The `adjust_fedex_costs()` function only adjusts base rate + fuel. Surcharges are left unchanged. But if the earned discount applies to surcharges too (some FedEx contracts discount everything), the adjustment is incomplete. Verify the contract terms.

d) **S7 "Drop OnTrac" threshold risk:** FedEx undiscounted is $4,500,015 — only $15 above $4.5M. In practice, if even a single shipment is routed differently, the threshold could be missed. Is this flagged as a risk? The summary mentions it but does the code build in any safety buffer?

e) **DHL handling:** 40,157 DHL shipments at $6.00/shipment = $240,942. In S4-S7 (optimization scenarios), what happens to DHL shipments? They're in the unified dataset. Do they get assigned to real carriers (OnTrac/USPS/FedEx/P2P)? Or are they excluded? If included, their S1 cost is $6/shipment but their optimized cost could be very different. This affects the savings calculation.

## How to Conduct the Audit

1. **Start with `fedex_adjustment.py`** — read it completely and verify the math line by line.
2. **Read `carriers/fedex/calculate_costs.py`** — understand what `fedex_cost_base_rate`, `fedex_cost_total`, `fedex_hd_cost_total`, `fedex_sp_cost_total` represent.
3. **Read `carriers/fedex/README.md`** — verify the discount structure (additive vs multiplicative).
4. **Read `build_shipment_dataset.py`** and `build_aggregated_dataset.py` — understand the data pipeline.
5. **For each scenario (1-7)**: read the script, trace the logic, verify the key numbers match the summary.
6. **Cross-check the executive summary** against individual scenario summaries.
7. **Check for the DHL handling gap** in optimization scenarios.
8. **Verify the S1 baseline is used consistently** across all "vs S1" comparisons.

## Output Format

Produce a structured audit report with:
- **PASS** / **FAIL** / **WARNING** for each check
- For FAILs: describe the exact discrepancy with line numbers
- For WARNINGs: describe the risk and suggested verification
- A final summary of findings with severity ratings (Critical / Major / Minor / Info)
