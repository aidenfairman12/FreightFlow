import logging
import sys
from contextlib import asynccontextmanager

# Configure app-level logging (uvicorn only configures its own loggers)
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:     %(name)s - %(message)s",
    stream=sys.stdout,
)

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import flights, analytics, kpi, economics, predictions, scenarios, schedule
from api.websocket import websocket_router, broadcast
from config import settings
from services.enrichment import lookup_airline, get_aircraft_type, schedule_type_fetch
from services.fuel_model import estimate_for_sv
from services.opensky import fetch_swiss_states, validate_credentials
from services.persistence import insert_state_vectors
from services.redis_cache import cache_flights
from services import route_cache
from services import swiss_routes
from services.opensky_credits import get_usage as get_credit_usage
from services.flight_aggregator import aggregate_completed_flights
from services.kpi_aggregator import compute_current_week_kpis
from services.economic_etl import run_economic_etl, validate_eia_key
from services.unit_economics import compute_unit_economics
from services.schedule_imputation import run_imputation_cycle
from services.route_performance import compute_route_performance

logger = logging.getLogger(__name__)

_opensky_enabled = False
_eia_enabled = False


async def _poll_opensky() -> None:
    try:
        flights_data = await fetch_swiss_states()

        enriched = []
        for sv in flights_data:
            origin, destination = route_cache.get_route(sv.icao24, sv.callsign)
            route_cache.schedule_fetch(sv.icao24, sv.callsign)
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

        await insert_state_vectors(enriched)
        if not settings.collect_mode:
            await cache_flights(enriched)
            await broadcast({
                "type": "flight_update",
                "data": [f.model_dump(mode="json") for f in enriched],
            })
        logger.info("Polled %d SWISS flights%s", len(enriched),
                     " (collect mode)" if settings.collect_mode else "")
    except Exception:
        logger.exception("OpenSky poll failed")


async def _periodic_aggregation() -> None:
    """Run flight aggregation and KPI computation (every 5 minutes)."""
    try:
        await aggregate_completed_flights()
    except Exception:
        logger.exception("Flight aggregation failed")


async def _weekly_kpi_job() -> None:
    """Compute SWISS operational KPIs for the current week (every hour)."""
    try:
        kpis = await compute_current_week_kpis()
        if kpis:
            # Chain: compute unit economics after KPIs are ready
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            start = now - timedelta(days=now.weekday(), hours=now.hour,
                                    minutes=now.minute, seconds=now.second)
            await compute_unit_economics(start, now, "weekly")
    except Exception:
        logger.exception("Weekly KPI computation failed")


async def _daily_economic_etl() -> None:
    """Fetch external economic data (every 6 hours)."""
    try:
        await run_economic_etl()
    except Exception:
        logger.exception("Economic ETL failed")


async def _schedule_imputation_job() -> None:
    """Learn schedule patterns and reconcile imputed flights (every hour)."""
    try:
        await run_imputation_cycle()
    except Exception:
        logger.exception("Schedule imputation failed")


async def _route_performance_job() -> None:
    """Compute route performance baselines vs actuals (every hour)."""
    try:
        await compute_route_performance()
    except Exception:
        logger.exception("Route performance computation failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _opensky_enabled, _eia_enabled

    # Validate API keys before starting scheduled jobs
    _opensky_enabled = await validate_credentials()
    _eia_enabled = await validate_eia_key()

    # Bootstrap route database from AirLabs if API key is configured
    if settings.airlabs_api_key:
        count = await swiss_routes.fetch_routes_from_airlabs()
        logger.info("AirLabs bootstrap: %d routes loaded", count)

    if settings.collect_mode:
        logger.info("=== COLLECT MODE — data collection only, heavy compute disabled ===")

    scheduler = AsyncIOScheduler()
    if _opensky_enabled:
        poll_interval = settings.poll_interval_seconds
        if settings.collect_mode and poll_interval < 60:
            poll_interval = 60  # save API credits in collect mode
        scheduler.add_job(_poll_opensky, "interval", seconds=poll_interval)
        logger.info("OpenSky polling every %ds", poll_interval)
    else:
        logger.warning("OpenSky polling DISABLED — fix credentials and restart")
    # Flight aggregation — always on (lightweight)
    scheduler.add_job(_periodic_aggregation, "interval", minutes=5)
    # Schedule imputation — always on (learns from flights, reconciles on resume)
    scheduler.add_job(_schedule_imputation_job, "interval", hours=1)
    if not settings.collect_mode:
        # Phase 5: KPI computation
        scheduler.add_job(_weekly_kpi_job, "interval", hours=1)
        # Phase 6: Economic data
        scheduler.add_job(_daily_economic_etl, "interval", hours=6)
        # Route performance analysis
        scheduler.add_job(_route_performance_job, "interval", hours=1)
    else:
        logger.info("Skipping KPI, economics, route performance, and unit economics jobs")
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="PlaneLogistics API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(flights.router, prefix="/flights", tags=["flights"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(kpi.router, prefix="/kpi", tags=["kpi"])
app.include_router(economics.router, prefix="/economics", tags=["economics"])
app.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
app.include_router(scenarios.router, prefix="/scenarios", tags=["scenarios"])
app.include_router(schedule.router, prefix="/schedule", tags=["schedule"])
app.include_router(websocket_router, tags=["websocket"])


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mode": "collect" if settings.collect_mode else "full",
        "opensky": "active" if _opensky_enabled else "disabled — check credentials",
        "opensky_credits": get_credit_usage(),
        "eia": "active" if _eia_enabled else "disabled — check EIA_API_KEY",
        "routes": swiss_routes.get_cache_stats(),
    }
