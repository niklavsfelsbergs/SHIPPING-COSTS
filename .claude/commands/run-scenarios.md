---
description: Run US 2026 tender optimization scenarios 1-15 and update summaries
---

Run all optimization scenarios for the US 2026 tenders analysis and update the result summaries.

## Scenario Overview

| # | Name | FedEx Earned | Carriers | Key Constraint |
|---|------|-------------|----------|----------------|
| S1 | Current Carrier Mix | 16% (actual tier) | As-shipped | Baseline |
| S2 | 100% Maersk | n/a | Maersk | Full coverage |
| S3 | 100% FedEx | 18% (baked, conservative) | FedEx | Full coverage |
| S4 | Constrained Optimal | 0% (lost) | OnTrac/USPS/FedEx | Volume minimums |
| S5 | Constrained + P2P | 0% (lost) | OnTrac/USPS/FedEx/P2P | Volume minimums |
| S6 | FedEx 16% Optimal | 16% | OnTrac/USPS/FedEx | Volume minimums + FedEx $4.5M threshold |
| S7 | FedEx 16% + P2P | 16% | OnTrac/USPS/FedEx/P2P | Volume minimums + FedEx $4.5M threshold |
| S8 | Conservative P2P ($5M buffer) | 16% | USPS/FedEx/P2P | $5M FedEx threshold (Drop OnTrac) |
| S9 | 100% Maersk (NSD $9) | n/a | Maersk | Discounted NSD surcharge |
| S10 | Static Rules (per-packagetype) | 16% | USPS/FedEx/P2P | PCS-implementable rules (Drop OnTrac) |
| S11 | Static Rules (3-group) | 16% | USPS/FedEx/P2P | 3 group rules (Drop OnTrac) |
| S12 | 100% P2P Combined | n/a | P2P US + P2P US2 | Both P2P contracts |
| S13 | P2P + FedEx | 0% (lost) | P2P US + P2P US2 + FedEx | No USPS, no OnTrac |
| S14 | P2P + FedEx constrained | 16% | P2P US + P2P US2 + FedEx | $5.1M FedEx undiscounted floor |
| S15 | P2P + FedEx 3-Group | 16% | P2P US + P2P US2 + FedEx | 3 weight groups, $4.5M FedEx threshold |

**FedEx earned discount logic:**
- S1: Current mix qualifies for 16% tier. Rates adjusted from baked 18% to 16% (multiplier 1.0541).
- S3: 100% FedEx qualifies for 19% tier but uses baked 18% rate (conservative).
- S4/S5: Optimization drops FedEx below $4.5M threshold → 0% earned. Rates adjusted 18% → 0% (multiplier 1.4865).
- S6/S7/S8/S10/S11: Optimization constrained to maintain FedEx at 16% tier ($4.5M undiscounted threshold). Rates at 16%.
- S12: No FedEx (100% P2P).
- S13: P2P takes most volume, FedEx below $4.5M threshold → 0% earned. Rates adjusted 18% → 0% (multiplier 1.4865).
- S14: Same carriers as S13 but forces FedEx volume above $5.1M undiscounted → 16% earned. Rates at 16%. 187K P2P shipments forced to FedEx.
- S15: P2P + FedEx with 3 weight groups (Light/Medium/Heavy). Per-group carrier selection. FedEx constrained to $4.5M undiscounted → 16% earned.

## Before Running

**Ask the user to confirm** that the datasets are ready. The following steps must have been completed before running scenarios:

1. **Carrier calculations** - All 6 carriers (OnTrac, USPS, FedEx, P2P, P2P US2, Maersk) have been calculated with current rates
2. **Unified dataset** - `analysis/US_2026_tenders/combined_datasets/shipments_unified.parquet` exists and is up to date
3. **Aggregated dataset** - `analysis/US_2026_tenders/combined_datasets/shipments_aggregated.parquet` exists and is up to date

If the user is unsure, point them to the refresh workflow:
```bash
# Full refresh (if needed):
python -m analysis.US_2026_tenders.scripts.run_all_carriers --parquet-data shared/data/pcs_shipments_all_us_2025-01-01_2025-12-31.parquet --start-date 2025-01-01 --end-date 2025-12-31
python -m analysis.US_2026_tenders.scripts.build_aggregated_dataset
```

See `analysis/US_2026_tenders/README.md` for full instructions.

## Step 1: Run All Scenarios

Run these commands. Parallelization rules:
- **S1, S2, S3** can run in parallel (independent)
- **S4** must complete before **S5** (S5 references S4 results internally)
- **S6** can run in parallel with S4/S5 (independent)
- **S7** must complete after **S6** (S7 references S6 results internally)
- **S8, S9, S10, S11, S12, S13, S14, S15** can run in parallel with each other (independent)

```bash
python -m analysis.US_2026_tenders.optimization.scenario_1_current_mix
python -m analysis.US_2026_tenders.optimization.scenario_2_maersk_100
python -m analysis.US_2026_tenders.optimization.scenario_3_fedex_100
python -m analysis.US_2026_tenders.optimization.scenario_4_constrained
python -m analysis.US_2026_tenders.optimization.scenario_5_with_p2p
python -m analysis.US_2026_tenders.optimization.scenario_6_fedex_16pct
python -m analysis.US_2026_tenders.optimization.scenario_7_with_p2p
python -m analysis.US_2026_tenders.optimization.scenario_8_conservative
python -m analysis.US_2026_tenders.optimization.scenario_9_maersk_discounted
python -m analysis.US_2026_tenders.optimization.scenario_10_static_rules
python -m analysis.US_2026_tenders.optimization.scenario_11_three_groups
python -m analysis.US_2026_tenders.optimization.scenario_12_p2p_combined
python -m analysis.US_2026_tenders.optimization.scenario_13_p2p_fedex
python -m analysis.US_2026_tenders.optimization.scenario_14_p2p_fedex_constrained
python -m analysis.US_2026_tenders.optimization.scenario_15_p2p_fedex_3group
```

If any scenario fails, diagnose and fix the issue before continuing. Common failure: stale aggregated dataset missing expected columns - rebuild with `python -m analysis.US_2026_tenders.scripts.build_aggregated_dataset`.

**Important:** S4/S5 and S6/S7 use `fedex_adjustment.py` to adjust FedEx costs. S4/S5 call `adjust_and_aggregate(target_earned=0.0)` and S6/S7 call `adjust_and_aggregate(target_earned=0.16)`. S13 adjusts FedEx to 0% earned internally. S14 loads both 16% and 0% earned data (16% for costs, 0% for undiscounted spend tracking). If FedEx rates change, all affected scenarios must be re-run.

## Step 2: Update Summaries

After all scenarios complete, update each summary markdown file in `analysis/US_2026_tenders/results/scenario_*/summary.md`.

For each scenario:
1. **Read the existing summary** to understand the structure and narrative
2. **Compare old numbers to new script output** - identify what changed
3. **Update all numbers** that changed (costs, shipment counts, percentages, carrier mixes, savings)
4. **Update the narrative** if the story changed (e.g., if a scenario became more/less competitive)
5. **Preserve the structure** - keep the same sections, tables, and formatting style

**Key numbers to verify across scenarios:**
- Scenario 1 baseline cost (referenced by all other scenarios as universal baseline)
- FedEx earned discount tier qualification (S1=16%, S3=18% conservative, S4/S5=0%, S6/S7/S8/S10/S11=16%, S13=0%)
- Scenario 4 total cost (referenced by S5 for comparison)
- Scenario 6 total cost (referenced by S7 for comparison)
- Constraint satisfaction: OnTrac >= 279K, USPS >= 140K (S4-S7)
- FedEx $4.5M undiscounted threshold (S6/S7/S8/S10/S11 only)
- S6/S7 "Both constraints" infeasibility: OnTrac + USPS minimums prevent FedEx from reaching $4.5M
- S12: 100% P2P (no FedEx threshold relevant)
- S13: FedEx at 0% earned (P2P takes too much volume for FedEx to reach $4.5M)
- S14: FedEx at 16% earned (constrained to $5.1M undiscounted floor, $5M penalty threshold)
- S15: 3 weight groups (Light ≤3 lbs, Medium 3-21 lbs, Heavy >21 lbs), per-group carrier selection from P2P US, P2P US2, FedEx. FedEx HD/SP split tracked separately.

**Cross-references:**
- S5 compares against S4's cost
- S7 compares against S6's cost
- S12 compares P2P US vs P2P US2 contract split
- S13 compares P2P+FedEx vs USPS+FedEx (both at 2 carriers)
- S14 compares against S13's cost (unconstrained vs constrained) and S7-S11 (2 vs 3 carriers)
- S15 compares against S13/S14 (same carriers, different grouping strategy). Tracks FedEx HD/SP split in carrier_selection.csv and summary_metrics.csv.
- All scenarios compare against S1 baseline in the executive summary
- S6/S7 "Both constraints" are infeasible for FedEx 16% tier — note this clearly

**Formatting:** Follow the rules in `analysis/US_2026_tenders/docs/optimization_implementation.md` - aligned markdown tables with consistent column widths.

## Step 3: Update Executive Summary

After all scenario summaries are updated, update `analysis/US_2026_tenders/results/executive_summary.md`:

1. **Read the existing executive summary** to understand the structure
2. **Update the scenario comparison table** with all 15 scenarios. Include FedEx earned discount tier for each. Use Scenario 1's total cost as the universal baseline.
3. **Update the "Comparison to 2025 Actuals" table** - compute each scenario's 2026 calculated cost for matched shipments vs 2025 invoice actuals. Use the following approach:
   - Load `shipments_unified.parquet`, filter to matched shipments (`cost_actual` is not null)
   - S1: apply `adjust_fedex_costs(df, target_earned=0.16)` first, then sum `cost_current_carrier` for matched shipments
   - S2: sum `maersk_cost_total` for matched shipments
   - S3: sum `fedex_cost_total` for matched shipments (unadjusted, baked 18%)
   - S4/S5: apply `adjust_fedex_costs(df, target_earned=0.0)`, join `assignments.parquet` (from `results/scenario_4_constrained/` or `results/scenario_5_with_p2p/`) on (packagetype, shipping_zip_code, weight_bracket) to matched shipments, sum the assigned carrier's cost column
   - S6/S7: apply `adjust_fedex_costs(df, target_earned=0.16)`, join `assignments.parquet` (from `results/scenario_6_fedex_16pct/` or `results/scenario_7_with_p2p/`) on (packagetype, shipping_zip_code, weight_bracket) to matched shipments, sum the assigned carrier's cost column
   - S12: per-shipment cheapest of p2p_cost_total and p2p_us2_cost_total
   - S13: apply `adjust_fedex_costs(df, target_earned=0.0)`, per-shipment cheapest of p2p_cost_total, p2p_us2_cost_total, fedex_cost_total
   - weight_bracket = `ceil(weight_lbs)` cast to integer
   - Compare each scenario total vs `cost_actual` sum
   - For S6/S7, note which variants are feasible (FedEx 16% tier met) and which are not
4. **Update the monthly breakdown table** - same computation as above but grouped by `ship_date` month. Show matched shipment count, 2025 actuals, and each scenario's monthly cost in $K (rounded to nearest thousand)
5. **Update scenario detail sections** with key metrics from each scenario's output. Add S12, S13, S14, and S15 sections.
6. **Update key insights** - include new findings about P2P US2 and P2P+FedEx scenarios
7. **Preserve the structure** - keep the same sections, tables, and formatting style.

## Step 3b: Update S15 Validation

After S15 completes, update the S15 validation documents in `analysis/US_2026_tenders/S15_validation/`:

1. **`s15_summary.md`** - Update all numbers: total cost, carrier split table (P2P US, P2P US2, FedEx HD, FedEx SP), per-group routing rules, weight boundaries, FedEx undiscounted spend, HD/SP ratio
2. **`validation_plan.md`** - Update numbers in validation items that reference S15 outputs
3. **`actuals_reconciliation.md`** - Update if the matched shipment count or actuals total changed (e.g., after rebuilding unified dataset with matched-only filter)

## Step 4: Report Results

Present a summary table to the user showing all 15 scenarios with key metrics:
- Total cost
- FedEx earned discount tier
- Savings vs S1 baseline ($ and %)
- Key variant details (for S4-S7, show "Both constraints" and "Drop OnTrac" variants)
- Whether any numbers changed significantly from previous run
- Flag infeasible combinations (S6/S7 "Both constraints" for FedEx 16%)
- S12/S13/S14 carrier composition and P2P US vs P2P US2 split
- S14 forced-to-FedEx count and constraint cost
- S15 3-group routing rules, FedEx HD/SP split, per-group carrier assignments
