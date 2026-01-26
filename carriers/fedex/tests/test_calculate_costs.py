"""
Tests for FedEx Shipping Cost Calculator

Run with: pytest carriers/fedex/tests/ -v
"""

import polars as pl
import pytest
from datetime import date

from carriers.fedex.calculate_costs import (
    calculate_costs,
    supplement_shipments,
    calculate,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def base_shipment() -> pl.DataFrame:
    """
    Create a base shipment DataFrame for testing.

    Standard small package:
    - 10x8x6 inches, 5 lbs
    - Ships from Phoenix to zone 5
    """
    return pl.DataFrame([{
        "ship_date": date(2025, 6, 15),
        "production_site": "Phoenix",
        "shipping_zip_code": "90210",
        "shipping_region": "California",
        "length_in": 10.0,
        "width_in": 8.0,
        "height_in": 6.0,
        "weight_lbs": 5.0,
        "pcs_shipping_provider": "FXEHD",  # Home Delivery
    }])


@pytest.fixture
def large_shipment() -> pl.DataFrame:
    """
    Create a large shipment DataFrame for testing.

    Large package that may trigger surcharges:
    - 40x30x20 inches, 75 lbs
    """
    return pl.DataFrame([{
        "ship_date": date(2025, 6, 15),
        "production_site": "Phoenix",
        "shipping_zip_code": "90210",
        "shipping_region": "California",
        "length_in": 40.0,
        "width_in": 30.0,
        "height_in": 20.0,
        "weight_lbs": 75.0,
        "pcs_shipping_provider": "FXEHD",  # Home Delivery
    }])


# =============================================================================
# TESTS: SUPPLEMENT SHIPMENTS
# =============================================================================

class TestSupplementShipments:
    """Tests for supplement_shipments function."""

    def test_adds_calculated_dimensions(self, base_shipment):
        """Verify calculated dimensions are added correctly."""
        df = supplement_shipments(base_shipment)

        assert "cubic_in" in df.columns
        assert "longest_side_in" in df.columns
        assert "second_longest_in" in df.columns
        assert "length_plus_girth" in df.columns

        row = df.row(0, named=True)
        assert row["cubic_in"] == 480  # 10 * 8 * 6
        assert row["longest_side_in"] == 10.0
        assert row["second_longest_in"] == 8.0
        # length_plus_girth = 10 + 2*(8+6) = 10 + 28 = 38
        assert row["length_plus_girth"] == 38.0

    def test_adds_billable_weight(self, base_shipment):
        """Verify billable weight calculation."""
        df = supplement_shipments(base_shipment)

        assert "dim_weight_lbs" in df.columns
        assert "uses_dim_weight" in df.columns
        assert "billable_weight_lbs" in df.columns

        row = df.row(0, named=True)
        # dim_weight = 480 / 139 = 3.45 (less than actual 5 lbs)
        assert row["uses_dim_weight"] == False
        assert row["billable_weight_lbs"] == 5.0

    def test_large_package_uses_dim_weight(self, large_shipment):
        """Verify large packages use dimensional weight when greater."""
        df = supplement_shipments(large_shipment)

        row = df.row(0, named=True)
        # cubic_in = 40 * 30 * 20 = 24000
        # dim_weight = 24000 / 139 = 172.66 (greater than actual 75 lbs)
        assert row["uses_dim_weight"] == True
        assert row["billable_weight_lbs"] > row["weight_lbs"]

    def test_adds_shipping_zone(self, base_shipment):
        """Verify shipping zone is added."""
        df = supplement_shipments(base_shipment)

        assert "shipping_zone" in df.columns
        # TODO: Update assertion when zone lookup is implemented


# =============================================================================
# TESTS: CALCULATE
# =============================================================================

class TestCalculate:
    """Tests for calculate function."""

    def test_adds_cost_columns(self, base_shipment):
        """Verify cost columns are added."""
        df = supplement_shipments(base_shipment)
        df = calculate(df)

        assert "cost_base_rate" in df.columns
        assert "cost_subtotal" in df.columns
        assert "cost_fuel" in df.columns
        assert "cost_total" in df.columns
        assert "calculator_version" in df.columns

    def test_cost_total_equals_subtotal_plus_fuel(self, base_shipment):
        """Verify cost_total = cost_subtotal + cost_fuel."""
        df = calculate_costs(base_shipment)

        row = df.row(0, named=True)
        expected_total = row["cost_subtotal"] + row["cost_fuel"]
        assert abs(row["cost_total"] - expected_total) < 0.01


# =============================================================================
# TESTS: FULL PIPELINE
# =============================================================================

class TestCalculateCosts:
    """Tests for full calculate_costs pipeline."""

    def test_full_pipeline_runs(self, base_shipment):
        """Verify full pipeline completes without error."""
        df = calculate_costs(base_shipment)

        # Should have all expected output columns
        assert "shipping_zone" in df.columns
        assert "billable_weight_lbs" in df.columns
        assert "cost_total" in df.columns
        assert "calculator_version" in df.columns

    def test_pipeline_preserves_input_columns(self, base_shipment):
        """Verify input columns are preserved in output."""
        df = calculate_costs(base_shipment)

        # All input columns should still be present
        for col in base_shipment.columns:
            assert col in df.columns


# =============================================================================
# TESTS: DAS SURCHARGE
# =============================================================================

class TestDASSurcharge:
    """Tests for Delivery Area Surcharge."""

    def test_das_triggers_for_das_zip(self):
        """DAS should trigger for ZIPs in DAS zones."""
        df = pl.DataFrame([{
            "ship_date": date(2025, 11, 15),
            "production_site": "Phoenix",
            "shipping_zip_code": "01002",  # DAS zone
            "shipping_region": "Massachusetts",
            "length_in": 10.0,
            "width_in": 8.0,
            "height_in": 6.0,
            "weight_lbs": 5.0,
            "pcs_shipping_provider": "FXEHD",
        }])
        result = calculate_costs(df)

        assert result["das_zone"][0] == "DAS"
        assert result["surcharge_das"][0] == True
        assert result["cost_das"][0] == 2.17  # HD_DAS price

    def test_das_extended_triggers_for_extended_zip(self):
        """DAS_EXTENDED should trigger for ZIPs in extended zones."""
        df = pl.DataFrame([{
            "ship_date": date(2025, 11, 15),
            "production_site": "Phoenix",
            "shipping_zip_code": "01005",  # DAS_EXTENDED zone
            "shipping_region": "Massachusetts",
            "length_in": 10.0,
            "width_in": 8.0,
            "height_in": 6.0,
            "weight_lbs": 5.0,
            "pcs_shipping_provider": "FXEHD",
        }])
        result = calculate_costs(df)

        assert result["das_zone"][0] == "DAS_EXTENDED"
        assert result["surcharge_das"][0] == True
        assert result["cost_das"][0] == 2.91  # HD_DAS_EXTENDED price

    def test_no_das_for_non_das_zip(self):
        """DAS should not trigger for ZIPs not in DAS zones."""
        df = pl.DataFrame([{
            "ship_date": date(2025, 11, 15),
            "production_site": "Phoenix",
            "shipping_zip_code": "90210",  # Not in DAS zones
            "shipping_region": "California",
            "length_in": 10.0,
            "width_in": 8.0,
            "height_in": 6.0,
            "weight_lbs": 5.0,
            "pcs_shipping_provider": "FXEHD",
        }])
        result = calculate_costs(df)

        assert result["das_zone"][0] is None
        assert result["surcharge_das"][0] == False
        assert result["cost_das"][0] == 0.0

    def test_das_smartpost_different_price(self):
        """SmartPost should have different DAS prices than Home Delivery."""
        df = pl.DataFrame([{
            "ship_date": date(2025, 11, 15),
            "production_site": "Phoenix",
            "shipping_zip_code": "01005",  # DAS_EXTENDED zone
            "shipping_region": "Massachusetts",
            "length_in": 10.0,
            "width_in": 8.0,
            "height_in": 6.0,
            "weight_lbs": 5.0,
            "pcs_shipping_provider": "FXESPPS",  # SmartPost
        }])
        result = calculate_costs(df)

        assert result["das_zone"][0] == "DAS_EXTENDED"
        assert result["surcharge_das"][0] == True
        assert result["cost_das"][0] == 4.15  # SP_DAS_EXTENDED price


# =============================================================================
# PLACEHOLDER TESTS FOR OTHER SURCHARGES
# =============================================================================

# TODO: Add surcharge tests as surcharges are implemented
# Example structure:

# class TestAHSSurcharge:
#     """Tests for Additional Handling Surcharge."""
#
#     def test_ahs_triggers_for_heavy_package(self):
#         """AHS should trigger for packages over weight threshold."""
#         pass
#
#     def test_ahs_triggers_for_long_package(self):
#         """AHS should trigger for packages over length threshold."""
#         pass
