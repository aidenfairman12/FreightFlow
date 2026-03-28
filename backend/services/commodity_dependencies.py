"""Commodity dependency mappings: finished goods and their precursor materials.

Maps curated finished goods to their upstream input commodities using SCTG2 codes.
Input ratios are weight-based BOM (bill of materials) fractions derived from
industry sources.

Motor Vehicles ratios sourced from:
  American Chemistry Council, "Chemistry and Automobiles: Driving the Future"
  (May 2024), Table 5 — Materials Content as a Percent of Total Vehicle Weight (2023).
  Steel 49.4% + Iron 6.2% + Aluminum 11.4% + Other metals 5.5% = 72.5% → SCTG 33: 0.58
  Plastics 9.6% + Synthetic rubber 5.3% + Natural rubber 1.7% = 16.6% → SCTG 24: 0.17
  Fluids/lubricants 4.7% + Coatings 1.0% = 5.7% → SCTG 20: 0.06
  Glass 2.5% → SCTG 31: 0.03
  Electronics (SCTG 35) not weight-reported by ACC; ratio 0.10 retained as
  engineering estimate (electronics are low weight but high supply-chain significance).

Pharmaceutical ratios are engineering approximations; precise public weight-based
BOM data is not available due to proprietary formulation diversity across drug types.

These ratios represent the proportional weight share of each precursor input
relative to total precursor tonnage tracked for that finished good.
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
                "ratio": 0.58,
                # Steel 49.4% + Iron 6.2% + Aluminum 11.4% + Other metals 5.5% = 72.5%
                # Source: ACC Chemistry and Automobiles 2024, Table 5
                "role": "Steel, aluminum, and iron — body, chassis, and structural components",
            },
            {
                "sctg2": "24",
                "name": "Plastics and rubber",
                "ratio": 0.17,
                # Plastics/polymer composites 9.6% + Synthetic rubber 5.3% + Natural rubber 1.7% = 16.6%
                # Source: ACC Chemistry and Automobiles 2024, Table 5
                "role": "Tires, dashboards, bumpers, seals, and polymer composites",
            },
            {
                "sctg2": "35",
                "name": "Electronic and electrical equipment",
                "ratio": 0.10,
                # Weight not reported by ACC (measured by value: $567/vehicle in 2023)
                # Ratio retained as engineering estimate; electronics are low-weight
                # but high supply-chain significance (wiring harnesses, ECUs, sensors)
                "role": "Wiring harnesses, ECUs, sensors, and semiconductors",
            },
            {
                "sctg2": "20",
                "name": "Basic chemicals",
                "ratio": 0.06,
                # Fluids & Lubricants 4.7% + Coatings 1.0% = 5.7%
                # Source: ACC Chemistry and Automobiles 2024, Table 5
                "role": "Paints, coatings, fluids, lubricants, and adhesives",
            },
            {
                "sctg2": "31",
                "name": "Non-metallic mineral products",
                "ratio": 0.03,
                # Glass 2.5%
                # Source: ACC Chemistry and Automobiles 2024, Table 5
                "role": "Glass windshields, windows, and mirrors",
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
