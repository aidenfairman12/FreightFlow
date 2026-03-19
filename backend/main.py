import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import flights, analytics
from api.websocket import websocket_router, broadcast
from config import settings
from services.enrichment import lookup_airline, get_aircraft_type, schedule_type_fetch
from services.fuel_model import estimate_for_sv
from services.opensky import fetch_swiss_states
from services.persistence import insert_state_vectors
from services.redis_cache import cache_flights
from services import route_cache

logger = logging.getLogger(__name__)


async def _poll_opensky() -> None:
    try:
        flights_data = await fetch_swiss_states()

        enriched = []
        for sv in flights_data:
            origin, destination = route_cache.get_route(sv.icao24)
            route_cache.schedule_fetch(sv.icao24)
            aircraft_type = get_aircraft_type(sv.icao24)
            schedule_type_fetch(sv.icao24)
            fuel = None if sv.on_ground else estimate_for_sv(
                aircraft_type, sv.velocity, sv.baro_altitude
            )
            enriched.append(sv.model_copy(update={
                "aircraft_type": aircraft_type,
                "airline_name": lookup_airline(sv.callsign),
                "origin_airport": origin,
                "destination_airport": destination,
                "fuel_flow_kg_s": fuel.fuel_flow_kg_s if fuel else None,
                "co2_kg_s": fuel.co2_kg_s if fuel else None,
            }))

        await cache_flights(enriched)
        await insert_state_vectors(enriched)
        await broadcast({
            "type": "flight_update",
            "data": [f.model_dump(mode="json") for f in enriched],
        })
        logger.info("Broadcast %d flights", len(enriched))
    except Exception:
        logger.exception("OpenSky poll failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(_poll_opensky, "interval", seconds=settings.poll_interval_seconds)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="PlaneLogistics API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(flights.router, prefix="/flights", tags=["flights"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(websocket_router, tags=["websocket"])


@app.get("/health")
async def health():
    return {"status": "ok"}
