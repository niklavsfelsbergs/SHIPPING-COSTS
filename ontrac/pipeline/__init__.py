"""
Pipeline Package

Core calculation logic (source-agnostic):
- inputs: Load reference data (rates, zones, fuel, dim config)
- supplement: Enrich shipments with zones and billable weight
- calculate: Apply surcharges and calculate costs
"""

from .inputs import load_rates, load_zones, FUEL_RATE
from .supplement import supplement_shipments
from .calculate import calculate
