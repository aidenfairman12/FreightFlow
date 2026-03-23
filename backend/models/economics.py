from datetime import date

from pydantic import BaseModel


class EconomicFactor(BaseModel):
    date: date
    factor_name: str
    value: float
    unit: str | None = None
    source: str | None = None


class EconomicSnapshot(BaseModel):
    """Latest values for all tracked economic factors."""
    diesel_usd_gal: float | None = None
    brent_crude_usd_bbl: float | None = None
    trucking_ppi: float | None = None
    freight_tsi: float | None = None
    as_of: date | None = None
