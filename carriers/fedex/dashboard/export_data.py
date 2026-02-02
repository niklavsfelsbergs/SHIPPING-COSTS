"""
Export Dashboard Data
=====================

Pulls comparison data from Redshift and saves locally as parquet + JSON.
Run this before launching the dashboard to avoid needing a live DB connection.

Usage:
    python -m carriers.fedex.dashboard.export_data
"""

import json
from pathlib import Path

import polars as pl
from shared.database import pull_data

SQL_DIR = Path(__file__).parent / "sql"
DATA_DIR = Path(__file__).parent / "data"

EXPECTED_TABLE = "shipping_costs.expected_shipping_costs_fedex"
ACTUAL_TABLE = "shipping_costs.actual_shipping_costs_fedex"


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # --- 1. Export comparison dataset ---
    print("Loading comparison data from Redshift...")
    query = (SQL_DIR / "comparison.sql").read_text()
    # Use pandas first to handle Decimal types, then convert to Polars
    df = pull_data(query, as_polars=False)
    df = pl.from_pandas(df)
    print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")

    parquet_path = DATA_DIR / "comparison.parquet"
    df.write_parquet(parquet_path)
    print(f"  Saved to {parquet_path}")

    # --- 2. Export match rate counts ---
    print("Loading match rate counts...")
    actual_count = int(
        pull_data(
            f"SELECT COUNT(DISTINCT pcs_orderid) AS cnt FROM {ACTUAL_TABLE}"
        )["cnt"][0]
    )
    matched_count = int(
        pull_data(
            f"SELECT COUNT(DISTINCT e.pcs_orderid) AS cnt "
            f"FROM {EXPECTED_TABLE} e "
            f"INNER JOIN {ACTUAL_TABLE} a ON e.pcs_orderid = a.pcs_orderid"
        )["cnt"][0]
    )

    match_rate = {
        "actual_orderids": actual_count,
        "matched_orderids": matched_count,
    }

    json_path = DATA_DIR / "match_rate.json"
    json_path.write_text(json.dumps(match_rate, indent=2))
    print(f"  actual_orderids: {actual_count:,}")
    print(f"  matched_orderids: {matched_count:,}")
    print(f"  Saved to {json_path}")

    # --- 3. Export unmatched shipments (expected-only / actual-only) ---
    print("Loading unmatched shipments...")
    unmatched_expected_query = f"""
        SELECT
            e.pcs_orderid,
            e.pcs_ordernumber,
            e.latest_trackingnumber,
            e.pcs_created,
            e.ship_date,
            e.production_site,
            e.shipping_region,
            e.packagetype,
            e.rate_service,
            e.shipping_zone,
            e.das_zone,
            e.billable_weight_lbs,
            e.length_in,
            e.width_in,
            e.height_in,
            e.weight_lbs,
            e.cubic_in,
            e.longest_side_in,
            e.second_longest_in,
            e.length_plus_girth,
            e.dim_weight_lbs,
            e.uses_dim_weight,
            e.cost_base_rate,
            e.cost_performance_pricing,
            e.cost_earned_discount,
            e.cost_grace_discount,
            e.cost_ahs,
            e.cost_ahs_weight,
            e.cost_oversize,
            e.cost_das,
            e.cost_residential,
            e.cost_dem_base,
            e.cost_dem_ahs,
            e.cost_dem_oversize,
            e.cost_fuel,
            e.cost_total
        FROM {EXPECTED_TABLE} e
        LEFT JOIN {ACTUAL_TABLE} a
            ON e.pcs_orderid = a.pcs_orderid
        WHERE a.pcs_orderid IS NULL
    """

    unmatched_actual_query = f"""
        SELECT
            a.pcs_orderid,
            a.trackingnumber AS actual_trackingnumber,
            a.invoice_number,
            a.invoice_date,
            a.actual_zone,
            a.rated_weight_lbs AS actual_rated_weight_lbs,
            a.actual_base,
            a.actual_performance_pricing,
            a.actual_earned_discount,
            a.actual_grace_discount,
            a.actual_ahs,
            a.actual_ahs_weight,
            a.actual_oversize,
            a.actual_das,
            a.actual_residential,
            a.actual_dem_base,
            a.actual_dem_ahs,
            a.actual_dem_oversize,
            a.actual_dem_residential,
            a.actual_fuel,
            a.actual_net_charge,
            a.actual_unpredictable
        FROM {ACTUAL_TABLE} a
        LEFT JOIN {EXPECTED_TABLE} e
            ON a.pcs_orderid = e.pcs_orderid
        WHERE e.pcs_orderid IS NULL
    """

    unmatched_expected = pl.from_pandas(pull_data(unmatched_expected_query, as_polars=False))
    unmatched_actual = pl.from_pandas(pull_data(unmatched_actual_query, as_polars=False))

    unmatched_expected_path = DATA_DIR / "unmatched_expected.parquet"
    unmatched_actual_path = DATA_DIR / "unmatched_actual.parquet"

    unmatched_expected.write_parquet(unmatched_expected_path)
    unmatched_actual.write_parquet(unmatched_actual_path)

    print(f"  Expected-only: {len(unmatched_expected):,}")
    print(f"  Actual-only:   {len(unmatched_actual):,}")
    print(f"  Saved to {unmatched_expected_path} and {unmatched_actual_path}")

    print("\nDone. Run the dashboard with:")
    print("  streamlit run carriers/fedex/dashboard/FedEx.py")


if __name__ == "__main__":
    main()
