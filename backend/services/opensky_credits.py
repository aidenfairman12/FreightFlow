"""
OpenSky API credit tracker.

OpenSky free tier: 4000 API credits per day.
Tracks usage and prevents exceeding the daily limit.

Credit budget (at 30s poll interval):
  - State polls:  86400 / 30 = 2880/day
  - Route lookups: ~50 aircraft × 6 refreshes (4hr TTL) = ~300/day
  - Total: ~3180/day (safe margin under 4000)
"""

import logging
import time

from config import settings

logger = logging.getLogger(__name__)

_credits_used: int = 0
_day_start: float = time.time()

# Warn at 90% of limit, pause at 98%
WARN_THRESHOLD = 0.90
PAUSE_THRESHOLD = 0.98


def _reset_if_new_day() -> None:
    """Reset counter if 24 hours have elapsed."""
    global _credits_used, _day_start
    if time.time() - _day_start >= 86400:
        logger.info("OpenSky credit counter reset (%d used in last 24h)", _credits_used)
        _credits_used = 0
        _day_start = time.time()


def record_call(count: int = 1) -> None:
    """Record API call(s) against the daily budget."""
    global _credits_used
    _reset_if_new_day()
    _credits_used += count

    limit = settings.opensky_daily_credit_limit
    if _credits_used == int(limit * WARN_THRESHOLD):
        logger.warning(
            "OpenSky credit usage at 90%%: %d / %d used", _credits_used, limit
        )


def can_call() -> bool:
    """Return True if we have remaining credits for today."""
    _reset_if_new_day()
    limit = settings.opensky_daily_credit_limit
    if _credits_used >= int(limit * PAUSE_THRESHOLD):
        logger.warning(
            "OpenSky credits exhausted for today (%d / %d). "
            "Pausing API calls until reset.", _credits_used, limit
        )
        return False
    return True


def get_usage() -> dict:
    """Return current credit usage stats."""
    _reset_if_new_day()
    limit = settings.opensky_daily_credit_limit
    return {
        "credits_used": _credits_used,
        "credits_limit": limit,
        "credits_remaining": max(0, limit - _credits_used),
        "pct_used": round(_credits_used / limit * 100, 1) if limit else 0,
        "resets_in_seconds": int(86400 - (time.time() - _day_start)),
    }
