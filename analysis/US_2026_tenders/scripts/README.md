# US 2026 Tenders - Scripts

Scripts for calculating carrier costs and building datasets for optimization analysis.

## Overview

```
PCS Database ──► export_pcs_shipments.py ──► pcs_shipments.parquet (shared/data/)
                                                      │
                                                      ▼
                                            ┌─────────────────────┐
                                            │  run_all_carriers   │
                                            │         or          │
                                            │  individual carrier │
                                            │     calculators     │
                                            └─────────────────────┘
                                                      │
                                                      ▼
                              carriers/{carrier}/scripts/output/all_us/*.parquet
                                                      │
                                                      ▼
                                          copy_carrier_datasets.py
                                                      │
                                                      ▼
                              US_2026_tenders/carrier_datasets/*.parquet
                                                      │
                                                      ▼
                                          build_shipment_dataset.py
                                                      │
                                                      ▼
                              US_2026_tenders/combined_datasets/shipments_unified.parquet
```

## Workflows

### Full Rebuild (All Carriers)

Run all 5 carrier calculators and build the combined dataset:

```bash
# Step 1: Export PCS data (only needed once, or when date range changes)
python -m shared.scripts.export_pcs_shipments --start-date 2025-01-01 --end-date 2025-12-31

# Step 2: Run all carriers and build combined dataset
python -m analysis.US_2026_tenders.scripts.run_all_carriers \
    --parquet-data shared/data/pcs_shipments_all_us_2025-01-01_2025-12-31.parquet \
    --start-date 2025-01-01 --end-date 2025-12-31
```

This will:
1. Calculate costs for all 5 carriers (OnTrac, USPS, FedEx, P2P US, Maersk US)
2. Copy outputs to `carrier_datasets/`
3. Build `combined_datasets/shipments_unified.parquet`

### Single Carrier Update

Update one carrier and rebuild the combined dataset:

```bash
# Step 1: Run the single carrier's calculator
python -m carriers.fedex.scripts.upload_expected_all_us --full --parquet \
    --parquet-data shared/data/pcs_shipments_all_us_2025-01-01_2025-12-31.parquet \
    --start-date 2025-01-01 --end-date 2025-12-31

# Step 2: Copy updated files to carrier_datasets/
python -m analysis.US_2026_tenders.scripts.copy_carrier_datasets

# Step 3: Rebuild the combined dataset
python -m analysis.US_2026_tenders.scripts.build_shipment_dataset
```

### Rebuild Combined Dataset Only

If carrier datasets already exist and you just need to rebuild the combined dataset:

```bash
python -m analysis.US_2026_tenders.scripts.build_shipment_dataset
```

Or using run_all_carriers with skip flag:

```bash
python -m analysis.US_2026_tenders.scripts.run_all_carriers --skip-calculation --start-date 2025-01-01
```

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `run_all_carriers.py` | Runs all 5 carrier calculators and builds combined dataset |
| `copy_carrier_datasets.py` | Copies latest parquet from each carrier's output to `carrier_datasets/` |
| `build_shipment_dataset.py` | Joins all carrier datasets into `shipments_unified.parquet` |
| `build_aggregated_dataset.py` | Aggregates unified dataset by (packagetype, zip, weight) for optimization |

## Carrier Calculators

Each carrier has an `upload_expected_all_us.py` script:

| Carrier | Module |
|---------|--------|
| OnTrac | `carriers.ontrac.scripts.upload_expected_all_us` |
| USPS | `carriers.usps.scripts.upload_expected_all_us` |
| FedEx | `carriers.fedex.scripts.upload_expected_all_us` |
| P2P US | `carriers.p2p_us.scripts.upload_expected_all_us` |
| Maersk US | `carriers.maersk_us.scripts.upload_expected_all_us` |

### Common Options

```
--full              Full calculation, delete existing and reupload
--parquet           Save output to parquet file instead of database
--parquet-data PATH Load PCS shipments from parquet file instead of database
--start-date DATE   Start date (YYYY-MM-DD)
--end-date DATE     End date (YYYY-MM-DD)
--dry-run           Preview without making changes
```

## Output Locations

| Output | Path |
|--------|------|
| PCS export | `shared/data/pcs_shipments_all_us_{start}_{end}.parquet` |
| Carrier outputs | `carriers/{carrier}/scripts/output/all_us/{carrier}_all_us_{start}_{end}.parquet` |
| Carrier datasets | `analysis/US_2026_tenders/carrier_datasets/` |
| Combined dataset | `analysis/US_2026_tenders/combined_datasets/shipments_unified.parquet` |
| Aggregated dataset | `analysis/US_2026_tenders/combined_datasets/shipments_aggregated.parquet` |
