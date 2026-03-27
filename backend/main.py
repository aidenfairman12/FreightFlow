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

from api.routes import economics, flows, tracking, supply_chain
from api.websocket import websocket_router, broadcast
from config import settings
from services.corridor_definitions import seed_corridors, seed_zones, seed_commodities
from services.faf5_loader import load_faf5_data
from services.economic_etl import run_economic_etl, validate_eia_key

logger = logging.getLogger(__name__)


async def _daily_economic_etl() -> None:
    """Fetch external economic data (every 6 hours)."""
    try:
        await run_economic_etl()
    except Exception:
        logger.exception("Economic ETL failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed reference data
    await seed_zones()
    await seed_commodities()
    await seed_corridors()

    # Load FAF5 freight flow data (idempotent — skips if already loaded)
    count = await load_faf5_data()
    if count > 0:
        logger.info("Loaded %d FAF5 freight flow records", count)

    # Validate EIA key and run initial economic data fetch
    await validate_eia_key()
    await run_economic_etl()

    # Scheduled jobs
    scheduler = AsyncIOScheduler()
    scheduler.add_job(_daily_economic_etl, "interval", hours=6)
    scheduler.start()

    logger.info("FreightFlow started")
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="FreightFlow API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(supply_chain.router, prefix="/supply-chain", tags=["supply-chain"])
app.include_router(flows.router, prefix="/flows", tags=["flows"])
app.include_router(economics.router, prefix="/economics", tags=["economics"])
app.include_router(tracking.router, prefix="/tracking", tags=["tracking"])
app.include_router(websocket_router, tags=["websocket"])


@app.get("/health")
async def health():
    return {"status": "ok"}
