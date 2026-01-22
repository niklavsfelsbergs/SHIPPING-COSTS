"""
Unit Tests for USPS Cost Calculator

Tests surcharge logic, cost calculations, and edge cases.

Run with: pytest carriers/usps/tests/test_calculate_costs.py -v
"""

import pytest
import polars as pl
from datetime import date

from carriers.usps.calculate_costs import calculate_costs, supplement_shipments, calculate
from carriers.usps.surcharges import NSL1, NSL2, NSV, PEAK_RATES


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def base_shipment():
    """Base shipment with no surcharges triggered."""
    return pl.DataFrame({
        "ship_date": [date(2025, 6, 15)],
        "production_site": ["Phoenix"],
        "shipping_zip_code": ["90210"],  # California, zone 4 from Phoenix
        "shipping_region": ["California"],
        "length_in": [10.0],
        "width_in": [8.0],
        "height_in": [6.0],
        "weight_lbs": [2.0],
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
        """Phoenix shipment to California 90210 should get zone 4."""
        df = supplement_shipments(base_shipment)
        # 902 prefix from Phoenix should be zone 4
        assert df["rate_zone"][0] == 4

    def test_zone_lookup_columbus(self, base_shipment):
        """Columbus shipment to California 90210 should get zone 8."""
        shipment = base_shipment.with_columns([
            pl.lit("Columbus").alias("production_site"),
        ])
        df = supplement_shipments(shipment)
        # 902 prefix from Columbus should be zone 8
        assert df["rate_zone"][0] == 8

    def test_zone_with_asterisk(self, base_shipment):
        """ZIP prefix with asterisk zone should preserve in shipping_zone but strip for rate_zone."""
        # ZIP 85006 (prefix 850) from Phoenix should have zone 1*
        shipment = base_shipment.with_columns([
            pl.lit("85006").alias("shipping_zip_code"),
            pl.lit("Arizona").alias("shipping_region"),
        ])
        df = supplement_shipments(shipment)
        assert df["shipping_zone"][0] == "1*"
        assert df["rate_zone"][0] == 1


# =============================================================================
# BILLABLE WEIGHT TESTS
# =============================================================================

class TestBillableWeight:
    """Tests for billable weight calculations."""

    def test_actual_weight_used_small_package(self, base_shipment):
        """Small package uses actual weight (< DIM threshold)."""
        df = supplement_shipments(base_shipment)
        assert df["uses_dim_weight"][0] == False
        assert df["billable_weight_lbs"][0] == pytest.approx(2.0)

    def test_dim_weight_used_large_volume(self, base_shipment):
        """Large volume package uses DIM weight when > actual."""
        # Make a large box: 20x20x10 = 4000 cubic inches
        # DIM weight = 4000 / 200 = 20 lbs
        shipment = base_shipment.with_columns([
            pl.lit(20.0).alias("length_in"),
            pl.lit(20.0).alias("width_in"),
            pl.lit(10.0).alias("height_in"),
            pl.lit(5.0).alias("weight_lbs"),  # Actual weight 5 lbs
        ])
        df = supplement_shipments(shipment)
        assert df["uses_dim_weight"][0] == True
        assert df["dim_weight_lbs"][0] == pytest.approx(20.0)
        assert df["billable_weight_lbs"][0] == pytest.approx(20.0)

    def test_actual_weight_used_when_heavier(self, base_shipment):
        """Actual weight used when heavier than DIM weight."""
        # Large box but heavy: 20x20x10 = 4000 cubic inches
        # DIM weight = 20 lbs, actual = 25 lbs
        shipment = base_shipment.with_columns([
            pl.lit(20.0).alias("length_in"),
            pl.lit(20.0).alias("width_in"),
            pl.lit(10.0).alias("height_in"),
            pl.lit(25.0).alias("weight_lbs"),  # Heavier than DIM
        ])
        df = supplement_shipments(shipment)
        # Still uses_dim_weight=False because actual > dim
        assert df["uses_dim_weight"][0] == False
        assert df["billable_weight_lbs"][0] == pytest.approx(25.0)


# =============================================================================
# SURCHARGE FLAG TESTS
# =============================================================================

class TestSurchargeFlags:
    """Tests for surcharge flag logic."""

    def test_no_surcharges_small_package(self, base_shipment):
        """Small package should have no surcharges."""
        df = run_pipeline(base_shipment)
        assert df["surcharge_nsl1"][0] == False
        assert df["surcharge_nsl2"][0] == False
        assert df["surcharge_nsv"][0] == False

    def test_nsl1_triggers_22_to_30(self, base_shipment):
        """NSL1 triggers when longest side > 22" and <= 30"."""
        shipment = base_shipment.with_columns(pl.lit(25.0).alias("length_in"))
        df = run_pipeline(shipment)
        assert df["surcharge_nsl1"][0] == True
        assert df["surcharge_nsl2"][0] == False

    def test_nsl1_at_boundary_22(self, base_shipment):
        """NSL1 does NOT trigger at exactly 22"."""
        shipment = base_shipment.with_columns(pl.lit(22.0).alias("length_in"))
        df = run_pipeline(shipment)
        assert df["surcharge_nsl1"][0] == False

    def test_nsl1_at_boundary_30(self, base_shipment):
        """NSL1 triggers at exactly 30"."""
        shipment = base_shipment.with_columns(pl.lit(30.0).alias("length_in"))
        df = run_pipeline(shipment)
        assert df["surcharge_nsl1"][0] == True
        assert df["surcharge_nsl2"][0] == False

    def test_nsl2_triggers_over_30(self, base_shipment):
        """NSL2 triggers when longest side > 30" (wins over NSL1)."""
        shipment = base_shipment.with_columns(pl.lit(35.0).alias("length_in"))
        df = run_pipeline(shipment)
        assert df["surcharge_nsl2"][0] == True
        assert df["surcharge_nsl1"][0] == False  # NSL2 takes priority

    def test_nsv_triggers_over_2_cubic_feet(self, base_shipment):
        """NSV triggers when volume > 3456 cubic inches (2 cu ft)."""
        # 20x20x10 = 4000 cubic inches > 3456
        shipment = base_shipment.with_columns([
            pl.lit(20.0).alias("length_in"),
            pl.lit(20.0).alias("width_in"),
            pl.lit(10.0).alias("height_in"),
        ])
        df = run_pipeline(shipment)
        assert df["surcharge_nsv"][0] == True

    def test_nsv_does_not_trigger_at_boundary(self, base_shipment):
        """NSV does NOT trigger at exactly 3456 cubic inches."""
        # 12x12x24 = 3456 cubic inches exactly
        shipment = base_shipment.with_columns([
            pl.lit(12.0).alias("length_in"),
            pl.lit(12.0).alias("width_in"),
            pl.lit(24.0).alias("height_in"),
        ])
        df = run_pipeline(shipment)
        assert df["surcharge_nsv"][0] == False

    def test_nsl2_and_nsv_can_stack(self, base_shipment):
        """NSL2 and NSV can both apply (different exclusivity groups)."""
        # Long AND high volume: 35x12x10 = 4200 cu in (DIM weight = 21 lbs, so use 20 lbs actual)
        # Actually need to keep DIM weight <= 20 lbs: 35x11x10 = 3850 cu in, DIM = 19.25 lbs
        shipment = base_shipment.with_columns([
            pl.lit(35.0).alias("length_in"),
            pl.lit(11.0).alias("width_in"),
            pl.lit(10.0).alias("height_in"),
            pl.lit(19.0).alias("weight_lbs"),  # Use actual weight
        ])
        df = run_pipeline(shipment)
        assert df["surcharge_nsl2"][0] == True
        assert df["surcharge_nsv"][0] == True


# =============================================================================
# COST CALCULATION TESTS
# =============================================================================

class TestCostCalculations:
    """Tests for cost calculations."""

    def test_base_rate_lookup_zone_4_2lbs(self, base_shipment):
        """Base rate for zone 4, 2 lbs should be $6.13."""
        df = run_pipeline(base_shipment)
        # From rate card: zone 4, 1-2 lb bracket = $6.13
        assert df["cost_base"][0] == pytest.approx(6.13)

    def test_base_rate_lookup_zone_8_5lbs(self, base_shipment):
        """Base rate for zone 8, 5 lbs should be $13.27."""
        shipment = base_shipment.with_columns([
            pl.lit("Columbus").alias("production_site"),  # Zone 8 from Columbus to CA
            pl.lit(5.0).alias("weight_lbs"),
        ])
        df = run_pipeline(shipment)
        # From rate card: zone 8, 4-5 lb bracket = $13.27
        assert df["cost_base"][0] == pytest.approx(13.27)

    def test_nsl1_cost(self, base_shipment):
        """NSL1 cost should be $3.00."""
        shipment = base_shipment.with_columns(pl.lit(25.0).alias("length_in"))
        df = run_pipeline(shipment)
        assert df["cost_nsl1"][0] == pytest.approx(3.00)

    def test_nsl2_cost(self, base_shipment):
        """NSL2 cost should be $3.00."""
        shipment = base_shipment.with_columns(pl.lit(35.0).alias("length_in"))
        df = run_pipeline(shipment)
        assert df["cost_nsl2"][0] == pytest.approx(3.00)

    def test_nsv_cost(self, base_shipment):
        """NSV cost should be $10.00."""
        shipment = base_shipment.with_columns([
            pl.lit(20.0).alias("length_in"),
            pl.lit(20.0).alias("width_in"),
            pl.lit(10.0).alias("height_in"),
        ])
        df = run_pipeline(shipment)
        assert df["cost_nsv"][0] == pytest.approx(10.00)

    def test_no_surcharge_zero_cost(self, base_shipment):
        """Non-triggered surcharges should have zero cost."""
        df = run_pipeline(base_shipment)
        assert df["cost_nsl1"][0] == pytest.approx(0.0)
        assert df["cost_nsl2"][0] == pytest.approx(0.0)
        assert df["cost_nsv"][0] == pytest.approx(0.0)

    def test_subtotal_calculation(self, base_shipment):
        """Subtotal should be sum of base + all surcharge costs."""
        df = run_pipeline(base_shipment)
        expected = df["cost_base"][0]  # No surcharges for base shipment
        assert df["cost_subtotal"][0] == pytest.approx(expected)

    def test_total_equals_subtotal_no_fuel(self, base_shipment):
        """Total should equal subtotal (USPS has no fuel surcharge)."""
        df = run_pipeline(base_shipment)
        assert df["cost_total"][0] == pytest.approx(df["cost_subtotal"][0])

    def test_total_with_surcharges(self, base_shipment):
        """Total should be base + NSL2 + NSV for long high-volume package."""
        # 35x11x10 = 3850 cu in triggers NSL2 ($3) and NSV ($10)
        # DIM weight = 3850/200 = 19.25 lbs, use 19 lbs actual
        shipment = base_shipment.with_columns([
            pl.lit(35.0).alias("length_in"),
            pl.lit(11.0).alias("width_in"),
            pl.lit(10.0).alias("height_in"),
            pl.lit(19.0).alias("weight_lbs"),
        ])
        df = run_pipeline(shipment)
        expected = df["cost_base"][0] + 3.00 + 10.00  # NSL2 + NSV
        assert df["cost_total"][0] == pytest.approx(expected)

    def test_total_with_nsl2_only(self, base_shipment):
        """Total should be base + NSL2 for long package."""
        # 35x8x6 triggers NSL2 but not NSV (1680 cu in < 3456)
        shipment = base_shipment.with_columns([
            pl.lit(35.0).alias("length_in"),
        ])
        df = run_pipeline(shipment)
        expected = df["cost_base"][0] + 3.00  # NSL2 cost
        assert df["cost_total"][0] == pytest.approx(expected)


# =============================================================================
# WEIGHT BRACKET EDGE CASES
# =============================================================================

class TestWeightBrackets:
    """Tests for weight bracket edge cases."""

    def test_4oz_bracket(self, base_shipment):
        """0.2 lbs should use 4oz bracket."""
        shipment = base_shipment.with_columns(pl.lit(0.2).alias("weight_lbs"))
        df = run_pipeline(shipment)
        # Zone 4, 0-0.25 lb bracket = $3.41
        assert df["cost_base"][0] == pytest.approx(3.41)

    def test_8oz_bracket(self, base_shipment):
        """0.4 lbs should use 8oz bracket."""
        shipment = base_shipment.with_columns(pl.lit(0.4).alias("weight_lbs"))
        df = run_pipeline(shipment)
        # Zone 4, 0.25-0.5 lb bracket = $3.41
        assert df["cost_base"][0] == pytest.approx(3.41)

    def test_12oz_bracket(self, base_shipment):
        """0.6 lbs should use 12oz bracket."""
        shipment = base_shipment.with_columns(pl.lit(0.6).alias("weight_lbs"))
        df = run_pipeline(shipment)
        # Zone 4, 0.5-0.75 lb bracket = $3.77
        assert df["cost_base"][0] == pytest.approx(3.77)

    def test_1lb_bracket(self, base_shipment):
        """0.9 lbs should use 1lb bracket."""
        shipment = base_shipment.with_columns(pl.lit(0.9).alias("weight_lbs"))
        df = run_pipeline(shipment)
        # Zone 4, 0.75-1 lb bracket = $4.43
        assert df["cost_base"][0] == pytest.approx(4.43)

    def test_20lb_max(self, base_shipment):
        """20 lbs should use 20lb bracket."""
        shipment = base_shipment.with_columns(pl.lit(20.0).alias("weight_lbs"))
        df = run_pipeline(shipment)
        # Zone 4, 19-20 lb bracket = $11.63
        assert df["cost_base"][0] == pytest.approx(11.63)

    def test_over_20lb_fails(self, base_shipment):
        """Weight over 20 lbs should fail (no matching bracket)."""
        shipment = base_shipment.with_columns(pl.lit(21.0).alias("weight_lbs"))
        with pytest.raises(ValueError, match="no matching rate bracket"):
            run_pipeline(shipment)


# =============================================================================
# PEAK SURCHARGE TESTS
# =============================================================================

class TestPeakSurcharge:
    """Tests for peak season surcharge."""

    def test_no_peak_surcharge_outside_season(self, base_shipment):
        """Peak surcharge should NOT apply outside peak season (June)."""
        # base_shipment uses date(2025, 6, 15) which is outside peak
        df = run_pipeline(base_shipment)
        assert df["surcharge_peak"][0] == False
        assert df["cost_peak"][0] == pytest.approx(0.0)

    def test_peak_surcharge_applies_in_season(self, base_shipment):
        """Peak surcharge should apply during peak season (Nov)."""
        shipment = base_shipment.with_columns(
            pl.lit(date(2025, 11, 15)).alias("ship_date")
        )
        df = run_pipeline(shipment)
        assert df["surcharge_peak"][0] == True
        assert df["cost_peak"][0] > 0

    def test_peak_surcharge_light_zone_1_4(self, base_shipment):
        """Peak surcharge for 0-3 lbs, zones 1-4 should be $0.30."""
        # 2 lbs, zone 4 (Phoenix to 90210)
        shipment = base_shipment.with_columns(
            pl.lit(date(2025, 11, 15)).alias("ship_date")
        )
        df = run_pipeline(shipment)
        assert df["cost_peak"][0] == pytest.approx(PEAK_RATES[(3, 4)])  # $0.30

    def test_peak_surcharge_light_zone_5_9(self, base_shipment):
        """Peak surcharge for 0-3 lbs, zones 5-9 should be $0.35."""
        # 2 lbs, zone 8 (Columbus to 90210)
        shipment = base_shipment.with_columns([
            pl.lit(date(2025, 11, 15)).alias("ship_date"),
            pl.lit("Columbus").alias("production_site"),
        ])
        df = run_pipeline(shipment)
        assert df["cost_peak"][0] == pytest.approx(PEAK_RATES[(3, 9)])  # $0.35

    def test_peak_surcharge_medium_zone_1_4(self, base_shipment):
        """Peak surcharge for 4-10 lbs, zones 1-4 should be $0.45."""
        # 5 lbs, zone 4 (Phoenix to 90210)
        shipment = base_shipment.with_columns([
            pl.lit(date(2025, 11, 15)).alias("ship_date"),
            pl.lit(5.0).alias("weight_lbs"),
        ])
        df = run_pipeline(shipment)
        assert df["cost_peak"][0] == pytest.approx(PEAK_RATES[(10, 4)])  # $0.45

    def test_peak_surcharge_medium_zone_5_9(self, base_shipment):
        """Peak surcharge for 4-10 lbs, zones 5-9 should be $0.75."""
        # 5 lbs, zone 8 (Columbus to 90210)
        shipment = base_shipment.with_columns([
            pl.lit(date(2025, 11, 15)).alias("ship_date"),
            pl.lit("Columbus").alias("production_site"),
            pl.lit(5.0).alias("weight_lbs"),
        ])
        df = run_pipeline(shipment)
        assert df["cost_peak"][0] == pytest.approx(PEAK_RATES[(10, 9)])  # $0.75

    def test_peak_surcharge_heavy_zone_1_4(self, base_shipment):
        """Peak surcharge for 11-25 lbs, zones 1-4 should be $0.75."""
        # 15 lbs, zone 4 (Phoenix to 90210)
        shipment = base_shipment.with_columns([
            pl.lit(date(2025, 11, 15)).alias("ship_date"),
            pl.lit(15.0).alias("weight_lbs"),
        ])
        df = run_pipeline(shipment)
        assert df["cost_peak"][0] == pytest.approx(PEAK_RATES[(25, 4)])  # $0.75

    def test_peak_surcharge_heavy_zone_5_9(self, base_shipment):
        """Peak surcharge for 11-25 lbs, zones 5-9 should be $1.25."""
        # 15 lbs, zone 8 (Columbus to 90210)
        shipment = base_shipment.with_columns([
            pl.lit(date(2025, 11, 15)).alias("ship_date"),
            pl.lit("Columbus").alias("production_site"),
            pl.lit(15.0).alias("weight_lbs"),
        ])
        df = run_pipeline(shipment)
        assert df["cost_peak"][0] == pytest.approx(PEAK_RATES[(25, 9)])  # $1.25

    def test_peak_surcharge_included_in_total(self, base_shipment):
        """Peak surcharge should be included in cost_total."""
        shipment = base_shipment.with_columns(
            pl.lit(date(2025, 11, 15)).alias("ship_date")
        )
        df = run_pipeline(shipment)
        expected = df["cost_base"][0] + df["cost_peak"][0]
        assert df["cost_total"][0] == pytest.approx(expected)

    def test_peak_start_date_inclusive(self, base_shipment):
        """Peak surcharge should apply on start date (Oct 5, 2025)."""
        shipment = base_shipment.with_columns(
            pl.lit(date(2025, 10, 5)).alias("ship_date")
        )
        df = run_pipeline(shipment)
        assert df["surcharge_peak"][0] == True

    def test_peak_end_date_inclusive(self, base_shipment):
        """Peak surcharge should apply on end date (Jan 18, 2026)."""
        shipment = base_shipment.with_columns(
            pl.lit(date(2026, 1, 18)).alias("ship_date")
        )
        df = run_pipeline(shipment)
        assert df["surcharge_peak"][0] == True

    def test_day_before_peak_no_surcharge(self, base_shipment):
        """Peak surcharge should NOT apply day before peak (Oct 4, 2025)."""
        shipment = base_shipment.with_columns(
            pl.lit(date(2025, 10, 4)).alias("ship_date")
        )
        df = run_pipeline(shipment)
        assert df["surcharge_peak"][0] == False

    def test_day_after_peak_no_surcharge(self, base_shipment):
        """Peak surcharge should NOT apply day after peak (Jan 19, 2026)."""
        shipment = base_shipment.with_columns(
            pl.lit(date(2026, 1, 19)).alias("ship_date")
        )
        df = run_pipeline(shipment)
        assert df["surcharge_peak"][0] == False


# =============================================================================
# VERSION STAMP TEST
# =============================================================================

class TestVersionStamp:
    """Tests for version stamping."""

    def test_version_stamp(self, base_shipment):
        """Output should have calculator_version column."""
        from carriers.usps.version import VERSION
        df = run_pipeline(base_shipment)
        assert df["calculator_version"][0] == VERSION


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
