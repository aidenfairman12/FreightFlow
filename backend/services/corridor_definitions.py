"""Curated freight corridor definitions.

Defines 3 major US freight corridors for analysis. Each corridor maps to
a set of FAF5 origin and destination zones.
"""

import logging

from sqlalchemy import text

from db.session import AsyncSessionLocal
from services.faf5_zones import _BUILTIN_ZONES

logger = logging.getLogger(__name__)

# Corridor definitions: name, description, origin zone IDs, dest zone IDs, coords
CORRIDORS = [
    {
        "name": "LA - Chicago",
        "description": "Pacific imports to Midwest distribution. The highest-volume "
                       "domestic freight corridor, dominated by intermodal rail and truck.",
        "origin_zones": [61],   # Los Angeles, CA
        "dest_zones": [171],    # Chicago, IL
        "origin_lat": 33.94,
        "origin_lon": -118.24,
        "dest_lat": 41.88,
        "dest_lon": -87.63,
    },
    {
        "name": "Houston - New York",
        "description": "Gulf Coast to Northeast. Petrochemicals, refined products, and "
                       "manufactured goods flow from the Houston port complex to the NYC metro.",
        "origin_zones": [482],  # Houston, TX
        "dest_zones": [361],    # New York, NY
        "origin_lat": 29.76,
        "origin_lon": -95.37,
        "dest_lat": 40.71,
        "dest_lon": -74.01,
    },
    {
        "name": "Seattle - Dallas",
        "description": "Pacific Northwest to Sun Belt. Growing corridor carrying imports "
                       "from Puget Sound ports to the rapidly expanding Texas distribution network.",
        "origin_zones": [531],  # Seattle, WA
        "dest_zones": [481],    # Dallas-Fort Worth, TX
        "origin_lat": 47.61,
        "origin_lon": -122.33,
        "dest_lat": 32.78,
        "dest_lon": -96.80,
    },
]


async def seed_corridors() -> int:
    """Insert corridor definitions into the database. Idempotent via ON CONFLICT.

    Returns the number of corridors seeded.
    """
    async with AsyncSessionLocal() as session:
        count = 0
        for c in CORRIDORS:
            await session.execute(text("""
                INSERT INTO corridors (name, description, origin_zones, dest_zones,
                                       origin_lat, origin_lon, dest_lat, dest_lon)
                VALUES (:name, :desc, :ozones, :dzones, :olat, :olon, :dlat, :dlon)
                ON CONFLICT (name) DO UPDATE SET
                    description = EXCLUDED.description,
                    origin_zones = EXCLUDED.origin_zones,
                    dest_zones = EXCLUDED.dest_zones,
                    origin_lat = EXCLUDED.origin_lat,
                    origin_lon = EXCLUDED.origin_lon,
                    dest_lat = EXCLUDED.dest_lat,
                    dest_lon = EXCLUDED.dest_lon
            """), {
                "name": c["name"],
                "desc": c["description"],
                "ozones": c["origin_zones"],
                "dzones": c["dest_zones"],
                "olat": c["origin_lat"],
                "olon": c["origin_lon"],
                "dlat": c["dest_lat"],
                "dlon": c["dest_lon"],
            })
            count += 1
        await session.commit()
        logger.info("Seeded %d corridors", count)
        return count


async def seed_zones() -> int:
    """Insert FAF zone reference data into the database. Idempotent via ON CONFLICT.

    Returns the number of zones seeded.
    """
    zones = _BUILTIN_ZONES
    async with AsyncSessionLocal() as session:
        count = 0
        for zone_id, info in zones.items():
            await session.execute(text("""
                INSERT INTO faf_zones (zone_id, zone_name, state_name, latitude, longitude, zone_type)
                VALUES (:zid, :name, :state, :lat, :lon, :type)
                ON CONFLICT (zone_id) DO UPDATE SET
                    zone_name = EXCLUDED.zone_name,
                    state_name = EXCLUDED.state_name,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    zone_type = EXCLUDED.zone_type
            """), {
                "zid": zone_id,
                "name": info["name"],
                "state": info["state"],
                "lat": info["lat"],
                "lon": info["lon"],
                "type": info["type"],
            })
            count += 1
        await session.commit()
        logger.info("Seeded %d FAF zones", count)
        return count


async def seed_commodities() -> int:
    """Insert SCTG commodity codes into the database. Idempotent via ON CONFLICT."""
    from services.faf5_zones import COMMODITY_CODES

    async with AsyncSessionLocal() as session:
        count = 0
        for code, name in COMMODITY_CODES.items():
            await session.execute(text("""
                INSERT INTO commodities (sctg2, commodity_name)
                VALUES (:code, :name)
                ON CONFLICT (sctg2) DO UPDATE SET commodity_name = EXCLUDED.commodity_name
            """), {"code": code, "name": name})
            count += 1
        await session.commit()
        logger.info("Seeded %d commodity codes", count)
        return count
