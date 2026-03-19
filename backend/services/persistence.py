from sqlalchemy import text

from db.session import AsyncSessionLocal
from models.state_vector import StateVector


async def insert_state_vectors(state_vectors: list[StateVector]) -> None:
    if not state_vectors:
        return
    rows = [
        {
            "time": sv.last_contact,
            "icao24": sv.icao24,
            "callsign": sv.callsign,
            "latitude": sv.latitude,
            "longitude": sv.longitude,
            "baro_altitude": sv.baro_altitude,
            "velocity": sv.velocity,
            "heading": sv.heading,
            "vertical_rate": sv.vertical_rate,
            "on_ground": sv.on_ground,
            "fuel_flow_kg_s": sv.fuel_flow_kg_s,
            "co2_kg_s": sv.co2_kg_s,
        }
        for sv in state_vectors
    ]
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("""
                INSERT INTO state_vectors
                  (time, icao24, callsign, latitude, longitude, baro_altitude,
                   velocity, heading, vertical_rate, on_ground,
                   fuel_flow_kg_s, co2_kg_s)
                VALUES
                  (:time, :icao24, :callsign, :latitude, :longitude,
                   :baro_altitude, :velocity, :heading, :vertical_rate,
                   :on_ground, :fuel_flow_kg_s, :co2_kg_s)
                ON CONFLICT DO NOTHING
            """),
            rows,
        )
        await session.commit()
