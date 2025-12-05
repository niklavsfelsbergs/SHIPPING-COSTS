"""
Load PCS Shipments

Pulls shipment data from the PCS database.
"""

import polars as pl
from pathlib import Path
from typing import Optional
import sys

# Add root directory to path for shared imports
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
from shared.database import pull_data


SQL_FILE = ROOT_DIR / "shared" / "sql" / "pcs_shipments.sql"

# Defaults for OnTrac
DEFAULT_CARRIER = "ONTRAC"
DEFAULT_PRODUCTION_SITES = ["Columbus", "Phoenix"]
DEFAULT_START_DATE = "2025-01-01"


def load_pcs_shipments(
    start_date: str = DEFAULT_START_DATE,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    carrier: str = DEFAULT_CARRIER,
    production_sites: Optional[list[str]] = None,
) -> pl.DataFrame:
    """
    Load shipment data from PCS database.

    Args:
        start_date: Start date (YYYY-MM-DD), defaults to 2025-01-01
        end_date: End date (YYYY-MM-DD), optional
        limit: Max rows to return, optional (for testing)
        carrier: Carrier extkey filter, defaults to 'ONTRAC'
        production_sites: List of production sites, defaults to ['Columbus', 'Phoenix']

    Returns:
        DataFrame with shipment data ready for supplement_shipments()
    """
    if production_sites is None:
        production_sites = DEFAULT_PRODUCTION_SITES

    # Build filter clauses
    carrier_filter = ""
    if carrier:
        carrier_filter = f"and ps.extkey = '{carrier}'"

    production_sites_filter = ""
    if production_sites:
        sites_list = ", ".join(f"'{site}'" for site in production_sites)
        production_sites_filter = f'and pp."name" in ({sites_list})'

    start_date_filter = ""
    if start_date:
        start_date_filter = f"and po.createddate >= '{start_date}'"

    end_date_filter = ""
    if end_date:
        end_date_filter = f"and po.createddate <= '{end_date}'"

    limit_clause = ""
    if limit:
        limit_clause = f"limit {limit}"

    query = SQL_FILE.read_text().format(
        carrier_filter=carrier_filter,
        production_sites_filter=production_sites_filter,
        start_date_filter=start_date_filter,
        end_date_filter=end_date_filter,
        limit_clause=limit_clause,
    )

    return pull_data(query)
