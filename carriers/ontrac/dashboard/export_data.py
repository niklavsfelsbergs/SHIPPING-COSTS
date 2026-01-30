"""
Export Dashboard Data
=====================

Pulls comparison data from Redshift and saves locally as parquet + JSON.
Run this before launching the dashboard to avoid needing a live DB connection.

Usage:
    python -m carriers.ontrac.dashboard.export_data
"""

import json
from pathlib import Path

from shared.database import pull_data

SQL_DIR = Path(__file__).parent / "sql"
DATA_DIR = Path(__file__).parent / "data"

EXPECTED_TABLE = "shipping_costs.expected_shipping_costs_ontrac"
ACTUAL_TABLE = "shipping_costs.actual_shipping_costs_ontrac"


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # --- 1. Export comparison dataset ---
    print("Loading comparison data from Redshift...")
    query = (SQL_DIR / "comparison.sql").read_text()
    df = pull_data(query)
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
            e.shop_ordernumber,
            e.pcs_created,
            e.ship_date,
            e.production_site,
            e.shipping_zip_code,
            e.shipping_region,
            e.shipping_country,
            e.packagetype,
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
            e.cost_base,
            e.cost_oml,
            e.cost_lps,
            e.cost_ahs,
            e.cost_das,
            e.cost_edas,
            e.cost_res,
            e.cost_dem_oml,
            e.cost_dem_lps,
            e.cost_dem_ahs,
            e.cost_dem_res,
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
            a.billing_date,
            a.actual_zone,
            a.actual_billed_weight_lbs,
            a.actual_base,
            a.actual_oml,
            a.actual_lps,
            a.actual_ahs,
            a.actual_das,
            a.actual_edas,
            a.actual_res,
            a.actual_dem_oml,
            a.actual_dem_lps,
            a.actual_dem_ahs,
            a.actual_dem_res,
            a.actual_fuel,
            a.actual_total,
            a.actual_unresolved_address,
            a.actual_address_correction,
            a.return_to_sender
        FROM {ACTUAL_TABLE} a
        LEFT JOIN {EXPECTED_TABLE} e
            ON a.pcs_orderid = e.pcs_orderid
        WHERE e.pcs_orderid IS NULL
    """

    unmatched_expected = pull_data(unmatched_expected_query)
    unmatched_actual = pull_data(unmatched_actual_query)

    unmatched_expected_path = DATA_DIR / "unmatched_expected.parquet"
    unmatched_actual_path = DATA_DIR / "unmatched_actual.parquet"

    unmatched_expected.write_parquet(unmatched_expected_path)
    unmatched_actual.write_parquet(unmatched_actual_path)

    print(f"  Expected-only: {len(unmatched_expected):,}")
    print(f"  Actual-only:   {len(unmatched_actual):,}")
    print(f"  Saved to {unmatched_expected_path} and {unmatched_actual_path}")

    print("\nDone. Run the dashboard with:")
    print("  streamlit run carriers/ontrac/dashboard/app.py")


if __name__ == "__main__":
    main()
