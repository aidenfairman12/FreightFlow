"""
Filters flight data to SWISS International Air Lines operations.

SWISS identification:
- Callsign prefix: SWR (ICAO code for SWISS)
- Also catches Edelweiss Air (EDW) when explicitly enabled
"""

SWISS_CALLSIGN_PREFIXES = {"SWR"}
EDELWEISS_CALLSIGN_PREFIXES = {"EDW"}


def is_swiss_flight(callsign: str | None, include_edelweiss: bool = False) -> bool:
    """Check if a callsign belongs to SWISS (or optionally Edelweiss)."""
    if not callsign:
        return False
    prefix = callsign[:3].upper()
    prefixes = SWISS_CALLSIGN_PREFIXES.copy()
    if include_edelweiss:
        prefixes |= EDELWEISS_CALLSIGN_PREFIXES
    return prefix in prefixes


def swiss_callsign_sql_filter(include_edelweiss: bool = False) -> str:
    """Return a SQL WHERE clause fragment for SWISS flights."""
    clauses = ["callsign LIKE 'SWR%'"]
    if include_edelweiss:
        clauses.append("callsign LIKE 'EDW%'")
    return "(" + " OR ".join(clauses) + ")"
