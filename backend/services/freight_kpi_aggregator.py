"""Freight KPI aggregator: compute aggregated metrics from freight_flows.

Computes per-year KPIs at national or corridor scope:
- Total tons, value, ton-miles
- Mode share percentages
- Average cost per ton-mile
- Value density (value per ton)
- Average haul length proxy (ton-miles per ton)
"""

import logging

from sqlalchemy import text

from db.session import AsyncSessionLocal
from services.freight_cost_model import get_rate

logger = logging.getLogger(__name__)


async def compute_freight_kpis(year: int, scope: str = "national") -> dict | None:
    """Compute freight KPIs for a given year and scope.

    Args:
        year: Analysis year
        scope: 'national' or 'corridor:<corridor_name>'

    Returns the computed KPI dict, or None if insufficient data.
    """
    # Build scope filter
    corridor_join = ""
    corridor_where = ""
    if scope.startswith("corridor:"):
        corridor_name = scope.split(":", 1)[1]
        corridor_join = """
            JOIN corridors c ON ff.origin_zone_id = ANY(c.origin_zones)
                            AND ff.dest_zone_id = ANY(c.dest_zones)
        """
        corridor_where = "AND c.name = :corridor_name"

    async with AsyncSessionLocal() as session:
        # Aggregate by mode
        result = await session.execute(text(f"""
            SELECT
                ff.mode_code,
                SUM(ff.tons_thousands) AS tons_k,
                SUM(ff.value_millions) AS value_m,
                SUM(ff.ton_miles_millions) AS tmiles_m
            FROM freight_flows ff
            {corridor_join}
            WHERE ff.year = :year
              {corridor_where}
            GROUP BY ff.mode_code
        """), {"year": year, "corridor_name": scope.split(":", 1)[1] if ":" in scope else None})

        modes = {}
        total_tons = 0
        total_value = 0
        total_tmiles = 0
        total_cost = 0

        for row in result.mappings():
            mc = row["mode_code"]
            tons_k = float(row["tons_k"] or 0)
            value_m = float(row["value_m"] or 0)
            tmiles_m = float(row["tmiles_m"] or 0)

            modes[mc] = {"tons_k": tons_k, "value_m": value_m, "tmiles_m": tmiles_m}
            total_tons += tons_k
            total_value += value_m
            total_tmiles += tmiles_m
            total_cost += tmiles_m * 1_000_000 * get_rate(mc)

        if total_tons == 0:
            return None

        # Compute mode shares (by ton-miles)
        truck_share = (modes.get(1, {}).get("tmiles_m", 0) / total_tmiles * 100) if total_tmiles > 0 else 0
        rail_share = (modes.get(2, {}).get("tmiles_m", 0) / total_tmiles * 100) if total_tmiles > 0 else 0
        air_share = (modes.get(4, {}).get("tmiles_m", 0) / total_tmiles * 100) if total_tmiles > 0 else 0
        water_share = (modes.get(3, {}).get("tmiles_m", 0) / total_tmiles * 100) if total_tmiles > 0 else 0
        multi_share = (modes.get(5, {}).get("tmiles_m", 0) / total_tmiles * 100) if total_tmiles > 0 else 0

        avg_cost_per_tm = total_cost / (total_tmiles * 1_000_000) if total_tmiles > 0 else 0
        value_per_ton = (total_value * 1_000_000) / (total_tons * 1_000) if total_tons > 0 else 0
        tmiles_per_ton = (total_tmiles * 1_000_000) / (total_tons * 1_000) if total_tons > 0 else 0

        kpi = {
            "period_year": year,
            "scope": scope,
            "total_tons": total_tons * 1_000,  # convert from thousands
            "total_value_usd": total_value * 1_000_000,
            "total_ton_miles": total_tmiles * 1_000_000,
            "truck_share_pct": round(truck_share, 2),
            "rail_share_pct": round(rail_share, 2),
            "air_share_pct": round(air_share, 2),
            "water_share_pct": round(water_share, 2),
            "multi_share_pct": round(multi_share, 2),
            "avg_cost_per_ton_mile": round(avg_cost_per_tm, 4),
            "total_estimated_cost": round(total_cost, 2),
            "value_per_ton": round(value_per_ton, 2),
            "ton_miles_per_ton": round(tmiles_per_ton, 2),
        }

        # Upsert into freight_kpis
        await session.execute(text("""
            INSERT INTO freight_kpis
                (period_year, scope, total_tons, total_value_usd, total_ton_miles,
                 truck_share_pct, rail_share_pct, air_share_pct, water_share_pct,
                 multi_share_pct, avg_cost_per_ton_mile, total_estimated_cost,
                 value_per_ton, ton_miles_per_ton)
            VALUES
                (:period_year, :scope, :total_tons, :total_value_usd, :total_ton_miles,
                 :truck_share_pct, :rail_share_pct, :air_share_pct, :water_share_pct,
                 :multi_share_pct, :avg_cost_per_ton_mile, :total_estimated_cost,
                 :value_per_ton, :ton_miles_per_ton)
            ON CONFLICT (period_year, scope) DO UPDATE SET
                total_tons = EXCLUDED.total_tons,
                total_value_usd = EXCLUDED.total_value_usd,
                total_ton_miles = EXCLUDED.total_ton_miles,
                truck_share_pct = EXCLUDED.truck_share_pct,
                rail_share_pct = EXCLUDED.rail_share_pct,
                air_share_pct = EXCLUDED.air_share_pct,
                water_share_pct = EXCLUDED.water_share_pct,
                multi_share_pct = EXCLUDED.multi_share_pct,
                avg_cost_per_ton_mile = EXCLUDED.avg_cost_per_ton_mile,
                total_estimated_cost = EXCLUDED.total_estimated_cost,
                value_per_ton = EXCLUDED.value_per_ton,
                ton_miles_per_ton = EXCLUDED.ton_miles_per_ton
        """), kpi)
        await session.commit()

        logger.info("Computed freight KPIs for %d (%s): %.1fM tons, truck %.1f%%",
                     year, scope, total_tons * 1_000 / 1_000_000, truck_share)
        return kpi
