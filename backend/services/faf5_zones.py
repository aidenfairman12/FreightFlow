"""FAF5 zone geographic data: zone IDs, names, states, and lat/lon centroids.

FAF5 defines 132 domestic zones (metro areas + rest-of-state) plus international
gateway zones. This module provides centroid coordinates for map rendering.

Zone IDs follow FIPS conventions: first 2 digits = state FIPS, last 1-2 digits = zone.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_CENTROIDS_PATH = Path(__file__).parent.parent / "data" / "faf_zone_centroids.json"

# Mode code mapping (FAF5 standard)
MODE_CODES = {
    1: "Truck",
    2: "Rail",
    3: "Water",
    4: "Air (incl. truck-air)",
    5: "Multiple modes & mail",
    6: "Pipeline",
    7: "Other and unknown",
    8: "No domestic mode",
}

# SCTG2 commodity codes (subset — full list loaded from DB)
COMMODITY_CODES = {
    "01": "Live animals and fish",
    "02": "Cereal grains",
    "03": "Other agricultural products",
    "04": "Animal feed",
    "05": "Meat, poultry, fish, seafood",
    "06": "Milled grain products",
    "07": "Other foodstuffs",
    "08": "Alcoholic beverages",
    "09": "Tobacco products",
    "10": "Building stone",
    "11": "Natural sands",
    "12": "Gravel and crusite stone",
    "13": "Non-metallic minerals",
    "14": "Metallic ores",
    "15": "Coal",
    "16": "Crude petroleum",
    "17": "Gasoline and aviation fuel",
    "18": "Fuel oils",
    "19": "Products of petroleum refining",
    "20": "Basic chemicals",
    "21": "Pharmaceutical products",
    "22": "Fertilizers",
    "23": "Chemical products",
    "24": "Plastics and rubber",
    "25": "Logs and other wood",
    "26": "Wood products",
    "27": "Pulp, newsprint, paper",
    "28": "Paper or paperboard articles",
    "29": "Printed products",
    "30": "Textiles, leather",
    "31": "Non-metallic mineral products",
    "32": "Base metal in primary forms",
    "33": "Articles of base metal",
    "34": "Machinery",
    "35": "Electronic and electrical equipment",
    "36": "Motorized and other vehicles",
    "37": "Transport equipment",
    "38": "Precision instruments",
    "39": "Furniture, mattresses",
    "40": "Miscellaneous manufactured products",
    "41": "Waste and scrap",
    "43": "Mixed freight",
}


def load_zone_centroids() -> dict[int, dict]:
    """Load zone centroid data from JSON file.

    Returns dict keyed by zone_id with {name, state, lat, lon, type} values.
    """
    if _CENTROIDS_PATH.exists():
        with open(_CENTROIDS_PATH) as f:
            data = json.load(f)
        # JSON keys are strings; convert to int
        return {int(k): v for k, v in data.items()}

    logger.warning("Zone centroids file not found at %s, using built-in subset", _CENTROIDS_PATH)
    return _BUILTIN_ZONES


# Built-in subset: major metro zones used by our corridors + key hubs
# Full dataset in faf_zone_centroids.json
_BUILTIN_ZONES: dict[int, dict] = {
    11: {"name": "Birmingham, AL", "state": "AL", "lat": 33.52, "lon": -86.80, "type": "metro"},
    12: {"name": "Rest of Alabama", "state": "AL", "lat": 32.32, "lon": -86.90, "type": "rest_of_state"},
    20: {"name": "Rest of Alaska", "state": "AK", "lat": 64.20, "lon": -152.49, "type": "rest_of_state"},
    40: {"name": "Rest of Arizona", "state": "AZ", "lat": 34.05, "lon": -111.09, "type": "rest_of_state"},
    41: {"name": "Phoenix, AZ", "state": "AZ", "lat": 33.45, "lon": -112.07, "type": "metro"},
    50: {"name": "Rest of Arkansas", "state": "AR", "lat": 35.20, "lon": -91.83, "type": "rest_of_state"},
    60: {"name": "Rest of California", "state": "CA", "lat": 36.78, "lon": -119.42, "type": "rest_of_state"},
    61: {"name": "Los Angeles, CA", "state": "CA", "lat": 33.94, "lon": -118.24, "type": "metro"},
    62: {"name": "San Francisco, CA", "state": "CA", "lat": 37.77, "lon": -122.42, "type": "metro"},
    63: {"name": "San Diego, CA", "state": "CA", "lat": 32.72, "lon": -117.16, "type": "metro"},
    64: {"name": "Sacramento, CA", "state": "CA", "lat": 38.58, "lon": -121.49, "type": "metro"},
    80: {"name": "Rest of Colorado", "state": "CO", "lat": 39.55, "lon": -105.78, "type": "rest_of_state"},
    81: {"name": "Denver, CO", "state": "CO", "lat": 39.74, "lon": -104.99, "type": "metro"},
    90: {"name": "Rest of Connecticut", "state": "CT", "lat": 41.60, "lon": -72.76, "type": "rest_of_state"},
    100: {"name": "Rest of Delaware", "state": "DE", "lat": 39.16, "lon": -75.52, "type": "rest_of_state"},
    111: {"name": "Washington, DC", "state": "DC", "lat": 38.91, "lon": -77.04, "type": "metro"},
    120: {"name": "Rest of Florida", "state": "FL", "lat": 27.66, "lon": -81.52, "type": "rest_of_state"},
    121: {"name": "Jacksonville, FL", "state": "FL", "lat": 30.33, "lon": -81.66, "type": "metro"},
    122: {"name": "Miami, FL", "state": "FL", "lat": 25.76, "lon": -80.19, "type": "metro"},
    123: {"name": "Orlando, FL", "state": "FL", "lat": 28.54, "lon": -81.38, "type": "metro"},
    124: {"name": "Tampa, FL", "state": "FL", "lat": 27.95, "lon": -82.46, "type": "metro"},
    130: {"name": "Rest of Georgia", "state": "GA", "lat": 32.17, "lon": -82.90, "type": "rest_of_state"},
    131: {"name": "Atlanta, GA", "state": "GA", "lat": 33.75, "lon": -84.39, "type": "metro"},
    150: {"name": "Rest of Hawaii", "state": "HI", "lat": 19.90, "lon": -155.58, "type": "rest_of_state"},
    160: {"name": "Rest of Idaho", "state": "ID", "lat": 44.07, "lon": -114.74, "type": "rest_of_state"},
    170: {"name": "Rest of Illinois", "state": "IL", "lat": 40.63, "lon": -89.40, "type": "rest_of_state"},
    171: {"name": "Chicago, IL", "state": "IL", "lat": 41.88, "lon": -87.63, "type": "metro"},
    180: {"name": "Rest of Indiana", "state": "IN", "lat": 40.27, "lon": -86.13, "type": "rest_of_state"},
    181: {"name": "Indianapolis, IN", "state": "IN", "lat": 39.77, "lon": -86.16, "type": "metro"},
    190: {"name": "Rest of Iowa", "state": "IA", "lat": 41.88, "lon": -93.10, "type": "rest_of_state"},
    200: {"name": "Rest of Kansas", "state": "KS", "lat": 38.50, "lon": -98.00, "type": "rest_of_state"},
    201: {"name": "Kansas City, MO-KS", "state": "KS", "lat": 39.10, "lon": -94.58, "type": "metro"},
    210: {"name": "Rest of Kentucky", "state": "KY", "lat": 37.84, "lon": -84.27, "type": "rest_of_state"},
    211: {"name": "Louisville, KY-IN", "state": "KY", "lat": 38.25, "lon": -85.76, "type": "metro"},
    220: {"name": "Rest of Louisiana", "state": "LA", "lat": 31.17, "lon": -91.87, "type": "rest_of_state"},
    221: {"name": "New Orleans, LA", "state": "LA", "lat": 29.95, "lon": -90.07, "type": "metro"},
    222: {"name": "Baton Rouge, LA", "state": "LA", "lat": 30.45, "lon": -91.19, "type": "metro"},
    230: {"name": "Rest of Maine", "state": "ME", "lat": 45.25, "lon": -69.45, "type": "rest_of_state"},
    240: {"name": "Rest of Maryland", "state": "MD", "lat": 39.05, "lon": -76.64, "type": "rest_of_state"},
    241: {"name": "Baltimore, MD", "state": "MD", "lat": 39.29, "lon": -76.61, "type": "metro"},
    250: {"name": "Rest of Massachusetts", "state": "MA", "lat": 42.41, "lon": -71.38, "type": "rest_of_state"},
    251: {"name": "Boston, MA", "state": "MA", "lat": 42.36, "lon": -71.06, "type": "metro"},
    260: {"name": "Rest of Michigan", "state": "MI", "lat": 44.31, "lon": -85.60, "type": "rest_of_state"},
    261: {"name": "Detroit, MI", "state": "MI", "lat": 42.33, "lon": -83.05, "type": "metro"},
    262: {"name": "Grand Rapids, MI", "state": "MI", "lat": 42.96, "lon": -85.66, "type": "metro"},
    270: {"name": "Rest of Minnesota", "state": "MN", "lat": 46.73, "lon": -94.69, "type": "rest_of_state"},
    271: {"name": "Minneapolis-St. Paul, MN-WI", "state": "MN", "lat": 44.98, "lon": -93.27, "type": "metro"},
    280: {"name": "Rest of Mississippi", "state": "MS", "lat": 32.35, "lon": -89.40, "type": "rest_of_state"},
    290: {"name": "Rest of Missouri", "state": "MO", "lat": 38.57, "lon": -92.60, "type": "rest_of_state"},
    291: {"name": "St. Louis, MO-IL", "state": "MO", "lat": 38.63, "lon": -90.20, "type": "metro"},
    300: {"name": "Rest of Montana", "state": "MT", "lat": 46.88, "lon": -110.36, "type": "rest_of_state"},
    310: {"name": "Rest of Nebraska", "state": "NE", "lat": 41.49, "lon": -99.90, "type": "rest_of_state"},
    320: {"name": "Rest of Nevada", "state": "NV", "lat": 38.80, "lon": -116.42, "type": "rest_of_state"},
    321: {"name": "Las Vegas, NV", "state": "NV", "lat": 36.17, "lon": -115.14, "type": "metro"},
    330: {"name": "Rest of New Hampshire", "state": "NH", "lat": 43.19, "lon": -71.57, "type": "rest_of_state"},
    340: {"name": "Rest of New Jersey", "state": "NJ", "lat": 40.06, "lon": -74.41, "type": "rest_of_state"},
    350: {"name": "Rest of New Mexico", "state": "NM", "lat": 34.52, "lon": -105.87, "type": "rest_of_state"},
    360: {"name": "Rest of New York", "state": "NY", "lat": 42.17, "lon": -74.95, "type": "rest_of_state"},
    361: {"name": "New York, NY", "state": "NY", "lat": 40.71, "lon": -74.01, "type": "metro"},
    362: {"name": "Buffalo, NY", "state": "NY", "lat": 42.89, "lon": -78.88, "type": "metro"},
    363: {"name": "Rochester, NY", "state": "NY", "lat": 43.16, "lon": -77.61, "type": "metro"},
    370: {"name": "Rest of North Carolina", "state": "NC", "lat": 35.76, "lon": -79.02, "type": "rest_of_state"},
    371: {"name": "Charlotte, NC-SC", "state": "NC", "lat": 35.23, "lon": -80.84, "type": "metro"},
    372: {"name": "Greensboro, NC", "state": "NC", "lat": 36.07, "lon": -79.79, "type": "metro"},
    373: {"name": "Raleigh, NC", "state": "NC", "lat": 35.78, "lon": -78.64, "type": "metro"},
    380: {"name": "Rest of North Dakota", "state": "ND", "lat": 47.55, "lon": -100.34, "type": "rest_of_state"},
    390: {"name": "Rest of Ohio", "state": "OH", "lat": 40.42, "lon": -82.91, "type": "rest_of_state"},
    391: {"name": "Cleveland, OH", "state": "OH", "lat": 41.50, "lon": -81.69, "type": "metro"},
    392: {"name": "Columbus, OH", "state": "OH", "lat": 39.96, "lon": -83.00, "type": "metro"},
    393: {"name": "Cincinnati, OH-KY-IN", "state": "OH", "lat": 39.10, "lon": -84.51, "type": "metro"},
    400: {"name": "Rest of Oklahoma", "state": "OK", "lat": 35.47, "lon": -97.52, "type": "rest_of_state"},
    401: {"name": "Oklahoma City, OK", "state": "OK", "lat": 35.47, "lon": -97.52, "type": "metro"},
    402: {"name": "Tulsa, OK", "state": "OK", "lat": 36.15, "lon": -95.99, "type": "metro"},
    410: {"name": "Rest of Oregon", "state": "OR", "lat": 43.80, "lon": -120.55, "type": "rest_of_state"},
    411: {"name": "Portland, OR-WA", "state": "OR", "lat": 45.52, "lon": -122.68, "type": "metro"},
    420: {"name": "Rest of Pennsylvania", "state": "PA", "lat": 41.20, "lon": -77.19, "type": "rest_of_state"},
    421: {"name": "Philadelphia, PA-NJ-DE-MD", "state": "PA", "lat": 39.95, "lon": -75.17, "type": "metro"},
    422: {"name": "Pittsburgh, PA", "state": "PA", "lat": 40.44, "lon": -80.00, "type": "metro"},
    440: {"name": "Rest of Rhode Island", "state": "RI", "lat": 41.58, "lon": -71.48, "type": "rest_of_state"},
    450: {"name": "Rest of South Carolina", "state": "SC", "lat": 34.00, "lon": -81.03, "type": "rest_of_state"},
    460: {"name": "Rest of South Dakota", "state": "SD", "lat": 43.97, "lon": -99.90, "type": "rest_of_state"},
    470: {"name": "Rest of Tennessee", "state": "TN", "lat": 35.52, "lon": -86.58, "type": "rest_of_state"},
    471: {"name": "Memphis, TN-MS-AR", "state": "TN", "lat": 35.15, "lon": -90.05, "type": "metro"},
    472: {"name": "Nashville, TN", "state": "TN", "lat": 36.16, "lon": -86.78, "type": "metro"},
    480: {"name": "Rest of Texas", "state": "TX", "lat": 31.97, "lon": -99.90, "type": "rest_of_state"},
    481: {"name": "Dallas-Fort Worth, TX", "state": "TX", "lat": 32.78, "lon": -96.80, "type": "metro"},
    482: {"name": "Houston, TX", "state": "TX", "lat": 29.76, "lon": -95.37, "type": "metro"},
    483: {"name": "San Antonio, TX", "state": "TX", "lat": 29.42, "lon": -98.49, "type": "metro"},
    484: {"name": "Austin, TX", "state": "TX", "lat": 30.27, "lon": -97.74, "type": "metro"},
    485: {"name": "El Paso, TX", "state": "TX", "lat": 31.76, "lon": -106.49, "type": "metro"},
    486: {"name": "Laredo, TX", "state": "TX", "lat": 27.51, "lon": -99.51, "type": "metro"},
    490: {"name": "Rest of Utah", "state": "UT", "lat": 39.32, "lon": -111.09, "type": "rest_of_state"},
    491: {"name": "Salt Lake City, UT", "state": "UT", "lat": 40.76, "lon": -111.89, "type": "metro"},
    500: {"name": "Rest of Vermont", "state": "VT", "lat": 44.56, "lon": -72.58, "type": "rest_of_state"},
    510: {"name": "Rest of Virginia", "state": "VA", "lat": 37.43, "lon": -78.66, "type": "rest_of_state"},
    511: {"name": "Virginia Beach-Norfolk, VA", "state": "VA", "lat": 36.85, "lon": -75.98, "type": "metro"},
    512: {"name": "Richmond, VA", "state": "VA", "lat": 37.54, "lon": -77.44, "type": "metro"},
    530: {"name": "Rest of Washington", "state": "WA", "lat": 47.75, "lon": -120.74, "type": "rest_of_state"},
    531: {"name": "Seattle, WA", "state": "WA", "lat": 47.61, "lon": -122.33, "type": "metro"},
    540: {"name": "Rest of West Virginia", "state": "WV", "lat": 38.60, "lon": -80.45, "type": "rest_of_state"},
    550: {"name": "Rest of Wisconsin", "state": "WI", "lat": 44.27, "lon": -89.62, "type": "rest_of_state"},
    551: {"name": "Milwaukee, WI", "state": "WI", "lat": 43.04, "lon": -87.91, "type": "metro"},
    560: {"name": "Rest of Wyoming", "state": "WY", "lat": 43.08, "lon": -107.29, "type": "rest_of_state"},
}
