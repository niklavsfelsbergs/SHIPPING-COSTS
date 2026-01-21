"""
Tests for USPS Cost Calculator

Run with: pytest carriers/usps/tests/test_calculate_costs.py -v
"""

import pytest
import polars as pl
from datetime import date

# TODO: Import calculator once implemented
# from carriers.usps.calculate_costs import calculate_costs, supplement_shipments, calculate


def make_shipment(
    ship_date: date = date(2025, 6, 15),
    production_site: str = "Phoenix",
    shipping_zip_code: str = "90210",
    shipping_region: str = "California",
    length_in: float = 10.0,
    width_in: float = 8.0,
    height_in: float = 6.0,
    weight_lbs: float = 2.0,
) -> pl.DataFrame:
    """Create a test shipment DataFrame with a single row."""
    return pl.DataFrame({
        "ship_date": [ship_date],
        "production_site": [production_site],
        "shipping_zip_code": [shipping_zip_code],
        "shipping_region": [shipping_region],
        "length_in": [length_in],
        "width_in": [width_in],
        "height_in": [height_in],
        "weight_lbs": [weight_lbs],
    })


class TestSupplementShipments:
    """Tests for supplement_shipments() function."""

    @pytest.mark.skip(reason="Not yet implemented")
    def test_cubic_inches(self):
        """Test cubic inch calculation."""
        df = make_shipment(length_in=10.0, width_in=8.0, height_in=6.0)
        # result = supplement_shipments(df)
        # assert result["cubic_in"][0] == 480.0
        pass

    @pytest.mark.skip(reason="Not yet implemented")
    def test_zone_lookup(self):
        """Test zone lookup from ZIP code."""
        pass


class TestSurchargeFlags:
    """Tests for surcharge flag logic."""

    @pytest.mark.skip(reason="Not yet implemented")
    def test_placeholder(self):
        """Placeholder test - implement surcharge tests."""
        pass


class TestCostCalculations:
    """Tests for cost calculations."""

    @pytest.mark.skip(reason="Not yet implemented")
    def test_base_rate_lookup(self):
        """Test base rate lookup by zone and weight."""
        pass

    @pytest.mark.skip(reason="Not yet implemented")
    def test_total_calculation(self):
        """Test total cost calculation."""
        pass


class TestVersionStamp:
    """Tests for version stamping."""

    @pytest.mark.skip(reason="Not yet implemented")
    def test_version_stamp(self):
        """Test that calculator version is stamped on output."""
        pass
