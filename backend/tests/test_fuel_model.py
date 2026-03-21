"""Tests for services.fuel_model — fuel estimation guards and dataclass."""

from unittest.mock import patch, MagicMock

from services.fuel_model import estimate_for_sv, FuelEstimate, _model_cache


class TestEstimateForSvGuards:
    def test_none_velocity_returns_none(self):
        assert estimate_for_sv("A320", None, 10000.0) is None

    def test_none_altitude_returns_none(self):
        assert estimate_for_sv("A320", 250.0, None) is None

    def test_low_velocity_returns_none(self):
        assert estimate_for_sv("A320", 30.0, 10000.0) is None

    def test_valid_input_calls_model(self):
        mock_model = MagicMock()
        mock_model.enroute_burn.return_value = FuelEstimate(
            fuel_flow_kg_s=1.5, co2_kg_s=4.7, nox_kg_s=0.01
        )
        _model_cache["A320"] = mock_model

        result = estimate_for_sv("A320", 250.0, 10668.0)
        assert result is not None
        assert result.fuel_flow_kg_s == 1.5

        # Verify unit conversions: m/s→knots, m→feet
        call_kwargs = mock_model.enroute_burn.call_args[1]
        assert abs(call_kwargs["tas_kt"] - 250.0 * 1.94384) < 0.01
        assert abs(call_kwargs["alt_ft"] - 10668.0 * 3.28084) < 0.1


class TestFuelEstimate:
    def test_construction(self):
        fe = FuelEstimate(fuel_flow_kg_s=1.5, co2_kg_s=4.7, nox_kg_s=0.01)
        assert fe.fuel_flow_kg_s == 1.5
        assert fe.co2_kg_s == 4.7
        assert fe.nox_kg_s == 0.01
