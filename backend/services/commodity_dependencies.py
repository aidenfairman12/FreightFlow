"""Commodity dependency mappings: finished goods and their precursor materials.

Maps curated finished goods to their upstream input commodities using SCTG2 codes.
Input ratios are approximate weight-based BOM (bill of materials) estimates derived
from industry sources (BLS I-O tables, USITC sector profiles, engineering estimates).

These ratios represent tons of precursor input per ton of finished good output.
"""

from typing import Any

FINISHED_GOODS: dict[str, dict[str, Any]] = {
    "36": {
        "name": "Motor Vehicles",
        "description": "Automobiles, light trucks, and vehicle parts",
        "precursors": [
            {
                "sctg2": "33",
                "name": "Articles of base metal",
                "ratio": 0.45,
                "role": "Body panels, frame, fasteners",
            },
            {
                "sctg2": "24",
                "name": "Plastics and rubber",
                "ratio": 0.18,
                "role": "Tires, dashboards, bumpers, seals",
            },
            {
                "sctg2": "35",
                "name": "Electronic and electrical equipment",
                "ratio": 0.12,
                "role": "Wiring harnesses, ECUs, sensors",
            },
            {
                "sctg2": "20",
                "name": "Basic chemicals",
                "ratio": 0.08,
                "role": "Paints, coatings, adhesives",
            },
            {
                "sctg2": "31",
                "name": "Non-metallic mineral products",
                "ratio": 0.05,
                "role": "Glass windshields, mirrors",
            },
        ],
    },
    "35": {
        "name": "Electronics",
        "description": "Computers, semiconductors, consumer electronics",
        "precursors": [
            {
                "sctg2": "14",
                "name": "Metallic ores",
                "ratio": 0.25,
                "role": "Copper, rare earths, silicon",
            },
            {
                "sctg2": "20",
                "name": "Basic chemicals",
                "ratio": 0.20,
                "role": "Solvents, etching chemicals, resins",
            },
            {
                "sctg2": "24",
                "name": "Plastics and rubber",
                "ratio": 0.30,
                "role": "Housings, connectors, insulation",
            },
            {
                "sctg2": "38",
                "name": "Precision instruments",
                "ratio": 0.15,
                "role": "Sensors, optical components, test equipment",
            },
        ],
    },
    "34": {
        "name": "Machinery",
        "description": "Industrial machinery, engines, turbines",
        "precursors": [
            {
                "sctg2": "33",
                "name": "Articles of base metal",
                "ratio": 0.40,
                "role": "Gears, shafts, housings, bearings",
            },
            {
                "sctg2": "35",
                "name": "Electronic and electrical equipment",
                "ratio": 0.20,
                "role": "Control systems, motors, wiring",
            },
            {
                "sctg2": "24",
                "name": "Plastics and rubber",
                "ratio": 0.15,
                "role": "Seals, hoses, insulation",
            },
            {
                "sctg2": "32",
                "name": "Base metal in primary forms",
                "ratio": 0.15,
                "role": "Steel ingots, aluminum billets",
            },
        ],
    },
    "21": {
        "name": "Pharmaceuticals",
        "description": "Drugs, medicines, biological products",
        "precursors": [
            {
                "sctg2": "20",
                "name": "Basic chemicals",
                "ratio": 0.40,
                "role": "Active pharmaceutical ingredients, solvents",
            },
            {
                "sctg2": "23",
                "name": "Chemical products",
                "ratio": 0.30,
                "role": "Excipients, coatings, intermediates",
            },
            {
                "sctg2": "24",
                "name": "Plastics and rubber",
                "ratio": 0.10,
                "role": "Packaging, blister packs, vials",
            },
        ],
    },
    "39": {
        "name": "Furniture",
        "description": "Household and office furniture, mattresses",
        "precursors": [
            {
                "sctg2": "26",
                "name": "Wood products",
                "ratio": 0.35,
                "role": "Lumber, plywood, particle board",
            },
            {
                "sctg2": "30",
                "name": "Textiles and leather",
                "ratio": 0.25,
                "role": "Upholstery fabrics, leather",
            },
            {
                "sctg2": "33",
                "name": "Articles of base metal",
                "ratio": 0.15,
                "role": "Springs, fasteners, frames",
            },
            {
                "sctg2": "24",
                "name": "Plastics and rubber",
                "ratio": 0.15,
                "role": "Foam, plastic components",
            },
        ],
    },
    "07": {
        "name": "Prepared Foodstuffs",
        "description": "Processed foods, bakery, dairy, beverages",
        "precursors": [
            {
                "sctg2": "02",
                "name": "Cereal grains",
                "ratio": 0.30,
                "role": "Wheat, corn, rice for processing",
            },
            {
                "sctg2": "05",
                "name": "Meat, poultry, fish, seafood",
                "ratio": 0.25,
                "role": "Protein inputs for prepared meals",
            },
            {
                "sctg2": "03",
                "name": "Other agricultural products",
                "ratio": 0.20,
                "role": "Sugar, oils, spices, vegetables",
            },
            {
                "sctg2": "04",
                "name": "Animal feed and products",
                "ratio": 0.10,
                "role": "Feed-grade byproducts, fats, oils",
            },
        ],
    },
}


def get_finished_goods_list() -> list[dict[str, Any]]:
    """Return summary list of finished goods (no precursor detail)."""
    return [
        {
            "sctg2": code,
            "name": fg["name"],
            "description": fg["description"],
            "precursor_count": len(fg["precursors"]),
        }
        for code, fg in FINISHED_GOODS.items()
    ]


def get_precursor_codes(finished_good: str) -> list[str]:
    """Return list of precursor SCTG2 codes for a finished good."""
    fg = FINISHED_GOODS.get(finished_good)
    if not fg:
        return []
    return [p["sctg2"] for p in fg["precursors"]]
