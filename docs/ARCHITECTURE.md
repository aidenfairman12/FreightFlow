# FreightFlow — Architecture

## Overview

FreightFlow is a fully static web application. All supply chain analysis runs at build time via a Python precompute script. The deployed product is a Next.js app served from Vercel — no server, no database, no API at runtime.

```
FAF5 CSVs  ──►  precompute.py  ──►  public/data/*.json  ──►  Next.js (Vercel)
                                                                      │
                                                               Browser loads JSON
                                                               directly at runtime
```

## Data Pipeline (offline, runs once)

```
precompute.py
├── Reads FAF5 CSV freight flow records (~522K rows, 2022)
├── Applies zone remapping (e.g. Chicago IL+IN parts → "Chicago Metro")
├── Filters flows by precursor commodity codes per finished good
├── Aggregates tonnage by source zone, calculates concentration metrics
├── Computes disruption impact and cost estimates
├── Scores Critical Nodes across all supply chains
└── Writes JSON to frontend/public/data/
    ├── products.json           Finished goods catalogue
    ├── zones.json              132 FAF zone centroids
    ├── risk_scores.json        Concentration risk per product
    ├── supply_chain_XX.json    Full precursor detail per product (one file per SCTG code)
    └── critical_nodes.json     Top 30 zones by cross-supply-chain systemic score
```

## Frontend (deployed)

```
Next.js 14 (App Router, TypeScript)
├── /                       Risk Overview — concentration risk cards
├── /explorer               Supply Chain Explorer — map + disruption simulator
└── /critical-nodes         Critical Nodes — systemic risk map + ranked list

Runtime data flow:
  Page load → fetch /public/data/*.json → client-side computation → render
  Disruption simulation: pure client-side, no network request
```

## Key Design Decisions

**Static over dynamic.** FAF5 data updates annually. Running a live database and API for data that changes once a year adds complexity with no benefit. Pre-computing everything at build time gives instant load times, zero infrastructure cost, and no failure modes at runtime.

**Normalised flow line weights per precursor group.** Global normalisation made diffuse supply chains (pharmaceuticals) look identical to concentrated ones (steel). Normalising within each precursor group means the dominant source always gets the thickest line, making concentration visually obvious regardless of product.

**Chicago metro aggregation.** FAF5 splits Chicago across Illinois and Indiana zone IDs. Left uncorrected, Chicago appeared as two separate locations. Zone 171 (IL part) is remapped to 181 (IN part) pre-aggregation, and zone 181 is relabelled "Chicago Metro".

**Intra-zone exclusion in Critical Nodes.** Without this, large industrial zones score highly simply because they consume their own output — which is not a supply chain vulnerability.
