"""
Load All US Shipments from PCS

Pulls US shipment data from all production sites for US domestic carriers
(FedEx, OnTrac, USPS, DHL eCommerce). Used for carrier cost optimization
analysis - calculating what shipments would cost with P2P US2 regardless
of which carrier was actually used.
"""

import polars as pl
from pathlib import Path
from typing import Optional

import shared
from shared.database import pull_data


SQL_FILE = Path(shared.__file__).parent / "sql" / "pcs_shipments_country.sql"

# Defaults for all-US analysis
DEFAULT_COUNTRY = "United States of America"
DEFAULT_PRODUCTION_SITES = None  # All sites - costs calculated using CMH zones
DEFAULT_START_DATE = "2025-01-01"

# Carrier filter: only US domestic carriers we have calculators for
DEFAULT_CARRIER_FILTER = "and (ps.extkey like '%FX%' or ps.extkey = 'ONTRAC' or ps.extkey = 'USPS' or ps.extkey = 'DHL ECOMMERCE AMERICA')"


def load_pcs_shipments_all_us(
    start_date: str = DEFAULT_START_DATE,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    country: str = DEFAULT_COUNTRY,
    production_sites: Optional[list[str]] = None,
) -> pl.DataFrame:
    """
    Load ALL US shipment data from PCS database.

    Loads shipments from all production sites for US domestic carriers
    (FedEx, OnTrac, USPS, DHL eCommerce). Used for carrier cost optimization
    analysis - calculating what shipments would cost with different carriers.

    Args:
        start_date: Start date (YYYY-MM-DD), defaults to 2025-01-01
        end_date: End date (YYYY-MM-DD), optional
        limit: Max rows to return, optional (for testing)
        country: Country name filter, defaults to 'United States of America'
        production_sites: List of production sites, defaults to None (all sites)

    Returns:
        DataFrame with shipment data ready for supplement_shipments()
    """
    carrier_filter = DEFAULT_CARRIER_FILTER

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
