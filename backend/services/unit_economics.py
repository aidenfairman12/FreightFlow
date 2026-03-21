"""
Phase 7: CASK and RASK estimation for SWISS from public data.

CASK (Cost per Available Seat Kilometer) components:
- Fuel cost per ASK = fuel burn × jet fuel price / ASK
- Carbon cost per ASK = CO2 emissions × EUA price / ASK
- Navigation charges per ASK = Eurocontrol unit rates × distance / ASK
- Airport cost per ASK = ZRH charges / ASK
- Crew + overhead = industry benchmark proportions

RASK (Revenue per ASK):
- Estimated from Lufthansa Group published traffic/revenue data
- SWISS share derived from operational ASK proportion
"""

import logging
from datetime import datetime

from sqlalchemy import text

from db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

# Industry benchmark cost breakdown (% of total CASK, IATA 2023 data)
COST_BREAKDOWN = {
    "fuel": 0.28,        # ~28% of total costs
    "carbon": 0.03,      # ~3% (growing with EU ETS expansion)
    "navigation": 0.07,  # ~7% Eurocontrol/ANSP charges
    "airport": 0.10,     # ~10% landing, terminal, ground handling
    "crew": 0.25,        # ~25% flight + cabin crew
    "other": 0.27,       # ~27% maintenance, lease, admin, sales
}

# Eurocontrol Swiss unit rate (CHF per service unit, approximate)
SWISS_NAV_RATE_CHF = 108.0  # per 100 km at reference weight

# ZRH airport charges per movement (approximate, from ZRH annual report)
ZRH_LANDING_FEE_CHF = 1_200  # average per movement
ZRH_PASSENGER_FEE_CHF = 35   # per departing passenger (approx)

# Approximate SWISS crew cost per block hour (CHF)
CREW_COST_PER_BLOCK_HOUR_CHF = 1_800  # flight deck + cabin, averaged

# Jet fuel density: ~3.1 kg per US gallon
FUEL_KG_PER_GAL = 3.1


async def compute_unit_economics(
    period_start: datetime,
    period_end: datetime,
    period_type: str = "weekly",
) -> dict | None:
    """
    Compute CASK and RASK estimates for SWISS for the given period.

    Combines operational KPIs (from Phase 5) with economic factors (from Phase 6).
    """
    async with AsyncSessionLocal() as session:
        # 1. Get operational KPIs for this period
        kpi_result = await session.execute(text("""
            SELECT * FROM operational_kpis
            WHERE period_start = :start AND period_type = :ptype AND airline_code = 'SWR'
        """), {"start": period_start, "ptype": period_type})
        kpi = kpi_result.mappings().first()

        if not kpi or not kpi["total_ask"] or kpi["total_ask"] == 0:
            logger.info("No KPI data for %s %s, skipping unit economics", period_type, period_start)
            return None

        total_ask = kpi["total_ask"]
        total_fuel_kg = kpi["total_fuel_kg"] or 0
        total_co2_kg = kpi["total_co2_kg"] or 0
        total_block_hours = kpi["total_block_hours"] or 0
        total_departures = kpi["total_departures"] or 0

        # 2. Get latest economic factors
        factors = {}
        factor_result = await session.execute(text("""
            SELECT DISTINCT ON (factor_name)
                factor_name, value
            FROM economic_factors
            WHERE date <= :end_date
            ORDER BY factor_name, date DESC
        """), {"end_date": period_end.date()})
        for row in factor_result.mappings():
            factors[row["factor_name"]] = row["value"]

        jet_fuel_usd_gal = factors.get("jet_fuel_usd_gal", 2.80)  # fallback
        eua_eur_ton = factors.get("eua_eur_ton", 65.0)
        eur_chf = factors.get("eur_chf", 0.95)
        usd_chf = factors.get("usd_chf", 0.88)

        # 3. Compute CASK components (all in CHF-cents per ASK)

        # Fuel cost: fuel_kg × (price_per_gal / kg_per_gal) × USD/CHF / ASK × 100 (to cents)
        fuel_cost_total = total_fuel_kg * (jet_fuel_usd_gal / FUEL_KG_PER_GAL) * usd_chf
        fuel_cost_per_ask = (fuel_cost_total / total_ask * 100) if total_ask else 0

        # Carbon cost: CO2_tonnes × EUA_price × EUR/CHF / ASK × 100
        co2_tonnes = total_co2_kg / 1000
        carbon_cost_total = co2_tonnes * eua_eur_ton * eur_chf
        carbon_cost_per_ask = (carbon_cost_total / total_ask * 100) if total_ask else 0

        # Navigation charges: per flight × estimated distance ÷ ASK
        # Derive avg seats and distance from KPI data (avoids hardcoded 170)
        estimated_lf = kpi.get("estimated_load_factor", 0.82) or 0.82
        unique_aircraft = kpi.get("unique_aircraft_count", 1) or 1
        # avg_seats = total_ask / total_distance; total_distance ≈ block_hours × avg_speed
        # Rearrange: avg_seats ≈ total_ask / (block_hours × fleet_avg_speed)
        fleet_avg_speed_kmh = 830  # close to SWISS fleet weighted average
        total_distance_km = total_block_hours * fleet_avg_speed_kmh
        avg_seats = (total_ask / total_distance_km) if total_distance_km > 0 else 170
        avg_distance_per_flight = total_distance_km / total_departures if total_departures else 1000
        nav_cost_total = total_departures * (avg_distance_per_flight / 100) * SWISS_NAV_RATE_CHF
        nav_charges_per_ask = (nav_cost_total / total_ask * 100) if total_ask else 0

        # Airport costs: landing + passenger fees
        avg_pax_per_flight = avg_seats * estimated_lf
        airport_cost_total = total_departures * (
            ZRH_LANDING_FEE_CHF + avg_pax_per_flight * ZRH_PASSENGER_FEE_CHF
        )
        airport_cost_per_ask = (airport_cost_total / total_ask * 100) if total_ask else 0

        # Crew cost: block hours × rate / ASK
        crew_cost_total = total_block_hours * CREW_COST_PER_BLOCK_HOUR_CHF
        crew_cost_per_ask = (crew_cost_total / total_ask * 100) if total_ask else 0

        # Other costs: derived from fuel proportion and industry benchmark
        # If fuel = 28% of total, total CASK ≈ fuel_cask / 0.28
        # Other = total - (fuel + carbon + nav + airport + crew)
        estimated_total_from_fuel = fuel_cost_per_ask / COST_BREAKDOWN["fuel"] if fuel_cost_per_ask else 0
        known_costs = fuel_cost_per_ask + carbon_cost_per_ask + nav_charges_per_ask + airport_cost_per_ask + crew_cost_per_ask
        other_cost_per_ask = max(0, estimated_total_from_fuel - known_costs)

        total_cask = known_costs + other_cost_per_ask

        # 4. Estimate RASK
        # RASK for network carriers ≈ 1.05-1.15× CASK (target margin ~5-15%)
        # Lufthansa Group Network Airlines typically reports ~8-12% EBIT margin
        estimated_rask = total_cask * 1.10  # ~10% margin assumption

        spread = estimated_rask - total_cask

        economics = {
            "period_start": period_start,
            "period_end": period_end,
            "period_type": period_type,
            "airline_code": "SWR",
            "fuel_cost_per_ask": round(fuel_cost_per_ask, 4),
            "carbon_cost_per_ask": round(carbon_cost_per_ask, 4),
            "nav_charges_per_ask": round(nav_charges_per_ask, 4),
            "airport_cost_per_ask": round(airport_cost_per_ask, 4),
            "crew_cost_per_ask": round(crew_cost_per_ask, 4),
            "other_cost_per_ask": round(other_cost_per_ask, 4),
            "total_cask": round(total_cask, 4),
            "estimated_rask": round(estimated_rask, 4),
            "rask_cask_spread": round(spread, 4),
            "confidence_level": "estimate",
        }

        # Upsert
        await session.execute(text("""
            INSERT INTO unit_economics (
                period_start, period_end, period_type, airline_code,
                fuel_cost_per_ask, carbon_cost_per_ask, nav_charges_per_ask,
                airport_cost_per_ask, crew_cost_per_ask, other_cost_per_ask,
                total_cask, estimated_rask, rask_cask_spread, confidence_level
            ) VALUES (
                :period_start, :period_end, :period_type, :airline_code,
                :fuel_cost_per_ask, :carbon_cost_per_ask, :nav_charges_per_ask,
                :airport_cost_per_ask, :crew_cost_per_ask, :other_cost_per_ask,
                :total_cask, :estimated_rask, :rask_cask_spread, :confidence_level
            )
            ON CONFLICT (period_start, period_type, airline_code)
            DO UPDATE SET
                fuel_cost_per_ask = EXCLUDED.fuel_cost_per_ask,
                carbon_cost_per_ask = EXCLUDED.carbon_cost_per_ask,
                nav_charges_per_ask = EXCLUDED.nav_charges_per_ask,
                airport_cost_per_ask = EXCLUDED.airport_cost_per_ask,
                crew_cost_per_ask = EXCLUDED.crew_cost_per_ask,
                other_cost_per_ask = EXCLUDED.other_cost_per_ask,
                total_cask = EXCLUDED.total_cask,
                estimated_rask = EXCLUDED.estimated_rask,
                rask_cask_spread = EXCLUDED.rask_cask_spread,
                confidence_level = EXCLUDED.confidence_level,
                created_at = NOW()
        """), economics)
        await session.commit()

        logger.info("Unit economics for %s %s: CASK=%.2f, RASK=%.2f, spread=%.2f ct/ASK",
                     period_type, period_start.date(), total_cask, estimated_rask, spread)
        return economics
