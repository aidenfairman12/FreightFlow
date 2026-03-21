"""
Filters flight data to SWISS International Air Lines operations.

SWISS identification:
- Callsign prefix: SWR (ICAO code for SWISS)
- Callsign prefix: EDW (ICAO code for Edelweiss Air)

Edelweiss Air is a subsidiary of SWISS and is included in the Lufthansa Group
annual report as part of the SWISS (LX) fleet. Both are tracked by default.
"""

SWISS_CALLSIGN_PREFIXES = {"SWR", "EDW"}


def is_swiss_flight(callsign: str | None) -> bool:
    """Check if a callsign belongs to SWISS or Edelweiss Air."""
    if not callsign:
        return False
    prefix = callsign[:3].upper()
    return prefix in SWISS_CALLSIGN_PREFIXES


def swiss_callsign_sql_filter() -> str:
    """Return a SQL WHERE clause fragment for SWISS + Edelweiss flights."""
    return "(callsign LIKE 'SWR%' OR callsign LIKE 'EDW%')"
