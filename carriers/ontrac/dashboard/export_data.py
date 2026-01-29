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

    print("\nDone. Run the dashboard with:")
    print("  streamlit run carriers/ontrac/dashboard/app.py")


if __name__ == "__main__":
    main()
