"""Freight cost model: estimate cost per ton-mile by transport mode.

Rate constants sourced from:
- ATRI (American Transportation Research Institute) Operational Costs of Trucking 2023
- AAR (Association of American Railroads) Railroad Facts 2023
- BTS Air Cargo Statistics
- Army Corps of Engineers (waterway freight)
- JOC/IHS Markit (intermodal)

All rates are in USD per ton-mile.
"""

import logging
from typing import Any

from sqlalchemy import text

from db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

# ── Base Rates (USD per ton-mile, 2022 benchmark year) ────────────────────

BASE_RATES: dict[int, dict[str, Any]] = {
    1: {  # Truck
        "mode_name": "Truck",
        "cost_per_ton_mile": 0.12,
        "source": "ATRI Operational Costs 2023",
        "breakdown": {
            "fuel": 0.38,        # 38% of cost
            "labor": 0.35,       # 35%
            "equipment": 0.12,   # 12%
            "insurance": 0.05,   # 5%
            "tolls_fees": 0.05,  # 5%
            "other": 0.05,       # 5%
        },
    },
    2: {  # Rail
        "mode_name": "Rail",
        "cost_per_ton_mile": 0.035,
        "source": "AAR Railroad Facts 2023",
        "breakdown": {
            "fuel": 0.18,
            "labor": 0.25,
            "equipment": 0.30,
            "insurance": 0.03,
            "tolls_fees": 0.04,
            "other": 0.20,
        },
    },
    3: {  # Water
        "mode_name": "Water",
        "cost_per_ton_mile": 0.015,
        "source": "Army Corps of Engineers",
        "breakdown": {
            "fuel": 0.25,
            "labor": 0.30,
            "equipment": 0.25,
            "insurance": 0.05,
            "tolls_fees": 0.05,
            "other": 0.10,
        },
    },
    4: {  # Air
        "mode_name": "Air",
        "cost_per_ton_mile": 0.95,
        "source": "BTS Air Cargo Statistics",
        "breakdown": {
            "fuel": 0.30,
            "labor": 0.25,
            "equipment": 0.20,
            "insurance": 0.05,
            "tolls_fees": 0.10,
            "other": 0.10,
        },
    },
    5: {  # Multiple modes / intermodal
        "mode_name": "Intermodal",
        "cost_per_ton_mile": 0.07,
        "source": "JOC/IHS Markit",
        "breakdown": {
            "fuel": 0.25,
            "labor": 0.28,
            "equipment": 0.22,
            "insurance": 0.04,
            "tolls_fees": 0.06,
            "other": 0.15,
        },
    },
    6: {  # Pipeline
        "mode_name": "Pipeline",
        "cost_per_ton_mile": 0.02,
        "source": "EIA/BTS estimate",
        "breakdown": {
            "fuel": 0.15,
            "labor": 0.15,
            "equipment": 0.40,
            "insurance": 0.05,
            "tolls_fees": 0.05,
            "other": 0.20,
        },
    },
}

# Diesel price reference for fuel cost sensitivity
# When diesel is at this price, the base rates apply
DIESEL_BASELINE_USD_GAL = 3.85  # approx 2022 average on-highway diesel


def get_rate(mode_code: int) -> float:
    """Get base cost per ton-mile for a transport mode."""
    if mode_code in BASE_RATES:
        return BASE_RATES[mode_code]["cost_per_ton_mile"]
    return BASE_RATES.get(1, {}).get("cost_per_ton_mile", 0.12)  # default to truck


def get_cost_breakdown(mode_code: int) -> dict[str, float]:
    """Get cost component breakdown (as fractions summing to 1.0) for a mode."""
    if mode_code in BASE_RATES:
        return BASE_RATES[mode_code]["breakdown"]
    return BASE_RATES[1]["breakdown"]


def adjust_rate_for_diesel(mode_code: int, diesel_usd_gal: float) -> float:
    """Adjust cost per ton-mile based on current diesel price.

    Fuel cost sensitivity differs by mode:
    - Truck: highly sensitive (fuel = 38% of cost)
    - Rail: moderately sensitive (fuel = 18% of cost)
    - Air: uses jet fuel, loosely correlated with diesel
    """
    base_rate = get_rate(mode_code)
    breakdown = get_cost_breakdown(mode_code)
    fuel_share = breakdown.get("fuel", 0.30)

    # Price change ratio
    diesel_ratio = diesel_usd_gal / DIESEL_BASELINE_USD_GAL

    # Only the fuel portion scales with diesel price
    adjusted = base_rate * ((1 - fuel_share) + fuel_share * diesel_ratio)
    return adjusted


def estimate_flow_cost(
    tons_thousands: float,
    ton_miles_millions: float,
    mode_code: int,
    diesel_usd_gal: float | None = None,
) -> dict[str, float]:
    """Estimate total freight cost for a given flow.

    Args:
        tons_thousands: Thousands of tons
        ton_miles_millions: Millions of ton-miles
        mode_code: FAF5 transport mode code
        diesel_usd_gal: Current diesel price (if None, uses baseline)

    Returns:
        Dict with total_cost, cost_per_ton, cost_per_ton_mile, and component breakdown
    """
    if diesel_usd_gal:
        rate = adjust_rate_for_diesel(mode_code, diesel_usd_gal)
    else:
        rate = get_rate(mode_code)

    total_ton_miles = (ton_miles_millions or 0) * 1_000_000
    total_tons = (tons_thousands or 0) * 1_000
    total_cost = total_ton_miles * rate

    breakdown = get_cost_breakdown(mode_code)

    return {
        "total_cost_usd": total_cost,
        "cost_per_ton_mile": rate,
        "cost_per_ton": total_cost / total_tons if total_tons > 0 else 0,
        "components": {
            "fuel": total_cost * breakdown.get("fuel", 0),
            "labor": total_cost * breakdown.get("labor", 0),
            "equipment": total_cost * breakdown.get("equipment", 0),
            "insurance": total_cost * breakdown.get("insurance", 0),
            "tolls_fees": total_cost * breakdown.get("tolls_fees", 0),
            "other": total_cost * breakdown.get("other", 0),
        },
    }


async def compute_mode_cost_comparison(year: int = 2022) -> list[dict]:
    """Compute side-by-side cost comparison across all modes for a given year.

    Pulls actual freight flow volumes from the DB and applies cost rates.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT
                mode_code,
                mode_name,
                SUM(tons_thousands) AS total_tons_k,
                SUM(value_millions) AS total_value_m,
                SUM(ton_miles_millions) AS total_tmiles_m
            FROM freight_flows
            WHERE year = :year
            GROUP BY mode_code, mode_name
            ORDER BY total_tmiles_m DESC NULLS LAST
        """), {"year": year})

        modes = []
        for row in result.mappings():
            mc = row["mode_code"]
            cost_info = estimate_flow_cost(
                tons_thousands=row["total_tons_k"] or 0,
                ton_miles_millions=row["total_tmiles_m"] or 0,
                mode_code=mc,
            )
            modes.append({
                "mode_code": mc,
                "mode_name": row["mode_name"],
                "total_tons_thousands": row["total_tons_k"],
                "total_value_millions": row["total_value_m"],
                "total_ton_miles_millions": row["total_tmiles_m"],
                "cost_per_ton_mile": cost_info["cost_per_ton_mile"],
                "total_estimated_cost": cost_info["total_cost_usd"],
                "source": BASE_RATES.get(mc, {}).get("source", "estimate"),
            })
        return modes


async def estimate_corridor_cost(
    corridor_id: str,
    year: int = 2022,
    commodity: str | None = None,
    diesel_usd_gal: float | None = None,
) -> dict:
    """Estimate total freight cost for a corridor by mode.

    Args:
        corridor_id: UUID of the corridor
        year: Analysis year
        commodity: Optional SCTG2 filter
        diesel_usd_gal: Optional diesel price override
    """
    commodity_filter = "AND ff.sctg2 = :commodity" if commodity else ""

    async with AsyncSessionLocal() as session:
        result = await session.execute(text(f"""
            SELECT
                ff.mode_code,
                ff.mode_name,
                SUM(ff.tons_thousands) AS total_tons_k,
                SUM(ff.value_millions) AS total_value_m,
                SUM(ff.ton_miles_millions) AS total_tmiles_m
            FROM freight_flows ff
            JOIN corridors c ON ff.origin_zone_id = ANY(c.origin_zones)
                            AND ff.dest_zone_id = ANY(c.dest_zones)
            WHERE c.corridor_id = :cid
              AND ff.year = :year
              {commodity_filter}
            GROUP BY ff.mode_code, ff.mode_name
            ORDER BY total_tmiles_m DESC NULLS LAST
        """), {"cid": corridor_id, "year": year, "commodity": commodity})

        total_cost = 0
        mode_details = []
        for row in result.mappings():
            cost_info = estimate_flow_cost(
                tons_thousands=row["total_tons_k"] or 0,
                ton_miles_millions=row["total_tmiles_m"] or 0,
                mode_code=row["mode_code"],
                diesel_usd_gal=diesel_usd_gal,
            )
            total_cost += cost_info["total_cost_usd"]
            mode_details.append({
                "mode_code": row["mode_code"],
                "mode_name": row["mode_name"],
                "tons_thousands": row["total_tons_k"],
                "value_millions": row["total_value_m"],
                "ton_miles_millions": row["total_tmiles_m"],
                **cost_info,
            })

        return {
            "corridor_id": corridor_id,
            "year": year,
            "commodity": commodity,
            "total_estimated_cost": total_cost,
            "modes": mode_details,
        }
