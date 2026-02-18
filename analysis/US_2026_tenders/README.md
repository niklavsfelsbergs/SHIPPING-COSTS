# US 2026 Tenders - Carrier Optimization Analysis

Finds the optimal carrier routing strategy for US shipments using 2026 tender rates. Calculates costs across 5 carriers, then runs optimization scenarios with volume constraints.

## Scenarios

| #   | Script                       | Question                                          |
|-----|------------------------------|---------------------------------------------------|
| 1   | `scenario_1_current_mix`     | Baseline: what does current routing cost?          |
| 2   | `scenario_2_maersk_100`      | What if 100% Maersk? (not currently used)          |
| 3   | `scenario_3_fedex_100`       | What if 100% FedEx? What earned discount tier?     |
| 4   | `scenario_4_constrained`     | Optimal mix with OnTrac/USPS volume commitments    |
| 5   | `scenario_5_with_p2p`        | Does adding P2P improve the optimal mix?           |

Results and summaries are saved to `results/scenario_*/`.

## Full Refresh (from scratch)

### Step 1: Export PCS shipments (optional, avoids repeated DB queries)

```bash
python -m shared.scripts.export_pcs_shipments --start-date 2025-01-01 --end-date 2025-12-31
```

### Step 2: Run all carrier calculators + build unified dataset

```bash
python -m analysis.US_2026_tenders.scripts.run_all_carriers --parquet-data shared/data/pcs_shipments_all_us_2025-01-01_2025-12-31.parquet --start-date 2025-01-01 --end-date 2025-12-31
```

This runs all 5 carriers (OnTrac, USPS, FedEx, P2P, Maersk), copies outputs to `carrier_datasets/`, and builds `combined_datasets/shipments_unified.parquet`.

### Step 3: Build aggregated dataset

```bash
python -m analysis.US_2026_tenders.scripts.build_aggregated_dataset
```

Groups shipments by (packagetype, zip, weight bracket) into `combined_datasets/shipments_aggregated.parquet`. **Required before running scenarios 4 and 5.**

### Step 4: Run scenarios

```bash
python -m analysis.US_2026_tenders.optimization.scenario_1_current_mix
python -m analysis.US_2026_tenders.optimization.scenario_2_maersk_100
python -m analysis.US_2026_tenders.optimization.scenario_3_fedex_100
python -m analysis.US_2026_tenders.optimization.scenario_4_constrained
python -m analysis.US_2026_tenders.optimization.scenario_5_with_p2p
```

Scenarios 1-3 read from `shipments_unified.parquet`. Scenarios 4-5 read from `shipments_aggregated.parquet`.

## Partial Refresh (after updating a single carrier)

```bash
# 1. Recalculate the carrier (example: FedEx)
python -m carriers.fedex.scripts.upload_expected_all_us --full --parquet --parquet-data shared/data/pcs_shipments_all_us_2025-01-01_2025-12-31.parquet --start-date 2025-01-01 --end-date 2025-12-31

# 2. Copy and rebuild datasets
python -m analysis.US_2026_tenders.scripts.copy_carrier_datasets
python -m analysis.US_2026_tenders.scripts.build_shipment_dataset
python -m analysis.US_2026_tenders.scripts.build_aggregated_dataset

# 3. Re-run scenarios
python -m analysis.US_2026_tenders.optimization.scenario_1_current_mix
# ... (whichever scenarios need updating)
```

## Individual Carrier Commands

```bash
python -m carriers.ontrac.scripts.upload_expected_all_us --full --parquet --parquet-data shared/data/pcs_shipments_all_us_2025-01-01_2025-12-31.parquet --start-date 2025-01-01 --end-date 2025-12-31
python -m carriers.usps.scripts.upload_expected_all_us --full --parquet --parquet-data shared/data/pcs_shipments_all_us_2025-01-01_2025-12-31.parquet --start-date 2025-01-01 --end-date 2025-12-31
python -m carriers.fedex.scripts.upload_expected_all_us --full --parquet --parquet-data shared/data/pcs_shipments_all_us_2025-01-01_2025-12-31.parquet --start-date 2025-01-01 --end-date 2025-12-31
python -m carriers.p2p_us.scripts.upload_expected_all_us --full --parquet --parquet-data shared/data/pcs_shipments_all_us_2025-01-01_2025-12-31.parquet --start-date 2025-01-01 --end-date 2025-12-31
python -m carriers.maersk_us.scripts.upload_expected_all_us --full --parquet --parquet-data shared/data/pcs_shipments_all_us_2025-01-01_2025-12-31.parquet --start-date 2025-01-01 --end-date 2025-12-31
```

## Documentation

- `docs/optimization_guide.md` - Scenario definitions, FedEx earned discount tiers, constraints
- `docs/optimization_implementation.md` - Implementation details, data pipeline, output formatting
- `docs/calculation_logic/` - Per-carrier calculation documentation
