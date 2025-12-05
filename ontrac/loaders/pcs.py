"""
Load PCS Shipments

Pulls OnTrac shipment data from the PCS database.
"""

import polars as pl
from pathlib import Path
from typing import Optional
import sys

# Add root directory to path for database import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from database import pull_data


SQL_FILE = Path(__file__).parent / "sql" / "pcs_shipments.sql"


def load_pcs_shipments(
    start_date: str,
    end_date: Optional[str] = None,
    limit: Optional[int] = None
) -> pl.DataFrame:
    """
    Load OnTrac shipment data from PCS database.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD), optional
        limit: Max rows to return, optional (for testing)

    Returns:
        DataFrame with shipment data ready for supplement_shipments()
    """
    start_date_filter = f"and po.createddate >= '{start_date}'"

    end_date_filter = ""
    if end_date:
        end_date_filter = f"and po.createddate <= '{end_date}'"

    limit_clause = ""
    if limit:
        limit_clause = f"limit {limit}"

    query = SQL_FILE.read_text().format(
        start_date_filter=start_date_filter,
        end_date_filter=end_date_filter,
        limit_clause=limit_clause,
    )

    return pull_data(query)
