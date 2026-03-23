"""External economic data ETL pipeline for freight cost drivers.

Fetches publicly available data:
- EIA on-highway diesel price — requires EIA_API_KEY
- Brent crude price — via EIA
- FRED Freight Transportation Services Index (TSI) — free, no key
"""

import logging
from datetime import date

import httpx
from sqlalchemy import text

from config import settings
from db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def _upsert_factor(
    factor_date: date, factor_name: str, value: float,
    unit: str, source: str,
) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(text("""
            INSERT INTO economic_factors (date, factor_name, value, unit, source)
            VALUES (:date, :name, :value, :unit, :source)
            ON CONFLICT (date, factor_name)
            DO UPDATE SET value = EXCLUDED.value, unit = EXCLUDED.unit, source = EXCLUDED.source
        """), {"date": factor_date, "name": factor_name, "value": value,
               "unit": unit, "source": source})
        await session.commit()


# ── EIA Diesel & Crude Oil ──────────────────────────────────────────────────

EIA_API_BASE = "https://api.eia.gov/v2"
_eia_validated = False

EIA_SERIES = {
    "diesel_usd_gal": {
        "route": "/petroleum/pri/gnd/data/",
        "series": "EMD_EPD2D_PTE_NUS_DPG",
        "unit": "USD/gal",
    },
    "brent_crude_usd_bbl": {
        "route": "/petroleum/pri/spt/data/",
        "series": "RBRTE",
        "unit": "USD/bbl",
    },
}


async def validate_eia_key() -> bool:
    """Test EIA API key at startup. Returns True if valid."""
    global _eia_validated
    api_key = settings.eia_api_key
    if not api_key:
        logger.warning(
            "EIA_API_KEY not set — diesel and crude oil prices will be unavailable. "
            "Register for a free key at https://www.eia.gov/opendata/register.php"
        )
        return False
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{EIA_API_BASE}/petroleum/pri/spt/data/",
                params={"api_key": api_key, "length": 1},
            )
            if resp.status_code == 403:
                logger.error("EIA API key is invalid (HTTP 403). Check EIA_API_KEY in .env.")
                return False
            if resp.status_code >= 500:
                logger.warning("EIA API returned %d — will retry on next ETL cycle", resp.status_code)
                _eia_validated = True
                return True
            resp.raise_for_status()
            _eia_validated = True
            logger.info("EIA API key validated successfully")
            return True
    except (httpx.ConnectError, httpx.TimeoutException):
        logger.warning("Cannot reach EIA API — will retry on next ETL cycle")
        _eia_validated = True
        return True
    except Exception:
        logger.exception("Unexpected error validating EIA API key")
        return False


async def fetch_eia_prices() -> None:
    """Fetch diesel and Brent crude prices from EIA API."""
    api_key = settings.eia_api_key
    if not api_key:
        return

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            for factor_name, cfg in EIA_SERIES.items():
                params = {
                    "api_key": api_key,
                    "frequency": "weekly" if "gnd" in cfg["route"] else "daily",
                    "data[0]": "value",
                    "facets[series][]": cfg["series"],
                    "sort[0][column]": "period",
                    "sort[0][direction]": "desc",
                    "length": 5,
                }
                resp = await client.get(f"{EIA_API_BASE}{cfg['route']}", params=params)
                resp.raise_for_status()
                data = resp.json()

                for row in data.get("response", {}).get("data", []):
                    period = row.get("period")
                    value = row.get("value")
                    if period and value is not None:
                        await _upsert_factor(
                            date.fromisoformat(period), factor_name,
                            float(value), cfg["unit"], "EIA",
                        )
                logger.info("EIA %s: fetched %d data points", factor_name,
                            len(data.get("response", {}).get("data", [])))
    except Exception:
        logger.exception("EIA price fetch failed")


# ── FRED Freight Transportation Services Index ────────────────────────────

FRED_API_BASE = "https://api.stlouisfed.org/fred/series/observations"


async def fetch_freight_tsi() -> None:
    """Fetch Freight Transportation Services Index from FRED (requires free API key)."""
    api_key = settings.fred_api_key
    if not api_key:
        logger.warning(
            "FRED_API_KEY not set — freight TSI will be unavailable. "
            "Register for a free key at https://fred.stlouisfed.org/docs/api/api_key.html"
        )
        return
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.get(
                FRED_API_BASE,
                params={
                    "series_id": "TSIFRGHT",
                    "api_key": api_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 5,
                },
            )
            if resp.status_code != 200:
                logger.warning("FRED TSI fetch returned %d, skipping", resp.status_code)
                return

            data = resp.json()
            for obs in data.get("observations", []):
                obs_date = obs.get("date")
                value = obs.get("value")
                if obs_date and value and value != ".":
                    await _upsert_factor(
                        date.fromisoformat(obs_date), "freight_tsi",
                        float(value), "index", "FRED (TSIFRGHT)",
                    )
            logger.info("FRED freight TSI: fetched %d observations",
                        len(data.get("observations", [])))
    except Exception:
        logger.exception("FRED freight TSI fetch failed")


# ── Orchestrator ─────────────────────────────────────────────────────────────

async def run_economic_etl() -> None:
    """Run all economic data fetchers."""
    logger.info("Running economic ETL pipeline")
    await fetch_eia_prices()
    await fetch_freight_tsi()
    logger.info("Economic ETL complete")


async def get_latest_factors() -> dict:
    """Return the most recent value for each tracked economic factor."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT DISTINCT ON (factor_name)
                factor_name, value, unit, source, date
            FROM economic_factors
            ORDER BY factor_name, date DESC
        """))
        factors = {}
        for row in result.mappings():
            factors[row["factor_name"]] = {
                "value": row["value"],
                "unit": row["unit"],
                "source": row["source"],
                "date": row["date"].isoformat() if row["date"] else None,
            }
        return factors


async def get_factor_history(
    factor_name: str, days: int = 90,
) -> list[dict]:
    """Return time series for a specific economic factor."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT date, value, unit, source
            FROM economic_factors
            WHERE factor_name = :name
              AND date >= CURRENT_DATE - :days * INTERVAL '1 day'
            ORDER BY date ASC
        """), {"name": factor_name, "days": days})
        return [dict(row) for row in result.mappings()]
