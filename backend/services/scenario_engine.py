"""
Phase 9: Scenario engine for what-if analysis.

Supported scenario parameters:
- fuel_price_change_pct: % change in jet fuel price
- carbon_price_change_pct: % change in EU ETS price
- load_factor_change_pct: % change in load factor
- new_weekly_departures: additional departures on a route
- capacity_change_pct: fleet capacity change
- fx_eur_chf_change_pct: EUR/CHF exchange rate change
"""

import json
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import text

from db.session import AsyncSessionLocal
from services.unit_economics import COST_BREAKDOWN, FUEL_KG_PER_GAL

logger = logging.getLogger(__name__)


async def run_scenario(
    scenario_id: UUID,
    parameters: dict,
    base_period_start: datetime | None = None,
    base_period_end: datetime | None = None,
) -> dict:
    """
    Execute a what-if scenario against the latest unit economics baseline.

    Returns scenario results with deltas for each CASK/RASK component.
    """
    async with AsyncSessionLocal() as session:
        # Load baseline unit economics
        if base_period_start:
            baseline_q = await session.execute(text("""
                SELECT * FROM unit_economics
                WHERE period_start = :start AND airline_code = 'SWR'
                ORDER BY created_at DESC LIMIT 1
            """), {"start": base_period_start})
        else:
            baseline_q = await session.execute(text("""
                SELECT * FROM unit_economics
                WHERE airline_code = 'SWR'
                ORDER BY period_start DESC LIMIT 1
            """))

        baseline = baseline_q.mappings().first()
        if not baseline:
            return {"error": "No baseline unit economics data available"}

        # Load baseline economic factors
        factors_q = await session.execute(text("""
            SELECT DISTINCT ON (factor_name) factor_name, value
            FROM economic_factors
            ORDER BY factor_name, date DESC
        """))
        factors = {r["factor_name"]: r["value"] for r in factors_q.mappings()}

        # Load baseline KPIs
        kpi_q = await session.execute(text("""
            SELECT * FROM operational_kpis
            WHERE period_start = :start AND airline_code = 'SWR'
            ORDER BY created_at DESC LIMIT 1
        """), {"start": baseline["period_start"]})
        kpi = kpi_q.mappings().first() or {}

    # Apply scenario modifications
    scenario_factors = dict(factors)
    scenario_kpi = dict(kpi)

    fuel_change = parameters.get("fuel_price_change_pct", 0)
    carbon_change = parameters.get("carbon_price_change_pct", 0)
    lf_change = parameters.get("load_factor_change_pct", 0)
    capacity_change = parameters.get("capacity_change_pct", 0)
    fx_change = parameters.get("fx_eur_chf_change_pct", 0)
    new_departures = parameters.get("new_weekly_departures", 0)

    # Adjust fuel price
    if fuel_change:
        base_fuel = scenario_factors.get("jet_fuel_usd_gal", 2.80)
        scenario_factors["jet_fuel_usd_gal"] = base_fuel * (1 + fuel_change / 100)

    # Adjust carbon price
    if carbon_change:
        base_carbon = scenario_factors.get("eua_eur_ton", 65.0)
        scenario_factors["eua_eur_ton"] = base_carbon * (1 + carbon_change / 100)

    # Adjust FX
    if fx_change:
        base_fx = scenario_factors.get("eur_chf", 0.95)
        scenario_factors["eur_chf"] = base_fx * (1 + fx_change / 100)

    # Recompute CASK components with scenario values
    total_ask = float(kpi.get("total_ask", 1) or 1)
    total_fuel_kg = float(kpi.get("total_fuel_kg", 0) or 0)
    total_co2_kg = float(kpi.get("total_co2_kg", 0) or 0)
    total_block_hours = float(kpi.get("total_block_hours", 0) or 0)
    total_deps = int(kpi.get("total_departures", 0) or 0) + new_departures

    # Capacity change adjusts ASK
    if capacity_change:
        total_ask *= (1 + capacity_change / 100)

    usd_chf = scenario_factors.get("usd_chf", 0.88)
    eur_chf = scenario_factors.get("eur_chf", 0.95)
    jet_fuel = scenario_factors.get("jet_fuel_usd_gal", 2.80)
    eua_price = scenario_factors.get("eua_eur_ton", 65.0)

    # Fuel cost per ASK
    fuel_cost = total_fuel_kg * (jet_fuel / FUEL_KG_PER_GAL) * usd_chf
    s_fuel_per_ask = (fuel_cost / total_ask * 100) if total_ask else 0

    # Carbon cost per ASK
    carbon_cost = (total_co2_kg / 1000) * eua_price * eur_chf
    s_carbon_per_ask = (carbon_cost / total_ask * 100) if total_ask else 0

    # Keep other components proportional (nav, airport, crew, other)
    s_nav = float(baseline["nav_charges_per_ask"] or 0)
    s_airport = float(baseline["airport_cost_per_ask"] or 0)
    s_crew = float(baseline["crew_cost_per_ask"] or 0)
    s_other = float(baseline["other_cost_per_ask"] or 0)

    # If capacity changes, fixed costs spread across more/fewer ASK
    if capacity_change:
        scale = 1 / (1 + capacity_change / 100)
        s_nav *= scale
        s_airport *= scale
        s_crew *= scale
        s_other *= scale

    s_total_cask = s_fuel_per_ask + s_carbon_per_ask + s_nav + s_airport + s_crew + s_other

    # RASK adjustment: load factor change affects revenue
    base_rask = float(baseline["estimated_rask"] or 0)
    s_rask = base_rask * (1 + lf_change / 100) if lf_change else base_rask

    s_spread = s_rask - s_total_cask

    # Compute deltas
    b_cask = float(baseline["total_cask"] or 0)
    b_rask = float(baseline["estimated_rask"] or 0)

    results = {
        "scenario_id": str(scenario_id),
        "baseline": {
            "total_cask": b_cask,
            "estimated_rask": b_rask,
            "spread": round(b_rask - b_cask, 4),
            "fuel_cost_per_ask": float(baseline["fuel_cost_per_ask"] or 0),
            "carbon_cost_per_ask": float(baseline["carbon_cost_per_ask"] or 0),
        },
        "scenario": {
            "total_cask": round(s_total_cask, 4),
            "estimated_rask": round(s_rask, 4),
            "spread": round(s_spread, 4),
            "fuel_cost_per_ask": round(s_fuel_per_ask, 4),
            "carbon_cost_per_ask": round(s_carbon_per_ask, 4),
            "nav_charges_per_ask": round(s_nav, 4),
            "airport_cost_per_ask": round(s_airport, 4),
            "crew_cost_per_ask": round(s_crew, 4),
            "other_cost_per_ask": round(s_other, 4),
        },
        "deltas": {
            "total_cask": round(s_total_cask - b_cask, 4),
            "estimated_rask": round(s_rask - b_rask, 4),
            "spread": round(s_spread - (b_rask - b_cask), 4),
            "fuel_cost_per_ask": round(s_fuel_per_ask - float(baseline["fuel_cost_per_ask"] or 0), 4),
            "carbon_cost_per_ask": round(s_carbon_per_ask - float(baseline["carbon_cost_per_ask"] or 0), 4),
        },
        "impact_summary": _generate_summary(parameters, s_total_cask - b_cask, s_spread - (b_rask - b_cask)),
        "applied_parameters": parameters,
    }

    # Persist results
    async with AsyncSessionLocal() as session:
        await session.execute(text("""
            UPDATE scenarios
            SET results = :results, status = 'completed'
            WHERE id = :id
        """), {"id": scenario_id, "results": json.dumps(results)})
        await session.commit()

    logger.info("Scenario %s complete: CASK delta=%.4f, spread delta=%.4f",
                scenario_id, s_total_cask - b_cask, s_spread - (b_rask - b_cask))
    return results


def _generate_summary(params: dict, cask_delta: float, spread_delta: float) -> str:
    """Generate human-readable impact summary."""
    parts = []
    if params.get("fuel_price_change_pct"):
        parts.append(f"fuel price {'increase' if params['fuel_price_change_pct'] > 0 else 'decrease'} "
                     f"of {abs(params['fuel_price_change_pct'])}%")
    if params.get("carbon_price_change_pct"):
        parts.append(f"carbon price change of {params['carbon_price_change_pct']:+}%")
    if params.get("capacity_change_pct"):
        parts.append(f"capacity change of {params['capacity_change_pct']:+}%")
    if params.get("load_factor_change_pct"):
        parts.append(f"load factor change of {params['load_factor_change_pct']:+}%")
    if params.get("new_weekly_departures"):
        parts.append(f"{params['new_weekly_departures']} additional weekly departures")

    scenario_desc = ", ".join(parts) if parts else "No parameter changes"
    impact = "positive" if spread_delta > 0 else "negative"

    return (
        f"Scenario: {scenario_desc}. "
        f"CASK impact: {cask_delta:+.2f} ct/ASK. "
        f"Spread impact: {spread_delta:+.2f} ct/ASK ({impact})."
    )
