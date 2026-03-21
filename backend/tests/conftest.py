"""Shared test fixtures for PlaneLogistics backend tests."""

import pytest
from datetime import datetime

from models.state_vector import StateVector


@pytest.fixture
def sample_state_vector_array():
    """Raw 17-element list matching OpenSky state vector format."""
    return [
        "abc123",           # 0  icao24
        "SWR8   ",          # 1  callsign (with whitespace)
        "Switzerland",      # 2  origin_country
        1700000000,         # 3  time_position
        1700000000,         # 4  last_contact
        8.5492,             # 5  longitude
        47.4647,            # 6  latitude
        10668.0,            # 7  baro_altitude (meters, ~35000ft)
        False,              # 8  on_ground
        250.0,              # 9  velocity (m/s)
        90.0,               # 10 heading
        0.5,                # 11 vertical_rate
        None,               # 12 (unused)
        10972.0,            # 13 geo_altitude
        "1000",             # 14 squawk
        None,               # 15 (unused)
        None,               # 16 (unused)
    ]


@pytest.fixture
def sample_state_vector():
    """Constructed StateVector instance with realistic SWISS flight data."""
    return StateVector(
        icao24="abc123",
        callsign="SWR8",
        origin_country="Switzerland",
        latitude=47.4647,
        longitude=8.5492,
        baro_altitude=10668.0,
        on_ground=False,
        velocity=250.0,
        heading=90.0,
        vertical_rate=0.5,
        geo_altitude=10972.0,
        squawk="1000",
        last_contact=datetime(2023, 11, 14, 22, 13, 20),
    )


@pytest.fixture(autouse=True)
def _clean_enrichment_cache():
    """Reset enrichment module caches between tests."""
    from services.enrichment import _type_cache, _type_fetching
    saved_cache = _type_cache.copy()
    saved_fetching = _type_fetching.copy()
    yield
    _type_cache.clear()
    _type_cache.update(saved_cache)
    _type_fetching.clear()
    _type_fetching.update(saved_fetching)


@pytest.fixture(autouse=True)
def _clean_fuel_model_cache():
    """Reset fuel model cache between tests."""
    from services.fuel_model import _model_cache
    saved = _model_cache.copy()
    yield
    _model_cache.clear()
    _model_cache.update(saved)


@pytest.fixture(autouse=True)
def _clean_opensky_token_cache():
    """Reset OpenSky auth token cache between tests."""
    import services.opensky_auth as auth
    saved_token = auth._cached_token
    saved_expires = auth._token_expires_at
    yield
    auth._cached_token = saved_token
    auth._token_expires_at = saved_expires
