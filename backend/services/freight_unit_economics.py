"""Freight unit economics: cost breakdown per ton-mile.

Computes the component-level cost breakdown (fuel, labor, equipment,
insurance, tolls, other) for the freight network, weighted by mode share.
"""

import logging

from sqlalchemy import text

from db.session import AsyncSessionLocal
from services.freight_cost_model import BASE_RATES, get_rate, get_cost_breakdown

logger = logging.getLogger(__name__)


async def compute_freight_unit_economics(
    year: int,
    scope: str = "national",
) -> dict | None:
    """Compute weighted-average cost breakdown per ton-mile.

    Weights each mode's cost breakdown by its share of total ton-miles,
    producing a blended cost-per-ton-mile with component detail.
    """
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
        result = await session.execute(text(f"""
            SELECT
                ff.mode_code,
                SUM(ff.ton_miles_millions) AS tmiles_m
            FROM freight_flows ff
            {corridor_join}
            WHERE ff.year = :year
              {corridor_where}
            GROUP BY ff.mode_code
        """), {"year": year, "corridor_name": scope.split(":", 1)[1] if ":" in scope else None})

        total_tmiles = 0
        mode_tmiles = {}
        for row in result.mappings():
            mc = row["mode_code"]
            tm = float(row["tmiles_m"] or 0)
            mode_tmiles[mc] = tm
            total_tmiles += tm

        if total_tmiles == 0:
            return None

        # Compute weighted-average cost breakdown
        fuel_cptm = 0
        labor_cptm = 0
        equipment_cptm = 0
        insurance_cptm = 0
        tolls_cptm = 0
        other_cptm = 0

        for mc, tm in mode_tmiles.items():
            weight = tm / total_tmiles
            rate = get_rate(mc)
            breakdown = get_cost_breakdown(mc)

            fuel_cptm += rate * breakdown["fuel"] * weight
            labor_cptm += rate * breakdown["labor"] * weight
            equipment_cptm += rate * breakdown["equipment"] * weight
            insurance_cptm += rate * breakdown["insurance"] * weight
            tolls_cptm += rate * breakdown["tolls_fees"] * weight
            other_cptm += rate * breakdown["other"] * weight

        total_cptm = fuel_cptm + labor_cptm + equipment_cptm + insurance_cptm + tolls_cptm + other_cptm

        # Revenue proxy: value / ton-miles
        val_result = await session.execute(text(f"""
            SELECT
                SUM(ff.value_millions) AS total_value_m,
                SUM(ff.ton_miles_millions) AS total_tmiles_m
            FROM freight_flows ff
            {corridor_join}
            WHERE ff.year = :year
              {corridor_where}
        """), {"year": year, "corridor_name": scope.split(":", 1)[1] if ":" in scope else None})

        val_row = val_result.mappings().first()
        revenue_per_tm = 0
        if val_row and val_row["total_value_m"] and val_row["total_tmiles_m"]:
            total_value = float(val_row["total_value_m"]) * 1_000_000
            total_tm = float(val_row["total_tmiles_m"]) * 1_000_000
            revenue_per_tm = total_value / total_tm if total_tm > 0 else 0

        economics = {
            "year": year,
            "scope": scope,
            "fuel_cost_per_tm": round(fuel_cptm, 6),
            "labor_cost_per_tm": round(labor_cptm, 6),
            "equipment_cost_per_tm": round(equipment_cptm, 6),
            "insurance_cost_per_tm": round(insurance_cptm, 6),
            "tolls_fees_per_tm": round(tolls_cptm, 6),
            "other_cost_per_tm": round(other_cptm, 6),
            "total_cost_per_tm": round(total_cptm, 6),
            "revenue_per_tm": round(revenue_per_tm, 6),
            "margin_per_tm": round(revenue_per_tm - total_cptm, 6),
        }

        # Upsert
        await session.execute(text("""
            INSERT INTO freight_unit_economics
                (year, scope, fuel_cost_per_tm, labor_cost_per_tm, equipment_cost_per_tm,
                 insurance_cost_per_tm, tolls_fees_per_tm, other_cost_per_tm,
                 total_cost_per_tm, revenue_per_tm, margin_per_tm)
            VALUES
                (:year, :scope, :fuel_cost_per_tm, :labor_cost_per_tm, :equipment_cost_per_tm,
                 :insurance_cost_per_tm, :tolls_fees_per_tm, :other_cost_per_tm,
                 :total_cost_per_tm, :revenue_per_tm, :margin_per_tm)
            ON CONFLICT (year, scope) DO UPDATE SET
                fuel_cost_per_tm = EXCLUDED.fuel_cost_per_tm,
                labor_cost_per_tm = EXCLUDED.labor_cost_per_tm,
                equipment_cost_per_tm = EXCLUDED.equipment_cost_per_tm,
                insurance_cost_per_tm = EXCLUDED.insurance_cost_per_tm,
                tolls_fees_per_tm = EXCLUDED.tolls_fees_per_tm,
                other_cost_per_tm = EXCLUDED.other_cost_per_tm,
                total_cost_per_tm = EXCLUDED.total_cost_per_tm,
                revenue_per_tm = EXCLUDED.revenue_per_tm,
                margin_per_tm = EXCLUDED.margin_per_tm
        """), economics)
        await session.commit()

        logger.info("Unit economics for %d (%s): $%.4f/ton-mile", year, scope, total_cptm)
        return economics
