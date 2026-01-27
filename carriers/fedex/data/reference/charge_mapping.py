"""
FedEx Invoice Charge Mapping

Maps invoice charge_description values to actual_* column names for the
actuals table. Unmapped charges go to actual_unpredictable.

Source: Distinct charge_description values from fedex_invoicedata_historical
Last updated: 2026-01-27
"""

# Mapping of invoice charge_description -> actual column name
CHARGE_MAPPING = {
    # Base charge (calculated in SQL as net_charge - sum of itemized charges)
    "Base Charge": "actual_base",

    # AHS - Dimensions (packages exceeding dimension thresholds)
    "AHS - Dimensions": "actual_ahs",
    "Add'l Handling-Dimension": "actual_ahs",
    "Add'l Handling-Packaging": "actual_ahs",

    # AHS - Weight (packages exceeding weight threshold)
    "AHS - Weight": "actual_ahs_weight",
    "Add'l Handling-Weight": "actual_ahs_weight",
    "Additional weight charge": "actual_ahs_weight",

    # DAS - Delivery Area Surcharge (all variants map to single column)
    "DAS Comm": "actual_das",
    "DAS Commercial": "actual_das",
    "DAS Resi": "actual_das",
    "DAS Residential": "actual_das",
    "DAS Extended Comm": "actual_das",
    "DAS Extended Commercial": "actual_das",
    "DAS Extended Resi": "actual_das",
    "DAS Extended Residential": "actual_das",
    "DAS Remote Comm": "actual_das",
    "DAS Remote Residential": "actual_das",
    "DAS Alaska Comm": "actual_das",
    "DAS Alaska Resi": "actual_das",
    "DAS Hawaii Comm": "actual_das",
    "DAS Hawaii Resi": "actual_das",
    "Delivery Area Surcharge": "actual_das",
    "Delivery Area Surcharge Extended": "actual_das",
    "Delivery Area Surcharge Alaska": "actual_das",
    "Delivery Area Surcharge Hawaii": "actual_das",
    "Delivery Area Surcharge Intra-Hawaii": "actual_das",
    "Out of Delivery Area Tier B": "actual_das",

    # Residential delivery
    "Residential": "actual_residential",
    "Residential Delivery": "actual_residential",

    # Oversize (packages exceeding size limits)
    "Oversize Charge": "actual_oversize",

    # Demand surcharges (peak season)
    "Demand Surcharge": "actual_dem_base",
    "Demand-Add'l Handling": "actual_dem_ahs",
    "Demand-Oversize": "actual_dem_oversize",
    "Demand-Residential Del.": "actual_dem_residential",
    "Demand-Unauthorized": "actual_dem_base",

    # Fuel surcharge
    "Fuel Surcharge": "actual_fuel",

    # Discounts (stored as negative values)
    "Performance Pricing": "actual_performance_pricing",
    "Earned Discount": "actual_earned_discount",
    "Grace Discount": "actual_grace_discount",
    "Discount": "actual_discount",
}

# Default column for unmapped charges (taxes, signatures, address corrections, etc.)
DEFAULT_COLUMN = "actual_unpredictable"

# All actual columns that charges can be mapped to
ACTUAL_COLUMNS = [
    "actual_base",
    "actual_ahs",
    "actual_ahs_weight",
    "actual_das",
    "actual_residential",
    "actual_oversize",
    "actual_dem_base",
    "actual_dem_ahs",
    "actual_dem_oversize",
    "actual_dem_residential",
    "actual_fuel",
    "actual_performance_pricing",
    "actual_earned_discount",
    "actual_grace_discount",
    "actual_discount",
    "actual_unpredictable",
]


def get_column_for_charge(charge_description: str) -> str:
    """Get the actual column name for a charge description."""
    return CHARGE_MAPPING.get(charge_description, DEFAULT_COLUMN)
