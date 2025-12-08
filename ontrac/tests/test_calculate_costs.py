"""
Unit Tests for OnTrac Cost Calculator

Tests surcharge logic, cost calculations, and edge cases.
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import polars as pl
from datetime import date

from ontrac.calculate_costs import calculate_costs, supplement_shipments, calculate
from ontrac.surcharges import OML, LPS, AHS, DAS, EDAS, RES, DEM_RES, DEM_AHS


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def base_shipment():
    """Base shipment with no surcharges triggered."""
    return pl.DataFrame({
        "pcs_ordernumber": ["TEST"],
        "pcs_orderid": [1],
        "trackingnumber": ["TRK001"],
        "ship_date": [date(2025, 6, 15)],  # Outside demand period
        "shop_ordernumber": ["SHOP001"],
        "production_site": ["Phoenix"],
        "shipping_zip_code": ["75132"],  # Texas, NO DAS
        "shipping_region": ["Texas"],
        "shipping_country": ["United States"],
        "length_in": [10.0],
        "width_in": [8.0],
        "height_in": [6.0],
        "weight_lbs": [5.0],
    })


def run_pipeline(df: pl.DataFrame) -> pl.DataFrame:
    """Helper to run full pipeline."""
    df = supplement_shipments(df)
    df = calculate(df)
    return df


# =============================================================================
# SUPPLEMENT TESTS
# =============================================================================

class TestSupplementShipments:
    """Tests for supplement_shipments calculations."""

    def test_cubic_inches(self, base_shipment):
        """Cubic inches = length * width * height."""
        df = supplement_shipments(base_shipment)
        expected = 10.0 * 8.0 * 6.0  # 480
        assert df["cubic_in"][0] == pytest.approx(expected)

    def test_longest_side(self, base_shipment):
        """Longest side is max of dimensions."""
        df = supplement_shipments(base_shipment)
        assert df["longest_side_in"][0] == pytest.approx(10.0)

    def test_second_longest(self, base_shipment):
        """Second longest is middle dimension."""
        df = supplement_shipments(base_shipment)
        assert df["second_longest_in"][0] == pytest.approx(8.0)

    def test_length_plus_girth(self, base_shipment):
        """Length plus girth = longest + 2*(sum of other two)."""
        df = supplement_shipments(base_shipment)
        # longest=10, other two = 8+6=14, girth = 2*14=28, total = 10+28=38
        expected = 10.0 + 2 * (8.0 + 6.0)
        assert df["length_plus_girth"][0] == pytest.approx(expected)

    def test_zone_lookup_phoenix(self, base_shipment):
        """Phoenix shipment to Texas (75132) should get zone 4."""
        df = supplement_shipments(base_shipment)
        assert df["shipping_zone"][0] == 4

    def test_zone_lookup_columbus(self, base_shipment):
        """Columbus shipment to Delaware (19711) should get zone 4."""
        shipment = base_shipment.with_columns([
            pl.lit("Columbus").alias("production_site"),
            pl.lit("19711").alias("shipping_zip_code"),
            pl.lit("Delaware").alias("shipping_region"),
        ])
        df = supplement_shipments(shipment)
        assert df["shipping_zone"][0] == 4

    def test_das_zone_no(self, base_shipment):
        """75132 Texas should have NO DAS."""
        df = supplement_shipments(base_shipment)
        assert df["das_zone"][0] == "NO"

    def test_das_zone_edas(self, base_shipment):
        """95613 California should have EDAS."""
        shipment = base_shipment.with_columns([
            pl.lit("95613").alias("shipping_zip_code"),
            pl.lit("California").alias("shipping_region"),
        ])
        df = supplement_shipments(shipment)
        assert df["das_zone"][0] == "EDAS"

    def test_das_zone_das(self, base_shipment):
        """17202 Pennsylvania should have DAS."""
        shipment = base_shipment.with_columns([
            pl.lit("17202").alias("shipping_zip_code"),
            pl.lit("Pennsylvania").alias("shipping_region"),
        ])
        df = supplement_shipments(shipment)
        assert df["das_zone"][0] == "DAS"


# =============================================================================
# SURCHARGE FLAG TESTS
# =============================================================================

class TestSurchargeFlags:
    """Tests for surcharge flag logic."""

    def test_no_dimensional_surcharge(self, base_shipment):
        """Small package should have no dimensional surcharges."""
        df = run_pipeline(base_shipment)
        assert df["surcharge_oml"][0] == False
        assert df["surcharge_lps"][0] == False
        assert df["surcharge_ahs"][0] == False

    def test_ahs_weight_trigger(self, base_shipment):
        """Weight > 50 lbs should trigger AHS."""
        shipment = base_shipment.with_columns(pl.lit(55.0).alias("weight_lbs"))
        df = run_pipeline(shipment)
        assert df["surcharge_ahs"][0] == True
        assert df["surcharge_lps"][0] == False
        assert df["surcharge_oml"][0] == False

    def test_ahs_longest_trigger(self, base_shipment):
        """Longest side > 48" should trigger AHS."""
        shipment = base_shipment.with_columns(pl.lit(50.0).alias("length_in"))
        df = run_pipeline(shipment)
        assert df["surcharge_ahs"][0] == True

    def test_ahs_second_longest_trigger(self, base_shipment):
        """Second longest > 30" should trigger AHS."""
        shipment = base_shipment.with_columns([
            pl.lit(40.0).alias("length_in"),
            pl.lit(32.0).alias("width_in"),
        ])
        df = run_pipeline(shipment)
        assert df["surcharge_ahs"][0] == True

    def test_lps_longest_trigger(self, base_shipment):
        """Longest side > 72" should trigger LPS (not AHS)."""
        shipment = base_shipment.with_columns(pl.lit(75.0).alias("length_in"))
        df = run_pipeline(shipment)
        assert df["surcharge_lps"][0] == True
        assert df["surcharge_ahs"][0] == False  # LPS takes priority

    def test_oml_longest_trigger(self, base_shipment):
        """Longest side > 108" should trigger OML."""
        shipment = base_shipment.with_columns(pl.lit(110.0).alias("length_in"))
        df = run_pipeline(shipment)
        assert df["surcharge_oml"][0] == True

    def test_res_always_applies(self, base_shipment):
        """RES should always apply (allocated)."""
        df = run_pipeline(base_shipment)
        assert df["surcharge_res"][0] == True

    def test_edas_applies(self, base_shipment):
        """EDAS zone should trigger EDAS surcharge."""
        shipment = base_shipment.with_columns([
            pl.lit("95613").alias("shipping_zip_code"),
            pl.lit("California").alias("shipping_region"),
        ])
        df = run_pipeline(shipment)
        assert df["surcharge_edas"][0] == True
        assert df["surcharge_das"][0] == False

    def test_das_applies(self, base_shipment):
        """DAS zone should trigger DAS surcharge."""
        shipment = base_shipment.with_columns([
            pl.lit("17202").alias("shipping_zip_code"),
            pl.lit("Pennsylvania").alias("shipping_region"),
        ])
        df = run_pipeline(shipment)
        assert df["surcharge_das"][0] == True
        assert df["surcharge_edas"][0] == False


# =============================================================================
# DEMAND PERIOD TESTS
# =============================================================================

class TestDemandPeriod:
    """Tests for demand period surcharges."""

    def test_dem_res_outside_period(self, base_shipment):
        """DEM_RES should not apply outside demand period (June)."""
        df = run_pipeline(base_shipment)  # June 15
        assert df["surcharge_dem_res"][0] == False

    def test_dem_res_in_period(self, base_shipment):
        """DEM_RES should apply during demand period (Nov 15)."""
        shipment = base_shipment.with_columns(
            pl.lit(date(2025, 11, 15)).alias("ship_date")
        )
        df = run_pipeline(shipment)
        assert df["surcharge_dem_res"][0] == True

    def test_dem_ahs_outside_period(self, base_shipment):
        """DEM_AHS should not apply outside demand period."""
        shipment = base_shipment.with_columns(pl.lit(55.0).alias("weight_lbs"))
        df = run_pipeline(shipment)  # June 15
        assert df["surcharge_ahs"][0] == True
        assert df["surcharge_dem_ahs"][0] == False

    def test_dem_ahs_in_period(self, base_shipment):
        """DEM_AHS should apply when AHS + in demand period."""
        shipment = base_shipment.with_columns([
            pl.lit(55.0).alias("weight_lbs"),
            pl.lit(date(2025, 11, 15)).alias("ship_date"),
        ])
        df = run_pipeline(shipment)
        assert df["surcharge_ahs"][0] == True
        assert df["surcharge_dem_ahs"][0] == True


# =============================================================================
# BILLABLE WEIGHT TESTS
# =============================================================================

class TestBillableWeight:
    """Tests for billable weight adjustments."""

    def test_no_adjustment_small_package(self, base_shipment):
        """Small package should have no billable weight adjustment."""
        df = run_pipeline(base_shipment)
        assert df["billable_weight_lbs"][0] == pytest.approx(5.0)

    def test_ahs_min_billable_weight(self, base_shipment):
        """AHS should enforce 30 lb minimum billable weight."""
        # Trigger AHS with dimensions but low weight
        shipment = base_shipment.with_columns([
            pl.lit(50.0).alias("length_in"),  # Triggers AHS (longest > 48)
            pl.lit(10.0).alias("weight_lbs"),
        ])
        df = run_pipeline(shipment)
        assert df["surcharge_ahs"][0] == True
        assert df["billable_weight_lbs"][0] == pytest.approx(30.0)  # Min 30

    def test_lps_min_billable_weight(self, base_shipment):
        """LPS should enforce 90 lb minimum billable weight."""
        shipment = base_shipment.with_columns([
            pl.lit(75.0).alias("length_in"),  # Triggers LPS (longest > 72)
            pl.lit(20.0).alias("weight_lbs"),
        ])
        df = run_pipeline(shipment)
        assert df["surcharge_lps"][0] == True
        assert df["billable_weight_lbs"][0] == pytest.approx(90.0)  # Min 90

    def test_oml_min_billable_weight(self, base_shipment):
        """OML should enforce 150 lb minimum billable weight."""
        shipment = base_shipment.with_columns([
            pl.lit(110.0).alias("length_in"),  # Triggers OML (longest > 108)
            pl.lit(50.0).alias("weight_lbs"),
        ])
        df = run_pipeline(shipment)
        assert df["surcharge_oml"][0] == True
        assert df["billable_weight_lbs"][0] == pytest.approx(150.0)  # Min 150


# =============================================================================
# COST CALCULATION TESTS
# =============================================================================

class TestCostCalculations:
    """Tests for cost calculations."""

    def test_res_cost(self, base_shipment):
        """RES cost should be list_price * (1 - discount) * allocation_rate."""
        df = run_pipeline(base_shipment)
        expected = RES.cost()  # 6.10 * 0.10 * 0.95 = 0.5795
        assert df["cost_res"][0] == pytest.approx(expected)

    def test_ahs_cost(self, base_shipment):
        """AHS cost should be list_price * (1 - discount)."""
        shipment = base_shipment.with_columns(pl.lit(55.0).alias("weight_lbs"))
        df = run_pipeline(shipment)
        expected = AHS.cost()  # 32.00 * 0.30 = 9.60
        assert df["cost_ahs"][0] == pytest.approx(expected)

    def test_no_surcharge_zero_cost(self, base_shipment):
        """Non-triggered surcharges should have zero cost."""
        df = run_pipeline(base_shipment)
        assert df["cost_oml"][0] == pytest.approx(0.0)
        assert df["cost_lps"][0] == pytest.approx(0.0)
        assert df["cost_ahs"][0] == pytest.approx(0.0)

    def test_subtotal_calculation(self, base_shipment):
        """Subtotal should be sum of base + all surcharge costs."""
        df = run_pipeline(base_shipment)
        cost_base = df["cost_base"][0]
        cost_res = df["cost_res"][0]
        # All other surcharges should be 0 for base shipment
        expected_subtotal = cost_base + cost_res
        assert df["cost_subtotal"][0] == pytest.approx(expected_subtotal, rel=0.01)

    def test_fuel_calculation(self, base_shipment):
        """Fuel should be subtotal * FUEL_RATE."""
        from ontrac.data.fuel import RATE as FUEL_RATE
        df = run_pipeline(base_shipment)
        expected_fuel = df["cost_subtotal"][0] * FUEL_RATE
        assert df["cost_fuel"][0] == pytest.approx(expected_fuel)

    def test_total_calculation(self, base_shipment):
        """Total should be subtotal + fuel."""
        df = run_pipeline(base_shipment)
        expected_total = df["cost_subtotal"][0] + df["cost_fuel"][0]
        assert df["cost_total"][0] == pytest.approx(expected_total)


# =============================================================================
# VERSION STAMP TEST
# =============================================================================

class TestVersionStamp:
    """Tests for version stamping."""

    def test_version_stamp(self, base_shipment):
        """Output should have calculator_version column."""
        from ontrac.version import VERSION
        df = run_pipeline(base_shipment)
        assert df["calculator_version"][0] == VERSION


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
