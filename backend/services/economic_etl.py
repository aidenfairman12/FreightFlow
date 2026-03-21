"""
Phase 6: External economic data ETL pipeline.

Fetches publicly available cost and revenue drivers:
- ECB exchange rates (EUR/CHF, USD/CHF) — free, no key
- EIA jet fuel price — requires EIA_API_KEY
- Brent crude price — via EIA
- EU ETS carbon price — placeholder (manual or Ember API)

Each fetcher stores results in the economic_factors table.
"""

import logging
from datetime import date, timedelta
from xml.etree import ElementTree

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


# ── ECB Exchange Rates ───────────────────────────────────────────────────────

ECB_DAILY_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
ECB_NS = {"gesmes": "http://www.gesmes.org/xml/2002-08-01",
           "ecb": "http://www.ecb.int/vocabulary/2002-08-01/euref"}


async def fetch_ecb_exchange_rates() -> dict[str, float]:
    """Fetch latest ECB reference rates. Returns {currency: rate_vs_EUR}."""
    rates = {}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(ECB_DAILY_URL)
            resp.raise_for_status()

        root = ElementTree.fromstring(resp.text)
        cube = root.find(".//ecb:Cube/ecb:Cube", ECB_NS)
        if cube is None:
            logger.warning("ECB XML: could not find Cube element")
            return rates

        ref_date = date.fromisoformat(cube.attrib["time"])
        for rate in cube.findall("ecb:Cube", ECB_NS):
            currency = rate.attrib["currency"]
            value = float(rate.attrib["rate"])
            rates[currency] = value

        # Store key rates
        if "CHF" in rates:
            await _upsert_factor(ref_date, "eur_chf", rates["CHF"], "CHF/EUR", "ECB")
        if "USD" in rates and "CHF" in rates:
            usd_chf = rates["CHF"] / rates["USD"]
            await _upsert_factor(ref_date, "usd_chf", usd_chf, "CHF/USD", "ECB (derived)")

        logger.info("ECB rates fetched for %s: CHF=%.4f", ref_date, rates.get("CHF", 0))
    except Exception:
        logger.exception("ECB exchange rate fetch failed")
    return rates


# ── EIA Jet Fuel & Crude Oil ─────────────────────────────────────────────────

EIA_API_BASE = "https://api.eia.gov/v2"
_eia_validated = False
# Series IDs: RJETC (jet fuel US Gulf Coast), RBRTE (Brent spot)
EIA_SERIES = {
    "jet_fuel_usd_gal": {"route": "/petroleum/pri/spt/data/", "series": "RJETC", "unit": "USD/gal"},
    "brent_crude_usd_bbl": {"route": "/petroleum/pri/spt/data/", "series": "RBRTE", "unit": "USD/bbl"},
}


async def validate_eia_key() -> bool:
    """Test EIA API key at startup. Returns True if valid."""
    global _eia_validated
    api_key = settings.eia_api_key
    if not api_key:
        logger.warning(
            "EIA_API_KEY not set — jet fuel and crude oil prices will be unavailable. "
            "Register for a free key at https://www.eia.gov/opendata/register.php"
        )
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{EIA_API_BASE}/petroleum/pri/spt/data/",
                params={"api_key": api_key, "length": 1},
            )
            if resp.status_code == 403:
                logger.error("EIA API key is invalid (HTTP 403). Check EIA_API_KEY in .env.")
                return False
            resp.raise_for_status()
            _eia_validated = True
            logger.info("EIA API key validated successfully")
            return True
    except httpx.ConnectError:
        logger.warning("Cannot reach EIA API — will retry on next ETL cycle")
        _eia_validated = True  # allow, will retry
        return True
    except Exception:
        logger.exception("Unexpected error validating EIA API key")
        return False


async def fetch_eia_prices() -> None:
    """Fetch jet fuel and Brent crude prices from EIA API."""
    api_key = settings.eia_api_key
    if not api_key:
        return

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            for factor_name, cfg in EIA_SERIES.items():
                params = {
                    "api_key": api_key,
                    "frequency": "daily",
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


# ── EU ETS Carbon Price ──────────────────────────────────────────────────────

async def fetch_carbon_price() -> None:
    """
    Fetch EU ETS carbon (EUA) price.

    Uses Ember Climate's public data API when available.
    Falls back to a placeholder that can be manually updated.
    """
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Ember's carbon price tracker (public, no key)
            resp = await client.get(
                "https://ember-climate.org/api/carbon-price/",
                headers={"Accept": "application/json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                # Extract latest EU ETS price
                for entry in data if isinstance(data, list) else [data]:
                    if entry.get("scheme") == "EU ETS":
                        price = entry.get("price")
                        price_date = entry.get("date")
                        if price and price_date:
                            await _upsert_factor(
                                date.fromisoformat(price_date[:10]),
                                "eua_eur_ton", float(price), "EUR/tCO2", "Ember",
                            )
                            logger.info("EU ETS carbon price: %.2f EUR/t", price)
                            return

        logger.debug("Carbon price: no data from Ember, using fallback estimate")
        # Fallback: approximate based on recent EUA range (€60-80)
        await _upsert_factor(
            date.today(), "eua_eur_ton", 65.0,
            "EUR/tCO2", "estimate",
        )
    except Exception:
        logger.exception("Carbon price fetch failed")


# ── Orchestrator ─────────────────────────────────────────────────────────────

async def run_economic_etl() -> None:
    """Run all economic data fetchers. Called on schedule (daily)."""
    logger.info("Running economic ETL pipeline")
    await fetch_ecb_exchange_rates()
    await fetch_eia_prices()
    await fetch_carbon_price()
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
