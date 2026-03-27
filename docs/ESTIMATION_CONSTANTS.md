# Estimation Constants & Assumptions

Every calculated metric in FreightFlow relies on assumptions and estimated values. This document catalogs all of them so they can be audited, calibrated, and improved.

**Rule:** When adding a new estimation constant anywhere in the codebase, add it to this document with its value, rationale, and the file where it lives.

---

## Freight Cost Rates (USD per ton-mile)

| Constant | Value | File | Source |
|----------|-------|------|--------|
| Truck cost/ton-mile | $0.12 | `freight_cost_model.py` | ATRI Operational Costs of Trucking 2023 |
| Rail cost/ton-mile | $0.035 | `freight_cost_model.py` | AAR Railroad Facts 2023 |
| Water cost/ton-mile | $0.015 | `freight_cost_model.py` | Army Corps of Engineers |
| Air cost/ton-mile | $0.95 | `freight_cost_model.py` | BTS Air Cargo Statistics |
| Intermodal cost/ton-mile | $0.07 | `freight_cost_model.py` | JOC/IHS Markit |
| Pipeline cost/ton-mile | $0.02 | `freight_cost_model.py` | EIA/BTS estimate |

## Cost Component Breakdowns (% of total cost)

### Truck (Mode 1)
| Component | Share | Source |
|-----------|-------|--------|
| Fuel | 38% | ATRI 2023 |
| Labor | 35% | ATRI 2023 |
| Equipment | 12% | ATRI 2023 |
| Insurance | 5% | ATRI 2023 |
| Tolls/Fees | 5% | ATRI 2023 |
| Other | 5% | ATRI 2023 |

### Rail (Mode 2)
| Component | Share | Source |
|-----------|-------|--------|
| Fuel | 18% | AAR 2023 |
| Labor | 25% | AAR 2023 |
| Equipment | 30% | AAR 2023 |
| Insurance | 3% | AAR 2023 |
| Tolls/Fees | 4% | AAR 2023 |
| Other | 20% | AAR 2023 |

### Water (Mode 3)
| Component | Share | Source |
|-----------|-------|--------|
| Fuel | 25% | Army Corps estimate |
| Labor | 30% | Army Corps estimate |
| Equipment | 25% | Army Corps estimate |
| Insurance | 5% | Industry average |
| Tolls/Fees | 5% | Lock/port fees |
| Other | 10% | Industry average |

### Air (Mode 4)
| Component | Share | Source |
|-----------|-------|--------|
| Fuel | 30% | BTS Air Cargo |
| Labor | 25% | BTS Air Cargo |
| Equipment | 20% | BTS Air Cargo |
| Insurance | 5% | Industry average |
| Tolls/Fees | 10% | Airport/ATC fees |
| Other | 10% | Industry average |

### Intermodal (Mode 5)
| Component | Share | Source |
|-----------|-------|--------|
| Fuel | 25% | JOC/IHS Markit |
| Labor | 28% | JOC/IHS Markit |
| Equipment | 22% | JOC/IHS Markit |
| Insurance | 4% | Industry average |
| Tolls/Fees | 6% | Drayage + rail fees |
| Other | 15% | Industry average |

### Pipeline (Mode 6)
| Component | Share | Source |
|-----------|-------|--------|
| Fuel | 15% | EIA/BTS |
| Labor | 15% | EIA/BTS |
| Equipment | 40% | EIA/BTS (capital-intensive) |
| Insurance | 5% | Industry average |
| Tolls/Fees | 5% | Regulatory fees |
| Other | 20% | Maintenance/overhead |

## Diesel Price Sensitivity

| Constant | Value | File | Rationale |
|----------|-------|------|-----------|
| Diesel baseline price | $3.85/gal | `freight_cost_model.py` | Approximate 2022 average US on-highway diesel (EIA). When diesel is at this price, base rates apply. |
| Fuel share scaling | Linear per mode | `freight_cost_model.py` | Only the fuel portion of cost scales with diesel price. Truck (38% fuel) is most sensitive; rail (18%) is moderately sensitive. `adjusted = base_rate × ((1 - fuel_share) + fuel_share × diesel_ratio)` |

## Commodity Dependency BOM Ratios (tons input per ton output)

These are approximate weight-based bill-of-materials ratios for the supply chain explorer.
Sources: BLS Input-Output tables, USITC sector profiles, engineering estimates.

| Finished Good | Precursor | Ratio | File | Rationale |
|---------------|-----------|-------|------|-----------|
| Motor Vehicles (36) | Articles of base metal (33) | 0.45 | `commodity_dependencies.py` | Body panels, frame, fasteners — steel is ~45% of vehicle weight |
| Motor Vehicles (36) | Plastics and rubber (24) | 0.18 | `commodity_dependencies.py` | Tires, dashboards, bumpers, seals |
| Motor Vehicles (36) | Electronics (35) | 0.12 | `commodity_dependencies.py` | Wiring harnesses, ECUs, sensors |
| Motor Vehicles (36) | Basic chemicals (20) | 0.08 | `commodity_dependencies.py` | Paints, coatings, adhesives |
| Motor Vehicles (36) | Non-metallic minerals (31) | 0.05 | `commodity_dependencies.py` | Glass windshields, mirrors |
| Electronics (35) | Metallic ores (14) | 0.25 | `commodity_dependencies.py` | Copper, rare earths, silicon |
| Electronics (35) | Basic chemicals (20) | 0.20 | `commodity_dependencies.py` | Solvents, etching chemicals, resins |
| Electronics (35) | Plastics and rubber (24) | 0.30 | `commodity_dependencies.py` | Housings, connectors, insulation |
| Electronics (35) | Precision instruments (38) | 0.15 | `commodity_dependencies.py` | Sensors, optical components |
| Machinery (34) | Articles of base metal (33) | 0.40 | `commodity_dependencies.py` | Gears, shafts, housings, bearings |
| Machinery (34) | Electronics (35) | 0.20 | `commodity_dependencies.py` | Control systems, motors, wiring |
| Machinery (34) | Plastics and rubber (24) | 0.15 | `commodity_dependencies.py` | Seals, hoses, insulation |
| Machinery (34) | Base metal primary forms (32) | 0.15 | `commodity_dependencies.py` | Steel ingots, aluminum billets |
| Pharmaceuticals (21) | Basic chemicals (20) | 0.40 | `commodity_dependencies.py` | Active pharmaceutical ingredients |
| Pharmaceuticals (21) | Chemical products (23) | 0.30 | `commodity_dependencies.py` | Excipients, coatings, intermediates |
| Pharmaceuticals (21) | Plastics and rubber (24) | 0.10 | `commodity_dependencies.py` | Packaging, vials |
| Furniture (39) | Wood products (26) | 0.35 | `commodity_dependencies.py` | Lumber, plywood, particle board |
| Furniture (39) | Textiles and leather (30) | 0.25 | `commodity_dependencies.py` | Upholstery fabrics |
| Furniture (39) | Articles of base metal (33) | 0.15 | `commodity_dependencies.py` | Springs, fasteners, frames |
| Furniture (39) | Plastics and rubber (24) | 0.15 | `commodity_dependencies.py` | Foam, plastic components |
| Prepared Foodstuffs (07) | Cereal grains (02) | 0.30 | `commodity_dependencies.py` | Wheat, corn, rice |
| Prepared Foodstuffs (07) | Meat/poultry/fish (05) | 0.25 | `commodity_dependencies.py` | Protein inputs |
| Prepared Foodstuffs (07) | Other agricultural (03) | 0.20 | `commodity_dependencies.py` | Sugar, oils, spices |
| Prepared Foodstuffs (07) | Animal feed (04) | 0.10 | `commodity_dependencies.py` | Feed-grade byproducts |

## Corridor Definitions

| Corridor | Origin Zone | Dest Zone | File | Rationale |
|----------|-------------|-----------|------|-----------|
| LA → Chicago | 61 | 171 | `corridor_definitions.py` | Largest US freight corridor. Pacific imports → Midwest distribution. |
| Houston → NYC | 482 | 361 | `corridor_definitions.py` | Gulf Coast petrochemical/industrial → Northeast consumer market. |
| Seattle → Dallas | 531 | 481 | `corridor_definitions.py` | Pacific NW tech/timber → Sun Belt growth market. |

## Economic Factor Fallbacks

These values are used only when the ETL pipeline has not yet fetched real data.

| Constant | Value | File | Rationale |
|----------|-------|------|-----------|
| Diesel price | (from EIA API) | `economic_etl.py` | EIA on-highway diesel series EMD_EPD2D_PTE_NUS_DPG. No hardcoded fallback — fetched from API. |
| Brent crude | (from EIA API) | `economic_etl.py` | EIA Europe Brent series. No hardcoded fallback. |

---

## How to Update This Document

When adding a new estimated or hardcoded value:

1. Add a row to the appropriate section above
2. Include: what the constant is, its value, which file it lives in, and **why** that value was chosen
3. If the value came from a specific source (e.g., "ATRI 2023"), cite it
4. If the value is a known simplification, note what would improve it

When calibrating a value against real data:
1. Update the value in code
2. Update this document
3. Note the calibration source and date in the rationale
