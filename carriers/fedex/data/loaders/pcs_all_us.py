"""
Load All US Shipments from PCS

Pulls ALL US shipment data from the PCS database, regardless of carrier.
Used for carrier cost optimization analysis - calculating what shipments
would cost with FedEx even if they actually used a different carrier.
"""

import polars as pl
from pathlib import Path
from typing import Optional

import shared
from shared.database import pull_data


SQL_FILE = Path(shared.__file__).parent / "sql" / "pcs_shipments_country.sql"

# Defaults for all-US analysis (no carrier filter, Columbus only)
DEFAULT_CARRIER = None  # No carrier filter - get ALL shipments
DEFAULT_COUNTRY = "United States of America"
DEFAULT_PRODUCTION_SITES = ["Columbus"]  # CMH zones only for consistent comparison
DEFAULT_START_DATE = "2025-01-01"


def load_pcs_shipments_all_us(
    start_date: str = DEFAULT_START_DATE,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    country: str = DEFAULT_COUNTRY,
    production_sites: Optional[list[str]] = None,
) -> pl.DataFrame:
    """
    Load ALL US shipment data from PCS database.

    Unlike load_pcs_shipments(), this does not filter by carrier.
    Used for carrier cost optimization analysis.

    Args:
        start_date: Start date (YYYY-MM-DD), defaults to 2025-01-01
        end_date: End date (YYYY-MM-DD), optional
        limit: Max rows to return, optional (for testing)
        country: Country name filter, defaults to 'United States of America'
        production_sites: List of production sites, defaults to ['Columbus']

    Returns:
        DataFrame with shipment data ready for supplement_shipments()
    """
    if production_sites is None:
        production_sites = DEFAULT_PRODUCTION_SITES

    # No carrier filter - we want ALL shipments
    carrier_filter = ""

    # Country filter
    country_filter = ""
    if country:
        country_filter = f"and pc.\"name\" = '{country}'"

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
        country_filter=country_filter,
        start_date_filter=start_date_filter,
        end_date_filter=end_date_filter,
        limit_clause=limit_clause,
    )

    return pull_data(query)
