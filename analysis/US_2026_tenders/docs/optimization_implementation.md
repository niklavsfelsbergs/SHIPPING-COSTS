# Optimization Implementation Notes

This document tracks the implementation details and how to repeat calculations.

---

## Step 0: Copy Carrier Datasets

**Script:** `scripts/copy_carrier_datasets.py`

**Run:**
```bash
python -m analysis.US_2026_tenders.scripts.copy_carrier_datasets
```

**What it does:**
- Copies latest parquet files from each carrier's `scripts/output/all_us/` folder
- Outputs to `carrier_datasets/`

**Output files:**
- `carrier_datasets/ontrac_all_us_*.parquet`
- `carrier_datasets/usps_all_us_*.parquet`
- `carrier_datasets/fedex_all_us_*.parquet`
- `carrier_datasets/p2p_us_all_us_*.parquet`
- `carrier_datasets/maersk_us_all_us_*.parquet`

**When to re-run:**
- After updating any carrier's cost calculations with new rates

---

## Step 1: Build Shipment Dataset

**Script:** `scripts/build_shipment_dataset.py`

**Run:**
```bash
python -m analysis.US_2026_tenders.scripts.build_shipment_dataset
```

**What it does:**
- Joins all 5 carrier parquet files on `pcs_orderid`
- Renames columns with carrier prefixes for clarity
- Creates `cost_current_carrier` based on `pcs_shipping_provider` mapping

**Output:**
- `combined_datasets/shipments_unified.parquet`
- 558,210 rows, 66 columns

**Column naming convention:**
- Base columns: no prefix (from Maersk which has most detail)
- Carrier-specific: `{carrier}_` prefix (e.g., `ontrac_cost_total`, `fedex_shipping_zone`)

**pcs_shipping_provider mapping:**
| Value                   | Maps to Carrier | Count   | %     |
|-------------------------|-----------------|---------|-------|
| `FXEHD`                 | FedEx           | 165,565 | 29.7% |
| `ONTRAC`                | OnTrac          | 137,961 | 24.7% |
| `FXESPPS`               | FedEx           | 107,197 | 19.2% |
| `USPS`                  | USPS            | 106,151 | 19.0% |
| `DHL ECOMMERCE AMERICA` | None (null)     | 40,157  | 7.2%  |
| `FXEGRD`, `FXE2D`, etc. | FedEx           | 1,179   | 0.2%  |

**When to re-run:**
- After Step 0 (new carrier datasets)

---

## Step 2: Build Aggregated Dataset

**Script:** `scripts/build_aggregated_dataset.py`

**Run:**
```bash
python -m analysis.US_2026_tenders.scripts.build_aggregated_dataset
```

**What it does:**
- Groups shipments by `(packagetype, shipping_zip_code, weight_bracket_1lb)`
- Calculates totals and averages per group
- Determines cheapest carrier (among current: OnTrac, USPS, FedEx) per group

**Output:**
- `combined_datasets/shipments_aggregated.parquet`
- 352,805 groups, 18 columns

**Key metrics (from 2025 data):**

| Scenario                | Total Cost   | vs Current |
|-------------------------|--------------|------------|
| Current mix             | $6,459,547   | -          |
| 100% P2P                | $5,778,874   | -10.5%     |
| 100% Maersk             | $6,444,525   | -0.2%      |
| 100% FedEx              | $6,920,940   | +7.1%      |
| 100% USPS               | $8,195,287   | +26.9%     |
| 100% OnTrac             | $102,989,854 | +1494%*    |
| Optimal (unconstrained) | $5,192,509   | -19.6%     |

*Note: Current mix baseline includes DHL shipments @ $6.00/shipment estimate (40,157 × $6 = $240,942)*

*OnTrac has penalty costs for non-serviceable areas

**Cheapest carrier distribution:**
| Carrier | Shipments | %     |
|---------|-----------|-------|
| USPS    | 296,087   | 53.0% |
| OnTrac  | 153,957   | 27.6% |
| FedEx   | 108,166   | 19.4% |

**When to re-run:**
- After Step 1 (new unified dataset)

---

## Scenario Scripts

All scenario scripts read from `combined_datasets/` and output analysis results.

| Scenario | Script | Description |
|----------|--------|-------------|
| 1 | `optimization/scenario_1_current_mix.py` | Baseline with current carrier routing |
| 2 | `optimization/scenario_2_maersk_100.py` | 100% Maersk analysis |
| 3 | `optimization/scenario_3_fedex_100.py` | 100% FedEx with Earned Discount |
| 4 | `optimization/scenario_4_constrained.py` | Optimal mix with constraints |
| 5 | `optimization/scenario_5_with_p2p.py` | Optimal mix including P2P |

**When to re-run:**
- After Step 2 (new aggregated dataset)
- After changing optimization parameters

---

## Full Refresh Sequence

To recalculate everything from scratch:

```bash
# 1. Update carrier calculations first (in carriers/*/scripts/)
python -m carriers.ontrac.scripts.upload_expected_all_us
python -m carriers.usps.scripts.upload_expected_all_us
python -m carriers.fedex.scripts.upload_expected_all_us
python -m carriers.p2p_us.scripts.upload_expected_all_us
python -m carriers.maersk_us.scripts.upload_expected_all_us

# 2. Copy to analysis folder
python -m analysis.US_2026_tenders.scripts.copy_carrier_datasets

# 3. Build combined datasets (both are required)
python -m analysis.US_2026_tenders.scripts.build_shipment_dataset
python -m analysis.US_2026_tenders.scripts.build_aggregated_dataset  # Required for scenarios 4 & 5

# 4. Run scenarios
python -m analysis.US_2026_tenders.optimization.scenario_1_current_mix
python -m analysis.US_2026_tenders.optimization.scenario_2_maersk_100
python -m analysis.US_2026_tenders.optimization.scenario_3_fedex_100
python -m analysis.US_2026_tenders.optimization.scenario_4_constrained
python -m analysis.US_2026_tenders.optimization.scenario_5_with_p2p
```

---

---

## Output Formatting Requirements

### Markdown Table Alignment

All markdown tables in result summaries **MUST** have properly aligned columns for readability. Use consistent column widths with padding spaces so columns align vertically.

**Bad (unaligned):**
```markdown
| Carrier | Shipments | Share | Total Cost |
|---------|-----------|-------|------------|
| FedEx | 273,941 | 49.1% | $3,531,655.39 |
| OnTrac | 137,961 | 24.7% | $1,890,986.48 |
```

**Good (aligned):**
```markdown
| Carrier   | Shipments   | Share    | Total Cost        |
|-----------|-------------|----------|-------------------|
| FedEx     | 273,941     | 49.1%    | $3,531,655.39     |
| OnTrac    | 137,961     | 24.7%    | $1,890,986.48     |
```

**Rules:**
1. Column headers and separators should have consistent widths
2. Numeric values should be right-aligned within their column width
3. Text values should be left-aligned within their column width
4. Add at least 2-3 spaces of padding after the longest value in each column
5. Use consistent separator line widths (match header width)

This ensures tables are readable in both raw markdown and rendered views.

---

*Last updated: February 2026*
