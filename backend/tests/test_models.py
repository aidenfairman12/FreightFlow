"""Tests for Pydantic models — construction, defaults, serialization."""

from datetime import datetime, date
from uuid import uuid4

from models.state_vector import StateVector
from models.kpi import OperationalKPI, KPISummary
from models.economics import EconomicFactor, EconomicSnapshot
from models.scenario import ScenarioCreate, Scenario
from models.prediction import Prediction, FeatureImportance, ModelInfo


class TestStateVector:
    def _make_sv(self, **overrides):
        defaults = dict(
            icao24="abc123", callsign=None, origin_country=None,
            latitude=None, longitude=None, baro_altitude=None,
            on_ground=False, velocity=None, heading=None,
            vertical_rate=None, geo_altitude=None, squawk=None,
            last_contact=datetime(2024, 1, 1),
        )
        defaults.update(overrides)
        return StateVector(**defaults)

    def test_required_fields(self):
        sv = self._make_sv(icao24="abc123", on_ground=False)
        assert sv.icao24 == "abc123"
        assert sv.on_ground is False

    def test_enrichment_defaults_are_none(self):
        sv = self._make_sv()
        assert sv.aircraft_type is None
        assert sv.fuel_flow_kg_s is None
        assert sv.co2_kg_s is None

    def test_model_dump_json(self):
        sv = self._make_sv(last_contact=datetime(2024, 1, 1, 12, 0, 0))
        d = sv.model_dump(mode="json")
        assert d["icao24"] == "abc123"
        assert isinstance(d["last_contact"], str)


class TestOperationalKPI:
    def test_construction(self):
        kpi = OperationalKPI(
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 1, 7),
            period_type="weekly",
        )
        assert kpi.airline_code == "SWR"
        assert kpi.period_type == "weekly"

    def test_all_metrics_optional(self):
        kpi = OperationalKPI(
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 1, 7),
            period_type="weekly",
        )
        assert kpi.total_ask is None
        assert kpi.total_departures is None
        assert kpi.avg_turnaround_min is None


class TestEconomics:
    def test_economic_factor_construction(self):
        ef = EconomicFactor(
            date=date(2024, 3, 1),
            factor_name="jet_fuel",
            value=2.85,
        )
        assert ef.unit is None
        assert ef.source is None

    def test_economic_snapshot_defaults(self):
        snap = EconomicSnapshot()
        assert snap.jet_fuel_usd_gal is None
        assert snap.eur_chf is None
        assert snap.as_of is None


class TestScenario:
    def test_scenario_create(self):
        sc = ScenarioCreate(
            name="Fuel spike",
            parameters={"fuel_price_change_pct": 20},
        )
        assert sc.name == "Fuel spike"
        assert sc.description is None

    def test_scenario_defaults(self):
        s = Scenario(name="test", parameters={})
        assert s.status == "pending"
        assert s.id is None


class TestPrediction:
    def test_prediction_construction(self):
        p = Prediction(
            model_name="fuel",
            model_version="1.0",
            target_variable="fuel_cost",
            predicted_value=1234.5,
        )
        assert p.predicted_value == 1234.5
        assert p.confidence_lower is None
