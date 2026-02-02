"""
Export Dashboard Data
=====================

Pulls comparison data from Redshift and saves locally as parquet + JSON.
Run this before launching the dashboard to avoid needing a live DB connection.

Usage:
    python -m carriers.usps.dashboard.export_data
"""

import json
from pathlib import Path

import polars as pl
from shared.database import pull_data

SQL_DIR = Path(__file__).parent / "sql"
DATA_DIR = Path(__file__).parent / "data"

EXPECTED_TABLE = "shipping_costs.expected_shipping_costs_usps"
ACTUAL_TABLE = "shipping_costs.actual_shipping_costs_usps"


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # --- 1. Export comparison dataset ---
    print("Loading comparison data from Redshift...")
    query = (SQL_DIR / "comparison.sql").read_text()
    # Use pandas for initial load to handle mixed types, then convert to polars
    df_pd = pull_data(query, as_polars=False)
    df = pl.from_pandas(df_pd)
    print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")

    # Cast billing_date to Date (removes time component, avoids 22:00:00 boundary issues)
    if "billing_date" in df.columns:
        df = df.with_columns(pl.col("billing_date").cast(pl.Date))
        print("  Cast billing_date to Date")

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
            e.shop_ordernumber,
            e.pcs_created,
            e.ship_date,
            e.production_site,
            e.shipping_zip_code,
            e.shipping_region,
            e.shipping_country,
            e.packagetype,
            CAST(e.shipping_zone AS VARCHAR(10)) AS shipping_zone,
            CAST(e.rate_zone AS VARCHAR(10)) AS rate_zone,
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
            e.cost_base,
            e.cost_nsl1,
            e.cost_nsl2,
            e.cost_nsv,
            e.cost_peak,
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
            a.billing_date,
            CAST(a.actual_zone AS VARCHAR(10)) AS actual_zone,
            a.actual_weight_lbs AS actual_billed_weight_lbs,
            a.actual_base,
            a.actual_nsl1,
            a.actual_nsl2,
            a.actual_noncompliance,
            a.actual_total,
            a.has_adjustment
        FROM {ACTUAL_TABLE} a
        LEFT JOIN {EXPECTED_TABLE} e
            ON a.pcs_orderid = e.pcs_orderid
        WHERE e.pcs_orderid IS NULL
    """

    # Use pandas for initial load to handle mixed types
    unmatched_expected_pd = pull_data(unmatched_expected_query, as_polars=False)
    unmatched_actual_pd = pull_data(unmatched_actual_query, as_polars=False)
    unmatched_expected = pl.from_pandas(unmatched_expected_pd)
    unmatched_actual = pl.from_pandas(unmatched_actual_pd)

    # Cast billing_date to Date (removes time component)
    if "billing_date" in unmatched_actual.columns:
        unmatched_actual = unmatched_actual.with_columns(
            pl.col("billing_date").cast(pl.Date)
        )

    unmatched_expected_path = DATA_DIR / "unmatched_expected.parquet"
    unmatched_actual_path = DATA_DIR / "unmatched_actual.parquet"

    unmatched_expected.write_parquet(unmatched_expected_path)
    unmatched_actual.write_parquet(unmatched_actual_path)

    print(f"  Expected-only: {len(unmatched_expected):,}")
    print(f"  Actual-only:   {len(unmatched_actual):,}")
    print(f"  Saved to {unmatched_expected_path} and {unmatched_actual_path}")

    print("\nDone. Run the dashboard with:")
    print("  streamlit run carriers/usps/dashboard/USPS.py")


if __name__ == "__main__":
    main()
