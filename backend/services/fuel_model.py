"""
Fuel burn and emissions estimation using OpenAP.

OpenAP covers ~30 common commercial aircraft types. Unsupported types
return None gracefully so the pipeline can continue without estimates.

Usage:
    estimate = FuelModel("A320").enroute_burn(mass_kg=65000, tas_kt=450, alt_ft=35000)
"""

# scipy.signal.gaussian was removed in scipy 1.12; openap.extra.filters still
# imports it from the old path.  Re-expose it before openap is imported.
import scipy.signal
import scipy.signal.windows
if not hasattr(scipy.signal, "gaussian"):
    scipy.signal.gaussian = scipy.signal.windows.gaussian  # type: ignore[attr-defined]

from dataclasses import dataclass

_model_cache: dict[str, "FuelModel"] = {}


@dataclass
class FuelEstimate:
    fuel_flow_kg_s: float
    co2_kg_s: float
    nox_kg_s: float


class FuelModel:
    def __init__(self, aircraft_type: str):
        self.aircraft_type = aircraft_type
        self._fuelflow = None
        self._emission = None
        self._supported = True

    def _load(self) -> None:
        """Lazy-load OpenAP models on first use."""
        try:
            import openap
            self._fuelflow = openap.FuelFlow(self.aircraft_type)
            self._emission = openap.Emission(self.aircraft_type)
        except Exception:
            self._supported = False

    def enroute_burn(
        self, mass_kg: float, tas_kt: float, alt_ft: float
    ) -> FuelEstimate | None:
        """Estimate instantaneous fuel burn in cruise phase."""
        if self._fuelflow is None and self._supported:
            self._load()
        if not self._supported or self._fuelflow is None:
            return None

        import openap
        ff = self._fuelflow.enroute(mass=mass_kg, tas=tas_kt, alt=alt_ft)
        emission = openap.Emission(self.aircraft_type)
        return FuelEstimate(
            fuel_flow_kg_s=ff,
            co2_kg_s=emission.co2(ff) / 1000,       # g/s → kg/s
            nox_kg_s=emission.nox(ff, tas=tas_kt, alt=alt_ft) / 1000,  # g/s → kg/s
        )


def estimate_for_sv(
    aircraft_type: str | None,
    velocity_ms: float | None,
    baro_altitude_m: float | None,
) -> FuelEstimate | None:
    """Compute instantaneous cruise fuel burn from a StateVector's fields."""
    if velocity_ms is None or baro_altitude_m is None or velocity_ms < 50:
        return None  # on ground or no data
    ac_type = aircraft_type or "A320"  # generic narrowbody fallback
    if ac_type not in _model_cache:
        _model_cache[ac_type] = FuelModel(ac_type)
    tas_kt = velocity_ms * 1.94384       # m/s → knots
    alt_ft = baro_altitude_m * 3.28084  # m → feet
    return _model_cache[ac_type].enroute_burn(mass_kg=65000, tas_kt=tas_kt, alt_ft=alt_ft)
