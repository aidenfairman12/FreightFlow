"""FAF5 data loader: parse CSV files and insert into freight_flows table.

The FAF5 dataset from BTS/FHWA comes as CSV files with freight flow data
between ~132 FAF zones. The data includes origin, destination, commodity (SCTG2),
transport mode, and year-based columns for tons, value, and ton-miles.

Expected CSV columns (FAF5 regional flows):
  dms_orig    - Domestic origin FAF zone ID
  dms_dest    - Domestic destination FAF zone ID
  sctg2       - 2-digit SCTG commodity code
  dms_mode    - Domestic transport mode code (1-8)
  trade_type  - 1=domestic, 2=import, 3=export
  tons_YYYY   - Thousands of tons for year YYYY
  value_YYYY  - Millions of USD for year YYYY
  tmiles_YYYY - Millions of ton-miles for year YYYY
  curval_YYYY - Current-year value (nominal dollars)

Mode codes: 1=Truck, 2=Rail, 3=Water, 4=Air, 5=Multiple/mail,
            6=Pipeline, 7=Other, 8=No domestic mode
"""

import logging
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from config import settings
from db.session import AsyncSessionLocal
from services.faf5_zones import MODE_CODES

logger = logging.getLogger(__name__)

# Historical years in FAF5 (actual data)
HISTORICAL_YEARS = list(range(2012, 2023))  # 2012-2022

# Projected years in FAF5
PROJECTED_YEARS = [2025, 2030, 2035, 2040, 2045, 2050, 2055]


def _find_faf5_csv(data_dir: str) -> Path | None:
    """Find the FAF5 CSV file in the data directory."""
    data_path = Path(data_dir)
    if not data_path.exists():
        return None

    # Look for FAF5 CSV files
    for pattern in ["FAF5*.csv", "faf5*.csv", "FAF*.csv"]:
        matches = list(data_path.glob(pattern))
        if matches:
            return matches[0]
    return None


def _parse_faf5_csv(csv_path: Path) -> pd.DataFrame:
    """Parse FAF5 CSV into a normalized DataFrame with one row per OD-commodity-mode-year.

    The raw CSV has year-based columns (tons_2012, tons_2017, value_2012, etc).
    We unpivot these into individual rows.
    """
    logger.info("Reading FAF5 CSV: %s", csv_path)
    df = pd.read_csv(csv_path, low_memory=False)

    # Normalize column names to lowercase
    df.columns = [c.strip().lower() for c in df.columns]

    # Identify the origin/destination/mode/commodity columns
    # FAF5 uses dms_orig/dms_dest for domestic, fr_orig/fr_dest for foreign
    orig_col = "dms_orig" if "dms_orig" in df.columns else "fr_orig"
    dest_col = "dms_dest" if "dms_dest" in df.columns else "fr_dest"
    mode_col = "dms_mode" if "dms_mode" in df.columns else "fr_inmode"

    # Find year columns for tons, value, and ton-miles
    tons_cols = sorted([c for c in df.columns if re.match(r"tons_\d{4}", c)])
    value_cols = sorted([c for c in df.columns if re.match(r"(value|curval)_\d{4}", c)])
    tmiles_cols = sorted([c for c in df.columns if re.match(r"tmiles_\d{4}", c)])

    if not tons_cols:
        raise ValueError(f"No tons_YYYY columns found in {csv_path}. Columns: {list(df.columns)}")

    logger.info("Found %d tons columns, %d value columns, %d tmiles columns",
                len(tons_cols), len(value_cols), len(tmiles_cols))

    # Extract years from column names
    years = sorted(set(int(c.split("_")[1]) for c in tons_cols))
    logger.info("Years in data: %s", years)

    # Filter to domestic flows only (trade_type=1) if column exists
    if "trade_type" in df.columns:
        domestic = df[df["trade_type"] == 1].copy()
        logger.info("Filtered to %d domestic flow rows (from %d total)", len(domestic), len(df))
    else:
        domestic = df.copy()

    # Unpivot: one row per OD-commodity-mode-year
    rows = []
    for year in years:
        tons_c = f"tons_{year}"
        # Find matching value column (could be value_YYYY or curval_YYYY)
        value_c = f"value_{year}" if f"value_{year}" in df.columns else f"curval_{year}"
        tmiles_c = f"tmiles_{year}"

        if tons_c not in domestic.columns:
            continue

        year_df = domestic[[orig_col, dest_col, "sctg2", mode_col]].copy()
        year_df["year"] = year
        year_df["tons_thousands"] = domestic[tons_c] if tons_c in domestic.columns else None
        year_df["value_millions"] = domestic[value_c] if value_c in domestic.columns else None
        year_df["ton_miles_millions"] = domestic[tmiles_c] if tmiles_c in domestic.columns else None
        year_df["data_type"] = "historical" if year <= 2022 else "projected"

        year_df = year_df.rename(columns={
            orig_col: "origin_zone_id",
            dest_col: "dest_zone_id",
            mode_col: "mode_code",
        })
        rows.append(year_df)

    result = pd.concat(rows, ignore_index=True)

    # Add mode names
    result["mode_name"] = result["mode_code"].map(MODE_CODES).fillna("Unknown")

    # Convert sctg2 to string with zero-padding
    result["sctg2"] = result["sctg2"].astype(str).str.zfill(2)

    # Drop rows with zero/null tons (empty flows)
    result = result[result["tons_thousands"].notna() & (result["tons_thousands"] > 0)]

    logger.info("Parsed %d freight flow records across %d years", len(result), len(years))
    return result


async def load_faf5_data(data_dir: str | None = None) -> int:
    """Load FAF5 data from CSV into the freight_flows table.

    Returns the number of rows inserted.
    """
    data_dir = data_dir or settings.faf5_data_dir
    csv_path = _find_faf5_csv(data_dir)

    if csv_path is None:
        logger.warning("No FAF5 CSV found in %s — skipping data load. "
                       "Download from https://www.bts.gov/faf", data_dir)
        return 0

    df = _parse_faf5_csv(csv_path)

    # Batch insert into database
    batch_size = 1000
    inserted = 0

    async with AsyncSessionLocal() as session:
        for start in range(0, len(df), batch_size):
            batch = df.iloc[start:start + batch_size]
            for _, row in batch.iterrows():
                try:
                    await session.execute(text("""
                        INSERT INTO freight_flows
                            (origin_zone_id, dest_zone_id, sctg2, mode_code, mode_name,
                             year, data_type, tons_thousands, value_millions, ton_miles_millions)
                        VALUES
                            (:orig, :dest, :sctg2, :mode, :mode_name,
                             :year, :dtype, :tons, :value, :tmiles)
                        ON CONFLICT (origin_zone_id, dest_zone_id, sctg2, mode_code, year)
                        DO UPDATE SET
                            tons_thousands = EXCLUDED.tons_thousands,
                            value_millions = EXCLUDED.value_millions,
                            ton_miles_millions = EXCLUDED.ton_miles_millions,
                            mode_name = EXCLUDED.mode_name,
                            data_type = EXCLUDED.data_type
                    """), {
                        "orig": int(row["origin_zone_id"]),
                        "dest": int(row["dest_zone_id"]),
                        "sctg2": str(row["sctg2"]),
                        "mode": int(row["mode_code"]),
                        "mode_name": row["mode_name"],
                        "year": int(row["year"]),
                        "dtype": row["data_type"],
                        "tons": float(row["tons_thousands"]) if pd.notna(row["tons_thousands"]) else None,
                        "value": float(row["value_millions"]) if pd.notna(row["value_millions"]) else None,
                        "tmiles": float(row["ton_miles_millions"]) if pd.notna(row["ton_miles_millions"]) else None,
                    })
                    inserted += 1
                except Exception as e:
                    logger.warning("Skipping row: %s", e)
            await session.commit()

            if start % 5000 == 0 and start > 0:
                logger.info("Loaded %d / %d rows...", inserted, len(df))

    logger.info("FAF5 load complete: %d rows inserted", inserted)
    return inserted
