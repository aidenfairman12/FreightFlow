"""Corridor performance analysis: efficiency scoring and trend comparison.

Compares corridor freight metrics across years, scoring each corridor
by cost efficiency (value transported per dollar of freight cost).
"""

import logging

from sqlalchemy import text

from db.session import AsyncSessionLocal
from services.freight_cost_model import estimate_corridor_cost

logger = logging.getLogger(__name__)


async def compute_corridor_performance(year: int = 2022) -> int:
    """Compute and store corridor performance metrics for a given year.

    Returns the number of corridors scored.
    """
    async with AsyncSessionLocal() as session:
        # Get all corridors
        result = await session.execute(text("""
            SELECT corridor_id, name FROM corridors
        """))
        corridors = list(result.mappings())

    count = 0
    for corridor in corridors:
        cid = str(corridor["corridor_id"])
        try:
            cost_data = await estimate_corridor_cost(cid, year)
            if not cost_data["modes"]:
                continue

            total_tons = sum(m.get("tons_thousands", 0) or 0 for m in cost_data["modes"]) * 1_000
            total_value = sum(m.get("value_millions", 0) or 0 for m in cost_data["modes"]) * 1_000_000
            total_tmiles = sum(m.get("ton_miles_millions", 0) or 0 for m in cost_data["modes"]) * 1_000_000
            total_cost = cost_data["total_estimated_cost"]

            # Mode breakdown as JSON
            mode_breakdown = {}
            for m in cost_data["modes"]:
                mode_breakdown[m["mode_name"]] = {
                    "tons_thousands": m.get("tons_thousands"),
                    "value_millions": m.get("value_millions"),
                    "ton_miles_millions": m.get("ton_miles_millions"),
                    "cost_per_ton_mile": m.get("cost_per_ton_mile"),
                    "total_cost": m.get("total_cost_usd"),
                }

            avg_value_per_ton = total_value / total_tons if total_tons > 0 else 0
            cost_per_ton = total_cost / total_tons if total_tons > 0 else 0

            async with AsyncSessionLocal() as session:
                await session.execute(text("""
                    INSERT INTO corridor_performance
                        (corridor_id, year, total_tons, total_value_usd,
                         total_ton_miles, mode_breakdown, avg_value_per_ton,
                         estimated_cost, cost_per_ton)
                    VALUES
                        (:cid, :year, :tons, :value, :tmiles,
                         :modes::jsonb, :vperton, :cost, :cpton)
                    ON CONFLICT (corridor_id, year, sctg2) DO UPDATE SET
                        total_tons = EXCLUDED.total_tons,
                        total_value_usd = EXCLUDED.total_value_usd,
                        total_ton_miles = EXCLUDED.total_ton_miles,
                        mode_breakdown = EXCLUDED.mode_breakdown,
                        avg_value_per_ton = EXCLUDED.avg_value_per_ton,
                        estimated_cost = EXCLUDED.estimated_cost,
                        cost_per_ton = EXCLUDED.cost_per_ton,
                        updated_at = NOW()
                """), {
                    "cid": cid,
                    "year": year,
                    "tons": total_tons,
                    "value": total_value,
                    "tmiles": total_tmiles,
                    "modes": str(mode_breakdown).replace("'", '"'),
                    "vperton": avg_value_per_ton,
                    "cost": total_cost,
                    "cpton": cost_per_ton,
                })
                await session.commit()
            count += 1
        except Exception:
            logger.exception("Failed to compute performance for corridor %s", corridor["name"])

    logger.info("Computed corridor performance for %d corridors (year %d)", count, year)
    return count


async def get_corridor_performance_summary(
    sort_by: str = "estimated_cost",
    limit: int = 50,
) -> list[dict]:
    """Return corridor performance metrics sorted by the given field."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(text(f"""
            SELECT
                cp.corridor_id,
                c.name AS corridor_name,
                c.description,
                cp.year,
                cp.total_tons,
                cp.total_value_usd,
                cp.total_ton_miles,
                cp.mode_breakdown,
                cp.avg_value_per_ton,
                cp.estimated_cost,
                cp.cost_per_ton
            FROM corridor_performance cp
            JOIN corridors c ON cp.corridor_id = c.corridor_id
            ORDER BY cp.{sort_by} DESC NULLS LAST
            LIMIT :limit
        """), {"limit": limit})
        return [dict(r) for r in result.mappings()]
