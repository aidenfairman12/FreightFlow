"""Tests for Pydantic models — construction, defaults, serialization."""

from datetime import date
from uuid import uuid4

from models.freight import FreightFlow, Corridor, FreightKPI, FreightUnitEconomics, FafZone
from models.economics import EconomicFactor, EconomicSnapshot
from models.scenario import ScenarioCreate, Scenario, ScenarioResult


class TestFreightModels:
    def test_freight_flow_construction(self):
        ff = FreightFlow(
            origin_zone_id=61,
            dest_zone_id=171,
            sctg2="35",
            mode_code=1,
            mode_name="Truck",
            year=2022,
        )
        assert ff.sctg2 == "35"
        assert ff.data_type == "historical"
        assert ff.tons_thousands is None

    def test_corridor_construction(self):
        c = Corridor(
            name="LA-Chicago",
            origin_zones=[61],
            dest_zones=[171],
        )
        assert c.corridor_id is None
        assert c.origin_zones == [61]

    def test_freight_kpi_defaults(self):
        kpi = FreightKPI(period_year=2022)
        assert kpi.scope == "national"
        assert kpi.total_tons is None
        assert kpi.truck_share_pct is None

    def test_freight_unit_economics_defaults(self):
        ue = FreightUnitEconomics(year=2022)
        assert ue.scope == "national"
        assert ue.fuel_cost_per_tm is None
        assert ue.total_cost_per_tm is None

    def test_faf_zone(self):
        z = FafZone(zone_id=61, zone_name="Los Angeles-Long Beach")
        assert z.latitude is None


class TestEconomics:
    def test_economic_factor_construction(self):
        ef = EconomicFactor(
            date=date(2024, 3, 1),
            factor_name="diesel_usd_gal",
            value=3.85,
        )
        assert ef.unit is None
        assert ef.source is None

    def test_economic_snapshot_defaults(self):
        snap = EconomicSnapshot()
        assert snap.diesel_usd_gal is None
        assert snap.brent_crude_usd_bbl is None
        assert snap.as_of is None


class TestScenario:
    def test_scenario_create(self):
        sc = ScenarioCreate(
            name="Diesel spike",
            parameters={"diesel_price_change_pct": 30},
        )
        assert sc.name == "Diesel spike"
        assert sc.description is None

    def test_scenario_defaults(self):
        s = Scenario(name="test", parameters={})
        assert s.status == "pending"
        assert s.id is None

    def test_scenario_result(self):
        sr = ScenarioResult(scenario_id=uuid4())
        assert sr.baseline_cost_per_tm is None
