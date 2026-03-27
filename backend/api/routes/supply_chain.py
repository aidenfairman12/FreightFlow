"""Supply chain analysis endpoints: trace precursor materials to finished goods."""

from typing import Any

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from services.commodity_dependencies import FINISHED_GOODS, get_finished_goods_list
from services.freight_cost_model import estimate_flow_cost

router = APIRouter()


@router.get("/finished-goods")
async def list_finished_goods() -> dict[str, Any]:
    """Return the curated list of finished goods with precursor mappings."""
    return {
        "data": get_finished_goods_list(),
        "error": None,
        "meta": {"count": len(FINISHED_GOODS)},
    }


@router.get("/assembly-zones")
async def list_assembly_zones(
    finished_good: str = Query(..., description="SCTG2 code of the finished good"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return FAF zones that receive precursor flows for a finished good.

    Filters to zones with meaningful inbound flow volume, ranked by total tonnage.
    """
    fg = FINISHED_GOODS.get(finished_good)
    if not fg:
        raise HTTPException(status_code=404, detail=f"Unknown finished good: {finished_good}")

    precursor_codes = [p["sctg2"] for p in fg["precursors"]]

    result = await db.execute(text("""
        SELECT
            ff.dest_zone_id AS zone_id,
            z.zone_name,
            z.state_name,
            z.latitude,
            z.longitude,
            SUM(ff.tons_thousands) AS total_tons_k
        FROM freight_flows ff
        JOIN faf_zones z ON ff.dest_zone_id = z.zone_id
        WHERE ff.sctg2 = ANY(:precursor_codes)
          AND ff.year = 2022
          AND ff.tons_thousands > 0
        GROUP BY ff.dest_zone_id, z.zone_name, z.state_name, z.latitude, z.longitude
        HAVING SUM(ff.tons_thousands) > 10
        ORDER BY total_tons_k DESC
        LIMIT 30
    """), {"precursor_codes": precursor_codes})

    zones = [dict(r) for r in result.mappings()]
    return {
        "data": zones,
        "error": None,
        "meta": {"finished_good": finished_good, "count": len(zones)},
    }


@router.get("/analyze")
async def analyze_supply_chain(
    finished_good: str = Query(..., description="SCTG2 code of the finished good"),
    assembly_zone: int = Query(..., description="FAF zone ID of assembly location"),
    year: int = Query(2022),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Analyze the inbound supply chain for a finished good at an assembly zone.

    For each precursor material, queries all inbound freight flows to the assembly zone,
    estimates costs, and aggregates by source zone and transport mode.
    """
    fg = FINISHED_GOODS.get(finished_good)
    if not fg:
        raise HTTPException(status_code=404, detail=f"Unknown finished good: {finished_good}")

    # Fetch assembly zone info
    zone_result = await db.execute(text(
        "SELECT zone_id, zone_name, state_name, latitude, longitude FROM faf_zones WHERE zone_id = :zid"
    ), {"zid": assembly_zone})
    zone_row = zone_result.mappings().first()
    if not zone_row:
        raise HTTPException(status_code=404, detail=f"Unknown zone: {assembly_zone}")

    assembly_zone_info = dict(zone_row)

    # Analyze each precursor
    precursors_result = []
    grand_tons_k = 0.0
    grand_value_m = 0.0
    grand_tmiles_m = 0.0
    grand_cost = 0.0
    grand_cost_components: dict[str, float] = {
        "fuel": 0, "labor": 0, "equipment": 0,
        "insurance": 0, "tolls_fees": 0, "other": 0,
    }
    grand_mode_tons: dict[str, float] = {}
    all_source_zone_ids: set[int] = set()

    for precursor in fg["precursors"]:
        result = await db.execute(text("""
            SELECT
                ff.origin_zone_id,
                oz.zone_name AS origin_name,
                oz.latitude,
                oz.longitude,
                ff.mode_code,
                ff.mode_name,
                SUM(ff.tons_thousands)      AS tons_k,
                SUM(ff.value_millions)      AS value_m,
                SUM(ff.ton_miles_millions)  AS tmiles_m
            FROM freight_flows ff
            LEFT JOIN faf_zones oz ON ff.origin_zone_id = oz.zone_id
            WHERE ff.sctg2 = :precursor_sctg2
              AND ff.dest_zone_id = :assembly_zone
              AND ff.year = :year
            GROUP BY ff.origin_zone_id, oz.zone_name, oz.latitude, oz.longitude,
                     ff.mode_code, ff.mode_name
            ORDER BY tons_k DESC NULLS LAST
        """), {
            "precursor_sctg2": precursor["sctg2"],
            "assembly_zone": assembly_zone,
            "year": year,
        })
        rows = [dict(r) for r in result.mappings()]

        # Aggregate by source zone
        source_map: dict[int, dict[str, Any]] = {}
        prec_tons_k = 0.0
        prec_value_m = 0.0
        prec_tmiles_m = 0.0
        prec_cost = 0.0
        prec_cost_components: dict[str, float] = {
            "fuel": 0, "labor": 0, "equipment": 0,
            "insurance": 0, "tolls_fees": 0, "other": 0,
        }
        prec_mode_tons: dict[str, float] = {}

        for row in rows:
            oid = row["origin_zone_id"]
            tons_k = row["tons_k"] or 0
            value_m = row["value_m"] or 0
            tmiles_m = row["tmiles_m"] or 0

            cost_info = estimate_flow_cost(tons_k, tmiles_m, row["mode_code"])
            cost_usd = cost_info["total_cost_usd"]

            prec_tons_k += tons_k
            prec_value_m += value_m
            prec_tmiles_m += tmiles_m
            prec_cost += cost_usd

            # Accumulate cost components
            for comp, val in cost_info["components"].items():
                prec_cost_components[comp] = prec_cost_components.get(comp, 0) + val

            # Mode tracking
            mode_name = row["mode_name"]
            prec_mode_tons[mode_name] = prec_mode_tons.get(mode_name, 0) + tons_k
            grand_mode_tons[mode_name] = grand_mode_tons.get(mode_name, 0) + tons_k

            all_source_zone_ids.add(oid)

            if oid not in source_map:
                source_map[oid] = {
                    "zone_id": oid,
                    "zone_name": row["origin_name"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "tons_k": 0,
                    "value_m": 0,
                    "ton_miles_m": 0,
                    "estimated_cost": 0,
                    "primary_mode": None,
                    "primary_mode_tons": 0,
                    "modes": [],
                }

            s = source_map[oid]
            s["tons_k"] += tons_k
            s["value_m"] += value_m
            s["ton_miles_m"] += tmiles_m
            s["estimated_cost"] += cost_usd
            s["modes"].append({
                "mode_name": mode_name,
                "mode_code": row["mode_code"],
                "tons_k": tons_k,
                "cost": cost_usd,
                "cost_per_ton_mile": cost_info["cost_per_ton_mile"],
            })
            if tons_k > s["primary_mode_tons"]:
                s["primary_mode"] = mode_name
                s["primary_mode_tons"] = tons_k

        # Build source list (top 8 by tonnage)
        sources = sorted(source_map.values(), key=lambda x: x["tons_k"], reverse=True)[:8]
        for s in sources:
            del s["primary_mode_tons"]

        # Mode split for this precursor
        mode_split = [
            {"mode_name": m, "tons_k": round(t, 2), "pct": round(t / prec_tons_k * 100, 1) if prec_tons_k else 0}
            for m, t in sorted(prec_mode_tons.items(), key=lambda x: x[1], reverse=True)
        ]

        grand_tons_k += prec_tons_k
        grand_value_m += prec_value_m
        grand_tmiles_m += prec_tmiles_m
        grand_cost += prec_cost
        for comp, val in prec_cost_components.items():
            grand_cost_components[comp] = grand_cost_components.get(comp, 0) + val

        precursors_result.append({
            "sctg2": precursor["sctg2"],
            "name": precursor["name"],
            "role": precursor["role"],
            "input_ratio": precursor["ratio"],
            "total_tons_k": round(prec_tons_k, 2),
            "total_value_m": round(prec_value_m, 2),
            "total_ton_miles_m": round(prec_tmiles_m, 2),
            "total_cost_usd": round(prec_cost, 2),
            "num_sources": len(source_map),
            "primary_mode": max(prec_mode_tons, key=prec_mode_tons.get) if prec_mode_tons else None,
            "mode_split": mode_split,
            "top_sources": sources,
            "cost_breakdown": {k: round(v, 2) for k, v in prec_cost_components.items()},
        })

    # Grand totals
    grand_mode_split = [
        {"mode_name": m, "tons_k": round(t, 2), "pct": round(t / grand_tons_k * 100, 1) if grand_tons_k else 0}
        for m, t in sorted(grand_mode_tons.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "data": {
            "finished_good": {
                "sctg2": finished_good,
                "name": fg["name"],
                "description": fg["description"],
            },
            "assembly_zone": assembly_zone_info,
            "year": year,
            "precursors": precursors_result,
            "totals": {
                "total_tons_k": round(grand_tons_k, 2),
                "total_value_m": round(grand_value_m, 2),
                "total_ton_miles_m": round(grand_tmiles_m, 2),
                "total_cost_usd": round(grand_cost, 2),
                "num_source_zones": len(all_source_zone_ids),
                "mode_split": grand_mode_split,
                "cost_breakdown": {k: round(v, 2) for k, v in grand_cost_components.items()},
            },
        },
        "error": None,
        "meta": {"finished_good": finished_good, "assembly_zone": assembly_zone, "year": year},
    }
