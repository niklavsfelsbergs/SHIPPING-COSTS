"""
Pull FedEx Invoice Data and Save as Parquet

Usage:
    python -m carriers.fedex.development.pull_invoice_data
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
from shared.database import pull_data

SQL_FILE = Path(__file__).parent.parent / "temp_files" / "fedex_invoice_data.sql"
OUTPUT_FILE = Path(__file__).parent / "invoice_data.parquet"


def main():
    print("Reading SQL query...")
    query = SQL_FILE.read_text()

    print("Pulling FedEx invoice data (this may take a while)...")
    df = pull_data(query)
    print(f"Loaded {len(df):,} rows")
    print(f"Columns: {df.columns}")

    # Save as parquet
    df.write_parquet(OUTPUT_FILE)
    print(f"Saved to {OUTPUT_FILE}")

    # Show summary
    print(f"\nDataset summary:")
    print(f"  Date range: {df['invoice_date'].min()} to {df['invoice_date'].max()}")
    print(f"  Service types: {df['service_type'].unique().to_list()}")
    print(f"  Charge descriptions: {df['charge_description'].unique().to_list()}")


if __name__ == "__main__":
    main()
