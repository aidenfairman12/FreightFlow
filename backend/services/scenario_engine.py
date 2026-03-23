"""Freight scenario engine for what-if analysis.

Supported scenario parameters:
- diesel_price_change_pct: % change in diesel price
- rail_capacity_change_pct: % change in rail capacity
- port_congestion_days: additional port delay (days)
- truck_driver_shortage_pct: % reduction in trucking capacity
- demand_change_pct: % change in corridor demand
- mode_shift_to_rail_pct: % of truck volume shifted to rail
- carbon_tax_per_ton_mile: USD carbon tax per ton-mile
- toll_increase_pct: % increase in highway tolls
"""

import json
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import text

from db.session import AsyncSessionLocal
from services.freight_cost_model import (
    BASE_RATES,
    DIESEL_BASELINE_USD_GAL,
    get_rate,
    get_cost_breakdown,
    adjust_rate_for_diesel,
)

logger = logging.getLogger(__name__)


async def run_scenario(
    scenario_id: UUID,
    parameters: dict,
    base_period_start: datetime | None = None,
    base_period_end: datetime | None = None,
) -> dict:
    """Execute a what-if scenario against the latest freight unit economics baseline.

    Returns scenario results with deltas for each cost component.
    """
    async with AsyncSessionLocal() as session:
        # Load baseline unit economics (most recent year)
        baseline_q = await session.execute(text("""
            SELECT * FROM freight_unit_economics
            ORDER BY year DESC
            LIMIT 1
        """))
        baseline = baseline_q.mappings().first()
        if not baseline:
            # No computed unit economics yet — use defaults from cost model
            baseline = _default_baseline()

        # Load baseline KPIs
        kpi_q = await session.execute(text("""
            SELECT * FROM freight_kpis
            WHERE scope = 'national'
            ORDER BY period_year DESC
            LIMIT 1
        """))
        kpi = kpi_q.mappings().first()

        # Load latest diesel price
        diesel_q = await session.execute(text("""
            SELECT value FROM economic_factors
            WHERE factor_name = 'diesel_usd_gal'
            ORDER BY date DESC LIMIT 1
        """))
        diesel_row = diesel_q.mappings().first()
        base_diesel = float(diesel_row["value"]) if diesel_row else DIESEL_BASELINE_USD_GAL

    # Extract parameters
    diesel_change = parameters.get("diesel_price_change_pct", 0)
    rail_capacity_change = parameters.get("rail_capacity_change_pct", 0)
    port_congestion = parameters.get("port_congestion_days", 0)
    driver_shortage = parameters.get("truck_driver_shortage_pct", 0)
    demand_change = parameters.get("demand_change_pct", 0)
    mode_shift_rail = parameters.get("mode_shift_to_rail_pct", 0)
    carbon_tax = parameters.get("carbon_tax_per_ton_mile", 0)
    toll_increase = parameters.get("toll_increase_pct", 0)

    # Baseline values
    b_fuel = float(baseline.get("fuel_cost_per_tm") or baseline["fuel_cost_per_tm"])
    b_labor = float(baseline.get("labor_cost_per_tm") or baseline["labor_cost_per_tm"])
    b_equipment = float(baseline.get("equipment_cost_per_tm") or baseline["equipment_cost_per_tm"])
    b_insurance = float(baseline.get("insurance_cost_per_tm") or baseline["insurance_cost_per_tm"])
    b_tolls = float(baseline.get("tolls_fees_per_tm") or baseline["tolls_fees_per_tm"])
    b_other = float(baseline.get("other_cost_per_tm") or baseline["other_cost_per_tm"])
    b_total = b_fuel + b_labor + b_equipment + b_insurance + b_tolls + b_other
    b_revenue = float(baseline.get("revenue_per_tm") or 0)

    # ── Apply scenario adjustments ──

    s_fuel = b_fuel
    s_labor = b_labor
    s_equipment = b_equipment
    s_insurance = b_insurance
    s_tolls = b_tolls
    s_other = b_other

    # 1. Diesel price change → fuel cost
    if diesel_change:
        s_fuel = b_fuel * (1 + diesel_change / 100)

    # 2. Truck driver shortage → labor cost increase
    if driver_shortage:
        # Shortage increases trucking rates; labor portion of truck cost rises
        s_labor = b_labor * (1 + driver_shortage / 100 * 0.8)  # 80% pass-through

    # 3. Toll increase → tolls/fees
    if toll_increase:
        s_tolls = b_tolls * (1 + toll_increase / 100)

    # 4. Carbon tax → added cost per ton-mile
    carbon_cost = carbon_tax  # directly $/ton-mile

    # 5. Port congestion → increases overall cost (delays, storage, rerouting)
    congestion_cost = 0
    if port_congestion:
        # Rough model: each day of delay adds ~$0.002/ton-mile in storage/rerouting costs
        congestion_cost = port_congestion * 0.002

    # 6. Mode shift to rail → changes weighted cost
    # Rail is cheaper per ton-mile; shifting volume from truck to rail reduces avg cost
    mode_shift_savings = 0
    if mode_shift_rail and kpi:
        truck_share = float(kpi.get("truck_share_pct") or 70) / 100
        truck_rate = get_rate(1)  # ~$0.12
        rail_rate = get_rate(2)   # ~$0.035
        # Savings from shifting X% of truck volume to rail
        shifted_fraction = mode_shift_rail / 100 * truck_share
        mode_shift_savings = shifted_fraction * (truck_rate - rail_rate)

    # Total scenario cost per ton-mile
    s_total = (s_fuel + s_labor + s_equipment + s_insurance + s_tolls + s_other
               + carbon_cost + congestion_cost - mode_shift_savings)

    # Revenue adjustment for demand change
    s_revenue = b_revenue * (1 + demand_change / 100) if demand_change else b_revenue

    s_margin = s_revenue - s_total
    b_margin = b_revenue - b_total

    results = {
        "scenario_id": str(scenario_id),
        "baseline": {
            "total_cost_per_tm": round(b_total, 6),
            "fuel": round(b_fuel, 6),
            "labor": round(b_labor, 6),
            "equipment": round(b_equipment, 6),
            "insurance": round(b_insurance, 6),
            "tolls_fees": round(b_tolls, 6),
            "other": round(b_other, 6),
            "revenue_per_tm": round(b_revenue, 6),
            "margin_per_tm": round(b_margin, 6),
        },
        "scenario": {
            "total_cost_per_tm": round(s_total, 6),
            "fuel": round(s_fuel, 6),
            "labor": round(s_labor, 6),
            "equipment": round(s_equipment, 6),
            "insurance": round(s_insurance, 6),
            "tolls_fees": round(s_tolls, 6),
            "other": round(s_other, 6),
            "carbon_tax": round(carbon_cost, 6),
            "congestion_cost": round(congestion_cost, 6),
            "mode_shift_savings": round(mode_shift_savings, 6),
            "revenue_per_tm": round(s_revenue, 6),
            "margin_per_tm": round(s_margin, 6),
        },
        "deltas": {
            "total_cost_per_tm": round(s_total - b_total, 6),
            "fuel": round(s_fuel - b_fuel, 6),
            "labor": round(s_labor - b_labor, 6),
            "tolls_fees": round(s_tolls - b_tolls, 6),
            "margin_per_tm": round(s_margin - b_margin, 6),
            "cost_change_pct": round((s_total - b_total) / b_total * 100, 2) if b_total else 0,
        },
        "impact_summary": _generate_summary(parameters, s_total - b_total, s_margin - b_margin),
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

    logger.info("Scenario %s complete: cost delta=%.4f $/tm, margin delta=%.4f $/tm",
                scenario_id, s_total - b_total, s_margin - b_margin)
    return results


def _default_baseline() -> dict:
    """Generate baseline from cost model defaults when no DB data exists."""
    # Weighted average assuming national mode split (truck-heavy)
    # Approximate US mode split by ton-miles: truck 40%, rail 30%, water 5%, pipe 20%, other 5%
    weights = {1: 0.40, 2: 0.30, 3: 0.05, 5: 0.05, 6: 0.20}

    fuel = sum(get_rate(m) * get_cost_breakdown(m)["fuel"] * w for m, w in weights.items())
    labor = sum(get_rate(m) * get_cost_breakdown(m)["labor"] * w for m, w in weights.items())
    equipment = sum(get_rate(m) * get_cost_breakdown(m)["equipment"] * w for m, w in weights.items())
    insurance = sum(get_rate(m) * get_cost_breakdown(m)["insurance"] * w for m, w in weights.items())
    tolls = sum(get_rate(m) * get_cost_breakdown(m)["tolls_fees"] * w for m, w in weights.items())
    other = sum(get_rate(m) * get_cost_breakdown(m)["other"] * w for m, w in weights.items())

    return {
        "fuel_cost_per_tm": fuel,
        "labor_cost_per_tm": labor,
        "equipment_cost_per_tm": equipment,
        "insurance_cost_per_tm": insurance,
        "tolls_fees_per_tm": tolls,
        "other_cost_per_tm": other,
        "revenue_per_tm": 0.10,  # rough national average
    }


def _generate_summary(params: dict, cost_delta: float, margin_delta: float) -> str:
    """Generate human-readable impact summary."""
    parts = []
    if params.get("diesel_price_change_pct"):
        parts.append(f"diesel price {params['diesel_price_change_pct']:+}%")
    if params.get("truck_driver_shortage_pct"):
        parts.append(f"driver shortage -{params['truck_driver_shortage_pct']}%")
    if params.get("rail_capacity_change_pct"):
        parts.append(f"rail capacity {params['rail_capacity_change_pct']:+}%")
    if params.get("port_congestion_days"):
        parts.append(f"port congestion +{params['port_congestion_days']} days")
    if params.get("demand_change_pct"):
        parts.append(f"demand {params['demand_change_pct']:+}%")
    if params.get("mode_shift_to_rail_pct"):
        parts.append(f"{params['mode_shift_to_rail_pct']}% truck→rail shift")
    if params.get("carbon_tax_per_ton_mile"):
        parts.append(f"carbon tax ${params['carbon_tax_per_ton_mile']}/ton-mile")
    if params.get("toll_increase_pct"):
        parts.append(f"toll increase {params['toll_increase_pct']:+}%")

    scenario_desc = ", ".join(parts) if parts else "No parameter changes"
    impact = "favorable" if margin_delta > 0 else "adverse"

    return (
        f"Scenario: {scenario_desc}. "
        f"Cost impact: {cost_delta:+.4f} $/ton-mile ({cost_delta / 0.06 * 100:+.1f}% of baseline). "
        f"Margin impact: {margin_delta:+.4f} $/ton-mile ({impact})."
    )
