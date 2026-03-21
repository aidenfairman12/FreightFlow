"""
SWISS International Air Lines route database with self-learning capability.

Three-tier route resolution:
1. Learned cache — routes discovered from completed flight data (persistent JSON).
   Takes priority over seed data since it reflects actual observed flights.
2. Static seed table — known SWISS flight number -> route mappings.
   Provides immediate coverage before the system has observed any flights.
3. Hub fallback — LSZH for flight numbers <2000, LSGG for 2000+.

Self-learning: when OpenSky returns route data for a completed flight, the
callsign -> route mapping is stored persistently. Next time that callsign
appears, the route is known instantly.

Optional: set AIRLABS_API_KEY for bulk-fetch of all SWISS routes on startup.
Free tier: 1000 requests/month at airlabs.co
"""

import json
import logging
import re
from pathlib import Path

import httpx

from config import settings

logger = logging.getLogger(__name__)

# ── Persistent cache ─────────────────────────────────────────────────────────
CACHE_FILE = Path(__file__).parent.parent / "data" / "learned_routes.json"

# callsign (e.g. "SWR8") -> [origin_icao, destination_icao]
_learned: dict[str, list[str]] = {}


def _load_cache() -> None:
    global _learned
    if CACHE_FILE.exists():
        try:
            _learned = json.loads(CACHE_FILE.read_text())
            logger.info("Loaded %d learned routes from cache", len(_learned))
        except Exception:
            logger.warning("Failed to load route cache, starting fresh")
            _learned = {}


def _save_cache() -> None:
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(_learned, indent=2, sort_keys=True))
    except Exception:
        logger.warning("Failed to save route cache")


# Load cache on module import
_load_cache()

# ── IATA -> ICAO airport code mapping ────────────────────────────────────────
# Used when converting API responses (AirLabs returns IATA codes)
IATA_TO_ICAO: dict[str, str] = {
    # Switzerland
    "ZRH": "LSZH", "GVA": "LSGG",
    # Americas
    "JFK": "KJFK", "EWR": "KEWR", "ORD": "KORD", "LAX": "KLAX",
    "SFO": "KSFO", "MIA": "KMIA", "BOS": "KBOS", "IAD": "KIAD",
    "YUL": "CYUL", "YYZ": "CYYZ",
    "GRU": "SBGR", "EZE": "SAEZ", "BOG": "SKBO",
    # Asia
    "NRT": "RJAA", "HND": "RJTT", "SIN": "WSSS", "BKK": "VTBS",
    "HKG": "VHHH", "PVG": "ZSPD", "PEK": "ZBAA", "ICN": "RKSI",
    "BOM": "VABB", "DEL": "VIDP",
    # Middle East / Africa
    "TLV": "LLBG", "CAI": "HECA", "JNB": "FAOR", "NBO": "HKJK",
    # UK & Ireland
    "LHR": "EGLL", "LCY": "EGLC", "MAN": "EGCC", "EDI": "EGPH",
    "BHX": "EGBB", "DUB": "EIDW",
    # France
    "CDG": "LFPG", "NCE": "LFMN", "LYS": "LFLL", "MRS": "LFML",
    # Benelux
    "AMS": "EHAM", "BRU": "EBBR",
    # Germany
    "FRA": "EDDF", "MUC": "EDDM", "BER": "EDDB", "HAM": "EDDH",
    "DUS": "EDDL",
    # Nordics
    "CPH": "EKCH", "ARN": "ESSA", "OSL": "ENGM", "HEL": "EFHK",
    # Eastern Europe
    "WAW": "EPWA", "PRG": "LKPR", "BUD": "LHBP", "VIE": "LOWW",
    "OTP": "LROP", "BEG": "LYBE", "ZAG": "LDZA", "SOF": "LBSF",
    # Italy
    "FCO": "LIRF", "MXP": "LIMC", "VCE": "LIPZ", "NAP": "LIRN",
    "FLR": "LIRQ",
    # Greece / Turkey / Cyprus
    "ATH": "LGAV", "SKG": "LGTS", "IST": "LTFM", "LCA": "LCLK",
    "HER": "LGIR",
    # Spain / Portugal
    "BCN": "LEBL", "MAD": "LEMD", "PMI": "LEPA",
    "LIS": "LPPT", "OPO": "LPPR", "FAO": "LPFR",
    # Other
    "MLA": "LMML", "DBV": "LDDU",
}

# ── Static seed table ────────────────────────────────────────────────────────
# Maps LX flight number (int) -> (origin_ICAO, destination_ICAO).
# Seed data — the learned cache takes precedence when both exist.
# Some flight number assignments may be approximate; the self-learning
# mechanism auto-corrects from actual observed flight data.

SEED_ROUTES: dict[int, tuple[str, str]] = {
    # ── Long-haul: Americas ──────────────────────────────────────────────────
    8: ("LSZH", "KJFK"),        # ZRH -> New York JFK
    9: ("KJFK", "LSZH"),        # New York JFK -> ZRH
    14: ("LSZH", "KJFK"),       # ZRH -> JFK (2nd daily)
    15: ("KJFK", "LSZH"),       # JFK -> ZRH (2nd daily)
    16: ("LSZH", "KEWR"),       # ZRH -> Newark
    17: ("KEWR", "LSZH"),       # Newark -> ZRH
    18: ("LSZH", "KMIA"),       # ZRH -> Miami
    19: ("KMIA", "LSZH"),       # Miami -> ZRH
    20: ("LSZH", "KBOS"),       # ZRH -> Boston
    21: ("KBOS", "LSZH"),       # Boston -> ZRH
    22: ("LSZH", "KORD"),       # ZRH -> Chicago
    23: ("KORD", "LSZH"),       # Chicago -> ZRH
    38: ("LSZH", "KSFO"),       # ZRH -> San Francisco
    39: ("KSFO", "LSZH"),       # San Francisco -> ZRH
    40: ("LSZH", "KLAX"),       # ZRH -> Los Angeles
    41: ("KLAX", "LSZH"),       # Los Angeles -> ZRH
    62: ("LSZH", "SBGR"),       # ZRH -> Sao Paulo
    63: ("SBGR", "LSZH"),       # Sao Paulo -> ZRH
    80: ("LSZH", "CYUL"),       # ZRH -> Montreal
    81: ("CYUL", "LSZH"),       # Montreal -> ZRH

    # ── Long-haul: Asia ──────────────────────────────────────────────────────
    52: ("LSZH", "RJAA"),       # ZRH -> Tokyo Narita
    53: ("RJAA", "LSZH"),       # Tokyo -> ZRH
    54: ("LSZH", "WSSS"),       # ZRH -> Singapore
    55: ("WSSS", "LSZH"),       # Singapore -> ZRH
    138: ("LSZH", "VHHH"),      # ZRH -> Hong Kong
    139: ("VHHH", "LSZH"),      # Hong Kong -> ZRH
    146: ("LSZH", "VABB"),      # ZRH -> Mumbai
    147: ("VABB", "LSZH"),      # Mumbai -> ZRH
    148: ("LSZH", "VIDP"),      # ZRH -> Delhi
    149: ("VIDP", "LSZH"),      # Delhi -> ZRH
    160: ("LSZH", "VTBS"),      # ZRH -> Bangkok
    161: ("VTBS", "LSZH"),      # Bangkok -> ZRH
    188: ("LSZH", "ZSPD"),      # ZRH -> Shanghai
    189: ("ZSPD", "LSZH"),      # Shanghai -> ZRH

    # ── Long-haul: Middle East / Africa ──────────────────────────────────────
    92: ("LSZH", "FAOR"),       # ZRH -> Johannesburg
    93: ("FAOR", "LSZH"),       # Johannesburg -> ZRH
    238: ("LSZH", "LLBG"),      # ZRH -> Tel Aviv
    239: ("LLBG", "LSZH"),      # Tel Aviv -> ZRH

    # ── European: UK & Ireland ───────────────────────────────────────────────
    316: ("LSZH", "EGLL"),      # ZRH -> London Heathrow
    317: ("EGLL", "LSZH"),      # LHR -> ZRH
    318: ("LSZH", "EGLL"),      # ZRH -> LHR (2nd)
    319: ("EGLL", "LSZH"),      # LHR -> ZRH (2nd)
    322: ("LSZH", "EGLL"),      # ZRH -> LHR (3rd)
    323: ("EGLL", "LSZH"),      # LHR -> ZRH (3rd)
    324: ("LSZH", "EGCC"),      # ZRH -> Manchester
    325: ("EGCC", "LSZH"),      # Manchester -> ZRH
    340: ("LSZH", "EGBB"),      # ZRH -> Birmingham
    341: ("EGBB", "LSZH"),      # Birmingham -> ZRH
    352: ("LSZH", "EGPH"),      # ZRH -> Edinburgh
    353: ("EGPH", "LSZH"),      # Edinburgh -> ZRH
    390: ("LSZH", "EIDW"),      # ZRH -> Dublin
    391: ("EIDW", "LSZH"),      # Dublin -> ZRH
    456: ("LSZH", "EGLC"),      # ZRH -> London City
    457: ("EGLC", "LSZH"),      # London City -> ZRH

    # ── European: France ─────────────────────────────────────────────────────
    638: ("LSZH", "LFPG"),      # ZRH -> Paris CDG
    639: ("LFPG", "LSZH"),      # CDG -> ZRH
    640: ("LSZH", "LFPG"),      # ZRH -> CDG (2nd)
    641: ("LFPG", "LSZH"),      # CDG -> ZRH (2nd)
    696: ("LSZH", "LFMN"),      # ZRH -> Nice
    697: ("LFMN", "LSZH"),      # Nice -> ZRH

    # ── European: Benelux ────────────────────────────────────────────────────
    724: ("LSZH", "EHAM"),      # ZRH -> Amsterdam
    725: ("EHAM", "LSZH"),      # Amsterdam -> ZRH
    726: ("LSZH", "EHAM"),      # ZRH -> AMS (2nd)
    727: ("EHAM", "LSZH"),      # AMS -> ZRH (2nd)
    782: ("LSZH", "EBBR"),      # ZRH -> Brussels
    783: ("EBBR", "LSZH"),      # Brussels -> ZRH

    # ── European: Germany ────────────────────────────────────────────────────
    960: ("LSZH", "EDDB"),      # ZRH -> Berlin
    961: ("EDDB", "LSZH"),      # Berlin -> ZRH
    962: ("LSZH", "EDDB"),      # ZRH -> BER (2nd)
    963: ("EDDB", "LSZH"),      # BER -> ZRH (2nd)
    1030: ("LSZH", "EDDL"),     # ZRH -> Dusseldorf
    1031: ("EDDL", "LSZH"),     # Dusseldorf -> ZRH
    1050: ("LSZH", "EDDH"),     # ZRH -> Hamburg
    1051: ("EDDH", "LSZH"),     # Hamburg -> ZRH
    1070: ("LSZH", "EDDF"),     # ZRH -> Frankfurt
    1071: ("EDDF", "LSZH"),     # Frankfurt -> ZRH
    1072: ("LSZH", "EDDF"),     # ZRH -> FRA (2nd)
    1073: ("EDDF", "LSZH"),     # FRA -> ZRH (2nd)
    1096: ("LSZH", "EDDM"),     # ZRH -> Munich
    1097: ("EDDM", "LSZH"),     # Munich -> ZRH

    # ── European: Nordics ────────────────────────────────────────────────────
    1210: ("LSZH", "ENGM"),     # ZRH -> Oslo
    1211: ("ENGM", "LSZH"),     # Oslo -> ZRH
    1250: ("LSZH", "ESSA"),     # ZRH -> Stockholm
    1251: ("ESSA", "LSZH"),     # Stockholm -> ZRH
    1270: ("LSZH", "EKCH"),     # ZRH -> Copenhagen
    1271: ("EKCH", "LSZH"),     # Copenhagen -> ZRH
    1300: ("LSZH", "EFHK"),     # ZRH -> Helsinki
    1301: ("EFHK", "LSZH"),     # Helsinki -> ZRH

    # ── European: Eastern Europe ─────────────────────────────────────────────
    1360: ("LSZH", "EPWA"),     # ZRH -> Warsaw
    1361: ("EPWA", "LSZH"),     # Warsaw -> ZRH
    1392: ("LSZH", "LHBP"),     # ZRH -> Budapest
    1393: ("LHBP", "LSZH"),     # Budapest -> ZRH
    1442: ("LSZH", "LROP"),     # ZRH -> Bucharest
    1443: ("LROP", "LSZH"),     # Bucharest -> ZRH
    1480: ("LSZH", "LKPR"),     # ZRH -> Prague
    1481: ("LKPR", "LSZH"),     # Prague -> ZRH
    1580: ("LSZH", "LOWW"),     # ZRH -> Vienna
    1581: ("LOWW", "LSZH"),     # Vienna -> ZRH
    1582: ("LSZH", "LOWW"),     # ZRH -> VIE (2nd)
    1583: ("LOWW", "LSZH"),     # VIE -> ZRH (2nd)

    # ── European: Italy ──────────────────────────────────────────────────────
    1610: ("LSZH", "LIMC"),     # ZRH -> Milan Malpensa
    1611: ("LIMC", "LSZH"),     # Milan -> ZRH
    1650: ("LSZH", "LIPZ"),     # ZRH -> Venice
    1651: ("LIPZ", "LSZH"),     # Venice -> ZRH
    1668: ("LSZH", "LIRQ"),     # ZRH -> Florence
    1669: ("LIRQ", "LSZH"),     # Florence -> ZRH
    1680: ("LSZH", "LIRN"),     # ZRH -> Naples
    1681: ("LIRN", "LSZH"),     # Naples -> ZRH
    1726: ("LSZH", "LIRF"),     # ZRH -> Rome Fiumicino
    1727: ("LIRF", "LSZH"),     # Rome -> ZRH
    1728: ("LSZH", "LIRF"),     # ZRH -> FCO (2nd)
    1729: ("LIRF", "LSZH"),     # FCO -> ZRH (2nd)

    # ── European: Greece / Turkey ────────────────────────────────────────────
    1800: ("LSZH", "LTFM"),     # ZRH -> Istanbul
    1801: ("LTFM", "LSZH"),     # Istanbul -> ZRH
    1830: ("LSZH", "LGAV"),     # ZRH -> Athens
    1831: ("LGAV", "LSZH"),     # Athens -> ZRH
    1852: ("LSZH", "LGTS"),     # ZRH -> Thessaloniki
    1853: ("LGTS", "LSZH"),     # Thessaloniki -> ZRH

    # ── European: Spain / Portugal ───────────────────────────────────────────
    1942: ("LSZH", "LEBL"),     # ZRH -> Barcelona
    1943: ("LEBL", "LSZH"),     # Barcelona -> ZRH
    1944: ("LSZH", "LEBL"),     # ZRH -> BCN (2nd)
    1945: ("LEBL", "LSZH"),     # BCN -> ZRH (2nd)
    1952: ("LSZH", "LEMD"),     # ZRH -> Madrid
    1953: ("LEMD", "LSZH"),     # Madrid -> ZRH
    1974: ("LSZH", "LEPA"),     # ZRH -> Palma de Mallorca
    1975: ("LEPA", "LSZH"),     # Palma -> ZRH
    2086: ("LSZH", "LPPT"),     # ZRH -> Lisbon
    2087: ("LPPT", "LSZH"),     # Lisbon -> ZRH
    2094: ("LSZH", "LPPR"),     # ZRH -> Porto
    2095: ("LPPR", "LSZH"),     # Porto -> ZRH

    # ── European: Other ──────────────────────────────────────────────────────
    1860: ("LSZH", "LMML"),     # ZRH -> Malta
    1861: ("LMML", "LSZH"),     # Malta -> ZRH

    # ── Geneva hub (LX 2xxx) ─────────────────────────────────────────────────
    2020: ("LSGG", "EGLL"),     # GVA -> London Heathrow
    2021: ("EGLL", "LSGG"),     # LHR -> GVA
    2100: ("LSGG", "LFPG"),     # GVA -> Paris CDG
    2101: ("LFPG", "LSGG"),     # CDG -> GVA
    2150: ("LSGG", "LEBL"),     # GVA -> Barcelona
    2151: ("LEBL", "LSGG"),     # BCN -> GVA
    2170: ("LSGG", "LPPT"),     # GVA -> Lisbon
    2171: ("LPPT", "LSGG"),     # LIS -> GVA
    2200: ("LSGG", "EDDB"),     # GVA -> Berlin
    2201: ("EDDB", "LSGG"),     # BER -> GVA
    2250: ("LSGG", "LOWW"),     # GVA -> Vienna
    2251: ("LOWW", "LSGG"),     # VIE -> GVA
    2300: ("LSGG", "LIRF"),     # GVA -> Rome
    2301: ("LIRF", "LSGG"),     # FCO -> GVA
    2350: ("LSGG", "LGAV"),     # GVA -> Athens
    2351: ("LGAV", "LSGG"),     # ATH -> GVA
    2400: ("LSGG", "EHAM"),     # GVA -> Amsterdam
    2401: ("EHAM", "LSGG"),     # AMS -> GVA
    2450: ("LSGG", "LEMD"),     # GVA -> Madrid
    2451: ("LEMD", "LSGG"),     # MAD -> GVA
}

# Callsign patterns: "SWR" or "EDW" + digits + optional letter suffix
_SWR_RE = re.compile(r"^SWR(\d+)[A-Z]?$", re.IGNORECASE)
_EDW_RE = re.compile(r"^EDW(\d+)[A-Z]?$", re.IGNORECASE)


def _is_swiss_or_edw(callsign: str) -> bool:
    """Check if callsign is SWISS (SWR) or Edelweiss (EDW)."""
    prefix = callsign.strip()[:3].upper()
    return prefix in ("SWR", "EDW")


def parse_flight_number(callsign: str | None) -> int | None:
    """Extract numeric flight number from an SWR or EDW callsign.

    SWR8 -> 8, SWR180A -> 180, EDW100 -> 100.
    Returns None if callsign is not a valid SWR/EDW format.
    """
    if not callsign:
        return None
    cs = callsign.strip()
    m = _SWR_RE.match(cs) or _EDW_RE.match(cs)
    if m:
        return int(m.group(1))
    return None


def _normalize_callsign(callsign: str) -> str:
    """Normalize callsign for cache key: strip suffix, uppercase.

    SWR8 -> SWR8, SWR180A -> SWR180, swr22 -> SWR22, EDW100 -> EDW100.
    """
    cs = callsign.strip().upper()
    m = _SWR_RE.match(cs)
    if m:
        return f"SWR{m.group(1)}"
    m = _EDW_RE.match(cs)
    if m:
        return f"EDW{m.group(1)}"
    return cs


def get_route(callsign: str | None) -> tuple[str | None, str | None]:
    """Look up route for a SWISS or Edelweiss callsign.

    Resolution order:
    1. Learned cache (persistent, from actual observed flights)
    2. Static seed table (built-in, covers major SWR routes)
    3. Hub fallback (LSZH for fn<2000, LSGG for fn>=2000)

    Returns (origin_ICAO, destination_ICAO). Either may be None if unknown.
    """
    if not callsign or not _is_swiss_or_edw(callsign):
        return None, None

    norm = _normalize_callsign(callsign)
    flight_num = parse_flight_number(callsign)

    # Tier 1: learned cache (from actual flights)
    if norm in _learned:
        route = _learned[norm]
        return route[0], route[1]

    # Tier 2: static seed table
    if flight_num is not None and flight_num in SEED_ROUTES:
        origin, dest = SEED_ROUTES[flight_num]
        return origin, dest

    # Tier 3: hub fallback
    if flight_num is not None:
        return _hub_fallback(flight_num)

    return "LSZH", None


def _hub_fallback(flight_num: int) -> tuple[str, None]:
    """Determine departure hub from flight number range."""
    if 2000 <= flight_num < 3000:
        return "LSGG", None
    return "LSZH", None


def learn_route(callsign: str | None, origin: str | None,
                destination: str | None) -> None:
    """Store a discovered route mapping in the persistent cache.

    Called when OpenSky flights API returns valid route data, or when
    the external schedule API provides a mapping. Learned routes take
    priority over the static seed table.
    """
    if not callsign or not _is_swiss_or_edw(callsign):
        return
    if not origin and not destination:
        return  # nothing useful to learn
    if origin and destination and origin == destination:
        logger.debug("Rejecting same origin/dest %s for %s", origin, callsign)
        return  # data artifact — no real flight has same origin and destination

    norm = _normalize_callsign(callsign)
    existing = _learned.get(norm)

    # Only update if we have new information
    new_origin = origin or (existing[0] if existing else None)
    new_dest = destination or (existing[1] if existing else None)

    if existing and existing[0] == new_origin and existing[1] == new_dest:
        return  # no change

    _learned[norm] = [new_origin, new_dest]
    _save_cache()
    logger.info("Learned route: %s -> %s to %s", norm, new_origin, new_dest)


def get_cache_stats() -> dict:
    """Return statistics about the route database."""
    seed_count = len(SEED_ROUTES)
    learned_count = len(_learned)
    learned_with_dest = sum(
        1 for r in _learned.values() if r[1] is not None
    )
    return {
        "seed_routes": seed_count,
        "learned_routes": learned_count,
        "learned_with_destination": learned_with_dest,
        "total_known": seed_count + learned_count,
    }


# ── Optional: AirLabs bulk fetch ─────────────────────────────────────────────

AIRLABS_BASE = "https://airlabs.co/api/v9"


async def _paginate_airlabs(client: httpx.AsyncClient, endpoint: str,
                            api_key: str, airline_icao: str) -> list[dict]:
    """Fetch all pages from an AirLabs endpoint (free tier returns 50/page)."""
    all_routes: list[dict] = []
    offset = 0
    while True:
        resp = await client.get(
            f"{AIRLABS_BASE}/{endpoint}",
            params={"api_key": api_key, "airline_icao": airline_icao, "offset": offset},
        )
        resp.raise_for_status()
        routes = resp.json().get("response", [])
        if not routes:
            break
        all_routes.extend(routes)
        offset += len(routes)
        if len(routes) < 50:
            break
    return all_routes


def _extract_route(route: dict, callsign_prefix: str) -> tuple[str, str, str] | None:
    """Extract (callsign, dep_icao, arr_icao) from an AirLabs route/schedule entry."""
    flight_num = route.get("flight_number")
    if flight_num is None:
        return None

    dep_icao = route.get("dep_icao") or IATA_TO_ICAO.get(
        route.get("dep_iata", ""), ""
    )
    arr_icao = route.get("arr_icao") or IATA_TO_ICAO.get(
        route.get("arr_iata", ""), ""
    )

    if not dep_icao or not arr_icao or dep_icao == arr_icao:
        return None

    return f"{callsign_prefix}{flight_num}", dep_icao, arr_icao


async def fetch_routes_from_airlabs() -> int:
    """Bulk-fetch all SWISS + Edelweiss routes from AirLabs.

    Queries both /routes (static route database) and /schedules (currently
    active flights) to maximize coverage. The free tier returns 50 results
    per page; we paginate to get all available data.

    Requires AIRLABS_API_KEY to be set in .env.
    Returns count of newly learned routes.
    """
    api_key = settings.airlabs_api_key
    if not api_key:
        logger.warning("AirLabs: AIRLABS_API_KEY not set, skipping route fetch")
        return 0

    logger.info("AirLabs: fetching routes for SWR + EDW...")

    try:
        count = 0
        async with httpx.AsyncClient(timeout=30) as client:
            for airline_icao, prefix in [("SWR", "SWR"), ("EDW", "EDW")]:
                # Fetch from both endpoints for maximum coverage
                for endpoint in ["routes", "schedules"]:
                    routes = await _paginate_airlabs(client, endpoint, api_key, airline_icao)
                    endpoint_count = 0
                    for route in routes:
                        extracted = _extract_route(route, prefix)
                        if extracted:
                            cs, dep, arr = extracted
                            if cs not in _learned:
                                _learned[cs] = [dep, arr]
                                endpoint_count += 1
                    logger.info("AirLabs %s /%s: %d entries, %d new routes learned",
                                airline_icao, endpoint, len(routes), endpoint_count)
                    count += endpoint_count

        if count > 0:
            _save_cache()
        logger.info("AirLabs: %d new routes learned (%d total in cache)",
                     count, len(_learned))
        return count

    except httpx.HTTPStatusError as e:
        logger.warning("AirLabs API error: HTTP %d — check your AIRLABS_API_KEY",
                        e.response.status_code)
        return 0
    except Exception:
        logger.exception("AirLabs route fetch failed")
        return 0
