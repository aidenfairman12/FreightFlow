"""Commodity tracking endpoints: trace a commodity through the freight network."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from services.freight_cost_model import estimate_flow_cost

router = APIRouter()


@router.get("/commodities")
async def list_commodities(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List all SCTG commodity codes."""
    result = await db.execute(text(
        "SELECT sctg2, commodity_name FROM commodities ORDER BY sctg2"
    ))
    rows = [dict(r) for r in result.mappings()]
    return {"data": rows, "error": None, "meta": {"count": len(rows)}}


@router.get("/summary")
async def tracking_summary(
    commodity: str = Query(..., description="SCTG2 commodity code"),
    origin: int = Query(..., description="Origin FAF zone ID"),
    year: int = Query(2022),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Trace a commodity from an origin zone to all destinations.

    Returns aggregated flows grouped by destination and mode, with cost estimates.
    """
    # Fetch flows grouped by destination + mode
    result = await db.execute(text("""
        SELECT
            ff.dest_zone_id,
            dz.zone_name AS dest_name,
            dz.latitude,
            dz.longitude,
            ff.mode_code,
            ff.mode_name,
            SUM(ff.tons_thousands)      AS tons_k,
            SUM(ff.value_millions)      AS value_m,
            SUM(ff.ton_miles_millions)  AS tmiles_m
        FROM freight_flows ff
        LEFT JOIN faf_zones dz ON ff.dest_zone_id = dz.zone_id
        WHERE ff.sctg2 = :commodity
          AND ff.origin_zone_id = :origin
          AND ff.year = :year
        GROUP BY ff.dest_zone_id, dz.zone_name, dz.latitude, dz.longitude,
                 ff.mode_code, ff.mode_name
        ORDER BY tons_k DESC NULLS LAST
    """), {"commodity": commodity, "origin": origin, "year": year})
    rows = [dict(r) for r in result.mappings()]

    if not rows:
        return {
            "data": {"summary": None, "destinations": []},
            "error": None,
            "meta": {"commodity": commodity, "origin": origin, "year": year},
        }

    # Aggregate by destination (combine modes)
    dest_map: dict[int, dict[str, Any]] = {}
    total_tons_k = 0.0
    total_value_m = 0.0
    total_tmiles_m = 0.0
    total_cost = 0.0
    mode_tons: dict[str, float] = {}

    for row in rows:
        did = row["dest_zone_id"]
        tons_k = row["tons_k"] or 0
        value_m = row["value_m"] or 0
        tmiles_m = row["tmiles_m"] or 0

        # Cost estimate for this mode-flow
        cost_info = estimate_flow_cost(tons_k, tmiles_m, row["mode_code"])

        total_tons_k += tons_k
        total_value_m += value_m
        total_tmiles_m += tmiles_m
        total_cost += cost_info["total_cost_usd"]

        # Mode split tracking
        mode_name = row["mode_name"]
        mode_tons[mode_name] = mode_tons.get(mode_name, 0) + tons_k

        if did not in dest_map:
            dest_map[did] = {
                "dest_zone_id": did,
                "dest_name": row["dest_name"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "total_tons_k": 0,
                "total_value_m": 0,
                "total_ton_miles_m": 0,
                "estimated_cost": 0,
                "primary_mode": None,
                "primary_mode_tons": 0,
                "modes": [],
            }

        d = dest_map[did]
        d["total_tons_k"] += tons_k
        d["total_value_m"] += value_m
        d["total_ton_miles_m"] += tmiles_m
        d["estimated_cost"] += cost_info["total_cost_usd"]
        d["modes"].append({
            "mode_name": mode_name,
            "mode_code": row["mode_code"],
            "tons_k": tons_k,
            "value_m": value_m,
            "cost": cost_info["total_cost_usd"],
            "cost_per_ton_mile": cost_info["cost_per_ton_mile"],
        })

        if tons_k > d["primary_mode_tons"]:
            d["primary_mode"] = mode_name
            d["primary_mode_tons"] = tons_k

    # Build destinations list sorted by tonnage
    destinations = sorted(dest_map.values(), key=lambda x: x["total_tons_k"], reverse=True)
    for d in destinations:
        del d["primary_mode_tons"]

    # Mode split percentages
    mode_split = [
        {"mode_name": m, "tons_k": t, "pct": round(t / total_tons_k * 100, 1) if total_tons_k else 0}
        for m, t in sorted(mode_tons.items(), key=lambda x: x[1], reverse=True)
    ]

    summary = {
        "total_tons_k": round(total_tons_k, 2),
        "total_value_m": round(total_value_m, 2),
        "total_ton_miles_m": round(total_tmiles_m, 2),
        "total_estimated_cost": round(total_cost, 2),
        "num_destinations": len(destinations),
        "mode_split": mode_split,
    }

    return {
        "data": {"summary": summary, "destinations": destinations},
        "error": None,
        "meta": {"commodity": commodity, "origin": origin, "year": year},
    }
