"""Tests for the freight cost model — rates, breakdowns, diesel sensitivity."""

from services.freight_cost_model import (
    get_rate, get_cost_breakdown, adjust_rate_for_diesel,
    estimate_flow_cost, BASE_RATES, DIESEL_BASELINE_USD_GAL,
)


class TestBaseRates:
    def test_truck_rate(self):
        assert get_rate(1) == 0.12

    def test_rail_rate(self):
        assert get_rate(2) == 0.035

    def test_water_rate(self):
        assert get_rate(3) == 0.015

    def test_air_rate(self):
        assert get_rate(4) == 0.95

    def test_intermodal_rate(self):
        assert get_rate(5) == 0.07

    def test_pipeline_rate(self):
        assert get_rate(6) == 0.02

    def test_unknown_mode_defaults_to_truck(self):
        assert get_rate(99) == 0.12


class TestCostBreakdown:
    def test_breakdown_sums_to_one(self):
        for mode_code, data in BASE_RATES.items():
            total = sum(data["breakdown"].values())
            assert abs(total - 1.0) < 0.01, f"Mode {mode_code} breakdown sums to {total}"

    def test_truck_breakdown_keys(self):
        bd = get_cost_breakdown(1)
        assert set(bd.keys()) == {"fuel", "labor", "equipment", "insurance", "tolls_fees", "other"}

    def test_unknown_mode_defaults(self):
        bd = get_cost_breakdown(99)
        assert bd == get_cost_breakdown(1)


class TestDieselAdjustment:
    def test_at_baseline_no_change(self):
        adj = adjust_rate_for_diesel(1, DIESEL_BASELINE_USD_GAL)
        assert abs(adj - get_rate(1)) < 0.0001

    def test_higher_diesel_increases_rate(self):
        adj = adjust_rate_for_diesel(1, DIESEL_BASELINE_USD_GAL * 1.5)
        assert adj > get_rate(1)

    def test_lower_diesel_decreases_rate(self):
        adj = adjust_rate_for_diesel(1, DIESEL_BASELINE_USD_GAL * 0.5)
        assert adj < get_rate(1)

    def test_truck_more_sensitive_than_rail(self):
        """Truck (38% fuel) should shift more than rail (18% fuel) for same diesel change."""
        diesel_high = DIESEL_BASELINE_USD_GAL * 1.3
        truck_delta = adjust_rate_for_diesel(1, diesel_high) - get_rate(1)
        rail_delta = adjust_rate_for_diesel(2, diesel_high) - get_rate(2)
        # Normalize by base rate to compare sensitivity
        truck_pct = truck_delta / get_rate(1)
        rail_pct = rail_delta / get_rate(2)
        assert truck_pct > rail_pct


class TestEstimateFlowCost:
    def test_basic_cost(self):
        result = estimate_flow_cost(
            tons_thousands=100,
            ton_miles_millions=50,
            mode_code=1,
        )
        # 50M ton-miles * $0.12/tm = $6M
        assert abs(result["total_cost_usd"] - 6_000_000) < 1
        assert result["cost_per_ton_mile"] == 0.12
        assert result["cost_per_ton"] == 6_000_000 / 100_000  # 60

    def test_zero_tons_no_division_error(self):
        result = estimate_flow_cost(
            tons_thousands=0,
            ton_miles_millions=10,
            mode_code=2,
        )
        assert result["cost_per_ton"] == 0

    def test_components_sum_to_total(self):
        result = estimate_flow_cost(
            tons_thousands=50,
            ton_miles_millions=20,
            mode_code=1,
        )
        component_sum = sum(result["components"].values())
        assert abs(component_sum - result["total_cost_usd"]) < 0.01

    def test_diesel_override(self):
        base = estimate_flow_cost(100, 50, 1)
        adj = estimate_flow_cost(100, 50, 1, diesel_usd_gal=6.0)
        assert adj["total_cost_usd"] > base["total_cost_usd"]
